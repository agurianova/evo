from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def get_smallest_triangle_indices(points):
        n = points.shape[0]
        min_area = float('inf')
        min_indices = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    x1, y1 = points[i]
                    x2, y2 = points[j]
                    x3, y3 = points[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        return min_indices, min_area

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        T = 1.0
        cooling_rate = 0.995
        step_size_base = 0.1
        plateau_threshold = 100
        plateau_count = 0
        max_iter = 2000

        for _ in range(max_iter):
            min_indices, _ = get_smallest_triangle_indices(current)
            candidate = current.copy()
            
            for idx in min_indices:
                perturbation = np.random.normal(0, step_size_base * T, size=2)
                candidate[idx] += perturbation

            if not is_inside_triangle(candidate, A, B, C):
                plateau_count += 1
                T *= cooling_rate
                continue

            new_score = get_smallest_triangle_area(candidate)
            if new_score <= 0:
                plateau_count += 1
                T *= cooling_rate
                continue

            delta = new_score - current_score
            if delta > 0:
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
                    plateau_count = 0
                else:
                    plateau_count += 1
            else:
                if np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = new_score
                plateau_count += 1

            T *= cooling_rate

            if plateau_count > plateau_threshold or T < 1e-5:
                break

        return best

    return improve