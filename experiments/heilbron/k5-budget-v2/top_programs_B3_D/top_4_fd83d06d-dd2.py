from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        def get_smallest_triangle_indices(pts):
            n = pts.shape[0]
            min_area = float('inf')
            min_indices = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = pts[i]
                        x2, y2 = pts[j]
                        x3, y3 = pts[k]
                        area = 0.5 * abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
                        if area < min_area:
                            min_area = area
                            min_indices = (i, j, k)
            return min_indices, min_area

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        global_best = current.copy()
        global_best_score = current_score

        initial_sa_temp = 0.01
        cooling_rate = 0.95
        base_step = 0.05
        two_point_prob = 0.1
        T = initial_sa_temp

        for _ in range(50):
            min_indices, _ = get_smallest_triangle_indices(current)
            i, j, k = min_indices

            if np.random.rand() < two_point_prob:
                idxs = np.random.choice([i, j, k], size=2, replace=False)
            else:
                idxs = [np.random.choice([i, j, k])]

            candidate = current.copy()
            step_size = base_step * (T / initial_sa_temp)
            for idx in idxs:
                candidate[idx] += np.random.normal(0, step_size, size=2)

            if not is_inside_triangle(candidate, A, B, C):
                T *= cooling_rate
                continue

            score = get_smallest_triangle_area(candidate)

            if score > global_best_score:
                global_best = candidate.copy()
                global_best_score = score

            if score > current_score:
                current = candidate
                current_score = score
            else:
                delta = score - current_score
                if np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = score

            T *= cooling_rate

        return global_best

    return improve