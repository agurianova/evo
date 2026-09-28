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
        
        # Adaptive iteration count using square-root gap scaling (replaces fixed cap)
        gap = 0.0365 - initial_score
        max_iter = 1000 + int(10000 * (gap / 0.0365)**0.5)

        pool = [(initial_score, points.copy())]

        current = points.copy()
        current_score = initial_score

        # Adaptive initial temperature based on gap
        initial_temp = 0.1 * (0.0365 - initial_score)
        temp = initial_temp
        cooling_rate = 0.995
        step_size = 0.1
        no_improve_count = 0
        restart_count = 0

        # For periodic temperature recalibration
        recent_deltas = []

        # Initialize caching for critical triangles
        counts_need_update = True
        critical_counts = None
        critical_triangles = []

        for i in range(max_iter):
            # Enhanced point selection with 5% random exploration
            if np.random.rand() < 0.05:
                idx = np.random.randint(0, n)
            else:
                # Update critical counts if needed
                if counts_need_update:
                    critical_counts = np.zeros(n, dtype=int)
                    critical_triangles = []
                    # Exponential decay threshold (replaces linear interpolation)
                    if current_score < 1e-9:
                        threshold = 1e-9
                    else:
                        exponent = current_score / 0.0365
                        relative_factor = 0.05 * (0.001 / 0.05) ** exponent
                        relative_factor = max(0.001, min(0.05, relative_factor))
                        threshold = relative_factor * current_score
                        if threshold < 1e-9:
                            threshold = 1e-9
                    for i_inner in range(n):
                        for j in range(i_inner+1, n):
                            for k in range(j+1, n):
                                p1, p2, p3 = current[i_inner], current[j], current[k]
                                area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1]))
                                if area <= current_score + threshold:
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
            
            # Compute normalized gap for adaptive parameters
            normalized_gap = (0.0365 - current_score) / 0.0365
            normalized_gap = max(0.0, min(1.0, normalized_gap))
            
            # Adaptive bias weight using normalized gap (replaces linear schedule)
            bias_weight = 0.8 * (1 - normalized_gap)
            
            # Biased perturbation for critical points
            if critical_counts is not None and critical_counts[idx] > 0:
                weighted_dir = np.zeros(2)
                total_weight = 0.0
                for tri in critical_triangles:
                    if idx in tri:
                        i_tri, j, k = tri
                        if i_tri == idx:
                            a, b = current[j], current[k]
                        elif j == idx:
                            a, b = current[i_tri], current[k]
                        else:  # k == idx
                            a, b = current[i_tri], current[j]
                        c = current[idx]
                        base = b - a
                        # Compute signed area * 2
                        S_val = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                        area_tri = 0.5 * abs(S_val)
                        # Weight by inverse distance to min area (replaces unit vector averaging)
                        weight = 1.0 / (area_tri - current_score + 1e-12)
                        sign = 1.0 if S_val >= 0 else -1.0
                        dir_vec = sign * np.array([-base[1], base[0]])
                        weighted_dir += weight * dir_vec
                        total_weight += weight
                
                if total_weight > 0:
                    avg_dir = weighted_dir / total_weight
