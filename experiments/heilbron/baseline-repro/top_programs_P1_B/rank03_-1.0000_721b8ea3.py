from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)

        restarts = 3
        base_step = 0.01
        initial_temp = 0.5
        cooling_rate = 0.99
        max_iter = 1000

        for r in range(restarts):
            if r == 0:
                current = best_overall.copy()
            else:
                current = best_overall.copy()
                gap = 0.0365 - best_score_overall
                base_noise_scale = max(0.02, 0.1 * gap)
                noise_scale = base_noise_scale * (r + 1)
                noise = np.random.normal(0, noise_scale, size=current.shape)
                current += noise
                centroid = (A + B + C) / 3
                for i in range(11):
                    for _ in range(10):
                        if is_inside_triangle(current[i:i+1], A, B, C):
                            break
                        current[i] = 0.5 * current[i] + 0.5 * centroid

            T = initial_temp
            current_score = get_smallest_triangle_area(current)
            best_current = current.copy()
            best_current_score = current_score

            for it in range(max_iter):
                min_area_val = float('inf')
                min_idx = None
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            a, b, c = current[i], current[j], current[k]
                            area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                            if area < min_area_val:
                                min_area_val = area
                                min_idx = (i, j, k)

                if min_area_val < 1e-10:
                    continue

                m = np.random.choice(min_idx)
                base_indices = [idx for idx in min_idx if idx != m]
                base1, base2, p = current[base_indices[0]], current[base_indices[1]], current[m]
                v = base2 - base1
                n = np.array([-v[1], v[0]])
                n_norm = np.linalg.norm(n)
                if n_norm < 1e-10:
                    continue
                n = n / n_norm

                w = p - base1
                cross = v[0]*w[1] - v[1]*w[0]
                d = n if cross >= 0 else -n

                ratio = 0.0365 / min_area_val
                step_ratio = min(2.0, ratio)
                step_size = base_step * step_ratio
                step_size = np.clip(step_size, 0.01, 0.2)

                candidate_point = p + step_size * d
                candidate_config = current.copy()
                candidate_config[m] = candidate_point

                if not is_inside_triangle(candidate_config[m:m+1], A, B, C):
                    temp_step = step_size
n                    found = False
                    for _ in range(5):
                        temp_step *= 0.5
                        candidate_point = p + temp_step * d
                        if is_inside_triangle(candidate_point.reshape(1,2), A, B, C):
                            candidate_config[m] = candidate_point
                            found = True
                            break
                    if not found:
                        T = T * cooling_rate
                        continue

                new_score = get_smallest_triangle_area(candidate_config)
                delta = new_score - min_area_val

                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    current = candidate_config
                    current_score = new_score
                    if new_score > best_current_score:
                        best_current = current.copy()
                        best_current_score = new_score

                T = T * cooling_rate

            if best_current_score > best_score_overall:
                best_overall = best_current.copy()
                best_score_overall = best_current_score

        return best_overall

    return improve