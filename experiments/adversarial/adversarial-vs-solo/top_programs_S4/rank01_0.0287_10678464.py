import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Precompute inward normals for all three edges
    def compute_edge_normal(A, B, C):
        AB = B - A
        n1 = np.array([-AB[1], AB[0]])
        n2 = np.array([AB[1], -AB[0]])
        M = (A + B) / 2
        MC = C - M
        if np.dot(n1, MC) > 0:
            normal = n1
        else:
            normal = n2
        norm = np.linalg.norm(normal)
        return normal / norm if norm > 1e-10 else np.array([0.0, 0.0])

    normal_AB = compute_edge_normal(A, B, C)
    normal_BC = compute_edge_normal(B, C, A)
    normal_CA = compute_edge_normal(C, A, B)

    # Boundary projection with adaptive repulsion
    def project_to_triangle(P, A, B, C, min_boundary_dist_val):
        def point_to_segment(p, a, b):
            ab = b - a
            ap = p - a
            len2_ab = np.dot(ab, ab)
            if len2_ab < 1e-10:
                return a
            t = np.dot(ap, ab) / len2_ab
            t = max(0.0, min(1.0, t))
            return a + t * ab

        p1 = point_to_segment(P, A, B)
        p2 = point_to_segment(P, B, C)
        p3 = point_to_segment(P, C, A)
        d1 = np.linalg.norm(P - p1)
        d2 = np.linalg.norm(P - p2)
        d3 = np.linalg.norm(P - p3)

        if d1 <= d2 and d1 <= d3:
            closest_point = p1
            normal_vec = normal_AB
        elif d2 <= d1 and d2 <= d3:
            closest_point = p2
            normal_vec = normal_BC
        else:
            closest_point = p3
            normal_vec = normal_CA

        # Attempt inward move with repulsion
        candidate = closest_point + min_boundary_dist_val * normal_vec
        if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
            return candidate
        
        candidate = closest_point + (min_boundary_dist_val / 2) * normal_vec
        if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
            return candidate
            
        return closest_point

    # Generate initial configuration with literature-backed row distribution
    rows_distribution = [3, 3, 2, 2, 1]  # Reverted from [4,3,2,1,1] to prevent dense-row clustering
    total_rows = len(rows_distribution)
    points = []
    for i, num_in_row in enumerate(rows_distribution):
        v = (i + 0.5) / total_rows
        for j in range(num_in_row):
            u = (j + 0.5) / num_in_row * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            # Apply increased initial perturbation
            candidate = P + np.random.uniform(-0.05, 0.05, 2)  # Increased from (-0.03,0.03)
            if not is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                candidate = project_to_triangle(candidate, A, B, C, 0.01)  # Initial repulsion
            points.append(candidate)
    
    current = np.array(points)
    best = current.copy()
    best_min_area = get_smallest_triangle_area(best)

    # Simulated annealing parameters
    T = 0.5
    T0 = T
    max_iter = 20000

    for _ in range(max_iter):
        n = len(current)
        
        # Find global minimum triangle area
        min_area = float('inf')
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    x1, y1 = current[i]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area < min_area:
                        min_area = area
        
        # Adaptive threshold with absolute floor
        threshold = min(0.001, 0.1 * min_area)  # Reverted from fixed 5% scaling
        
        # Weighted count of near-minimal triangles per point
        count = np.zeros(n, dtype=float)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    x1, y1 = current[i]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area <= threshold:
                        weight = threshold - area
                        count[i] += weight
                        count[j] += weight
                        count[k] += weight
        
        # Adaptive step size without lower bound
        step = T * 0.2
        min_boundary_dist_current = max(0.005, step * 0.5)  # Adaptive boundary repulsion

        # Decaying bias for point selection
        bias_prob = 0.9 * (1 - T / T0)

        # Attempt two-point move with 20% probability (reverted from 40%)
        two_point_done = False
        if np.random.rand() < 0.2:
            # Find all near-minimal triangles
            near_min_triangles = []
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        x1, y1 = current[i]
                        x2, y2 = current[j]
                        x3, y3 = current[k]
                        area_val = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area_val <= threshold:
                            near_min_triangles.append((i, j, k))
            
            if near_min_triangles:
                # Select random triangle and edge
                i, j, k = random.choice(near_min_triangles)
                edge_idx = np.random.randint(0, 3)
                if edge_idx == 0:
                    p1, p2 = i, j
                elif edge_idx == 1:
                    p1, p2 = j, k
                else:
                    p1, p2 = k, i
                
                # Move points apart in normal direction (corrected from edge direction)
                v = current[p2] - current[p1]
                n_vec = np.array([-v[1], v[0]])
                norm_n = np.linalg.norm(n_vec)
                if norm_n < 1e-10:
                    continue
                n_vec = n_vec / norm_n
                candidate1 = current[p1] - step * n_vec
                candidate2 = current[p2] + step * n_vec
                
                # Project to boundary if outside
                if not is_inside_triangle(candidate1.reshape(1, 2), A, B, C):
                    candidate1 = project_to_triangle(candidate1, A, B, C, min_boundary_dist_current)
                if not is_inside_triangle(candidate2.reshape(1, 2), A, B, C):
                    candidate2 = project_to_triangle(candidate2, A, B, C, min_boundary_dist_current)

                # Create candidate configuration
                new_config = current.copy()
                new_config[p1] = candidate1
                new_config[p2] = candidate2
                new_min_area = get_smallest_triangle_area(new_config)

                # Acceptance criterion
                delta = new_min_area - min_area
                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    current = new_config
                    if new_min_area > best_min_area:
                        best = current.copy()
                        best_min_area = new_min_area
                two_point_done = True

        # Single-point move if two-point not done or failed
        if not two_point_done:
            # Select point to move with decaying bias
            if np.random.rand() < (1 - bias_prob):
                idx = np.random.randint(0, n)
            else:
                total_count = np.sum(count)
                if total_count > 0:
                    probs = count / total_count
                    idx = np.random.choice(range(n), p=probs)
                else:
                    idx = np.random.randint(0, n)
            
            # Biased direction sampling toward problematic triangle normals
            candidate_directions = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        if i == idx or j == idx or k == idx:
                            x1, y1 = current[i]
                            x2, y2 = current[j]
                            x3, y3 = current[k]
                            area_val = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                            if area_val <= threshold:
                                # Identify the edge opposite to idx
                                if i == idx:
                                    j_idx, k_idx = j, k
                                elif j == idx:
                                    j_idx, k_idx = i, k
                                else:
                                    j_idx, k_idx = i, j
                                # Compute normal to edge (j_idx,k_idx)
                                v_edge = current[k_idx] - current[j_idx]
                                n_edge = np.array([-v_edge[1], v_edge[0]])
                                norm_n = np.linalg.norm(n_edge)
                                if norm_n < 1e-10:
                                    continue
                                n_edge = n_edge / norm_n
                                # Determine direction to increase area
                                w = current[idx] - current[j_idx]
                                d = np.dot(n_edge, w)
                                dir_candidate = n_edge if d >= 0 else -n_edge
                                candidate_directions.append(dir_candidate)

            # Sample 8 biased and 8 uniform directions
            directions = []
            num_biased = 8
            num_uniform = 8
            if candidate_directions:
                indices = np.random.choice(
                    len(candidate_directions), 
                    size=min(num_biased, len(candidate_directions)), 
                    replace=False
                )
                for idx_dir in indices:
                    directions.append(candidate_directions[idx_dir])
            while len(directions) < num_biased:
                angle = np.random.uniform(0, 2*np.pi)
                directions.append(np.array([np.cos(angle), np.sin(angle)]))
            for _ in range(num_uniform):
                angle = np.random.uniform(0, 2*np.pi)
                directions.append(np.array([np.cos(angle), np.sin(angle)]))

            # Evaluate all directions
            best_candidate = None
            best_new_min_area = -1
            for direction in directions:
                candidate_point = current[idx] + step * direction
                
                # Project to boundary if outside
                if not is_inside_triangle(candidate_point.reshape(1, 2), A, B, C):
                    candidate_point = project_to_triangle(candidate_point, A, B, C, min_boundary_dist_current)

                # Create candidate configuration
                new_config = current.copy()
                new_config[idx] = candidate_point
                new_min_area = get_smallest_triangle_area(new_config)

                # Track best candidate
                if new_min_area > best_new_min_area:
                    best_new_min_area = new_min_area
                    best_candidate = candidate_point

            # Accept best candidate
            if best_new_min_area > min_area or np.random.rand() < np.exp((best_new_min_area - min_area) / T):
                current[idx] = best_candidate
                if best_new_min_area > best_min_area:
                    best = current.copy()
                    best_min_area = best_new_min_area

        # Slower cooling schedule (0.999 instead of 0.995)
        T *= 0.999

    return best