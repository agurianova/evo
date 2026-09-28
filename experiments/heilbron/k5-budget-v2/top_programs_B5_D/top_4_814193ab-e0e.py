from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def get_min_triangle_indices(pts):
        n = pts.shape[0]
        min_area = float('inf')
        min_idx = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    x1, y1 = pts[i]
                    x2, y2 = pts[j]
                    x3, y3 = pts[k]
                    area = 0.5 * abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
                    if area < min_area:
                        min_area = area
                        min_idx = (i, j, k)
        return min_idx

    def improve(points: np.ndarray) -> np.ndarray:
        seed = hash(points.tobytes()) % (2**32)
        np.random.seed(seed)

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        n_points = current.shape[0]

        T0 = 0.005
        T_min = 0.0001
        rounds = 200
        initial_step = 0.05

        for round in range(rounds):
            T = T0 * (1 - round / rounds) + T_min * (round / rounds)
            step_size = initial_step * (T / T0)

            min_tri = get_min_triangle_indices(current)
            idx = np.random.choice(min_tri)

            candidate = current.copy()
            perturbation = np.random.normal(0, step_size, size=2)
            candidate[idx] += perturbation

            if not is_inside_triangle(candidate, A, B, C):
                continue

            candidate_score = get_smallest_triangle_area(candidate)

            if candidate_score > current_score:
                current = candidate
                current_score = candidate_score
            else:
                delta = candidate_score - current_score
                if np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = candidate_score

        return current

    return improve