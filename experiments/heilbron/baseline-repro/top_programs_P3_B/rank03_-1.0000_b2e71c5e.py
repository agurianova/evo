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
        
        # FIXED: Correct iteration allocation for hard problems
        gap = 0.0365 - initial_score
        max_iter = 2000 + int((1.0 - gap / 0.0365) * 4000)
        max_iter = min(5000, max_iter)

        # IMPLEMENTED: Parallel search with 3 adaptive chains
        num_chains = 3
        chains = []
        # ADDED: Adaptive diversity scale based on problem difficulty
        diversity_scale = 0.02 * (1 + 0.5 * (gap / 0.0365))
        
        for i in range(num_chains):
            chain_points = points.copy()
            # IMPROVED: Stronger initial diversity with adaptive scaling
n            if i > 0:
                chain_points += np.random.normal(0, diversity_scale * i, chain_points.shape)
                for j in range(len(chain_points)):
                    if not is_inside_triangle(chain_points[j], A, B, C):
                        chain_points[j] = project_to_triangle(chain_points[j], A, B, C)
            chains.append({
                'points': chain_points,
                'score': get_smallest_triangle_area(chain_points),
                'step_size': 0.1,
                'temp': 0.1 * (0.0365 - initial_score),
                'no_improve': 0,
                'restarts': 0,
                'critical_counts': None,
                'counts_need_update': True,
                'recent_deltas': [],
                'best_score': initial_score,
                'best_points': chain_points.copy(),
                'improvement_rate': []
            })

        # Synchronization interval for parallel chains
        sync_interval = 200
        
        for iter_count in range(max_iter):
            # Process each chain independently
            for chain_idx, chain in enumerate(chains):
                current = chain['points']
                current_score = chain['score']
                
                # FIXED: Widened threshold for harder problems
                threshold_factor = 1.0 + 0.05 * (gap / 0.0365)
                
                # IMPROVED: Bias schedule adapts to actual improvement rate
                progress = iter_count / max_iter
                # Track improvement rate for adaptive scheduling
                if 'improvement_rate' not in chain:
                    chain['improvement_rate'] = []
                
                # Calculate recent improvement rate
                positive_improvements = [x for x in chain['improvement_rate'] if x > 0]
                if len(positive_improvements) > 0:
                    avg_improvement = np.mean(positive_improvements)
                    # Delay exploitation when improvements are small
                    bias_center = 0.6 + 0.3 * (0.001 / (avg_improvement + 0.0001))
                else:
                    bias_center = 0.6
                
                bias_weight = 0.2 + 0.6 * (1 / (1 + np.exp(-5 * (progress - bias_center))))

                # Update critical counts if needed
                if chain['counts_need_update']:
                    critical_counts = np.zeros(n, dtype=int)
                    critical_triangles = []
                    for i_inner in range(n):
                        for j in range(i_inner+1, n):
                            for k in range(j+1, n):
                                p1, p2, p3 = current[i_inner], current[j], current[k]
                                area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1]))
                                # Adaptive threshold for critical triangles
                                if area <= current_score * threshold_factor:
                                    critical_counts[i_inner] += 1
                                    critical_counts[j] += 1
                                    critical_counts[k] += 1
                                    critical_triangles.append((i_inner, j, k))
                    chain['critical_counts'] = critical_counts
                    chain['critical_triangles'] = critical_triangles
                    chain['counts_need_update'] = False

                # IMPROVED: Increased base exploration rate with adaptive scaling
                exploration_rate = 0.15 * (1 + min(1.0, chain['no_improve'] / 10))
                if np.random.rand() < exploration_rate:
                    idx = np.random.randint(0, n)
                else:
                    total_count = np.sum(chain['critical_counts'])
                    if total_count == 0:
                        idx = np.random.randint(0, n)
                    else:
                        probs = chain['critical_counts'] / total_count
                        idx = np.random.choice(n, p=probs)

                candidate = current.copy()
                
                # Biased perturbation for critical points
                if chain['critical_counts'][idx] > 0:
                    directions = []
                    for tri in chain['critical_triangles']:
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
                    if directions:
                        avg_dir = np.mean(directions, axis=0)
                        norm_avg = np.linalg.norm(avg_dir)
                        if norm_avg > 1e-10:
                            avg_unit_dir = avg_dir / norm_avg
                        else:
                            avg_unit_dir = np.array([1, 0])
                    else:
                        avg_unit_dir = np.array([1, 0])
                    random_pert = np.random.normal(0, chain['step_size'], 2)
                    biased_pert = (1 - bias_weight) * random_pert + bias_weight * (chain['step_size'] * avg_unit_dir)
                    candidate[idx] += biased_pert
                else:
                    candidate[idx] += np.random.normal(0, chain['step_size'], 2)

                if not is_inside_triangle(candidate[idx], A, B, C):
                    candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
                    # IMPROVED: Geometry-adaptive boundary perturbation
                    centroid = (A + B + C) / 3.0
                    direction = centroid - candidate[idx]
                    norm_dir = np.linalg.norm(direction)
                    if norm_dir > 1e-10:
                        direction = direction / norm_dir
                        # Adaptive perturbation based on distance to centroid
                        distance_to_centroid = np.linalg.norm(centroid - candidate[idx])
                        adaptive_perturbation = max(1e-6, 0.01 * distance_to_centroid)
                        candidate[idx] = candidate[idx] + adaptive_perturbation * direction

                new_score = get_smallest_triangle_area(candidate)

                # Track deltas for improvement rate and temperature
                delta_val = new_score - current_score
                chain['recent_deltas'].append(delta_val)
                if delta_val > 0:
                    chain['improvement_rate'].append(delta_val)
                if len(chain['improvement_rate']) > 50:
                    chain['improvement_rate'].pop(0)
                if len(chain['recent_deltas']) > 100:
                    chain['recent_deltas'].pop(0)

                # Periodic temperature recalibration
                if iter_count == 49 or (iter_count > 50 and iter_count % 100 == 0):
                    positive_deltas = [d for d in chain['recent_deltas'] if d > 0]
                    if len(positive_deltas) > 0:
                        std_delta = np.std(positive_deltas)
                    else:
                        std_delta = 0.01
                    # Adaptive temperature factor
                    temp_factor = 8.0 * (0.5 + 0.5 * (1.0 - progress))
                    chain['temp'] = max(0.01, temp_factor * std_delta)

                # Acceptance criterion
                delta = new_score - current_score
                if delta > 0 or np.random.rand() < np.exp(delta / chain['temp']):
                    chain['points'] = candidate
                    chain['score'] = new_score
                    chain['no_improve'] = 0
                    chain['counts_need_update'] = True
                    
                    # Update best solution for this chain
                    if new_score > chain['best_score']:
                        chain['best_score'] = new_score
                        chain['best_points'] = candidate.copy()
                else:
                    chain['no_improve'] += 1

                # Cooling
                chain['temp'] *= 0.995

                # Step size decay
                chain['step_size'] = max(0.001, chain['step_size'] * 0.999)

            # IMPROVED: Periodic diversity injection to prevent chain convergence
            if iter_count > 0 and iter_count % (sync_interval * 2) == 0:
                for chain_idx, chain in enumerate(chains):
                    if chain['no_improve'] > 50:
                        # Add larger perturbation to stagnant chains
                        diversity_amount = 0.015 * (1 + 0.5 * (gap / 0.0365))
                        chain['points'] += np.random.normal(0, diversity_amount, chain['points'].shape)
                        # Project back to triangle
                        for j in range(len(chain['points'])):
                            if not is_inside_triangle(chain['points'][j], A, B, C):
                                chain['points'][j] = project_to_triangle(chain['points'][j], A, B, C)
                        chain['score'] = get_smallest_triangle_area(chain['points'])
                        chain['no_improve'] = 0
                        chain['counts_need_update'] = True

            # Periodic synchronization of chains
            if iter_count > 0 and iter_count % sync_interval == 0:
                # Find best solution across all chains
                best_chain_idx = np.argmax([chain['best_score'] for chain in chains])
                best_points = chains[best_chain_idx]['best_points']
                best_score = chains[best_chain_idx]['best_score']
                
                # Share best solution with all chains
                for chain in chains:
                    if chain['best_score'] < best_score * 0.99:
                        # Replace with slightly perturbed best solution
                        perturbation_scale = 0.005 * (1 + 0.5 * (1.0 - gap / 0.0365))
                        chain['points'] = best_points.copy() + np.random.normal(0, perturbation_scale, best_points.shape)
                        for j in range(len(chain['points'])):
                            if not is_inside_triangle(chain['points'][j], A, B, C):
                                chain['points'][j] = project_to_triangle(chain['points'][j], A, B, C)
                        chain['score'] = get_smallest_triangle_area(chain['points'])
                        chain['best_points'] = best_points.copy()
                        chain['best_score'] = best_score
                        chain['no_improve'] = 0
                        chain['counts_need_update'] = True

        # Return the best solution found across all chains
        best_chain = max(chains, key=lambda x: x['best_score'])
        return best_chain['best_points'].copy()

    return improve