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
        
        initial_temp = 0.1
        cooling_rate = 0.999
        initial_step = 0.05
        max_iter = 1000
        epsilon = 1e-5
        
        temperature = initial_temp
        step_size = initial_step

        for _ in range(max_iter):
            # Find all near-minimal triangles
            n = len(current)
            min_area = float('inf')
            all_triangles = []  # (i, j, k, area)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = current[i]
                        x2, y2 = current[j]
                        x3, y3 = current[k]
                        area_val = 0.5 * abs((x2 - x1)*(y3 - y1) - (x3 - x1)*(y2 - y1))
                        all_triangles.append((i, j, k, area_val))
                        if area_val < min_area:
                            min_area = area_val
            
            near_minimal = [tri for tri in all_triangles if tri[3] <= min_area + epsilon]
            if not near_minimal:
                continue

            # Compute gradient contributions from all near-minimal triangles
            grads = np.zeros_like(current)
            for (i, j, k, _) in near_minimal:
                x1, y1 = current[i]
                x2, y2 = current[j]
                x3, y3 = current[k]
                D = (x2 - x1)*(y3 - y1) - (x3 - x1)*(y2 - y1)
                multiplier = 1.0 if D >= 0 else -1.0

                grads[i] += multiplier * np.array([y2 - y3, x3 - x2])
                grads[j] += multiplier * np.array([y3 - y1, x1 - x3])
                grads[k] += multiplier * np.array([y1 - y2, x2 - x1])

            # Create candidate by moving points along gradient directions
            candidate = current.copy()
            for idx in range(n):
                grad_norm = np.linalg.norm(grads[idx])
                if grad_norm > 1e-8:
                    direction = grads[idx] / grad_norm
                    candidate[idx] += step_size * direction

            # Project out-of-bound points
            for idx in range(n):
                if not is_inside_triangle([candidate[idx]], A, B, C):
                    base = current[idx]
                    direction_vec = candidate[idx] - base
                    t_low, t_high = 0.0, 1.0
                    for _ in range(10):
                        t_mid = (t_low + t_high) / 2
                        mid_point = base + t_mid * direction_vec
                        if is_inside_triangle([mid_point], A, B, C):
                            t_low = t_mid
                        else:
                            t_high = t_mid
                    candidate[idx] = base + t_low * direction_vec

            new_score = get_smallest_triangle_area(candidate)
            delta = new_score - current_score

            # Simulated annealing acceptance
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate.copy()
                    best_score = new_score

            # Decay parameters
            temperature *= cooling_rate
            step_size *= cooling_rate

        return best

    return improve