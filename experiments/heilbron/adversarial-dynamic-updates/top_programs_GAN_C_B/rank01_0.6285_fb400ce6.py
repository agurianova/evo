from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A_big, B_big, C_big = get_unit_triangle()

    def find_smallest_triangle(pts):
        n = pts.shape[0]
        min_area = float('inf')
        best_indices = None
        best_cross = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    dx1 = pts[j,0] - pts[i,0]
                    dy1 = pts[j,1] - pts[i,1]
                    dx2 = pts[k,0] - pts[i,0]
                    dy2 = pts[k,1] - pts[i,1]
                    cross = dx1 * dy2 - dy1 * dx2
                    area = 0.5 * abs(cross)
                    if area < min_area:
                        min_area = area
                        best_indices = (i, j, k)
                        best_cross = cross
        return min_area, best_indices, best_cross

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current_score = best_score

        max_rounds = 200
        initial_temp = 0.001
        cooling_rate = 0.95
        initial_step = 0.05
        noise_factor = 0.1
        early_stop_patience = 20

        temp = initial_temp
        last_improvement = 0

        for round_idx in range(max_rounds):
            min_area_current, (i, j, k), cross = find_smallest_triangle(current)
            A_pt, B_pt, C_pt = current[i], current[j], current[k]

            grad_A = np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]])
            grad_B = np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[0]])
            grad_C = np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]])

            if cross < 0:
                grad_A, grad_B, grad_C = -grad_A, -grad_B, -grad_C

            def normalize(v):
                norm = np.linalg.norm(v)
                return v / norm if norm > 1e-10 else np.zeros_like(v)
            
            grad_A = normalize(grad_A)
            grad_B = normalize(grad_B)
            grad_C = normalize(grad_C)

            step = initial_step * (temp / initial_temp)
            candidate = current.copy()
            
            noise_i = np.random.randn(2) * noise_factor * step
            candidate[i] = A_pt + step * grad_A + noise_i
            
            noise_j = np.random.randn(2) * noise_factor * step
            candidate[j] = B_pt + step * grad_B + noise_j
            
            noise_k = np.random.randn(2) * noise_factor * step
            candidate[k] = C_pt + step * grad_C + noise_k

            if not is_inside_triangle(candidate, A_big, B_big, C_big):
                temp *= cooling_rate
                continue

            score = get_smallest_triangle_area(candidate)
            if score <= 1e-10:
                temp *= cooling_rate
                continue

            delta = score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temp):
                current, current_score = candidate, score
                if score > best_score:
                    best, best_score = candidate, score
                    last_improvement = round_idx

            temp *= cooling_rate
            if round_idx - last_improvement > early_stop_patience:
                break

        return best

    return improve