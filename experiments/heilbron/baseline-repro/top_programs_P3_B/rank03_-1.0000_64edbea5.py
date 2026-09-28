from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        def project_to_segment(p, v1, v2):
            v = v2 - v1
            w = p - v1
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 < 1e-12:
                return v1
            b = c1 / c2
            if b <= 0:
                return v1
            elif b >= 1:
                return v2
            else:
                return v1 + b * v

        def project_to_triangle(p, A, B, C):
            if is_inside_triangle(p, A, B, C):
                return p
            edges = [(A, B), (B, C), (C, A)]
            best_point = None
            best_dist = float('inf')
            for edge in edges:
                v1, v2 = edge
                proj = project_to_segment(p, v1, v2)
                dist = np.linalg.norm(p - proj)
                if dist < best_dist:
                    best_dist = dist
                    best_point = proj
            return best_point

        n = len(points)
        initial_score = get_smallest_triangle_area(points)
        
        # ENHANCED: Dynamic iteration budget allocation based on problem difficulty
        difficulty_factor = min(1.0, (0.0365 - initial_score) / 0.0365)
        max_iter = 2000 + int(difficulty_factor * (8000 + 3000 * difficulty_factor))
        max_iter = min(15000, max_iter)

        # DYNAMIC pool size based on problem difficulty
        pool_size = max(5, min(20, 5 + int(15 * difficulty_factor)))
        pool = [(initial_score, points.copy())]

        current = points.copy()
        current_score = initial_score

        # Adaptive initial temperature with minimum floor
        initial_temp = max(0.01, 0.5 * (0.0365 - initial_score))
        temp = initial_temp
        cooling_rate = 0.995
        step_size = 0.1
        patience = 20
        no_improve_count = 0
        restart_count = 0

        # For periodic temperature recalibration
        recent_deltas = []

        # Initialize caching for critical triangles
        counts_need_update = True
        critical_counts = None
        critical_triangles = []

        for i in range(max_iter):
            # Compute current gap for adaptive strategies
            gap_val = max(0.0, 0.0365 - current_score)
            
            # ADAPTIVE STEP SIZE CEILING BASED ON PROBLEM DIFFICULTY
            max_step = min(0.7, 0.3 + 0.4 * (gap_val / 0.0365))

            # Periodic critical triangle recalculation
            if i % 50 == 0:
                counts_need_update = True

            # DYNAMIC exploration rate: INVERTED to increase near optimum
            exploration_rate = 0.02 + 0.13 * (1 - gap_val / 0.0365)
            if np.random.rand() < exploration_rate:
                idx = np.random.randint(0, n)
            else:
                # Update critical counts if needed
                if counts_need_update:
                    critical_counts = np.zeros(n, dtype=int)
                    critical_triangles = []
                    
                    # ADAPTIVE THRESHOLD TUNING: dynamically scale based on gap
                    multiplier = 0.1 - 0.05 * (gap_val / 0.0365)
                    threshold_val = max(1e-4, multiplier * gap_val)
                    
                    for i_inner in range(n):
                        for j in range(i_inner+1, n):
                            for k in range(j+1, n):
                                p1, p2, p3 = current[i_inner], current[j], current[k]
                                area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1]))
                                if area <= current_score + threshold_val:
                                    critical_counts[i_inner] += 1
                                    critical_counts[j] += 1
                                    critical_counts[k] += 1
                                    critical_triangles.append((i_inner, j, k))
                    counts_need_update = False

                total_count = np.sum(critical_counts)
                if total_count == 0:
                    idx = np.random.randint(0, n)
                else:
                    probs = critical_counts / total_count
                    idx = np.random.choice(n, p=probs)

            candidate = current.copy()
            
            # Biased perturbation for critical points
            if critical_counts is not None and critical_counts[idx] > 0:
                directions = []
                weights = []
                for tri in critical_triangles:
                    if idx in tri:
                        i, j, k = tri
                        if i == idx:
                            a, b = current[j], current[k]
                        elif j == idx:
                            a, b = current[i], current[k]
                        else:  # k == idx
                            a, b = current[i], current[j]
                        c = current[idx]
                        base = b - a
                        # Compute signed area * 2
                        S_val = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                        sign = 1.0 if S_val >= 0 else -1.0
                        dir_vec = sign * np.array([-base[1], base[0]])
                        norm_dir = np.linalg.norm(dir_vec)
                        if norm_dir > 1e-10:
                            unit_dir = dir_vec / norm_dir
                            directions.append(unit_dir)
                            # SOFT EXPONENTIAL WEIGHTING for critical triangles
                            area_val = 0.5 * abs(S_val)
                            normalized_gap = (area_val - current_score) / threshold_val
