from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def tri_area(a, b, c):
        return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    def project_to_triangle(point, A, B, C):
        """Project a point back into the triangle if it's outside."""
        if is_inside_triangle(point, A, B, C):
            return point
        
        # Find the closest point on each edge
        def closest_point_on_segment(p, a, b):
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / np.dot(ab, ab)
            t = max(0, min(1, t))
            return a + t * ab
        
        p1 = closest_point_on_segment(point, A, B)
        p2 = closest_point_on_segment(point, B, C)
        p3 = closest_point_on_segment(point, C, A)
        
        # Return the closest of the three
        d1 = np.linalg.norm(point - p1)
        d2 = np.linalg.norm(point - p2)
        d3 = np.linalg.norm(point - p3)
        
        if d1 <= d2 and d1 <= d3:
            return p1
        elif d2 <= d1 and d2 <= d3:
            return p2
        else:
            return p3

    def run_optimization_stream(points, seed):
        """Run a single optimization stream with given random seed"""
        np.random.seed(seed)
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        
        step_size = 0.02
        max_iter = 500
        max_no_improve = 250
        no_improve_count = 0
        
        # Track area statistics for adaptive parameters
        area_history = []
        
        for iter in range(max_iter):
            # Find all triangles and their areas
            areas_triplets = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = tri_area(current[i], current[j], current[k])
                        areas_triplets.append((area, (i, j, k)))
            
            # Sort by area
            areas_triplets.sort(key=lambda x: x[0])
            
            # Track area statistics
            areas = [area for area, _ in areas_triplets]
            area_history.append(areas)
            min_area = areas_triplets[0][0] if areas_triplets else 0
            
            # Calculate normalized rank for exponential weighting
            max_area = areas_triplets[-1][0] if areas_triplets else min_area + 1e-10
            area_range = max_area - min_area + 1e-10
            
            # ADAPTIVE THRESHOLD: Start wide and narrow over iterations
            threshold_factor = 1.5 - 0.3 * (iter / max_iter)  # Start at 1.5, decrease to 1.2
            # Consider area variance to widen threshold when areas are spread out
            area_std = np.std(areas) if len(areas) > 1 else 0
            variance_factor = 1.0 + 0.2 * (area_std / min_area) if min_area > 1e-10 else 1.0
            threshold = threshold_factor * variance_factor * min_area
            
            # Apply exponential severity weighting to prioritize worst triangles
            critical_triplets = []
            for area, triplet in areas_triplets:
                if area <= threshold:
                    # Calculate normalized rank (0 = worst, 1 = least critical)
                    normalized_rank = (area - min_area) / area_range
                    # Exponential weighting: worse triangles get much higher weight
                    weight = np.exp(-5 * normalized_rank)
                    critical_triplets.append((area, triplet, weight))

            # Map each point to all critical triplets it's part of
            point_to_triplets = {i: [] for i in range(11)}
            for _, triplet, weight in critical_triplets:
                for idx in triplet:
                    point_to_triplets[idx].append((triplet, weight))

            # Generate candidate by perturbing relevant points with weighted displacement
            candidate = current.copy()
            
            # STAGNATION-TRIGGERED GLOBAL PERTURBATION (replaces fixed schedule)
            if no_improve_count > 0.3 * max_no_improve:
                # Scale perturbation magnitude by severity of stagnation
                global_step = 0.1 * (no_improve_count / max_no_improve)
                for i in range(11):
                    candidate[i] += global_step * np.random.normal(0, 1, 2)
                # Project back to triangle
                for i in range(11):
                    candidate[i] = project_to_triangle(candidate[i], A, B, C)
            else:
                for idx in range(11):
                    if not point_to_triplets[idx]:  # Skip points not in any critical triplet
                        continue
                    
                    total_weight = 0
                    displacement = np.zeros(2)
                    
                    for triplet, weight in point_to_triplets[idx]:
                        i, j, k = triplet
                        # Get the other two points in the triplet
                        others = [x for x in triplet if x != idx]
                        p0 = candidate[others[0]]
                        p1 = candidate[others[1]]
                        
                        # Calculate base vector and normal
                        base_vector = p1 - p0
                        normal = np.array([-base_vector[1], base_vector[0]])
                        vec = candidate[idx] - p0
                        if np.dot(normal, vec) < 0:
                            normal = -normal
                        norm = np.linalg.norm(normal)
                        if norm > 1e-10:
                            normal = normal / norm
                        
                        # STABILIZED WEIGHTING: Inverse area with damping
                        area = tri_area(candidate[i], candidate[j], candidate[k])
                        weight_val = 1.0 / (area + 1e-10)
                        # Add damping to prevent extreme weights
                        weight_val = weight_val / (1.0 + 0.1 * (min_area / (area + 1e-10)))
                        
                        # Apply severity-based weighting
                        displacement += weight * weight_val * normal
                        total_weight += weight * weight_val
                    
                    # Normalize and apply displacement
                    if total_weight > 0:
                        displacement = displacement / total_weight
                        candidate[idx] += step_size * displacement + np.random.normal(0, step_size/3, 2)

            # Project all points back into triangle if necessary
            for i in range(11):
                candidate[i] = project_to_triangle(candidate[i], A, B, C)

            # Check validity (should always be valid due to projection, but verify non-collinearity)
            candidate_invalid = False
            score = get_smallest_triangle_area(candidate)
            if score < 1e-10:
                candidate_invalid = True
            else:
                candidate_score = score

            # DEGENERACY RECOVERY for near-collinear cases
            if not candidate_invalid:
                for area, triplet, _ in critical_triplets:
                    i, j, k = triplet
                    p1, p2, p3 = candidate[i], candidate[j], candidate[k]
                    if area < 1e-5:  # Near-collinear
                        # Find the middle point
                        d12 = np.linalg.norm(p1 - p2)
                        d13 = np.linalg.norm(p1 - p3)
                        d23 = np.linalg.norm(p2 - p3)
                        if d12 + d13 <= d23 + 1e-10:  # p1 between p2 and p3
                            mid_idx, p_idx, q_idx = i, j, k
                        elif d12 + d23 <= d13 + 1e-10:  # p2 between p1 and p3
                            mid_idx, p_idx, q_idx = j, i, k
                        else:  # p3 between p1 and p2
                            mid_idx, p_idx, q_idx = k, i, j
                        
                        # Compute perpendicular direction
                        base_vector = candidate[q_idx] - candidate[p_idx]
                        normal = np.array([-base_vector[1], base_vector[0]])
                        if np.linalg.norm(normal) > 1e-10:
                            normal = normal / np.linalg.norm(normal)
                            # Perturb the middle point orthogonally
                            candidate[mid_idx] += 0.01 * normal
                            # Project back to triangle if needed
                            candidate[mid_idx] = project_to_triangle(candidate[mid_idx], A, B, C)
                # Re-evaluate after degeneracy recovery
                candidate_score = get_smallest_triangle_area(candidate)

            if candidate_invalid:
                no_improve_count += 1
            else:
                # ADAPTIVE ANNEALING PARAMETERS
                # Make initial_temp adaptive based on area distribution
                if iter == 0:
                    mean_area = np.mean(areas) if areas else 0
                    initial_temp = 0.05 + 0.15 * (1.0 - min_area / (mean_area + 1e-10)) if mean_area > 1e-10 else 0.1
                
                # Cooling rate adapts to progress
                cooling_rate = 0.98 + 0.02 * (no_improve_count / max_no_improve)
                temp = initial_temp * (cooling_rate ** iter)

                if candidate_score > current_score:
                    accept = True
                else:
                    delta = current_score - candidate_score
                    if np.random.rand() < np.exp(-delta / temp):
                        accept = True
                    else:
                        accept = False

                if accept:
                    old_current_score = current_score
                    current = candidate
                    current_score = candidate_score
                    if candidate_score > best_score:
                        best = candidate
                        best_score = candidate_score
                        no_improve_count = 0
                    else:
                        # Reset counter if current solution improved (uphill move)
                        if candidate_score > old_current_score:
                            no_improve_count = 0
                            step_size *= 0.95  # Reduce step after successful uphill move
                        else:
                            no_improve_count += 1
                else:
                    no_improve_count += 1

            # Adaptive step size control: increase after prolonged stagnation
            if no_improve_count > 50:
                step_size *= 1.1

            # Clamp step size
            step_size = max(1e-5, min(step_size, 0.15))

            # Stopping condition
            if no_improve_count >= max_no_improve:
                break

        return best, best_score

    def improve(points: np.ndarray) -> np.ndarray:
        # Run multiple optimization streams with different seeds
        num_streams = 3
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)
        
        # Run initial streams
        stream_results = []
        for i in range(num_streams):
            stream_seed = 42 + i * 100
            stream_best, stream_score = run_optimization_stream(points.copy(), stream_seed)
            stream_results.append((stream_best, stream_score))
            
            if stream_score > best_score_overall:
                best_overall = stream_best
                best_score_overall = stream_score
        
        # Periodic elite transfer between streams
        for elite_transfer_round in range(3):  # 3 rounds of elite transfer
            new_stream_results = []n            for i, (stream_best, stream_score) in enumerate(stream_results):
                # Inject best solution from other streams with some probability
                if np.random.rand() < 0.7 and best_score_overall > stream_score:
                    # Start from the global best but add small perturbation
                    perturbed_best = best_overall.copy()
                    for j in range(11):
                        perturbed_best[j] += 0.01 * np.random.normal(0, 1, 2)
                        perturbed_best[j] = project_to_triangle(perturbed_best[j], A, B, C)
                    
                    # Run additional optimization from this point
                    stream_seed = 42 + i * 100 + elite_transfer_round * 1000
                    enhanced_best, enhanced_score = run_optimization_stream(perturbed_best, stream_seed)
                    new_stream_results.append((enhanced_best, enhanced_score))
                    
                    if enhanced_score > best_score_overall:
                        best_overall = enhanced_best
                        best_score_overall = enhanced_score
                else:
                    new_stream_results.append((stream_best, stream_score))
            
            stream_results = new_stream_results

        return best_overall

    return improve