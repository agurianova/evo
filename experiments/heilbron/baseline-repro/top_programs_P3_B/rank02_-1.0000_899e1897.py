from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

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

    def improve(points: np.ndarray) -> np.ndarray:
        n = len(points)
        initial_score = get_smallest_triangle_area(points)
        gap = 0.0365 - initial_score
        
        # Compute base seed from input points for RNG
        base_seed = hash(tuple(map(tuple, points))) % 1000000
        
        # Change 1: Corrected and widened threshold factor
        threshold_factor = 1.0 + 0.2 * (gap / 0.0365)
        
        # Change 3: Fixed bias timing logic
        bias_center_val = 0.8 - 0.2 * (gap / 0.0365)
        
        max_iter = 5000 + int((1 - gap / 0.0365) * 3000)
        max_iter = min(8000, max_iter)
        
        global_pool = [(initial_score, points.copy())]
        chains = 3
        chain_states = []
        
        for chain_id in range(chains):
            # Change 2: Input-dependent RNG seeding
            rng = np.random.default_rng(seed=base_seed + chain_id)
            state = {
                'current': points.copy(),
                'current_score': initial_score,
                'temp': 0.1 * gap,
                'step_size': 0.1,
                'no_improve_count': 0,
                'restart_count': 0,
                'recent_deltas': [],
                'counts_need_update': True,
                'critical_counts': None,
                'critical_triangles': [],
                'rng': rng
            }
            chain_states.append(state)

        for i in range(max_iter):
            for state in chain_states:
                current = state['current']
                current_score = state['current_score']
                temp = state['temp']
                step_size = state['step_size']
                no_improve_count = state['no_improve_count']
                recent_deltas = state['recent_deltas']
                counts_need_update = state['counts_need_update']
                critical_counts = state['critical_counts']
                critical_triangles = state['critical_triangles']
                rng = state['rng']

                exploration_rate = 0.05 * (1 + min(1.0, no_improve_count / 10))
                if rng.random() < exploration_rate:
                    idx = rng.integers(0, n)
                else:
                    if counts_need_update:
                        critical_counts = np.zeros(n, dtype=int)
                        critical_triangles = []
                        for i_inner in range(n):
                            for j in range(i_inner+1, n):
                                for k in range(j+1, n):
                                    p1, p2, p3 = current[i_inner], current[j], current[k]
                                    area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1]))
                                    # Change 1: Corrected threshold factor
                                    if area <= current_score * threshold_factor:
                                        critical_counts[i_inner] += 1
                                        critical_counts[j] += 1
                                        critical_counts[k] += 1
                                        critical_triangles.append((i_inner, j, k))
                        counts_need_update = False
                        state['critical_counts'] = critical_counts
                        state['critical_triangles'] = critical_triangles

                    total_count = np.sum(critical_counts)
                    if total_count == 0:
                        idx = rng.integers(0, n)
                    else:
                        probs = critical_counts / total_count
                        idx = rng.choice(n, p=probs)

                candidate = current.copy()
                
                # Dynamic bias weight with corrected timing
                progress = i / max_iter
                # Change 3: Fixed bias timing
                bias_weight = 0.2 + 0.6 * (1 / (1 + np.exp(-5 * (progress - bias_center_val))))

                if critical_counts is not None and critical_counts[idx] > 0:
                    directions = []
                    for tri in critical_triangles:
                        if idx in tri:
                            i_idx, j, k = tri
                            if i_idx == idx:
                                a, b = current[j], current[k]
                            elif j == idx:
                                a, b = current[i_idx], current[k]
                            else:
                                a, b = current[i_idx], current[j]
                            c = current[idx]
                            base = b - a
                            S_val = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                            sign = 1.0 if S_val >= 0 else -1.0
                            dir_vec = sign * np.array([-base[1], base[0]])
                            norm_dir = np.linalg.norm(dir_vec)
                            if norm_dir > 1e-10:
                                unit_dir = dir_vec / norm_dir
                                directions.append(unit_dir)
                    if directions:
                        avg_dir = np.mean(directions, axis=0)
                        norm_avg = np.linalg.norm(avg_dir)
                        if norm_avg > 1e-10:
                            avg_unit_dir = avg_dir / norm_avg
                        else:
                            avg_unit_dir = np.array([1, 0])
                    else:
                        avg_unit_dir = np.array([1, 0])
                    random_pert = rng.normal(0, step_size, 2)
                    biased_pert = (1 - bias_weight) * random_pert + bias_weight * (step_size * avg_unit_dir)
                    candidate[idx] += biased_pert
                else:
                    candidate[idx] += rng.normal(0, step_size, 2)

                if not is_inside_triangle(candidate[idx], A, B, C):
                    candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
                    centroid = (A + B + C) / 3.0
                    direction = centroid - candidate[idx]
                    norm_dir = np.linalg.norm(direction)
                    if norm_dir > 1e-10:
                        direction = direction / norm_dir
                        candidate[idx] = candidate[idx] + 1e-5 * direction

                new_score = get_smallest_triangle_area(candidate)

                # Change 5: Enhanced pool diversity maintenance
                global_pool.append((new_score, candidate.copy()))
                if len(global_pool) > 20:
                    global_pool_sorted = sorted(global_pool, key=lambda x: x[0], reverse=True)
                    selected = global_pool_sorted[:5]
                    remaining = global_pool_sorted[5:]
                    diverse_selected = []
                    selected_set = selected[:]
                    for _ in range(5):
                        if not remaining:
                            break
                        best_candidate = None
                        best_min_dist = -1
                        for cand in remaining:
                            min_dist = float('inf')
                            for s in selected_set:
                                dist = np.linalg.norm(cand[1] - s[1])
                                if dist < min_dist:
                                    min_dist = dist
                            if min_dist > best_min_dist:
                                best_min_dist = min_dist
                                best_candidate = cand
                        if best_candidate:
                            diverse_selected.append(best_candidate)
                            remaining.remove(best_candidate)
                            selected_set.append(best_candidate)
                    global_pool = selected + diverse_selected
                    global_pool = global_pool[:10]

                delta_val = new_score - current_score
                recent_deltas.append(delta_val)
                if len(recent_deltas) > 100:
                    recent_deltas.pop(0)
                state['recent_deltas'] = recent_deltas

                # Change 4: Removed temperature recalibration block

                delta = new_score - current_score
                if delta > 0 or rng.random() < np.exp(delta / temp):
                    current = candidate
                    current_score = new_score
                    no_improve_count = 0
                    counts_need_update = True
                else:
                    no_improve_count += 1

                state['current'] = current
                state['current_score'] = current_score
                state['no_improve_count'] = no_improve_count
                state['counts_need_update'] = counts_need_update
                state['temp'] = temp * 0.995
                # Change 4: Slowed step decay rate
                step_size = max(0.001, step_size * 0.9995)
                state['step_size'] = step_size

            # Periodic chain replacement every 100 iterations
            if i % 100 == 0 and i > 0:
                global_best_score, global_best_points = global_pool[0]
                worst_chain_index = np.argmin([s['current_score'] for s in chain_states])
                chain_states[worst_chain_index]['current'] = global_best_points.copy()
                chain_states[worst_chain_index]['current_score'] = global_best_score
                chain_states[worst_chain_index]['no_improve_count'] = 0
                chain_states[worst_chain_index]['restart_count'] += 1
                chain_states[worst_chain_index]['recent_deltas'] = []
                chain_states[worst_chain_index]['counts_need_update'] = True
                chain_states[worst_chain_index]['step_size'] = 0.1

        return global_pool[0][1].copy()

    return improve