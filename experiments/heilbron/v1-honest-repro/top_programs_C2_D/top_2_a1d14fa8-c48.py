from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        def triangle_area(a, b, c):
            return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))

        best = points.copy()
        best_score = get_smallest_triangle_area(best)

        for _ in range(50):
            min_area_val = float('inf')
            min_indices = None
            n = best.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = triangle_area(best[i], best[j], best[k])
                        if area < min_area_val:
                            min_area_val = area
                            min_indices = (i, j, k)

            if min_indices is None:
                continue

            i, j, k = min_indices
            p0, p1, p2 = best[i], best[j], best[k]
            centroid = (p0 + p1 + p2) / 3.0

            d0 = p0 - centroid
            d1 = p1 - centroid
            d2 = p2 - centroid

            norm0 = np.linalg.norm(d0)
            norm1 = np.linalg.norm(d1)
            norm2 = np.linalg.norm(d2)

            if norm0 < 1e-9 or norm1 < 1e-9 or norm2 < 1e-9:
                continue

            u0 = d0 / norm0
            u1 = d1 / norm1
            u2 = d2 / norm2

            step_size = 0.1 * np.sqrt(min_area_val)

            candidate = best.copy()
            candidate[i] = p0 + step_size * u0
            candidate[j] = p1 + step_size * u1
            candidate[k] = p2 + step_size * u2

            if not is_inside_triangle(candidate, A, B, C):
                continue

            score = get_smallest_triangle_area(candidate)
            if score > best_score:
                best = candidate
                best_score = score

        return best

    return improve