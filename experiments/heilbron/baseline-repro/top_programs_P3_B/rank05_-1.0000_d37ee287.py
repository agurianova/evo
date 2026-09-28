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
        
        # ADAPTIVE iteration allocation based on historical improvement success
        # Calculate base iteration count from historical improvement rate
        improvement_gap = 0.0365 - initial_score
        # Use sigmoid to scale base_iter between 500-2000 based on improvement_gap
        base_iter = 500 + 1500 / (1 + np.exp(-10 * (improvement_gap / 0.0365 - 0.5)))
        
        # Calculate dynamic iteration range based on historical success rate
        # If we've had success improving similar gaps before, allocate more iterations
        historical_success_rate = min(1.0, max(0.1, 0.5 + (initial_score - 0.02) * 10))
        iter_range = 2000 * historical_success_rate
        
        max_iter = int(base_iter + ((0.0365 - initial_score) / 0.0365) * iter_range)
        max_iter = min(10000, max(500, max_iter))

        pool = [(initial_score, points.copy())]

        current = points.copy()
        current_score = initial_score

        # ADAPTIVE temperature initialization based on landscape ruggedness
        # Scale factor now depends on expected difficulty
        ruggedness_factor = 1.0 / (0.1 + improvement_gap)
        initial_temp = max(0.01, 0.08 * ruggedness_factor * improvement_gap)
        temp = initial_temp
        cooling_rate = 0.995
        step_size = 0.1
        patience = 20
        no_improve_count = 0
        restart_count = 0

        # For periodic temperature recalibration
        recent_deltas = []
        improvement_history = []

        # Initialize caching for critical triangles
        counts_need_update = True
        critical_counts = None
        critical_triangles = []
        
        # ADDED diversity tracking for solution pool
        diversity_history = []

        for i in range(max_iter):
            # ADAPTIVE exploration rate based on optimization stage and recent progress
            progress = i / max(max_iter, 1)
            # If we've made recent improvements, reduce exploration
            recent_improvement = np.mean(improvement_history[-20:]) if improvement_history else 0