n                            normalized_gap = max(0.0, min(1.0, normalized_gap))
                            weight_val = np.exp(-0.5 * normalized_gap)
                            weights.append(weight_val)
                if directions:
                    # Weighted average by triangle proximity
                    total_weight = sum(weights)
                    if total_weight > 1e-10:
                        weighted_dir = np.zeros(2)
                        for d, w in zip(directions, weights):
                            weighted_dir += w * d
                        avg_dir = weighted_dir / total_weight
                    else:
                        avg_dir = np.array([1, 0])
                    norm_avg = np.linalg.norm(avg_dir)
                    if norm_avg > 1e-10:
                        avg_unit_dir = avg_dir / norm_avg
                    else:
                        avg_unit_dir = np.array([1, 0])
                else:
                    avg_unit_dir = np.array([1, 0])
                
                # INVERTED BIAS WEIGHT TO STRENGTHEN GUIDANCE WHEN FAR FROM OPTIMUM
                bias_weight = 0.8 * (gap_val / 0.0365)
                
                random_pert = np.random.normal(0, step_size, 2)
                biased_pert = (1 - bias_weight) * random_pert + bias_weight * (step_size * avg_unit_dir)
                candidate[idx] += biased_pert
            else:
                candidate[idx] += np.random.normal(0, step_size, 2)

            if not is_inside_triangle(candidate[idx], A, B, C):
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
                # Correct boundary projection by perturbing inward
                centroid = (A + B + C) / 3.0
                direction = centroid - candidate[idx]
                norm_dir = np.linalg.norm(direction)
                if norm_dir > 1e-10:
                    direction = direction / norm_dir
                    # ADAPTIVE BOUNDARY NUDGE with minimum safety margin
                    nudge = max(0.001, 0.005 * (1 - gap_val / 0.0365)) * step_size
                    candidate[idx] = candidate[idx] + nudge * direction

            new_score = get_smallest_triangle_area(candidate)

            # MAINTAIN DIVERSE SOLUTION POOL WITH COMBINED SCORE
            if len(pool) < pool_size:
                pool.append((new_score, candidate.copy()))
            else:
                # Recalculate combined score (0.7*score + 0.3*diversity) for entire candidate set
                candidates_list = pool + [(new_score, candidate.copy())]
                n_candidates = len(candidates_list)
                min_dists = []
                for i in range(n_candidates):
                    min_dist = float('inf')
                    for j in range(n_candidates):
                        if i == j:
                            continue
                        dist = np.linalg.norm(candidates_list[i][1] - candidates_list[j][1])
                        if dist < min_dist:
                            min_dist = dist
                    min_dists.append(min_dist)
                
                max_dist = max(min_dists) if min_dists else 1.0
                if max_dist < 1e-10:
                    normalized_dists = [1.0] * n_candidates
                else:
                    normalized_dists = [d / max_dist for d in min_dists]
                
                combined_scores = [0.7 * score + 0.3 * nd for (score, _), nd in zip(candidates_list, normalized_dists)]
                sorted_indices = np.argsort(combined_scores)[::-1]
                pool = [candidates_list[i] for i in sorted_indices[:pool_size]]

            # Track deltas for temperature recalibration
            delta_val = new_score - current_score
            recent_deltas.append(delta_val)
            if len(recent_deltas) > 100:
                recent_deltas.pop(0)

            # ADAPTIVE temperature recalibration based on stagnation
            if no_improve_count >= 30 and no_improve_count % 30 == 0:
                positive_deltas = [d for d in recent_deltas if d > 0]
                if len(positive_deltas) > 0:
                    std_delta = np.std(positive_deltas)
                else:
                    std_delta = 0.01
                temp = max(0.01, 2.5 * std_delta)

            delta = new_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temp):
                current = candidate
                current_score = new_score
                no_improve_count = 0
                counts_need_update = True  # Mark counts for update
                
                # DYNAMIC step size adaptation: increase more when stagnation high
                step_increase_factor = 0.05 + 0.03 * min(1.0, no_improve_count / patience)
                step_size = min(max_step, step_size * (1.0 + step_increase_factor * (gap_val / 0.0365)))
            else:
                no_improve_count += 1
                # DYNAMIC step size adaptation: decrease less when stagnation high
                step_decrease_factor = 0.90 - 0.05 * min(1.0, no_improve_count / patience)
                step_size = max(0.0001, step_size * (step_decrease_factor + 0.05 * (gap_val / 0.0365)))

            temp *= cooling_rate

            if no_improve_count >= patience:
                # Restart from best solution in pool
                current_score, config = pool[0]
                current = config.copy()
                no_improve_count = 0
                restart_count += 1

        return pool[0][1].copy()

    return improve