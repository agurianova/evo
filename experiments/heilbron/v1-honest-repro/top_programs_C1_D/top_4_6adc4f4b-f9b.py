from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def triangle_area(a, b, c):
        return 0.5 * abs((a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1])))

    def improve(points: np.ndarray) -> np.ndarray:
        # Seed per input using hash of points
        seed = hash(points.tobytes()) % (2**32)
        np.random.seed(seed)

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        total_rounds = 200
        initial_step = 0.05
        final_step = 0.005
        T0 = max(0.0001, current_score * 0.1)
        tolerance = 1e-10

        for round_idx in range(total_rounds):
            # Adaptive step size and temperature
            step = initial_step * (final_step / initial_step) ** (round_idx / total_rounds)
            T = T0 * (0.99 ** round_idx)

            # Identify critical points from minimal triangles
            n = current.shape[0]
            min_triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = triangle_area(current[i], current[j], current[k])
                        if abs(area - current_score) < tolerance:
                            min_triangles.append((i, j, k))

            critical_points = set()
            for tri in min_triangles:
                critical_points.update(tri)
            critical_points = list(critical_points) or list(range(11))

            # Perturb a critical point
            idx = np.random.choice(critical_points)
            candidate = current.copy()
            candidate[idx] += np.random.normal(0, step, size=2)

            if not is_inside_triangle(candidate, A, B, C):
                continue

            candidate_score = get_smallest_triangle_area(candidate)

            # Update global best
            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score

            # Simulated annealing acceptance
            if candidate_score > current_score:
                current, current_score = candidate, candidate_score
            else:
                delta = current_score - candidate_score
                if np.random.random() < np.exp(-delta / T):
                    current, current_score = candidate, candidate_score

        return best

    return improve