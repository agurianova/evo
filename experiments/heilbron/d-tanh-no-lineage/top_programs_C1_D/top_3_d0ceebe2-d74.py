from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_segment(p, a, b):
        ab = b - a
        ap = p - a
        ab2 = np.dot(ab, ab)
        if ab2 < 1e-12:
            return a
        t = np.dot(ap, ab) / ab2
        t = max(0.0, min(1.0, t))
        return a + t * ab

    def project_to_triangle(p):
        proj_ab = project_to_segment(p, A, B)
        proj_bc = project_to_segment(p, B, C)
        proj_ca = project_to_segment(p, C, A)
        d_ab = np.linalg.norm(p - proj_ab)
        d_bc = np.linalg.norm(p - proj_bc)
        d_ca = np.linalg.norm(p - proj_ca)
        if d_ab <= d_bc and d_ab <= d_ca:
            return proj_ab
        elif d_bc <= d_ab and d_bc <= d_ca:
            return proj_bc
        else:
            return proj_ca

    def improve(points: np.ndarray) -> np.ndarray:
        max_iter = 200
        T0 = 0.1
        adaptive_step_initial = 0.05
        adaptive_step_final = 0.001
        k_perturb_initial = 3
        k_perturb_final = 1
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        last_improvement = 0
        prev_best_score = best_score

        for iteration in range(max_iter):
            factor = iteration / max_iter
            
            # Adaptive step decay based on improvement rate
            if iteration > 0 and iteration % 10 == 0:
                improvement_rate = (best_score - prev_best_score)
                if improvement_rate < 1e-7:  # Very small improvement
                    adaptive_step_initial *= 0.8  # Reduce step size more aggressively
                else:
                    adaptive_step_initial *= 0.95  # Gentle reduction when making progress
            prev_best_score = best_score
            
            step_size = max(adaptive_step_final, adaptive_step_initial * (adaptive_step_final / adaptive_step_initial) ** factor)
            T = T0 * (1 - factor)
            
            # Adaptive threshold based on triangle area distribution
            n = 11
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = current[i], current[j], current[k]
                        area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        triangles.append((area, (i, j, k)))
            
            areas = [tr[0] for tr in triangles]
            min_area = min(areas)
            # Use percentile-based threshold that narrows over time
            threshold_percentile = 5.0 * (1 - factor)
            threshold = np.percentile(areas, threshold_percentile)
            
            critical_triangles = [triple for area, triple in triangles if area <= threshold]
            
            # Gradient-based movement with weighting by inverse area
            total_grad = np.zeros((n, 2))
            for (area, (i, j, k)) in triangles:
                if area <= threshold:
                    a, b, c = current[i], current[j], current[k]
                    s_val = a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1])
                    sign_s = 1.0 if s_val >= 0 else -1.0
                    
                    # Weight by inverse area to prioritize smallest triangles
                    weight = 1.0 / (area + 1e-12)
                    
                    # Gradient for point i
                    total_grad[i] += weight * sign_s * np.array([b[1]-c[1], c[0]-b[0]])
                    # Gradient for point j
                    total_grad[j] += weight * sign_s * np.array([c[1]-a[1], a[0]-c[0]])
                    # Gradient for point k
                    total_grad[k] += weight * sign_s * np.array([a[1]-b[1], b[0]-a[0]])

            # Normalize gradients to prevent oversized steps
            grad_norms = np.linalg.norm(total_grad, axis=1)
            max_norm = np.max(grad_norms)
            if max_norm > 0:
                total_grad = total_grad / max_norm

            candidate = current + step_size * total_grad

            # Adaptive perturbation count
            k_perturb = max(1, int(k_perturb_initial - (k_perturb_initial - k_perturb_final) * factor))
            
            # Weighted perturbation based on critical triangle involvement
            count = np.zeros(n, dtype=int)
            for (i, j, k) in critical_triangles:
                count[i] += 1
                count[j] += 1
                count[k] += 1
            
            # Scale perturbation magnitude by critical triangle involvement
            for i in range(n):
                if count[i] > 0:
                    perturb_magnitude = step_size * 0.01 * (count[i] / max(count))
                    candidate[i] += np.random.normal(0, perturb_magnitude, size=2)

            # Project all points to triangle boundary if outside
            for i in range(n):
                if not is_inside_triangle(np.array([candidate[i]]), A, B, C):
                    candidate[i] = project_to_triangle(candidate[i])

            new_score = get_smallest_triangle_area(candidate)
            delta = new_score - current_score
            
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
                    last_improvement = iteration

            # Dynamic early termination based on improvement rate
            if iteration - last_improvement > 30 + 20 * (1 - factor):
                break

        return best

    return improve