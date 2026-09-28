from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()
    rng = np.random.default_rng(seed=42)

    def compute_triangle_area(a, b, c):
        return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))

    def get_minimal_triangle(points, min_area_val):
        n = points.shape[0]
        candidates = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = compute_triangle_area(points[i], points[j], points[k])
                    if abs(area - min_area_val) < 1e-10:
                        candidates.append((i, j, k))
        if candidates:
            return rng.choice(candidates)
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = compute_triangle_area(points[i], points[j], points[k])
                    if area <= min_area_val + 1e-10:
                        return (i, j, k)
        return (0, 1, 2)

    def improve(points: np.ndarray) -> np.ndarray:
        base_step = 0.02
        max_iter = 200
        initial_temperature = 0.01
        cooling_rate = 0.99

        current = points.copy()
        best = current.copy()
        current_score = get_smallest_triangle_area(current)
        best_score = current_score

        temperature = initial_temperature

        for _ in range(max_iter):
            i1, i2, i3 = get_minimal_triangle(current, current_score)
            candidate = current.copy()
            
            centroid = (candidate[i1] + candidate[i2] + candidate[i3]) / 3.0
            for idx in [i1, i2, i3]:
                direction = candidate[idx] - centroid
                norm_dir = np.linalg.norm(direction)
                if norm_dir > 1e-5:
                    direction = direction / norm_dir
                else:
                    direction = rng.uniform(-1, 1, size=2)
                    direction = direction / np.linalg.norm(direction)
                step = base_step * temperature * direction
                candidate[idx] += step

            if not is_inside_triangle(candidate, A, B, C):
                continue

            candidate_score = get_smallest_triangle_area(candidate)

            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score

            delta = candidate_score - current_score
            if delta > 0 or rng.random() < np.exp(delta / temperature):
                current = candidate
                current_score = candidate_score

            temperature *= cooling_rate

        return best

    return improve