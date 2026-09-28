from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    """Return an improve(points) -> improved_points callable."""
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Set seed per input for independent randomness
        seed_val = hash(points.tobytes()) % (2**32)
        np.random.seed(seed_val)

        total_rounds = 200
        initial_step = 0.05
        final_step = 0.005
        initial_temp = 0.0001
        final_temp = 1e-7

        # Helper to identify critical points in minimal triangles
        def get_minimal_triangles(pts):
            n = pts.shape[0]
            min_area_val = get_smallest_triangle_area(pts)
            tol = 1e-12
            critical_indices = set()
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = pts[i]
                        x2, y2 = pts[j]
                        x3, y3 = pts[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if abs(area - min_area_val) < tol:
                            critical_indices.update([i, j, k])
            return list(critical_indices) if critical_indices else list(range(11))

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        for t in range(total_rounds):
            # Adaptive parameters
            progress = t / total_rounds
            step_size = initial_step * (final_step / initial_step) ** progress
            temp = initial_temp * (final_temp / initial_temp) ** progress

            # Focus perturbations on critical points
            critical_points = get_minimal_triangles(current)
            idx = np.random.choice(critical_points)

            # Generate candidate
            candidate = current.copy()
            candidate[idx] += np.random.normal(0, step_size, size=2)

            # Validate containment
            if not is_inside_triangle(candidate, A, B, C):
                continue

            candidate_score = get_smallest_triangle_area(candidate)

            # Simulated annealing acceptance
            if candidate_score > current_score:
                current, current_score = candidate, candidate_score
                if candidate_score > best_score:
                    best, best_score = candidate, candidate_score
            else:
                delta = candidate_score - current_score
                if np.random.rand() < np.exp(delta / temp):
                    current, current_score = candidate, candidate_score

        return best

    return improve