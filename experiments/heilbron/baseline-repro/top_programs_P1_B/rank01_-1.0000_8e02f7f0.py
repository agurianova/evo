from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import random

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_triangle(p, A, B, C):
        # Compute vectors
        v0 = C - A
        v1 = B - A
        v2 = p - A

        # Compute dot products
        dot00 = np.dot(v0, v0)
        dot01 = np.dot(v0, v1)
        dot02 = np.dot(v0, v2)
        dot11 = np.dot(v1, v1)
        dot12 = np.dot(v1, v2)

        # Compute barycentric coordinates
        invDenom = 1 / (dot00 * dot11 - dot01 * dot01)
        u = (dot11 * dot02 - dot01 * dot12) * invDenom
        v = (dot00 * dot12 - dot01 * dot02) * invDenom
        w = 1 - u - v

        # Check if point is inside
        if u >= 0 and v >= 0 and w >= 0:
            return p

        # Project to edge AB (w=0)
        tAB = np.dot(v2, v1) / dot11
        tAB = np.clip(tAB, 0, 1)
        pAB = A + tAB * v1

        # Project to edge BC (u=0)
        v3 = p - B
        v0_BC = C - B
        dot00_BC = np.dot(v0_BC, v0_BC)
        tBC = np.dot(v3, v0_BC) / dot00_BC
        tBC = np.clip(tBC, 0, 1)
        pBC = B + tBC * v0_BC

        # Project to edge CA (v=0)
        v4 = p - C
        v1_CA = A - C
        dot11_CA = np.dot(v1_CA, v1_CA)
        tCA = np.dot(v4, v1_CA) / dot11_CA
        tCA = np.clip(tCA, 0, 1)
        pCA = C + tCA * v1_CA

        # Compute distances
        dAB = np.linalg.norm(p - pAB)
        dBC = np.linalg.norm(p - pBC)
        dCA = np.linalg.norm(p - pCA)

        # Return closest projection
        if dAB <= dBC and dAB <= dCA:
            return pAB
        elif dBC <= dCA:
            return pBC
        else:
            return pCA

    def improve(points: np.ndarray) -> np.ndarray:
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)

        # Dynamic restart count based on solution quality
        restarts = max(3, min(7, int(4 + 3 * (0.0365 - best_score_overall) / 0.0365)))
        base_step = 0.02
        initial_temp = 0.5
        max_iter = 500

        for r in range(restarts):
            dynamic_target = min(0.0365, 1.5 * best_score_overall)
            
            # Add noise with quality-proportional scaling
            current = best_overall.copy()
            gap = 0.0365 - best_score_overall
            noise_scale = max(0.003, 0.1 * gap * (1 + 0.5 * gap / 0.0365))
            noise = np.random.normal(0, noise_scale, size=current.shape)
            current += noise
            
            # Project any out-of-bounds points
            centroid = (A + B + C) / 3
            for i in range(11):
                for _ in range(10):
                    if is_inside_triangle(current[i:i+1], A, B, C):
                        break
                    current[i] = 0.5 * current[i] + 0.5 * centroid

            # Initialize triangle data structure
            n = 11
            num_triangles = n * (n-1) * (n-2) // 6
            triangle_areas = np.zeros(num_triangles)
            triangle_list = []
            point_to_triangles = [[] for _ in range(n)]
            idx = 0
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = current[i], current[j], current[k]
                        area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        triangle_areas[idx] = area
                        triangle_list.append((i, j, k))
                        point_to_triangles[i].append(idx)
                        point_to_triangles[j].append(idx)
                        point_to_triangles[k].append(idx)
                        idx += 1
            
            current_min = np.min(triangle_areas)
            T = initial_temp
            best_current = current.copy()
            best_current_score = current_min
            stagnation_count = 0

            for it in range(max_iter):
                # Adaptive triangle selection with quality-aware bounds
                gap = max(0.0, 0.0365 - current_min)
                k_val = max(3, min(15, int(12 * gap / 0.0365) + int(0.5 * (1 - current_min / 0.0365) * 10)))
                
                if k_val < num_triangles:
                    idxs = np.argpartition(triangle_areas, k_val-1)[:k_val]
                else:
                    idxs = np.arange(num_triangles)
                
                weights = 1.0 / (triangle_areas[idxs] + 1e-10)
                weights /= np.sum(weights)
                chosen_idx = np.random.choice(idxs, p=weights)
                i, j, k = triangle_list[chosen_idx]
                min_area_val = triangle_areas[chosen_idx]

                if min_area_val < 1e-10:
                    T = T * (0.95 + 0.05 * random.random())
                    continue

                m = np.random.choice([i, j, k])
                base_indices = [idx for idx in [i, j, k] if idx != m]
                base1, base2, p = current[base_indices[0]], current[base_indices[1]], current[m]
                v = base2 - base1
                n_vec = np.array([-v[1], v[0]])
                n_norm = np.linalg.norm(n_vec)
                if n_norm < 1e-10:
                    T = T * (0.95 + 0.05 * random.random())
                    continue
                n_vec = n_vec / n_norm

                w = p - base1
                cross = v[0]*w[1] - v[1]*w[0]
                d = n_vec if cross >= 0 else -n_vec

                # Step size with dual-phase adaptation
                step_size = base_step * (0.7 + 0.3 * (current_min / 0.0365)) * \
                           np.sqrt(dynamic_target / min_area_val) * \
                           (1 - it/max_iter)**0.3
                step_size = max(min(step_size, 0.25), 0.003)

                candidate_point = p + step_size * d
                if not is_inside_triangle(candidate_point.reshape(1,2), A, B, C):
                    candidate_point = project_to_triangle(candidate_point, A, B, C)

                # Save old areas for rollback
                old_areas = []
                for tri_idx in point_to_triangles[m]:
                    old_areas.append(triangle_areas[tri_idx])

                # Update candidate config and triangle areas
                candidate_config = current.copy()
                candidate_config[m] = candidate_point
                for tri_idx in point_to_triangles[m]:
                    i_tr, j_tr, k_tr = triangle_list[tri_idx]
                    a, b, c = candidate_config[i_tr], candidate_config[j_tr], candidate_config[k_tr]
                    area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    triangle_areas[tri_idx] = area_val

                new_score = np.min(triangle_areas)
                delta = new_score - current_min

                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    current = candidate_config
                    current_min = new_score
                    if new_score > best_current_score:
                        best_current = current.copy()
                        best_current_score = new_score
                        stagnation_count = 0
                    else:
                        stagnation_count += 1
                else:
                    # Restore old areas
                    for idx, tri_idx in enumerate(point_to_triangles[m]):
                        triangle_areas[tri_idx] = old_areas[idx]
                    stagnation_count += 1

                # Quality-aware reheating with perturbation
                if stagnation_count >= 50:
                    T = initial_temp * (0.4 + 0.2 * (best_current_score / 0.0365))
                    # Add small random perturbation to current points
                    perturbation = np.random.normal(0, 0.005, size=current.shape)
                    current += perturbation
                    # Re-project any out-of-bounds points
n                    for i in range(11):
                        for _ in range(10):
                            if is_inside_triangle(current[i:i+1], A, B, C):
                                break
                            current[i] = 0.5 * current[i] + 0.5 * centroid
                    # Recompute all triangle areas after perturbation
                    idx = 0
                    for i in range(n):
                        for j in range(i+1, n):
                            for k in range(j+1, n):
                                a, b, c = current[i], current[j], current[k]
                                area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                                triangle_areas[idx] = area
                                idx += 1
                    current_min = np.min(triangle_areas)
                    stagnation_count = 0

                # Adaptive cooling rate based on improvement rate
                if it > 0 and it % 50 == 0:
                    improvement_rate = (current_min - best_current_score) / (0.0365 - best_current_score + 1e-10)
                    cooling_rate = 0.95 + 0.04 * (1 - max(0, min(1, improvement_rate)))
                else:
                    cooling_rate = 0.98
                
                T = T * cooling_rate

            if best_current_score > best_score_overall:
                best_overall = best_current.copy()
                best_score_overall = best_current_score

        return best_overall

    return improve