n                    norm_avg = np.linalg.norm(avg_dir)
                    if norm_avg > 1e-10:
                        avg_unit_dir = avg_dir / norm_avg
                    else:
                        avg_unit_dir = np.array([1, 0])
                else:
                    avg_unit_dir = np.array([1, 0])
                
                random_pert = np.random.normal(0, step_size, 2)
                biased_pert = (1 - bias_weight) * random_pert + bias_weight * (step_size * avg_unit_dir)
                candidate[idx] += biased_pert
            else:
                candidate[idx] += np.random.normal(0, step_size, 2)

            if not is_inside_triangle(candidate[idx], A, B, C):
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
                # Correct boundary projection by perturbing inward (proportional to step_size)
                centroid = (A + B + C) / 3.0
                direction = centroid - candidate[idx]
                norm_dir = np.linalg.norm(direction)
                if norm_dir > 1e-10:
                    direction = direction / norm_dir
                    candidate[idx] = candidate[idx] + (0.01 * step_size) * direction

            new_score = get_smallest_triangle_area(candidate)

            # Maintain larger solution pool (size 10)
            if len(pool) < 10:
                pool.append((new_score, candidate.copy()))
                pool = sorted(pool, key=lambda x: x[0], reverse=True)[:10]
            else:
                if new_score > pool[-1][0]:
                    pool.append((new_score, candidate.copy()))
                    pool = sorted(pool, key=lambda x: x[0], reverse=True)[:10]

            # Track deltas for temperature recalibration
            delta_val = new_score - current_score
            recent_deltas.append(delta_val)
            if len(recent_deltas) > 100:
                recent_deltas.pop(0)

            # Periodic temperature recalibration with gap-dependent multiplier
            if i == 49 or (i > 50 and i % 100 == 0):
                positive_deltas = [d for d in recent_deltas if d > 0]
                if len(positive_deltas) > 0:
                    std_delta = np.std(positive_deltas)
                else:
                    std_delta = 0.01
                # Gap-dependent multiplier (increases as gap narrows)
                multiplier = 2.5 + 1.5 * (1 - normalized_gap)
                temp = max(0.01, multiplier * std_delta)

            delta = new_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temp):
                current = candidate
                current_score = new_score
                no_improve_count = 0
                counts_need_update = True  # Mark counts for update
            else:
                no_improve_count += 1

            temp *= cooling_rate

            # Adaptive restart patience based on current gap (increases as gap narrows)
            patience = max(10, int(50 * (1 - normalized_gap)))

            if no_improve_count >= patience:
                # Restart from best solution in pool
                current_score, config = pool[0]
                current = config.copy()
                no_improve_count = 0
                restart_count += 1
                step_size = 0.1  # Reset step_size to 0.1 on restart

            # Adaptive step size decay (slows during stagnation)
            ratio = no_improve_count / max(1, patience)
            decay_rate = 0.995 + 0.004 * ratio
            step_size = max(0.001, step_size * decay_rate)

        # Post-annealing gradient ascent on critical triangles
        best_score, best_config = pool[0]
        current_grad = best_config.copy()
        best_grad_score = best_score
        best_grad_config = best_config.copy()
        
        for grad_step in range(10):
            # Identify critical triangles with tight threshold
            critical_triangles_grad = []
            for i_inner in range(n):
                for j in range(i_inner+1, n):
                    for k in range(j+1, n):
                        p1, p2, p3 = current_grad[i_inner], current_grad[j], current_grad[k]
                        area_val = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1]))
                        if area_val <= best_grad_score + 1e-9:
                            critical_triangles_grad.append((i_inner, j, k))

            # Compute gradient updates for critical triangles
            grads = np.zeros((n, 2))
            for tri in critical_triangles_grad:
                i_idx, j_idx, k_idx = tri
                p1, p2, p3 = current_grad[i_idx], current_grad[j_idx], current_grad[k_idx]
                S = (p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1])
                sign_S = 1.0 if S >= 0 else -1.0
                
                grad_p1 = 0.5 * sign_S * np.array([p2[1]-p3[1], p3[0]-p2[0]])
                grad_p2 = 0.5 * sign_S * np.array([p3[1]-p1[1], p1[0]-p3[0]])
                grad_p3 = 0.5 * sign_S * np.array([p1[1]-p2[1], p2[0]-p1[0]])
                
                grads[i_idx] += grad_p1
                grads[j_idx] += grad_p2
                grads[k_idx] += grad_p3

            # Apply gradient updates with projection
            step_grad = 0.01 * (1.0 / (grad_step + 1))
            for idx in range(n):
                if np.linalg.norm(grads[idx]) > 1e-10:
                    unit_grad = grads[idx] / np.linalg.norm(grads[idx])
                    current_grad[idx] += step_grad * unit_grad
                
                if not is_inside_triangle(current_grad[idx], A, B, C):
                    current_grad[idx] = project_to_triangle(current_grad[idx], A, B, C)
                    centroid = (A + B + C) / 3.0
                    direction = centroid - current_grad[idx]
                    norm_dir = np.linalg.norm(direction)
                    if norm_dir > 1e-10:
                        direction = direction / norm_dir
                        current_grad[idx] = current_grad[idx] + 0.001 * direction

            # Track best configuration during gradient steps
            new_grad_score = get_smallest_triangle_area(current_grad)
            if new_grad_score > best_grad_score:
                best_grad_score = new_grad_score
                best_grad_config = current_grad.copy()

        return best_grad_config.copy()

    return improve