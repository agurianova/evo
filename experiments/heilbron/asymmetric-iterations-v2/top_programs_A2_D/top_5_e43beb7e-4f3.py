import numpy as np
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle


def entrypoint():
    base_seed = 42
    A, B, C = get_unit_triangle()

    def to_barycentric(p):
        u = ((B[1] - C[1]) * (p[0] - C[0]) + (C[0] - B[0]) * (p[1] - C[1])) / 2.0
        v = ((C[1] - A[1]) * (p[0] - C[0]) + (A[0] - C[0]) * (p[1] - C[1])) / 2.0
        w = 1 - u - v
        return np.array([u, v, w])

    def to_cartesian(bary):
        u, v, w = bary
        return u * A + v * B + w * C

    def point_to_line_distance(p, a, b):
        ap = p - a
        ab = b - a
        base_length = np.linalg.norm(ab)
        if base_length < 1e-10:
            return 0.0
        area = 0.5 * abs(ap[0] * ab[1] - ap[1] * ab[0])
        return 2 * area / base_length

    def triangle_aspect_ratio(p0, p1, p2):
        """Calculate aspect ratio (longest side / shortest side) of a triangle"""
        d1 = np.linalg.norm(p0 - p1)
        d2 = np.linalg.norm(p1 - p2)
        d3 = np.linalg.norm(p2 - p0)
        sides = sorted([d1, d2, d3])
        return sides[2] / max(sides[0], 1e-10)  # Avoid division by zero

    def get_min_triplet(pts):
        n = pts.shape[0]
        min_area = float('inf')
        min_triplet = (0, 1, 2)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    p1, p2, p3 = pts[i], pts[j], pts[k]
                    area = 0.5 * abs(
                        (p2[0] - p1[0]) * (p3[1] - p1[1]) - 
                        (p3[0] - p1[0]) * (p2[1] - p1[1])
                    )
                    if area < min_area:
                        min_area = area
                        min_triplet = (i, j, k)
        return min_triplet, min_area

    def estimate_gradient(points, idx, base_score, step=0.01):
        """Estimate gradient direction for improvement at given point"""
        current = points[idx]
        directions = [
            np.array([1, 0]), np.array([-1, 0]),
            np.array([0, 1]), np.array([0, -1]),
            np.array([1, 1]), np.array([-1, -1]),
            np.array([0.707, 0.707]), np.array([-0.707, 0.707]),
            np.array([0.707, -0.707]), np.array([-0.707, -0.707]),
            np.array([1, 0.5]), np.array([0.5, 1])
        ]
        
        best_dir = None
        best_improvement = 0
        
        for d in directions:
            candidate = current + d * step
            if is_inside_triangle(candidate, A, B, C):
                test_points = points.copy()
                test_points[idx] = candidate
                score = get_smallest_triangle_area(test_points)
                improvement = score - base_score
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_dir = d
        
        if best_dir is not None and np.linalg.norm(best_dir) > 0:
            return best_dir / np.linalg.norm(best_dir)
        return None

    def optimize_smallest_triangle(points, max_iter=150, base_step_size=0.015):
        """Optimize smallest triangle with multiple strategies"""
        points = points.copy()
        best_points = points.copy()
        best_score = get_smallest_triangle_area(points)
        
        # Calculate overall aspect ratio for adaptive step sizing
        current_min_area = best_score
        n = points.shape[0]
        aspect_ratios = []
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    area = 0.5 * abs(
                        (points[j, 0] - points[i, 0]) * (points[k, 1] - points[i, 1]) - 
                        (points[k, 0] - points[i, 0]) * (points[j, 1] - points[i, 1])
                    )
                    # Only consider triangles within 10% of current minimum area
                    if area <= 1.1 * current_min_area:
                        aspect_ratios.append(triangle_aspect_ratio(points[i], points[j], points[k]))
        overall_aspect = np.mean(aspect_ratios) if aspect_ratios else 1.0
        
        # Adaptive step size based on current score and triangle flatness
        current_score = best_score
        step_size = base_step_size * (1.0 / max(overall_aspect, 1.0)) * (0.1 + 0.9 * (current_score / 0.0365))
        
        for iter_count in range(max_iter):
            # Find the smallest triangle
            min_triplet, min_area = get_min_triplet(points)
            p0, p1, p2 = points[min_triplet[0]], points[min_triplet[1]], points[min_triplet[2]]
            
            # Calculate aspect ratio to determine strategy priority
            aspect_ratio = triangle_aspect_ratio(p0, p1, p2)
            
            # Strategy priority based on aspect ratio
            strategy_order = []
            if aspect_ratio < 1.5:
                strategy_order = ["outward", "rotation", "gradient"]
            elif aspect_ratio < 2.5:
                strategy_order = ["rotation", "outward", "gradient"]
            else:
                strategy_order = ["gradient", "rotation", "outward"]

            # Calculate distances to opposite edges
            d0 = point_to_line_distance(p0, p1, p2)
            d1 = point_to_line_distance(p1, p0, p2)
            d2 = point_to_line_distance(p2, p0, p1)
            dists = [d0, d1, d2]
            
            improved = False
            improvement_magnitude = 0.0
            
            # Try strategies in priority order
            for strategy in strategy_order:
                if strategy == "outward":
                    # Strategy 1: Move all points outward simultaneously
                    new_points = points.copy()
                    move_vectors = []
                    
                    for idx_in_triplet, idx in enumerate(min_triplet):
                        edge_idx1, edge_idx2 = min_triplet[(idx_in_triplet+1)%3], min_triplet[(idx_in_triplet+2)%3]
                        edge_p1, edge_p2 = points[edge_idx1], points[edge_idx2]
                        
                        edge_vec = edge_p2 - edge_p1
                        perp_vec = np.array([-edge_vec[1], edge_vec[0]])
                        
                        if np.linalg.norm(perp_vec) > 1e-10:
                            perp_vec = perp_vec / np.linalg.norm(perp_vec)
                            # Scale movement by distance to edge (smaller distance = larger movement)
                            scale = 1.0 - (dists[idx_in_triplet] / sum(dists))
                            move_vec = perp_vec * step_size * (0.5 + 1.5 * scale)
                            move_vectors.append((idx, move_vec))

                    # Try coordinated movement of all three points
                    candidate_points = points.copy()
                    valid_move = True
                    for idx, move_vec in move_vectors:
                        candidate = points[idx] + move_vec
                        if not is_inside_triangle(candidate, A, B, C):
                            valid_move = False
                            break
                        candidate_points[idx] = candidate
                        
                    if valid_move:
                        new_score = get_smallest_triangle_area(candidate_points)
                        if new_score > best_score:
                            improvement_magnitude = new_score - best_score
                            best_score = new_score
                            best_points = candidate_points.copy()
                            points = candidate_points.copy()
                            improved = True
                            break

                elif strategy == "rotation":
                    # Strategy 2: Rotation around centroid
                    centroid = (p0 + p1 + p2) / 3.0
                    # Adaptive rotation angle based on aspect ratio
                    angle = 0.03 * (2.5 / max(aspect_ratio, 1.0))
                    
                    candidate_points = points.copy()
                    valid_move = True
                    for idx in min_triplet:
                        # Vector from centroid to point
                        vec = points[idx] - centroid
                        # Rotate
                        rotated = np.array([
                            vec[0] * np.cos(angle) - vec[1] * np.sin(angle),
                            vec[0] * np.sin(angle) + vec[1] * np.cos(angle)
                        ])
                        candidate = centroid + rotated
                        
                        if not is_inside_triangle(candidate, A, B, C):
                            valid_move = False
                            break
                        candidate_points[idx] = candidate

                    if valid_move:
                        new_score = get_smallest_triangle_area(candidate_points)
                        if new_score > best_score:
                            improvement_magnitude = new_score - best_score
                            best_score = new_score
                            best_points = candidate_points.copy()
                            points = candidate_points.copy()
                            improved = True
                            break

                elif strategy == "gradient":
                    # Strategy 3: Gradient-based movement
                    for idx in min_triplet:
                        grad = estimate_gradient(points, idx, best_score, step=step_size)
                        if grad is not None:
                            candidate_points = points.copy()
                            candidate = points[idx] + grad * step_size
                            
                            if is_inside_triangle(candidate, A, B, C):
                                candidate_points[idx] = candidate
                                new_score = get_smallest_triangle_area(candidate_points)
                                
                                if new_score > best_score:
                                    improvement_magnitude = new_score - best_score
                                    best_score = new_score
                                    best_points = candidate_points.copy()
                                    points = candidate_points.copy()
                                    improved = True
                                    break
                    if improved:
                        break

            # Adjust step size based on success, proportional to improvement magnitude
            if improved:
                # Scale adaptation by improvement magnitude with diminishing returns
                improvement_factor = 1.0 + 0.05 * min(1.0, np.sqrt(improvement_magnitude))
                step_size = min(step_size * improvement_factor, 0.02)
            else:
                # Reduce step size more when no improvement
                step_size *= 0.9
                if step_size < 1e-5:
                    break

        return best_points

    def is_symmetric(points, threshold=0.01):
        """Detect if configuration has mirror symmetry across vertical midline"""
        mid_x = (A[0] + B[0]) / 2.0
        for p in points:
            if abs(p[0] - mid_x) > threshold:
                mirrored = np.array([2 * mid_x - p[0], p[1]])
                if not any(np.linalg.norm(mirrored - q) < threshold for q in points):
                    return False
        return True

    def detect_rows(points, y_threshold=0.02):
        """Identify horizontal rows in the point configuration"""
        # Sort points by y-coordinate
        sorted_indices = np.argsort(points[:, 1])
        sorted_points = points[sorted_indices]
        
        rows = []
        current_row = [0]  # Start with first point
        
        for i in range(1, len(sorted_points)):
            # Check if this point is in the same row as previous
            if abs(sorted_points[i, 1] - sorted_points[current_row[-1], 1]) < y_threshold:
                current_row.append(i)
            else:
                if len(current_row) > 1:  # Only consider rows with multiple points
                    rows.append([sorted_indices[j] for j in current_row])
                current_row = [i]
        
        if len(current_row) > 1:
            rows.append([sorted_indices[j] for j in current_row])
        
        return rows

    def disrupt_row_patterns(points, y_threshold=0.02, move_distance=0.02):
        """Identify and disrupt row-based patterns by moving points vertically"""
        rows = detect_rows(points, y_threshold)
        
        if not rows:
            return points.copy()
        
        points = points.copy()
        for row in rows:
            if len(row) > 1:  # Only disrupt rows with multiple points
                # Randomly select a point in the row to move
                idx = np.random.choice(row)
                # Move it vertically (break the row pattern)
                direction = 1 if np.random.random() > 0.5 else -1
                points[idx, 1] += direction * move_distance  # Small vertical move
                # Ensure point stays inside triangle
                if not is_inside_triangle(points[idx], A, B, C):
                    points[idx, 1] -= direction * move_distance  # Revert if outside
        
        return points

    def generate_sobol_points(n, seed=42):
        """Generate points using Sobol sequence for structured exploration"""
        try:
            from scipy.stats import qmc
            sampler = qmc.Sobol(d=2, scramble=False, seed=seed)
            sobol_points = sampler.random(n=n)
            # Convert to barycentric coordinates
            barycentric_points = []
            for u, v in sobol_points:
                s = 1 - np.sqrt(u)
                t = v * (1 - s)
                w = 1 - s - t
                barycentric_points.append(np.array([s, t, w]))
            return np.array(barycentric_points)
        except ImportError:
            # Fallback to uniform random if scipy not available
            return np.random.dirichlet(alpha=[1, 1, 1], size=n)

    def multi_point_move(points, indices, step_size, rng, A, B, C):
        """Perform coordinated move on multiple points"""
        candidate = points.copy()
        valid_move = True
        for idx in indices:
            angle = rng.uniform(0, 2 * np.pi)
            dx = step_size * np.cos(angle)
            dy = step_size * np.sin(angle)
            candidate_point = points[idx] + np.array([dx, dy])
            if not is_inside_triangle(candidate_point, A, B, C):
                valid_move = False
                break
            candidate[idx] = candidate_point
        return candidate, valid_move

    def improve(points):
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)

        # Calculate theoretical maximum for adaptive parameter tuning
        theoretical_max = 0.0365
        
        # Detect symmetry in initial configuration
        symmetric = is_symmetric(points)

        # Prioritize hard configurations with greater improvement potential
        initial_score = best_score_overall
        restart_count = max(5, 5 + int(15 * (initial_score / 0.0365)))

        for restart in range(restart_count):
            rng = np.random.default_rng(seed=base_seed + restart)
            current = points.copy()
            current_score = get_smallest_triangle_area(current)
            best_restart = current.copy()
            best_score_restart = current_score

            # Adaptive initial temperature based on current score
            initial_temp = max(0.1 * current_score, 0.003)
            step_size = 0.01
            recent_accepts = 0
            acceptance_window = 50

            # Use Sobol sequence for structured exploration based on initial score
            if initial_score < 0.025:
                sobol_bary = generate_sobol_points(11, seed=base_seed + restart)
                for i in range(11):
                    current[i] = to_cartesian(sobol_bary[i])
                current_score = get_smallest_triangle_area(current)
                if current_score > best_score_restart:
                    best_score_restart = current_score
                    best_restart = current.copy()

            # Track improvement rate for temperature schedule
            improvement_history = []
            last_score = current_score
            last_improvement_iter = 0

            # Symmetry-aware exploration
            symmetry_maintenance_prob = 0.8 * (current_score / theoretical_max) if symmetric else 0.0
            stall_threshold = 5  # Reduced from 20 to address symmetry_breaking_delay

            for i_iter in range(2500):
                # Track if we've had recent improvements
                if current_score > last_score:
                    last_improvement_iter = i_iter

                # Check for symmetry breaking opportunity only when improvement stalls
                if symmetric and (i_iter - last_improvement_iter > stall_threshold):
                    # Break symmetry with targeted move
                    idx = rng.integers(0, 11)
                    old_point = current[idx].copy()
                    bary = to_barycentric(old_point)
                    # Larger perturbation to break symmetry (reduced concentration from 0.5 to 0.3)
                    concentration = 0.3
                    perturbation = rng.dirichlet(alpha=[concentration] * 3)
                    new_bary = bary * 0.7 + perturbation * 0.3
                    new_bary = np.maximum(new_bary, 1e-10)
                    new_bary /= new_bary.sum()
                    new_point = to_cartesian(new_bary)
                    current[idx] = new_point
                    
                    new_score = get_smallest_triangle_area(current)
                    if new_score > 0 and is_inside_triangle(current, A, B, C):
                        current_score = new_score
                        if new_score > best_score_restart:
                            best_score_restart = new_score
                            best_restart = current.copy()
                        # Record improvement for adaptive cooling
                        improvement = new_score - last_score
                        improvement_history.append(improvement)
                        if len(improvement_history) > 100:
                            improvement_history.pop(0)
                        last_score = new_score
                    else:
                        current[idx] = old_point
                        improvement_history.append(0.0)
                        if len(improvement_history) > 100:
                            improvement_history.pop(0)
                    continue

                # Adaptive exploration rate based on progress
                progress_ratio = current_score / theoretical_max
                exploration_rate = max(0.03, 0.35 * (0.96 ** (i_iter / 100)) * (1.0 - progress_ratio * 0.7))
                
                # Use multi-point moves in earlier stages for coordinated optimization
                if i_iter > 200 and rng.random() < 0.3:
                    num_points = rng.choice([2, 3])
                    indices = rng.choice(11, size=num_points, replace=False)
                    candidate, valid = multi_point_move(current, indices, step_size, rng, A, B, C)
                    if valid:
                        new_score = get_smallest_triangle_area(candidate)
                        if new_score > current_score:
                            current = candidate
                            current_score = new_score
                            if new_score > best_score_restart:
                                best_score_restart = new_score
                                best_restart = current.copy()
                            # Record improvement
                            improvement = new_score - last_score
                            improvement_history.append(improvement)
                            if len(improvement_history) > 100:
                                improvement_history.pop(0)
                            last_score = new_score
                        else:
                            improvement_history.append(0.0)
                            if len(improvement_history) > 100:
                                improvement_history.pop(0)
                    continue

                if rng.random() < exploration_rate:
                    # Focused exploration on smallest triangle with multi-point approach
                    min_triplet, min_area_val = get_min_triplet(current)
                    p0, p1, p2 = current[min_triplet[0]], current[min_triplet[1]], current[min_triplet[2]]
                    d0 = point_to_line_distance(p0, p1, p2)
                    d1 = point_to_line_distance(p1, p0, p2)
                    d2 = point_to_line_distance(p2, p0, p1)
                    dists = [d0, d1, d2]
                    
                    # Choose which points to focus on based on distances
                    focus_indices = []
                    for i, d in enumerate(dists):
                        # Focus more on points closer to their opposite edges
                        if d < 0.7 * np.mean(dists):
                            focus_indices.append(min_triplet[i])
                    
                    if not focus_indices:
                        focus_indices = [min_triplet[np.argmin(dists)]]
                    
                    idx = rng.choice(focus_indices)
                    focus_step_size = step_size * (1.2 + 0.8 * (1.0 - dists[focus_indices.index(idx)] / sum(dists)))
                    current_score = min_area_val
                else:
                    # Random exploration mode
                    focus_step_size = step_size
                    idx = rng.integers(0, 11)

                old_point = current[idx].copy()
                bary = to_barycentric(old_point)

                # Dirichlet distribution sampling with reduced concentration and added noise
                concentration = 1.0 + 2.0 * progress_ratio + 0.5 * rng.random()
                perturbation = rng.dirichlet(alpha=[concentration] * 3)
                new_bary = bary * (1 - focus_step_size) + perturbation * focus_step_size
                # Ensure numerical stability
                new_bary = np.maximum(new_bary, 1e-10)
                new_bary /= new_bary.sum()

                new_point = to_cartesian(new_bary)
                current[idx] = new_point
                new_score = get_smallest_triangle_area(current)

                delta = new_score - current_score
                if delta > 0:
                    accepted = True
                else:
                    # Adaptive temperature schedule with progress-based cooling
                    if len(improvement_history) > 20:
                        avg_improvement = np.mean(improvement_history[-20:])
                        # If progress is slow, cool slower; if progress is good, cool faster
                        cooling_factor = 0.99 if avg_improvement < 0.0001 * 0.0365 else 0.98
                        T = max(initial_temp * (cooling_factor ** i_iter), 1e-10)
                    else:
                        T = max(initial_temp * (0.995 ** i_iter), 1e-10)
                    
                    if T < 1e-10:
                        accepted = False
                    else:
                        accepted = (rng.random() < np.exp(delta / T))

                if accepted:
                    current_score = new_score
                    recent_accepts += 1
                    
                    # Track improvement for adaptive cooling
                    improvement = new_score - last_score
                    improvement_history.append(improvement)
                    if len(improvement_history) > 100:
                        improvement_history.pop(0)
                    last_score = new_score
                    
                    if new_score > best_score_restart:
                        best_score_restart = new_score
                        best_restart = current.copy()
                else:
                    current[idx] = old_point
                    improvement_history.append(0.0)
                    if len(improvement_history) > 100:
                        improvement_history.pop(0)

                # Update progress ratio for adaptive parameters
                progress_ratio = current_score / theoretical_max

                # Make acceptance thresholds responsive to local improvement rate
                if len(improvement_history) > 30:
                    recent_improvements = improvement_history[-30:]
                    improvement_rate = np.mean(recent_improvements) / max(current_score, 1e-10)
                    # Adjust thresholds based on improvement rate
                    acceptance_high_threshold = max(0.25, min(0.45, 0.35 + 0.1 * improvement_rate))
                    acceptance_low_threshold = max(0.15, min(0.35, 0.25 + 0.05 * improvement_rate))
                else:
                    acceptance_high_threshold = 0.35 + 0.15 * progress_ratio
                    acceptance_low_threshold = 0.25 + 0.1 * progress_ratio

                if (i_iter + 1) % acceptance_window == 0:
                    acceptance_rate = recent_accepts / acceptance_window
                    # Adaptive thresholds based on progress
                    if acceptance_rate > acceptance_high_threshold:
                        step_size = min(step_size * 1.08, 0.2)
                    elif acceptance_rate < acceptance_low_threshold:
                        step_size = max(step_size * 0.92, 1e-4)
                    recent_accepts = 0

            if best_score_restart > best_score_overall:
                best_score_overall = best_score_restart
                best_overall = best_restart.copy()

        # Apply Constructor-specific pattern disruption for row-based configurations
        if initial_score > 0.01:  # Lowered from 0.015 to address row_disruption_threshold
            pattern_disrupted = disrupt_row_patterns(best_overall.copy())
            pattern_score = get_smallest_triangle_area(pattern_disrupted)
            if pattern_score > best_score_overall:
                best_score_overall = pattern_score
                best_overall = pattern_disrupted

        # Apply enhanced specialized optimization on the smallest triangle
        # Calculate overall aspect ratio for adaptive step sizing
        n = best_overall.shape[0]
        aspect_ratios = []
        current_min_area = get_smallest_triangle_area(best_overall)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    area = 0.5 * abs(
                        (best_overall[j, 0] - best_overall[i, 0]) * (best_overall[k, 1] - best_overall[i, 1]) - 
                        (best_overall[k, 0] - best_overall[i, 0]) * (best_overall[j, 1] - best_overall[i, 1])
                    )
                    # Only consider triangles within 10% of current minimum area
                    if area <= 1.1 * current_min_area:
                        aspect_ratios.append(triangle_aspect_ratio(best_overall[i], best_overall[j], best_overall[k]))
        overall_aspect = np.mean(aspect_ratios) if aspect_ratios else 1.0
        
        # Adaptive step size based on triangle flatness
        adaptive_step = 0.015 * (1.0 / max(overall_aspect, 1.0))
        final_points = optimize_smallest_triangle(best_overall.copy(), base_step_size=adaptive_step)
        final_score = get_smallest_triangle_area(final_points)
        if final_score > best_score_overall:
            best_overall = final_points

        return best_overall

    return improve