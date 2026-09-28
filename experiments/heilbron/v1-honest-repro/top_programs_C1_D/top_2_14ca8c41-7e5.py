from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Seed per input for independent randomness
        seed = hash(points.tobytes()) % (2**32 - 1)
        np.random.seed(seed)

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        max_iter = 500
        T0 = 0.005
        initial_step = 0.05
        final_step = 0.005

        for t in range(max_iter):
            # Identify critical points forming minimal-area triangles
            min_area_val = current_score
            critical_points = set()
            for i in range(11):
                for j in range(i + 1, 11):
                    for k in range(j + 1, 11):
                        a, b, c = current[i], current[j], current[k]
                        area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        if abs(area - min_area_val) < 1e-10:
                            critical_points.add(i)
                            critical_points.add(j)
                            critical_points.add(k)

            if not critical_points:
                critical_points = set(range(11))

            idx = np.random.choice(list(critical_points))

            # Adaptive step size and temperature
            step_size = initial_step - (initial_step - final_step) * (t / max_iter)
            T = T0 * (1 - t / max_iter)

            candidate = current.copy()
            candidate[idx] += np.random.normal(0, step_size, size=2)

            if not is_inside_triangle(candidate, A, B, C):
                continue

            new_score = get_smallest_triangle_area(candidate)

            # Simulated annealing acceptance
            if new_score > current_score:
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
            else:
                delta = new_score - current_score
                if T > 1e-10 and np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = new_score

        return best

    return improve