from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    # Precompute denominator for barycentric conversion (fixed for unit triangle)
    denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        best = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_score = current_score

        T = 0.01  # Initial temperature
        step_size = 0.05  # Initial step size in barycentric space
        min_step_size = 0.001
        no_improve_count = 0

        for _ in range(200):
            # Find smallest triangle by area
            min_area = float('inf')
            min_indices = None
            for i1 in range(11):
                for i2 in range(i1 + 1, 11):
                    for i3 in range(i2 + 1, 11):
                        x1, y1 = current[i1]
                        x2, y2 = current[i2]
                        x3, y3 = current[i3]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area < min_area:
                            min_area = area
                            min_indices = (i1, i2, i3)

            # Randomly select one vertex from the smallest triangle
            idx = np.random.choice(min_indices)

            # Convert to barycentric coordinates
            P = current[idx]
            u = ((B[1] - C[1]) * (P[0] - C[0]) + (C[0] - B[0]) * (P[1] - C[1])) / denom
            v = ((C[1] - A[1]) * (P[0] - C[0]) + (A[0] - C[0]) * (P[1] - C[1])) / denom
            w = 1 - u - v

            # Perturb in barycentric space
            du = np.random.normal(0, step_size)
            dv = np.random.normal(0, step_size)
            new_u = max(0, u + du)
            new_v = max(0, v + dv)
            total = new_u + new_v
            if total > 1:
                new_u /= total
                new_v /= total
            new_w = 1 - new_u - new_v

            # Convert back to Cartesian
            x = new_u * A[0] + new_v * B[0] + new_w * C[0]
            y = new_u * A[1] + new_v * B[1] + new_w * C[1]
            candidate = current.copy()
            candidate[idx] = [x, y]

            # Validate point containment (boundary allowed)
            if not is_inside_triangle(candidate[idx], A, B, C):
                no_improve_count += 1
            else:
                score = get_smallest_triangle_area(candidate)
                delta = score - current_score
                # Simulated annealing acceptance
                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = score
                    if score > best_score:
                        best = candidate.copy()
                        best_score = score
                        no_improve_count = 0
                    else:
                        no_improve_count += 1
                else:
                    no_improve_count += 1

            # Adaptive step size reduction
            if no_improve_count >= 20:
                step_size = max(min_step_size, step_size * 0.8)
                no_improve_count = 0

            # Cool temperature
            T = max(0.0001, T * 0.95)

        return best

    return improve