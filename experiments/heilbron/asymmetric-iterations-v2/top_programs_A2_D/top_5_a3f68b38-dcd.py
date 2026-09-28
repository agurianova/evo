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

    def estimate_gradient(points, idx, base_score, step=0.001):
        """Estimate gradient direction for improvement at given point"""
        current = points[idx]
        directions = [
            np.array([1, 0]), np.array([-1, 0]),
            np.array([0, 1]), np.array([0, -1]),
            np.array([1, 1]), np.array([-1, -1])
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
            
            # Calculate distances to opposite edges
            d0 = point_to_line_distance(p0, p1, p2)
            d1 = point_to_line_distance(p1, p0, p2)
            d2 = point_to_line_distance(p2, p0, p1)
            dists = [d0, d1, d2]
            
            # Strategy 1: Move all points outward simultaneously
            new_points = points.copy()
            improved = False
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
                    best_score = new_score
                    best_points = candidate_points.copy()
                    points = candidate_points.copy()
                    improved = True

            # Strategy 2: Rotation around centroid if direct movement fails
            if not improved:
                centroid = (p0 + p1 + p2) / 3.0
                angle = 0.05  # Small rotation angle (radians)
                
                candidate_points = points.copy()
                valid_move = True
                for idx in min_triplet:
                    # Vector from centroid to point
                    vec = points[idx] - centroid
                    # Rotate 5 degrees
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
                        best_score = new_score
                        best_points = candidate_points.copy()
                        points = candidate_points.copy()
                        improved = True

            # Strategy 3: Gradient-based movement if other strategies fail
            if not improved:
                for idx in min_triplet:
                    grad = estimate_gradient(points, idx, best_score, step=step_size)
                    if grad is not None:
                        candidate_points = points.copy()
                        candidate = points[idx] + grad * step_size
                        
                        if is_inside_triangle(candidate, A, B, C):
                            candidate_points[idx] = candidate
                            new_score = get_smallest_triangle_area(candidate_points)
                            
                            if new_score > best_score:
                                best_score = new_score
                                best_points = candidate_points.copy()
                                points = candidate_points.copy()
                                improved = True
                                break

            # Adjust step size based on success
            if improved:
                step_size = min(step_size * 1.05, 0.02)
            else:
                step_size *= 0.95
                if step_size < 1e-5:
                    break

        return best_points

    def improve(points):
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)

        # Calculate theoretical maximum for adaptive parameter tuning
        theoretical_max = 0.0365
        
        for restart in range(15):  # Increased restarts adaptively
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

            for i_iter in range(2500):  # Slightly increased iterations
                # Adaptive exploration rate based on progress
                exploration_rate = max(0.03, 0.35 * (0.96 ** (i_iter / 100)) * (1.0 - progress_ratio * 0.7))
                
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

                # Adaptive perturbation in barycentric space
                adaptive_scale = 0.8 + 0.4 * progress_ratio
                du, dv = rng.normal(0, focus_step_size * adaptive_scale, 2)
                new_bary = np.array([
                    bary[0] + du,
                    bary[1] + dv,
                    bary[2] - du - dv
                ])
                new_bary = np.maximum(new_bary, 0)
                total = new_bary.sum()
                if total == 0:
                    new_bary = np.array([1/3, 1/3, 1/3])
                else:
                    new_bary /= total

                new_point = to_cartesian(new_bary)
                current[idx] = new_point
                new_score = get_smallest_triangle_area(current)

                delta = new_score - current_score
                if delta > 0:
                    accepted = True
                else:
                    # Adaptive temperature schedule
                    T = max(initial_temp * (0.995 ** i_iter), 1e-10)
                    
                    # Adjust cooling rate based on recent progress
                    if len(improvement_history) > 20:
                        recent_improvement = np.mean(improvement_history[-20:])
                        if recent_improvement < 1e-6:  # Very slow progress
                            T = max(T * 0.9, 1e-10)  # Cool faster
                        elif recent_improvement > 1e-4:  # Good progress
                            T = min(T * 1.05, initial_temp)  # Cool slower
                    
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

        # Apply enhanced specialized optimization on the smallest triangle
        final_points = optimize_smallest_triangle(best_overall.copy(), base_step_size=0.007)
        final_score = get_smallest_triangle_area(final_points)
        if final_score > best_score_overall:
            best_overall = final_points

        return best_overall

    return improve