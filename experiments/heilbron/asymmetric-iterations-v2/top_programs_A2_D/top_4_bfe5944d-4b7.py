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

    def get_top_k_triplets(pts, k=3):
        n = pts.shape[0]
        areas = []
        triplets = []
        
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    p1, p2, p3 = pts[i], pts[j], pts[k]
                    area = 0.5 * abs(
                        (p2[0] - p1[0]) * (p3[1] - p1[1]) - 
                        (p3[0] - p1[0]) * (p2[1] - p1[1])
                    )
                    areas.append(area)
                    triplets.append((i, j, k))
        
        # Sort by area and get top k
        sorted_indices = np.argsort(areas)
        top_k_triplets = [triplets[i] for i in sorted_indices[:k]]
        top_k_areas = [areas[i] for i in sorted_indices[:k]]
        
        return top_k_triplets, top_k_areas

    def optimize_smallest_triangle(points, max_iter=100, step_size=0.005):
        """Optimize the smallest triangle by moving all its vertices outward simultaneously."""
        points = points.copy()
        best_points = points.copy()
        best_score = get_smallest_triangle_area(points)
        
        for _ in range(max_iter):
            # Find the smallest triangle
            min_triplet, min_area = get_min_triplet(points)
            p0, p1, p2 = points[min_triplet[0]], points[min_triplet[1]], points[min_triplet[2]]
            
            # Calculate the centroid of the triangle
            centroid = (p0 + p1 + p2) / 3.0
            
            # For each vertex, compute direction away from the opposite edge
            new_points = points.copy()
            improved = False
            candidate_points = []
            
            # First try: move all points outward simultaneously
            all_outward_candidate = points.copy()
            all_outward_improved = False
            
            for idx_in_triplet, idx in enumerate(min_triplet):
                # Find the opposite edge
                edge_idx1, edge_idx2 = min_triplet[(idx_in_triplet+1)%3], min_triplet[(idx_in_triplet+2)%3]
                edge_p1, edge_p2 = points[edge_idx1], points[edge_idx2]
                
                # Direction perpendicular to the edge, pointing outward
                edge_vec = edge_p2 - edge_p1
                perp_vec = np.array([-edge_vec[1], edge_vec[0]])
                # Normalize and scale
                if np.linalg.norm(perp_vec) > 1e-10:
                    perp_vec = perp_vec / np.linalg.norm(perp_vec) * step_size
                    all_outward_candidate[idx] += perp_vec
            
            # Check if all points remain inside the triangle
            all_inside = True
            for idx in min_triplet:
                if not is_inside_triangle(all_outward_candidate[idx], A, B, C):
                    all_inside = False
                    break
                    
            if all_inside:
                new_score = get_smallest_triangle_area(all_outward_candidate)
                if new_score > best_score:
                    candidate_points.append((all_outward_candidate, new_score))
                    all_outward_improved = True
            
            # If simultaneous outward movement didn't work, try individual movements
            if not all_outward_improved:
                for idx_in_triplet, idx in enumerate(min_triplet):
                    # Find the opposite edge
                    edge_idx1, edge_idx2 = min_triplet[(idx_in_triplet+1)%3], min_triplet[(idx_in_triplet+2)%3]
                    edge_p1, edge_p2 = points[edge_idx1], points[edge_idx2]
                    
                    # Direction perpendicular to the edge, pointing outward
                    edge_vec = edge_p2 - edge_p1
                    perp_vec = np.array([-edge_vec[1], edge_vec[0]])
                    # Normalize and scale
                    if np.linalg.norm(perp_vec) > 1e-10:
                        perp_vec = perp_vec / np.linalg.norm(perp_vec) * step_size
                        
                        # Move the point in the perpendicular direction
                        candidate = points.copy()
                        candidate[idx] += perp_vec
                        
                        # Check if inside triangle
                        if is_inside_triangle(candidate[idx], A, B, C):
                            new_score = get_smallest_triangle_area(candidate)
                            if new_score > best_score:
                                candidate_points.append((candidate, new_score))
            
            # Try gradient-based fallback for precise adjustments
            if not candidate_points:
                p0, p1, p2 = points[min_triplet[0]], points[min_triplet[1]], points[min_triplet[2]]
                
                for idx_in_triplet, idx in enumerate(min_triplet):
                    # Find the opposite edge
                    edge_idx1, edge_idx2 = min_triplet[(idx_in_triplet+1)%3], min_triplet[(idx_in_triplet+2)%3]
                    edge_p1, edge_p2 = points[edge_idx1], points[edge_idx2]
                    
                    # Direction perpendicular to the edge, pointing outward (gradient direction)
                    edge_vec = edge_p2 - edge_p1
                    perp_vec = np.array([-edge_vec[1], edge_vec[0]])
                    
                    # Normalize and scale with slightly larger step for gradient precision
                    if np.linalg.norm(perp_vec) > 1e-10:
                        perp_vec = perp_vec / np.linalg.norm(perp_vec) * step_size * 1.2
                        
                        candidate = points.copy()
                        candidate[idx] += perp_vec
                        
                        # Check if inside triangle
                        if is_inside_triangle(candidate[idx], A, B, C):
                            new_score = get_smallest_triangle_area(candidate)
                            if new_score > best_score:
                                candidate_points.append((candidate, new_score))

            # Try more sophisticated fallbacks if direct approaches fail
            if not candidate_points:
                # Option 1: Rotate points around centroid
                angle = 0.05  # Small rotation angle (radians)
                for idx in min_triplet:
                    # Vector from centroid to point
                    vec = points[idx] - centroid
                    # Rotate 90 degrees (perpendicular to current direction)
                    rotated_vec = np.array([-vec[1], vec[0]])
                    # Normalize and scale
                    if np.linalg.norm(rotated_vec) > 1e-10:
                        rotated_vec = rotated_vec / np.linalg.norm(rotated_vec) * step_size
                        candidate = points.copy()
                        candidate[idx] = centroid + rotated_vec
                        if is_inside_triangle(candidate[idx], A, B, C):
                            new_score = get_smallest_triangle_area(candidate)
                            if new_score > best_score:
                                candidate_points.append((candidate, new_score))
                
                # Option 2: Perturb all three points toward expanding the triangle
                for i in range(3):
                    candidate = points.copy()
                    for j, idx in enumerate(min_triplet):
                        # Move away from the opposite vertex
                        opp_idx = min_triplet[(j+1)%3]
                        direction = points[idx] - points[opp_idx]
                        if np.linalg.norm(direction) > 1e-10:
                            direction = direction / np.linalg.norm(direction) * step_size * 0.7
                            candidate[idx] += direction
                    
                    # Check all points are inside
                    all_inside = True
                    for idx in min_triplet:
                        if not is_inside_triangle(candidate[idx], A, B, C):
                            all_inside = False
                            break
                    
                    if all_inside:
                        new_score = get_smallest_triangle_area(candidate)
                        if new_score > best_score:
                            candidate_points.append((candidate, new_score))
            
            # Select the best candidate
            if candidate_points:
                best_candidate, best_candidate_score = max(candidate_points, key=lambda x: x[1])
                if best_candidate_score > best_score:
                    points = best_candidate
                    best_points = points.copy()
                    best_score = best_candidate_score
                    improved = True
            else:
                break
        
        return best_points

    def improve(points):
        # Calculate adaptive restart count based on initial quality
        initial_score = get_smallest_triangle_area(points)
        # If initial score is poor (< 0.015), do more restarts to explore
        # If initial score is good (> 0.025), do fewer restarts but with more iterations
        if initial_score < 0.015:
            num_restarts = 15
            base_iter = 2500
        elif initial_score < 0.020:
            num_restarts = 12
            base_iter = 2200
        elif initial_score < 0.025:
            num_restarts = 10
            base_iter = 2000
        else:
            num_restarts = 8
            base_iter = 1800
        
        best_overall = points.copy()
        best_score_overall = initial_score

        for restart in range(num_restarts):
            rng = np.random.default_rng(seed=base_seed + restart)
            current = points.copy()
            current_score = get_smallest_triangle_area(current)
            best_restart = current.copy()
            best_score_restart = current_score

            # Dynamic temperature schedule
            initial_temp = max(0.15 * current_score, 0.005)
            step_size = 0.01
            recent_accepts = 0
            acceptance_window = 50
            improvement_streak = 0
            max_improvement_streak = 50
            cooling_factor = 0.995  # Will be adjusted dynamically

            # Stagnation recovery parameters
            stagnation_counter = 0
            max_stagnation = 500

            for i_iter in range(base_iter):
                # Dynamic cooling factor based on improvement streak
                if improvement_streak > max_improvement_streak * 0.7:
                    cooling_factor = 0.992  # Slow down cooling when finding improvements
                elif improvement_streak < max_improvement_streak * 0.3:
                    cooling_factor = 0.998  # Speed up cooling when stuck
                
                # Calculate bottleneck severity for adaptive exploration
                top_triplets, top_areas = get_top_k_triplets(current, k=2)
                bottleneck_score = top_areas[0] / top_areas[1] if len(top_areas) > 1 and top_areas[1] > 0 else 0
                # Adaptive exploration rate based on bottleneck severity
                # Focus more on second triangle when bottleneck is less severe
                focus_second_triangle = (rng.random() < 0.5 * (1 - bottleneck_score)) and (i_iter > base_iter * 0.2)
                
                # Implement faster decaying exploration rate (0.3 -> 0.05)
                exploration_rate = max(0.05, 0.3 * (cooling_factor ** (i_iter / 100)))
                
                if rng.random() < exploration_rate or focus_second_triangle:
                    # Focused exploration mode - use larger step size
                    focus_step_size = step_size * 1.5
                    
                    if focus_second_triangle:
                        # Use second smallest triangle
                        if len(top_triplets) > 1:
                            min_triplet = top_triplets[1]
                            p0, p1, p2 = current[min_triplet[0]], current[min_triplet[1]], current[min_triplet[2]]
                            d0 = point_to_line_distance(p0, p1, p2)
                            d1 = point_to_line_distance(p1, p0, p2)
                            d2 = point_to_line_distance(p2, p0, p1)
                            dists = [d0, d1, d2]
                            idx_in_triplet = np.argmin(dists)
                            idx = min_triplet[idx_in_triplet]
                            
                            # Reuse the area we already calculated
                            current_score = top_areas[1]
                        else:
                            # Fall back to smallest triangle if only one exists
                            min_triplet, min_area_val = get_min_triplet(current)
                            p0, p1, p2 = current[min_triplet[0]], current[min_triplet[1]], current[min_triplet[2]]
                            d0 = point_to_line_distance(p0, p1, p2)
                            d1 = point_to_line_distance(p1, p0, p2)
                            d2 = point_to_line_distance(p2, p0, p1)
                            dists = [d0, d1, d2]
                            idx_in_triplet = np.argmin(dists)
                            idx = min_triplet[idx_in_triplet]
                            current_score = min_area_val
                    else:
                        # Normal focused exploration on smallest triangle
                        min_triplet, min_area_val = get_min_triplet(current)
                        p0, p1, p2 = current[min_triplet[0]], current[min_triplet[1]], current[min_triplet[2]]
                        d0 = point_to_line_distance(p0, p1, p2)
                        d1 = point_to_line_distance(p1, p0, p2)
                        d2 = point_to_line_distance(p2, p0, p1)
                        dists = [d0, d1, d2]
                        idx_in_triplet = np.argmin(dists)
                        idx = min_triplet[idx_in_triplet]
                        
                        # Reuse the min_area_val we already calculated
                        current_score = min_area_val
                else:
                    # Random exploration mode - use normal step size
                    focus_step_size = step_size
                    idx = rng.integers(0, 11)

                old_point = current[idx].copy()
                bary = to_barycentric(old_point)

                du, dv = rng.normal(0, focus_step_size, 2)
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
                    improvement_streak += 1
                    stagnation_counter = 0
                else:
                    T = max(initial_temp * (cooling_factor ** i_iter), 1e-10)
                    if T < 1e-10:
                        accepted = False
                    else:
                        accepted = (rng.random() < np.exp(delta / T))
                    improvement_streak = max(0, improvement_streak - 1)
                    stagnation_counter += 1

                if accepted:
                    current_score = new_score
                    recent_accepts += 1
                    if new_score > best_score_restart:
                        best_score_restart = new_score
                        best_restart = current.copy()
                else:
                    current[idx] = old_point

                # Stagnation recovery mechanism
                if stagnation_counter > max_stagnation:
                    # Perform large perturbation to 3-4 points
                    num_perturb = rng.integers(3, 5)
                    perturb_indices = rng.choice(11, num_perturb, replace=False)
                    
                    recovery_candidate = current.copy()
                    for idx in perturb_indices:
                        # Large random perturbation
                        angle = rng.random() * 2 * np.pi
                        radius = rng.uniform(0.05, 0.15)
                        dx = radius * np.cos(angle)
                        dy = radius * np.sin(angle)
                        recovery_candidate[idx] += np.array([dx, dy])
                        
                        # Ensure point stays inside triangle
                        if not is_inside_triangle(recovery_candidate[idx], A, B, C):
                            recovery_candidate[idx] = current[idx].copy()
                    
                    # Evaluate recovery candidate
                    recovery_score = get_smallest_triangle_area(recovery_candidate)
                    if recovery_score > best_score_restart:
                        current = recovery_candidate
                        current_score = recovery_score
                        best_score_restart = recovery_score
                        best_restart = current.copy()
                    
                    stagnation_counter = 0  # Reset counter after recovery

                if (i_iter + 1) % acceptance_window == 0:
                    acceptance_rate = recent_accepts / acceptance_window
                    # Changed thresholds from 0.6/0.2 to 0.45/0.35 for more stable adaptation
                    if acceptance_rate > 0.45:
                        step_size = min(step_size * 1.1, 0.2)
                    elif acceptance_rate < 0.35:
                        step_size = max(step_size * 0.9, 1e-4)
                    recent_accepts = 0

            if best_score_restart > best_score_overall:
                best_score_overall = best_score_restart
                best_overall = best_restart.copy()

        # Apply specialized optimization on the smallest triangle
        final_points = optimize_smallest_triangle(best_overall.copy())
        final_score = get_smallest_triangle_area(final_points)
        if final_score > best_score_overall:
            best_overall = final_points

        return best_overall

    return improve