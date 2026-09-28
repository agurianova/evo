from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A_big, B_big, C_big = get_unit_triangle()

    def compute_min_triangle(points):
        n = points.shape[0]
        min_area = float('inf')
        min_indices = (0, 1, 2)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    A = points[i]
                    B = points[j]
                    C = points[k]
                    expr = (B[0] - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (B[1] - A[1])
                    area = 0.5 * abs(expr)
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        return min_area, min_indices

    def improve(points: np.ndarray) -> np.ndarray:
        base_step = 0.02
        max_iter = 100
        no_improve_count = 0
        best = points.copy()
        best_score = get_smallest_triangle_area(best)

        for _ in range(max_iter):
            current = best.copy()
            current_score, (i, j, k) = compute_min_triangle(current)
            A = current[i]
            B = current[j]
            C = current[k]

            # Compute signed area expression to determine gradient direction
            expr = (B[0] - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (B[1] - A[1])
            sign = 1.0 if expr >= 0 else -1.0

            # Compute gradients for the three points
            grad_i = sign * np.array([B[1] - C[1], C[0] - B[0]])
            grad_j = sign * np.array([C[1] - A[1], A[0] - C[0]])
            grad_k = sign * np.array([A[1] - B[1], B[0] - A[0]])

            # Adaptive step size decays with stagnation
            step_size = base_step * (0.95 ** no_improve_count)

            candidate = current.copy()
            for idx, grad in zip([i, j, k], [grad_i, grad_j, grad_k]):
                grad_norm = np.linalg.norm(grad)
                if grad_norm > 1e-8:
                    candidate[idx] += step_size * grad / grad_norm

            # Skip if outside triangle or degenerate
            if not is_inside_triangle(candidate, A_big, B_big, C_big):
                no_improve_count += 1
                continue
            
            new_score = get_smallest_triangle_area(candidate)
            if new_score <= 1e-10:  # Avoid near-degenerate configurations
                no_improve_count += 1
                continue

            if new_score > best_score:
                best = candidate
                best_score = new_score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Escape local optima via shake mechanism
            if no_improve_count >= 10:
                candidate_shake = best.copy()
                candidate_shake += np.random.normal(0, 0.05, size=(11, 2))
                
                if is_inside_triangle(candidate_shake, A_big, B_big, C_big):
                    shake_score = get_smallest_triangle_area(candidate_shake)
                    if shake_score > best_score:
                        best = candidate_shake
                        best_score = shake_score
                        no_improve_count = 0
                    else:
                        no_improve_count = 5  # Reset counter to avoid immediate next shake
                else:
                    no_improve_count = 5

        return best

    return improve