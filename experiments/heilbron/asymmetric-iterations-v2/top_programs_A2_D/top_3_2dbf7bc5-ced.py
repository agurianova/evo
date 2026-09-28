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
        """Estimate gradient direction for improvement using geometry-aware directions"""
        current = points[idx]
        # Get the smallest triangle containing this point if it's part of one
        min_triplet, min_area = get_min_triplet(points)
        is_in_min_triplet = idx in min_triplet
        
        directions = []
        
        if is_in_min_triplet:
            # Get the other two points in the smallest triangle
            other_indices = [i for i in min_triplet if i != idx]
            p1, p2 = points[other_indices[0]], points[other_indices[1]]
            
            # Direction perpendicular to the opposite edge
            edge_vec = p2 - p1
            perp_vec = np.array([-edge_vec[1], edge_vec[0]])
            if np.linalg.norm(perp_vec) > 1e-10:
                perp_vec = perp_vec / np.linalg.norm(perp_vec)
                directions.append(perp_vec)
                directions.append(-perp_vec)
            
            # Direction toward centroid of the triangle
            centroid = (points[min_triplet[0]] + points[min_triplet[1]] + points[min_triplet[2]]) / 3.0
            centroid_vec = centroid - current
            if np.linalg.norm(centroid_vec) > 1e-10:
                centroid_vec = centroid_vec / np.linalg.norm(centroid_vec)
                directions.append(centroid_vec)
        
        # Add some random exploration directions
        for _ in range(8):
            angle = np.random.uniform(0, 2 * np.pi)
            directions.append(np.array([np.cos(angle), np.sin(angle)]))
        
        # Add cardinal directions as fallback
        directions.extend([
            np.array([1, 0]), np.array([-1, 0]),
            np.array([0, 1]), np.array([0, -1])
        ])
        
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

    def optimize_smallest_triangle(points, max_iter=150, base_step_size=0.005):
        """Optimize smallest triangle with multiple strategies"""
        points = points.copy()
        best_points = points.copy()
        best_score = get_smallest_triangle_area(points)
        
        # Adaptive step size based on current score
        current_score = best_score
        step_size = base_step_size * (0.1 + 0.9 * (current_score / 0.0365))
        
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

    def improve(points):
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)

        # Calculate theoretical maximum for adaptive parameter tuning
        theoretical_max = 0.0365
        
        # Detect symmetry in initial configuration
        symmetric = is_symmetric(points)

        # FIX: Inverted restart allocation to prioritize configurations with greater improvement potential
        initial_score = best_score_overall
        # Previously: restart_count = max(5, 5 + int(15 * (initial_score / 0.0365)))
        # Now allocating more restarts to configurations that need improvement
        restart_count = max(5, 5 + int(15 * (1.0 - initial_score / 0.0365)))

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

            # Adaptive acceptance thresholds based on progress
            progress_ratio = current_score / theoretical_max
            acceptance_high_threshold = 0.35 + 0.15 * progress_ratio
            acceptance_low_threshold = 0.25 + 0.1 * progress_ratio

            # Track improvement rate for temperature schedule
            improvement_history = []
            last_score = current_score
            last_improvement_iter = 0

            # CHANGED: Adaptive symmetry breaking threshold based on improvement history
            # Calculate recent improvement rate for adaptive exploration
            if len(improvement_history) > 50:
                improvement_std = np.std(improvement_history[-50:])
                # If improvements are very small, break symmetry sooner
                stall_threshold = max(5, int(30 * (1.0 - min(0.95, improvement_std / (1e-6 + current_score)))))
            else:
                stall_threshold = 20

            # CHANGED: More aggressive symmetry breaking for near-symmetric configurations
            symmetry_maintenance_prob = 0.5 * progress_ratio  # Reduced from 0.8

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
                    # FIX: Increased perturbation magnitude from 0.3 to 0.45
                    concentration = 0.5  # More diffuse for symmetry breaking
                    perturbation = rng.dirichlet(alpha=[concentration] * 3)
                    new_bary = bary * 0.55 + perturbation * 0.45
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

                # FIX: Implemented progress-based adaptive cooling schedule
                # Track improvement rate for cooling adjustments
                cooling_factor = 0.985  # Default cooling factor
                if len(improvement_history) > 20:
                    recent_improvement = np.mean(improvement_history[-20:])
                    # Adjust cooling based on improvement rate
                    if recent_improvement < 0.0001 * current_score:  # Very slow progress
                        cooling_factor = 0.99  # Cool slower
                    elif recent_improvement > 0.001 * current_score:  # Good progress
                        cooling_factor = 0.97  # Cool faster
                    else:
                        cooling_factor = 0.985  # Default

                # CHANGED: Adaptive exploration rate based on improvement history and progress ratio
                # Calculate recent improvement rate for adaptive exploration
                recent_improvement_rate = 0.0
                if len(improvement_history) > 20:
                    recent_improvement_rate = np.mean(improvement_history[-20:])
                    
                # Adaptive exploration rate based on improvement rate and progress
                base_exploration = 0.45  # Higher base for more exploration
                progress_factor = 1.0 - progress_ratio  # More exploration needed when progress is low
                improvement_factor = 1.0 + 5.0 * min(recent_improvement_rate / (1e-6 + current_score), 1.0)
                exploration_rate = max(0.05, base_exploration * progress_factor * improvement_factor)
                
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

                # FIX: Moderated Dirichlet concentration growth to maintain exploration diversity
                # Previously: concentration = 1.0 + 5.0 * progress_ratio
                # Now: concentration = 1.0 + 2.0 * progress_ratio with added noise
                concentration = 1.0 + 2.0 * progress_ratio
                # Add noise to maintain diversity even at high progress_ratio
                noise = 0.2 * (1.0 - progress_ratio)  # More noise when progress is low
                perturbation = rng.dirichlet(alpha=[concentration + noise] * 3)
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
                    # FIX: Use adaptive cooling factor instead of fixed cooling rate
                    T = max(initial_temp * (cooling_factor ** i_iter), 1e-10)
                    
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
        if initial_score > 0.015:  # Only disrupt if configuration looks optimized
            pattern_disrupted = disrupt_row_patterns(best_overall.copy())
            pattern_score = get_smallest_triangle_area(pattern_disrupted)
            if pattern_score > best_score_overall:
                best_score_overall = pattern_score
                best_overall = pattern_disrupted

        # FIX: Increased base step size for smallest triangle optimization from 0.007 to 0.015
        final_points = optimize_smallest_triangle(best_overall.copy(), base_step_size=0.015)
        final_score = get_smallest_triangle_area(final_points)
        if final_score > best_score_overall:
            best_overall = final_points

        return best_overall

    return improve