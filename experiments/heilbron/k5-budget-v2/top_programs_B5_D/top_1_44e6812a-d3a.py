from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def get_min_triangle_indices(pts):
        n = pts.shape[0]
        min_area = float('inf')
        min_indices = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = pts[i], pts[j], pts[k]
                    area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        return min_indices

    def improve(points: np.ndarray) -> np.ndarray:
        seed = hash(points.tobytes()) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        if best_score <= 0:
            return best

        initial_temp = 0.1 * best_score
        temperature = initial_temp
        base_step = 0.05
        cooling_rate = 0.995
        max_iter = 500

        for it in range(max_iter):
            i1, i2, i3 = get_min_triangle_indices(best)

            if rng.random() < 0.2:
                indices_to_perturb = [i1, i2, i3]
            else:
                if rng.random() < 0.8:
                    idx = rng.choice([i1, i2, i3])
                    indices_to_perturb = [idx]
                else:
                    idx = rng.integers(0, 11)
                    indices_to_perturb = [idx]

            candidate = best.copy()
            step_size = base_step * (temperature / initial_temp)
            for idx in indices_to_perturb:
                perturbation = step_size * rng.normal(0, 1, size=2)
                candidate[idx] += perturbation

            if not is_inside_triangle(candidate, A, B, C):
                continue

            candidate_score = get_smallest_triangle_area(candidate)
            if candidate_score <= 0:
                continue

            delta = candidate_score - best_score
            if delta > 0:
                best = candidate
                best_score = candidate_score
            else:
                if rng.random() < np.exp(delta / temperature):
                    best = candidate
                    best_score = candidate_score

            temperature *= cooling_rate

        return best

    return improve