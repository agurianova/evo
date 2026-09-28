from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        T = 0.1
        cooling_rate = 0.99
        max_iter = 1000
        step_scale = 0.1

        for _ in range(max_iter):
            # Find smallest triangle indices via triple-loop enumeration
            n = current.shape[0]
            min_area = float('inf')
            min_indices = None
            for i1 in range(n):
                for i2 in range(i1 + 1, n):
                    for i3 in range(i2 + 1, n):
                        p1, p2, p3 = current[i1], current[i2], current[i3]
                        area = 0.5 * abs((p2[0] - p1[0]) * (p3[1] - p1[1]) - 
                                         (p3[0] - p1[0]) * (p2[1] - p1[1]))
                        if area < min_area:
                            min_area = area
                            min_indices = (i1, i2, i3)

            # Generate candidate by perturbing smallest triangle vertices
            candidate = current.copy()
            for idx in min_indices:
                perturbation = np.random.normal(0, T * step_scale, size=2)
                candidate[idx] += perturbation

            # Validate containment
            if not is_inside_triangle(candidate, A, B, C):
                continue

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - current_score

            # Simulated annealing acceptance
            if delta >= 0 or np.random.rand() < np.exp(delta / T):
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score

            T *= cooling_rate

        return best

    return improve