n            exploration_rate = 0.05 * (1 - progress) + 0.15 * np.exp(-10 * max(recent_improvement, 0))
            exploration_rate = max(0.01, min(0.2, exploration_rate))
            
            if np.random.rand() < exploration_rate:
                idx = np.random.randint(0, n)
            else:
                # Update critical counts if needed
                if counts_need_update:
                    critical_counts = np.zeros(n, dtype=int)
                    critical_triangles = []
                    
                    # ADAPTIVE threshold factor based on historical improvement rates
                    if improvement_history:
                        # Calculate adaptive threshold factor (0.005-0.02 range)
                        avg_improvement = np.mean(improvement_history)
                        threshold_factor = 0.005 + 0.015 * (1 - min(1.0, avg_improvement / 1e-5))
                    else:
                        threshold_factor = 0.01
                        
                    threshold = threshold_factor * (0.0365 - current_score)
                    threshold = max(1e-9, threshold)
                    
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
            
            # ADAPTIVE directional bias that increases as we approach optimum
            bias_weight = 0.3 + 0.5 * (1 / (1 + np.exp(10 * (current_score - 0.03))))
            
            # IMPROVED perturbation direction calculation with area verification
            if critical_counts is not None and critical_counts[idx] > 0:
                directions = []
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
                        # Compute both perpendicular directions
                        dir1 = np.array([-base[1], base[0]])
                        dir2 = np.array([base[1], -base[0]])
                        
                        # Calculate area change for both directions
                        test_point1 = c + 1e-5 * dir1 / np.linalg.norm(dir1)
                        test_point2 = c + 1e-5 * dir2 / np.linalg.norm(dir2)
                        
                        # Original area
                        orig_area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        # Test area 1
                        test_area1 = 0.5 * abs((b[0]-a[0])*(test_point1[1]-a[1]) - (b[1]-a[1])*(test_point1[0]-a[0]))
                        # Test area 2
                        test_area2 = 0.5 * abs((b[0]-a[0])*(test_point2[1]-a[1]) - (b[1]-a[1])*(test_point2[0]-a[0]))
                        
                        # Choose direction that increases area
                        if test_area1 > orig_area:
                            directions.append(dir1 / np.linalg.norm(dir1))
                        elif test_area2 > orig_area:
                            directions.append(dir2 / np.linalg.norm(dir2))
                        # If neither increases area, skip (should be rare)
                if directions:
                    avg_dir = np.mean(directions, axis=0)
                    norm_avg = np.linalg.norm(avg_dir)
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
                # Correct boundary projection by perturbing inward
                centroid = (A + B + C) / 3.0
                direction = centroid - candidate[idx]
                norm_dir = np.linalg.norm(direction)
                if norm_dir > 1e-10:
                    direction = direction / norm_dir
                    candidate[idx] = candidate[idx] + 1e-5 * direction

            new_score = get_smallest_triangle_area(candidate)

            # ENHANCED solution pool with diversity tracking
            if len(pool) < 5:
                pool.append((new_score, candidate.copy()))
                pool = sorted(pool, key=lambda x: x[0], reverse=True)[:5]
            else:
                # Calculate diversity score against existing pool
                diversity_scores = []
                for _, config in pool:
                    # Hamming distance based on point positions
                    dist = np.mean(np.linalg.norm(candidate - config, axis=1))
                    diversity_scores.append(dist)
                
                min_diversity = min(diversity_scores)
                if new_score > pool[-1][0] or min_diversity > 0.01:
                    # Replace worst if new is better or if it adds diversity
                    if new_score > pool[-1][0]:
                        pool.append((new_score, candidate.copy()))
                    else:
                        # Replace the least diverse point if new point is sufficiently diverse
                        min_idx = np.argmin(diversity_scores)
                        if min_diversity > 0.01:
                            pool[min_idx] = (new_score, candidate.copy())
                    pool = sorted(pool, key=lambda x: x[0], reverse=True)[:5]

            # Track deltas for temperature recalibration
            delta_val = new_score - current_score
            recent_deltas.append(delta_val)
            if delta_val > 0:
                improvement_history.append(delta_val)
            if len(recent_deltas) > 100:
                recent_deltas.pop(0)
            if len(improvement_history) > 200:
                improvement_history.pop(0)

            # Periodic temperature recalibration
            if i == 49 or (i > 50 and i % 100 == 0):
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
            else:
                no_improve_count += 1

            temp *= cooling_rate

            if no_improve_count >= patience:
                # SMART restart: select diverse high-quality solution from pool
                if len(pool) > 1:
                    # Calculate diversity from current best
                    best_score, _ = pool[0]
                    diversity_scores = []
                    for score, config in pool[1:]:
                        # Weight diversity by score difference
                        diversity = np.linalg.norm(current - config)
                        # Prefer diverse configurations with high scores
                        diversity_score = diversity * (score / best_score)
                        diversity_scores.append(diversity_score)
                    
                    if diversity_scores:
                        # Select the most diverse high-quality configuration
                        restart_idx = 1 + np.argmax(diversity_scores)
                        current_score, config = pool[restart_idx]
                        current = config.copy()
                    else:
                        current_score, config = pool[0]
                        current = config.copy()
                else:
                    current_score, config = pool[0]
                    current = config.copy()
                
                no_improve_count = 0
                restart_count += 1
                step_size = 0.1  # Reset step_size to 0.1 on restart

            # ADAPTIVE step size decay based on recent improvement
            if i > 100 and i % 50 == 0:
                recent_improvements = [d for d in recent_deltas[-50:] if d > 0]
                if len(recent_improvements) > 10:
                    avg_improvement = np.mean(recent_improvements)
                    # Faster decay when improvements are small
                    step_decay = 0.995 if avg_improvement < 1e-5 else 0.99
                else:
                    step_decay = 0.995
                step_size = max(0.001, step_size * step_decay)
            else:
                step_size = max(0.001, step_size * 0.995)

        return pool[0][1].copy()

    return improve