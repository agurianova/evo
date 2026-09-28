from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)

        # Adaptive restart count with increased minimum
        gap_ratio = 1.0 - best_score_overall / 0.0365
        restarts = max(5, min(10, 1 + int(5 * gap_ratio)))
        
        base_step = 0.274  # Increased from 0.01 to enable larger steps
        initial_temp = 0.5
        cooling_rate = 0.95
        max_iter = 500

        for r in range(restarts):
            if r == 0:
                current = best_overall.copy()
            else:
                current = best_overall.copy()
                gap = 0.0365 - best_score_overall
                noise_scale = 0.5 * gap  # Increased multiplier, no lower bound
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
                triangles = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            a, b, c = current[i], current[j], current[k]
                            area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                            triangles.append((area, i, j, k))
                
                triangles.sort(key=lambda x: x[0])
                top_k = 1  # Always focus on the smallest triangle
                top_triangles = triangles[:top_k]
                
                if not top_triangles:
                    break
                    
                min_area_val, i, j, k = top_triangles[0]
                min_idx = (i, j, k)

                if min_area_val < 1e-10:
                    continue

                # Decide between single-point and two-point move
                two_point_move = (np.random.rand() < 0.5)
                candidates_configs = []

                if two_point_move:
                    # Try two-point move on base edge (i,j)
                    base1 = current[i]
                    base2 = current[j]
                    p = current[k]
                    v = base2 - base1
                    n_vec = np.array([-v[1], v[0]])
                    n_norm = np.linalg.norm(n_vec)
                    if n_norm < 1e-10:
                        two_point_move = False  # Fall back to single-point
                    else:
                        n_vec = n_vec / n_norm
                        w = p - base1
                        cross = v[0]*w[1] - v[1]*w[0]
                        d = n_vec if cross >= 0 else -n_vec

                        step_size = base_step * (0.0365 - min_area_val)
                        
                        # Generate candidate by moving base points apart
                        candidate_base1 = base1 - d * (step_size / 2)
                        candidate_base2 = base2 + d * (step_size / 2)
                        
                        # Constraint handling with halving
                        valid = False
                        for halve in range(10):
                            scale = 0.5 ** halve
                            cand1 = base1 - d * (step_size / 2 * scale)
                            cand2 = base2 + d * (step_size / 2 * scale)
                            if is_inside_triangle(cand1.reshape(1,2), A, B, C) and \
                               is_inside_triangle(cand2.reshape(1,2), A, B, C):
                                candidate_base1, candidate_base2 = cand1, cand2
                                valid = True
                                break
                        
                        if valid:
                            candidate_config = current.copy()
                            candidate_config[i] = candidate_base1
                            candidate_config[j] = candidate_base2
                            candidates_configs.append(candidate_config)

                if not two_point_move or not candidates_configs:
                    # Single-point move
                    m = np.random.choice(min_idx)
                    base_indices = [idx for idx in min_idx if idx != m]
                    base1, base2, p = current[base_indices[0]], current[base_indices[1]], current[m]
                    v = base2 - base1
                    n_vec = np.array([-v[1], v[0]])
                    n_norm = np.linalg.norm(n_vec)
                    if n_norm < 1e-10:
                        continue
                    n_vec = n_vec / n_norm

                    w = p - base1
                    cross = v[0]*w[1] - v[1]*w[0]
                    d = n_vec if cross >= 0 else -n_vec

                    step_size = base_step * (0.0365 - min_area_val)

                    # Generate candidate directions
                    for _ in range(3):
                        angle = np.random.uniform(-np.pi/12, np.pi/12)
                        rot = np.array([
                            [np.cos(angle), -np.sin(angle)],
                            [np.sin(angle), np.cos(angle)]
                        ])
                        d_rot = rot @ d
                        candidate_point = p + step_size * d_rot
                        
                        # Constraint handling
                        valid = False
                        for halve in range(10):
                            scale = 0.5 ** halve
                            temp_point = p + step_size * scale * d_rot
n                            if is_inside_triangle(temp_point.reshape(1,2), A, B, C):
                                candidate_point = temp_point
                                valid = True
                                break
                        
                        if valid:
                            candidate_config = current.copy()
                            candidate_config[m] = candidate_point
                            candidates_configs.append(candidate_config)

                # Evaluate all valid candidates
                best_candidate_config = None
                best_new_score = -1
                for candidate_config in candidates_configs:
                    new_score = get_smallest_triangle_area(candidate_config)
                    if new_score > best_new_score:
                        best_new_score = new_score
                        best_candidate_config = candidate_config

                if best_candidate_config is None:
                    T = T * cooling_rate
                    continue

                new_score = best_new_score
                delta = new_score - current_score

                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    current = best_candidate_config
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