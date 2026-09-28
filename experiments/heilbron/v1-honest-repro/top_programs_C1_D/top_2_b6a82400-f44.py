from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        np.random.seed(42)
        
        # Helper: signed triangle area (with orientation)
        def signed_triangle_area(a, b, c):
            return 0.5 * (a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
        
        # Helper: convert Cartesian to barycentric coordinates
        def cartesian_to_barycentric(p, A, B, C):
            u = signed_triangle_area(p, B, C)
            v = signed_triangle_area(A, p, C)
            w = signed_triangle_area(A, B, p)
            total = u + v + w
            if abs(total) < 1e-10:
                return (1/3, 1/3, 1/3)
            return (u/total, v/total, w/total)
        
        # Helper: find smallest triangle (area and indices)
        def get_min_triangle(pts):
            n = pts.shape[0]
            min_area = float('inf')
            min_indices = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = abs(signed_triangle_area(pts[i], pts[j], pts[k]))
                        if area < min_area:
                            min_area = area
                            min_indices = (i, j, k)
            return min_area, min_indices

        # Initialize optimization state
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_overall = current.copy()
        best_overall_score = current_score

        # Optimization parameters
        max_iter = 500
        base_noise = 0.05
        initial_temp = 0.0001
        cooling_rate = 0.995
        temperature = initial_temp

        for _ in range(max_iter):
            # Adaptive noise scaling based on current progress
            noise_magnitude = base_noise * (1.0 - current_score / 0.0365)
            noise_magnitude = max(0, min(base_noise, noise_magnitude))

            # Identify critical bottleneck (smallest triangle)
            _, min_indices = get_min_triangle(current)
            
            # Bias selection toward critical points (70% probability)
            if np.random.rand() < 0.7:
                points_to_perturb = min_indices
            else:
                idx = np.random.randint(0, 11)
                points_to_perturb = [idx]

            # Create candidate via barycentric perturbation
            candidate = current.copy()
            for idx in points_to_perturb:
                p = candidate[idx]
                u, v, w = cartesian_to_barycentric(p, A, B, C)
                
                # Apply Gaussian noise in barycentric space
                du = np.random.normal(0, noise_magnitude)
                dv = np.random.normal(0, noise_magnitude)
                u_new, v_new = u + du, v + dv
                
                # Project back to valid simplex
                u_new = max(0, u_new)
                v_new = max(0, v_new)
                total = u_new + v_new
                if total > 1:
                    u_new, v_new = u_new/total, v_new/total
                w_new = 1 - u_new - v_new
                
                # Convert back to Cartesian
                candidate[idx] = u_new * A + v_new * B + w_new * C

            # Evaluate candidate
            candidate_score = get_smallest_triangle_area(candidate)
            
            # Update global best
            if candidate_score > best_overall_score:
                best_overall = candidate.copy()
                best_overall_score = candidate_score

            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current, current_score = candidate, candidate_score

            # Cool temperature
            temperature *= cooling_rate

        return best_overall

    return improve