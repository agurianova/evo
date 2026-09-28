from helper import get_unit_triangle, get_smallest_triangle_area
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    AB = B - A
    AC = C - A
    M = np.column_stack((AB, AC))
    M_inv = np.linalg.inv(M)

    def get_min_triangle_indices(points):
        n = points.shape[0]
        min_area = float('inf')
        min_indices = None
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    x1, y1 = points[i]
                    x2, y2 = points[j]
                    x3, y3 = points[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        return min_indices

    num_searches = 5
    iterations_per_search = 1000
    initial_temp = 0.001
    cooling_rate = 0.99
    base_step_size = 0.05

    def improve(points: np.ndarray) -> np.ndarray:
        best_overall = points.copy()
        best_score = get_smallest_triangle_area(best_overall)

        for _ in range(num_searches):
            current = points.copy()
            current_score = best_score

            for i in range(iterations_per_search):
                # Select point with 80% focus on bottleneck triangle
                if np.random.rand() < 0.8:
                    min_indices = get_min_triangle_indices(current)
                    idx = np.random.choice(min_indices)
                else:
                    idx = np.random.randint(0, 11)

                # Transform to (s,t) coordinates
                p = current[idx]
                vec = p - A
                s, t = M_inv @ vec

                # Apply adaptive step size perturbation
                step_size = base_step_size * (cooling_rate ** i)
                s_new = s + np.random.normal(0, step_size)
                t_new = t + np.random.normal(0, step_size)

                # Project to feasible region (s,t >=0, s+t<=1)
                s_new = max(0.0, min(1.0, s_new))
                t_new = max(0.0, min(1.0, t_new))
                if s_new + t_new > 1.0:
                    scale = 1.0 / (s_new + t_new)
                    s_new *= scale
                    t_new *= scale

                # Transform back to Cartesian
                new_p = A + s_new * AB + t_new * AC
                candidate = current.copy()
                candidate[idx] = new_p

                # Evaluate candidate
                candidate_score = get_smallest_triangle_area(candidate)

                # Simulated annealing acceptance
                temp = initial_temp * (cooling_rate ** i)
                if candidate_score > current_score:
                    accept = True
                else:
                    delta = current_score - candidate_score
                    accept_prob = np.exp(-delta / temp)
                    accept = np.random.rand() < accept_prob

                if accept:
                    current = candidate
                    current_score = candidate_score
                    if candidate_score > best_score:
                        best_score = candidate_score
                        best_overall = candidate

        return best_overall

    return improve