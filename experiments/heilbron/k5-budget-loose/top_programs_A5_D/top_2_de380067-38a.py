from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def get_critical_points(points, min_area_val, tol=1e-10):
        n = points.shape[0]
        critical_points = set()
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        (points[j, 0] - points[i, 0]) * (points[k, 1] - points[i, 1]) -
                        (points[k, 0] - points[i, 0]) * (points[j, 1] - points[i, 1])
                    )
                    if area <= min_area_val + tol:
                        critical_points.add(i)
                        critical_points.add(j)
                        critical_points.add(k)
        return critical_points

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)

        for _round in range(50):
            headroom = max(0, 0.0365 - best_score)
            step_size = 0.1 * np.sqrt(headroom) * (1 - _round / 50)
            step_size = max(0.001, step_size)

            critical_points = get_critical_points(best, best_score)
            candidate = best.copy()

            if np.random.rand() < 0.2:
                num_to_move = np.random.choice([2, 3])
                if len(critical_points) >= num_to_move:
                    indices = np.random.choice(list(critical_points), num_to_move, replace=False)
                else:
                    indices = np.random.choice(11, num_to_move, replace=False)
                step_size_multi = step_size * 0.5
                for idx in indices:
                    perturbation = np.random.normal(0, step_size_multi, size=2)
                    candidate[idx] += perturbation
            else:
                if np.random.rand() < 0.7 and critical_points:
                    idx = np.random.choice(list(critical_points))
                else:
                    idx = np.random.randint(0, 11)
                perturbation = np.random.normal(0, step_size, size=2)
                candidate[idx] += perturbation

            if not is_inside_triangle(candidate, A, B, C):
                continue

            score = get_smallest_triangle_area(candidate)
            if score > best_score:
                best = candidate
                best_score = score

        return best

    return improve