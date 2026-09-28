from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)

        restarts = 10
        initial_temp = 0.5
        cooling_rate = 0.995  # Changed from 0.98 to prevent premature convergence
        max_iter = 2000

        for r in range(restarts):
            if r == 0:
                current = best_overall.copy()
            else:
                current = best_overall.copy()
                noise_scale = 0.5 * (0.0365 - best_score_overall)
                noise_scale = max(1e-5, noise_scale)
                # Noise decreases with restart number for proper annealing
                noise = np.random.normal(0, noise_scale * (restarts - r) / restarts, size=current.shape)
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
                triangles = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            a, b, c = current[i], current[j], current[k]
                            area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                            triangles.append((area, i, j, k))
                triangles.sort(key=lambda x: x[0])
                k = 5  # Changed from 3 to 5 to balance focus and exploration
                top_triangles = triangles[:k]
                chosen_idx = np.random.randint(0, len(top_triangles))
                min_area_val, i, j, k_val = top_triangles[chosen_idx]
                min_idx = (i, j, k_val)

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

                dynamic_target = min(0.0365, 1.05 * best_current_score)
                base_length = np.linalg.norm(base2 - base1)
                if base_length < 1e-10:
                    continue
                if dynamic_target <= min_area_val:
                    continue
                step_size = (2 * (dynamic_target - min_area_val)) / base_length
                step_size = min(step_size, 0.2)

                # Find maximum feasible step size via binary search
                low_bound = 0.0
                high_bound = step_size
                for _ in range(5):
                    mid = (low_bound + high_bound) / 2
                    candidate_point = p + mid * d
                    if is_inside_triangle(candidate_point.reshape(1,2), A, B, C):
                        low_bound = mid
                    else:
                        high_bound = mid
                max_step = low_bound

                # Line search: evaluate current (0), half, and full step
                candidates = [(0.0, current, current_score)]
                for s in [max_step/2, max_step]:
                    candidate_point = p + s * d
n                    candidate_config = current.copy()
                    candidate_config[m] = candidate_point
                    score = get_smallest_triangle_area(candidate_config)
                    candidates.append((s, candidate_config, score))
                
                # Select best candidate from line search
                s_best, candidate_config, new_score = max(candidates, key=lambda x: x[2])

                delta = new_score - current_score

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