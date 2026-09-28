from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        centroid = (A + B + C) / 3.0

        def get_critical_points(pts):
            n = pts.shape[0]
            min_area = float('inf')
            min_indices = None
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = pts[i], pts[j], pts[k]
                        area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                        if area < min_area:
                            min_area = area
                            min_indices = (i, j, k)
            return list(min_indices)

        def project_candidate(pts):
            projected = pts.copy()
            for i in range(len(pts)):
                p = projected[i]
                for step in range(10):
                    if is_inside_triangle(p, A, B, C):
                        break
                    p = p + 0.5 * (centroid - p)
                projected[i] = p
            return projected

        max_iter = 500
        max_stagnation_step = 20
        max_stagnation_early = 100
        initial_temp = 0.1
        cooling_rate = 0.99
        base_step = 0.05

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        step_size = base_step
        stagnation_step_count = 0
        stagnation_early_count = 0
        current_temp = initial_temp

        for it in range(max_iter):
            critical_indices = get_critical_points(current)

            if np.random.rand() < 0.7:
                num_to_perturb = 2 if np.random.rand() < 0.5 else 3
                indices_to_perturb = np.random.choice(critical_indices, num_to_perturb, replace=False)
            else:
                non_critical = [i for i in range(11) if i not in critical_indices]
                num_to_perturb = 1 if np.random.rand() < 0.5 else 2
                indices_to_perturb = np.random.choice(non_critical, num_to_perturb, replace=False)

            candidate = current.copy()
            for idx in indices_to_perturb:
                candidate[idx] += step_size * np.random.normal(0, 1, size=2)

            candidate = project_candidate(candidate)
            candidate_score = get_smallest_triangle_area(candidate)

            improved_best = False
            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                improved_best = True

            if improved_best:
                stagnation_step_count = 0
                stagnation_early_count = 0
            else:
                stagnation_step_count += 1
                stagnation_early_count += 1

            if stagnation_step_count > max_stagnation_step:
                step_size = min(step_size * 1.5, 0.1)
                stagnation_step_count = 0

            if stagnation_early_count > max_stagnation_early:
                break

            delta = candidate_score - current_score
            if delta > 0:
                current = candidate
                current_score = candidate_score
            else:
                if np.random.rand() < np.exp(delta / current_temp):
                    current = candidate
                    current_score = candidate_score

            current_temp *= cooling_rate

        return best

    return improve