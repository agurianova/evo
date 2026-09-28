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
        max_iter = 2000

        for r in range(restarts):
            if r == 0:
                current = best_overall.copy()
            else:
                current = best_overall.copy()
                # Decreasing noise scale across restarts for proper exploration->exploitation
                noise_scale = 0.5 * (0.0365 - best_score_overall)
                noise_scale = max(1e-5, noise_scale * (1 - r/restarts))
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
            
            # Track acceptance rate for adaptive cooling
            acceptance_window = 100
            recent_acceptances = []

            for it in range(max_iter):
                # Get all triangles using helper function for efficiency
                all_triangles = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            all_triangles.append((i, j, k))
                
                # Probabilistic selection based on inverse area
                areas = []
                for (i, j, k) in all_triangles:
                    a, b, c = current[i], current[j], current[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    areas.append(area)
                
                # Softmax selection with adaptive temperature
                adaptive_temp = max(0.001, T * 0.1)
                weights = np.exp(-np.array(areas) / adaptive_temp)
                weights /= np.sum(weights)
                
                # Select triangle based on weights
                triangle_idx = np.random.choice(len(all_triangles), p=weights)
                i, j, k_val = all_triangles[triangle_idx]
                min_area_val = areas[triangle_idx]
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

                # Golden section search for optimal step size
                phi = (1 + np.sqrt(5)) / 2  # Golden ratio
                resphi = 2 - phi
                
                # Define bounds for step size
                low = 0.0
                high = 0.5  # Maximum reasonable step size
                
                # Initial points for golden section search
                x1 = high - resphi * (high - low)
                x2 = low + resphi * (high - low)
                
                # Evaluate at initial points
                candidate1 = p + x1 * d
                candidate2 = p + x2 * d
                
                # Check boundaries
                if not is_inside_triangle(candidate1.reshape(1,2), A, B, C):
                    high = x1
                    x1 = x2
                    x2 = high - resphi * (high - low)
                elif not is_inside_triangle(candidate2.reshape(1,2), A, B, C):
                    low = x2
                    x2 = x1
                    x1 = low + resphi * (high - low)
                
                # Golden section search iterations
                for _ in range(8):  # 8 iterations gives good precision
                    if high - low < 1e-7:
                        break
                        
                    candidate1 = p + x1 * d
                    candidate2 = p + x2 * d
                    
                    # Ensure points are inside triangle
                    if not is_inside_triangle(candidate1.reshape(1,2), A, B, C):
                        candidate_config1 = current.copy()
                        low, high = 0.0, x1
                        for _ in range(5):
                            mid = (low + high) / 2
                            if is_inside_triangle((p + mid * d).reshape(1,2), A, B, C):
                                low = mid
                            else:
                                high = mid
                        x1 = low
                        candidate1 = p + x1 * d
                    
                    if not is_inside_triangle(candidate2.reshape(1,2), A, B, C):
                        candidate_config2 = current.copy()
                        low, high = 0.0, x2
                        for _ in range(5):
                            mid = (low + high) / 2
                            if is_inside_triangle((p + mid * d).reshape(1,2), A, B, C):
                                low = mid
                            else:
                                high = mid
                        x2 = low
                        candidate2 = p + x2 * d

                    # Create candidate configurations
                    candidate_config1 = current.copy()
                    candidate_config1[m] = candidate1
                    score1 = get_smallest_triangle_area(candidate_config1)

                    candidate_config2 = current.copy()
                    candidate_config2[m] = candidate2
                    score2 = get_smallest_triangle_area(candidate_config2)

                    if score1 < score2:
                        low = x1
                        x1 = x2
                        x2 = low + resphi * (high - low)
                    else:
                        high = x2
                        x2 = x1
                        x1 = high - resphi * (high - low)

                # Use the best point found
                best_x = (low + high) / 2
                candidate_point = p + best_x * d
                
                # Final boundary check
                if not is_inside_triangle(candidate_point.reshape(1,2), A, B, C):
                    low, high = 0.0, best_x
                    for _ in range(5):
                        mid = (low + high) / 2
                        if is_inside_triangle((p + mid * d).reshape(1,2), A, B, C):
                            low = mid
                        else:
                            high = mid
                    candidate_point = p + low * d

                candidate_config = current.copy()
                candidate_config[m] = candidate_point
                new_score = get_smallest_triangle_area(candidate_config)
                delta = new_score - current_score

                # Track acceptance for adaptive cooling
                accepted = delta > 0 or (T > 1e-5 and np.random.rand() < np.exp(delta / T))
                recent_acceptances.append(1 if accepted else 0)
                if len(recent_acceptances) > acceptance_window:
                    recent_acceptances.pop(0)

                # Adaptive cooling rate based on recent acceptance rate
                if len(recent_acceptances) == acceptance_window:
                    acceptance_rate = sum(recent_acceptances) / acceptance_window
n                    if acceptance_rate > 0.4:
                        cooling_rate = 0.995  # Slow cooling when many moves accepted
                    elif acceptance_rate > 0.1:
                        cooling_rate = 0.98
                    else:
                        cooling_rate = 0.95  # Faster cooling when stuck
                else:
                    cooling_rate = 0.98

                if accepted:
                    current = candidate_config
                    current_score = new_score
                    if new_score > best_current_score:
                        best_current = current.copy()
                        best_current_score = new_score

                T = T * cooling_rate
                if T < 1e-5:
                    T = 1e-5

            if best_current_score > best_score_overall:
                best_overall = best_current.copy()
                best_score_overall = best_current_score

        return best_overall

    return improve