from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Generate unique seed based on input configuration for true stochastic diversity
        config_hash = int(hashlib.sha256(points.tobytes()).hexdigest()[:8], 16)
        rng = np.random.default_rng(config_hash)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        initial_min_area = best_score
        
        # CORRECTED: Step size now proportional to problem difficulty (smaller for harder problems)
        base_step = max(0.001, min(0.05, 0.05 * initial_min_area))
        T0 = 0.1 * base_step
        cooling_rate = 0.99
        T = T0
        
        # Adaptive total iterations with reasonable bounds
        total_iterations = min(500, max(100, 200 * (0.01 / initial_min_area)))
        no_improve_count = 0
        
        # Adaptive parameters based on configuration difficulty
        critical_tolerance = max(1e-5, min(1e-2, 0.01 * initial_min_area))
        reheating_threshold = max(20, min(100, 50 * initial_min_area / 0.03))
        collinear_threshold = 1e-10

        for iteration in range(int(total_iterations)):
            # Identify critical points (vertices of smallest triangles) with adaptive tolerance
            critical_points = set()
            n = best.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        # Compute triangle area
                        area = 0.5 * abs((best[j,0]-best[i,0])*(best[k,1]-best[i,1]) - 
                                      (best[k,0]-best[i,0])*(best[j,1]-best[i,1]))
                        # Use adaptive tolerance to capture relevant near-minimal triangles
                        if area <= best_score * (1 + critical_tolerance):
                            critical_points.add(i)
                            critical_points.add(j)
                            critical_points.add(k)

            # MODIFIED: Reduced threshold to engage gradient search earlier on difficult problems
            use_gradient = False
            gradient_threshold = max(5, int(15 * initial_min_area / 0.03))
            if no_improve_count >= gradient_threshold and rng.random() < 0.2:
                use_gradient = True
                
                # Compute displacement vectors similar to constructor approach
                displacement_vectors = np.zeros_like(best)
                displacement_count = np.zeros(n)
                
                for i in range(n):
                    for j in range(i+1, n):
                        for k in range(j+1, n):
                            # Only consider near-minimal triangles
                            area = 0.5 * abs((best[j,0]-best[i,0])*(best[k,1]-best[i,1]) - 
                                          (best[k,0]-best[i,0])*(best[j,1]-best[i,1]))
                            if area <= best_score * (1 + critical_tolerance):
                                # Compute displacement for i
                                base_jk = best[k] - best[j]
                                normal_jk = np.array([-base_jk[1], base_jk[0]])
                                norm_jk = np.linalg.norm(normal_jk)
                                if norm_jk > 1e-10:
                                    normal_jk = normal_jk / norm_jk
                                    d_i = np.dot(best[i] - best[j], normal_jk)
                                    displacement_vectors[i] += np.sign(d_i) * normal_jk
                                    displacement_count[i] += 1
                                
                                # Compute displacement for j
                                base_ik = best[k] - best[i]
                                normal_ik = np.array([-base_ik[1], base_ik[0]])
                                norm_ik = np.linalg.norm(normal_ik)
                                if norm_ik > 1e-10:
                                    normal_ik = normal_ik / norm_ik
                                    d_j = np.dot(best[j] - best[i], normal_ik)
                                    displacement_vectors[j] += np.sign(d_j) * normal_ik
                                    displacement_count[j] += 1
                                
                                # Compute displacement for k
                                base_ij = best[j] - best[i]
                                normal_ij = np.array([-base_ij[1], base_ij[0]])
                                norm_ij = np.linalg.norm(normal_ij)
                                if norm_ij > 1e-10:
                                    normal_ij = normal_ij / norm_ij
                                    d_k = np.dot(best[k] - best[i], normal_ij)
                                    displacement_vectors[k] += np.sign(d_k) * normal_ij
                                    displacement_count[k] += 1

                # Normalize displacement vectors
                for idx in range(n):
                    if displacement_count[idx] > 0:
                        displacement_vectors[idx] /= displacement_count[idx]
                
                # Apply displacement with adaptive step size
                step_size = base_step * 0.5
                candidate = best.copy()
                for idx in range(n):
                    if displacement_count[idx] > 0:
                        candidate[idx] += step_size * displacement_vectors[idx]
            else:
                # Select points to perturb: adaptive count based on configuration difficulty
                num_perturb = min(6, max(2, int(11 * initial_min_area / 0.03)))
                if critical_points:
                    indices = rng.choice(list(critical_points), size=min(num_perturb, len(critical_points)), replace=False)
                else:
                    indices = rng.choice(11, size=min(num_perturb, 11), replace=False)

                candidate = best.copy()
                # Perturb selected points with adaptive step size
                step_size = base_step * (T / T0)
                for idx in indices:
                    perturbation = rng.normal(0, step_size, size=2)
                    candidate[idx] += perturbation

            # MODIFIED: Use enhanced projection that avoids collinearity
            for i in range(11):
                if not is_inside_triangle(candidate[i:i+1], A, B, C):
                    # Project to boundary but check for collinearity
                    candidate[i] = safe_project_point_to_triangle(candidate[i], A, B, C, best)

            # Validate candidate has no collinear points
            score = get_smallest_triangle_area(candidate)
            if score <= collinear_threshold:
                # If collinear, nudge points slightly to break collinearity
                candidate = break_collinearity(candidate, A, B, C, collinear_threshold)
                score = get_smallest_triangle_area(candidate)
                
            # Simulated annealing acceptance
            delta = score - best_score
            if delta > 0 or rng.random() < np.exp(delta / T):
                best = candidate
                best_score = score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Cooling and reheating
            T *= cooling_rate
            if no_improve_count >= reheating_threshold:
                T = T0
                no_improve_count = 0

        return best

    def safe_project_point_to_triangle(p, A, B, C, current_points):
        # First get the standard projection
        projected = project_point_to_triangle(p, A, B, C)
        
        # Check if this creates collinear points
        test_points = current_points.copy()
        test_points[np.argmin(np.linalg.norm(current_points - p, axis=1))] = projected
        min_area = get_smallest_triangle_area(test_points)
        
        # If collinear or near-collinear, nudge inward
        if min_area < 1e-8:
            # Determine which edge we're on
            edges = [(A, B), (B, C), (C, A)]
            closest_edge = None
            min_dist = float('inf')
            
            for i, (a, b) in enumerate(edges):
                v = b - a
                w = projected - a
                c1 = np.dot(w, v)
                c2 = np.dot(v, v)
                if c2 > 0:
                    b_val = c1 / c2
                    if 0 <= b_val <= 1:
                        dist = np.linalg.norm(w - b_val * v)
                        if dist < min_dist:
                            min_dist = dist
                            closest_edge = (a, b)

            if closest_edge:
                # Nudge inward perpendicular to the edge
                a, b = closest_edge
                edge_vec = b - a
                normal = np.array([-edge_vec[1], edge_vec[0]])
                normal = normal / np.linalg.norm(normal)
                # Nudge inward (opposite direction of outward normal)
                nudge = -0.001 * normal
                return projected + nudge
            
        return projected

    def break_collinearity(points, A, B, C, threshold=1e-8):
        # Find nearly collinear triplets and nudge points
        n = points.shape[0]
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                  (points[k,0]-points[i,0])*(points[j,1]-points[i,1]))
                    if area < threshold:
                        # Nudge the middle point slightly
                        mid_idx = j
                        # Determine the direction perpendicular to the line
                        line_vec = points[k] - points[i]
                        normal = np.array([-line_vec[1], line_vec[0]])
                        if np.linalg.norm(normal) > 0:
                            normal = normal / np.linalg.norm(normal)
                            # Nudge inward or outward based on triangle position
                            test_point = points[mid_idx] + 0.001 * normal
                            if is_inside_triangle(test_point.reshape(1, 2), A, B, C):
                                points[mid_idx] = test_point
                            else:
                                points[mid_idx] = points[mid_idx] - 0.001 * normal
        return points

    def project_point_to_triangle(p, A, B, C):
        def project_point_to_segment(p, a, b):
            v = b - a
            w = p - a
            c1 = np.dot(w, v)
            if c1 <= 0:
                return a
            c2 = np.dot(v, v)
            if c2 <= c1:
                return b
            b_val = c1 / c2
            return a + b_val * v

        closest_AB = project_point_to_segment(p, A, B)
        closest_BC = project_point_to_segment(p, B, C)
        closest_CA = project_point_to_segment(p, C, A)

        d_AB = np.linalg.norm(p - closest_AB)
        d_BC = np.linalg.norm(p - closest_BC)
        d_CA = np.linalg.norm(p - closest_CA)

        if d_AB <= d_BC and d_AB <= d_CA:
            return closest_AB
        elif d_BC <= d_AB and d_BC <= d_CA:
            return closest_BC
        else:
            return closest_CA

    return improve