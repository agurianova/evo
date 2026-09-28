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

        # Simulated annealing parameters
        initial_temp = 0.02
        cooling_rate = 0.99
        max_iterations = 200
        max_no_improve = 50
        no_improve_count = 0
        temperature = initial_temp

        def get_smallest_triplet(pts):
            n = pts.shape[0]
            min_val = float('inf')
            best_trip = (0, 1, 2)
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        x1, y1 = pts[i]
                        x2, y2 = pts[j]
                        x3, y3 = pts[k]
                        area_val = abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
                        if area_val < min_val:
                            min_val = area_val
                            best_trip = (i, j, k)
            return best_trip

        for _ in range(max_iterations):
            triplet = get_smallest_triplet(current)
            candidate = current.copy()

            # Perturb all three points of the smallest triangle
            for idx in triplet:
                candidate[idx] += np.random.normal(0, temperature, size=2)

            # Validate candidate
            if not is_inside_triangle(candidate, A, B, C):
                no_improve_count += 1
                temperature *= cooling_rate
                continue

            candidate_score = get_smallest_triangle_area(candidate)
            if candidate_score <= 1e-10:  # Degeneracy check
                no_improve_count += 1
                temperature *= cooling_rate
                continue

            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score
                    no_improve_count = 0
                else:
                    no_improve_count += 1
            else:
                no_improve_count += 1

            temperature *= cooling_rate
            if no_improve_count >= max_no_improve:
                break

        return best

    return improve