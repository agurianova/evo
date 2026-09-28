from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def get_critical_points(points, min_area_val, tol=1e-10):
        n = len(points)
        critical_indices = set()
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        points[i, 0] * (points[j, 1] - points[k, 1]) +
                        points[j, 0] * (points[k, 1] - points[i, 1]) +
                        points[k, 0] * (points[i, 1] - points[j, 1])
                    )
                    if abs(area - min_area_val) < tol:
                        critical_indices.add(i)
                        critical_indices.add(j)
                        critical_indices.add(k)
        return list(critical_indices)

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)

        for _round in range(50):
            current_min_area = get_smallest_triangle_area(best)
            step_size = 0.1 * np.sqrt(current_min_area) * (0.95 ** _round)

            # Determine move type: single or multiple
            use_multiple = (np.random.rand() < 0.2) and (len(points) >= 2)
            critical_points = get_critical_points(best, current_min_area)
            
            if use_multiple and len(critical_points) >= 2:
                # Multiple point move (2 points)
                idxs = np.random.choice(critical_points, size=2, replace=False)
                step_size_reduced = step_size / np.sqrt(2)
                perturbations = np.random.normal(0, step_size_reduced, size=(2, 2))
                candidate = best.copy()
                candidate[idxs[0]] += perturbations[0]
                candidate[idxs[1]] += perturbations[1]
                moved_indices = idxs
            else:
                # Single point move
                idx = np.random.choice(critical_points)
                perturbation = np.random.normal(0, step_size, size=2)
                candidate = best.copy()
                candidate[idx] += perturbation
                moved_indices = [idx]

            # Boundary handling via perturbation scaling
            if not is_inside_triangle(candidate, A, B, C):
                scale = 1.0
                found = False
                for _ in range(10):
                    candidate_scaled = best.copy()
                    for i, idx in enumerate(moved_indices):
                        if use_multiple and len(moved_indices) == 2:
                            candidate_scaled[idx] = best[idx] + scale * perturbations[i]
                        else:
                            candidate_scaled[idx] = best[idx] + scale * perturbation
                    if is_inside_triangle(candidate_scaled, A, B, C):
                        candidate = candidate_scaled
                        found = True
                        break
                    scale *= 0.5
                if not found:
                    continue

            score = get_smallest_triangle_area(candidate)
            if score > best_score:
                best = candidate
                best_score = score

        return best

    return improve