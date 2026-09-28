from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

MAX_THEORETICAL_AREA = 0.0365

def entrypoint():
    A_big, B_big, C_big = get_unit_triangle()

    def project_to_triangle(point):
        """Project a point back into the triangle along the shortest path if outside."""
        if is_inside_triangle(point, A_big, B_big, C_big):
            return point.copy()
        
        # Calculate distances to each edge and find closest boundary point
        def distance_to_edge(p, v1, v2):
            edge = v2 - v1
            edge_length_sq = np.dot(edge, edge)
            if edge_length_sq < 1e-10:
                return v1, np.linalg.norm(p - v1)
            
            t = max(0, min(1, np.dot(p - v1, edge) / edge_length_sq))
            projection = v1 + t * edge
            return projection, np.linalg.norm(p - projection)
        
        proj_ab, dist_ab = distance_to_edge(point, A_big, B_big)
        proj_bc, dist_bc = distance_to_edge(point, B_big, C_big)
        proj_ca, dist_ca = distance_to_edge(point, C_big, A_big)
        
        if dist_ab <= dist_bc and dist_ab <= dist_ca:
            result = proj_ab
        elif dist_bc <= dist_ab and dist_bc <= dist_ca:
            result = proj_bc
        else:
            result = proj_ca
        
        # Add small perpendicular perturbation to avoid collinearity
        edge_vector = None
        if np.array_equal(result, proj_ab):
            edge_vector = B_big - A_big
        elif np.array_equal(result, proj_bc):
            edge_vector = C_big - B_big
        else:
            edge_vector = A_big - C_big
        
        if edge_vector is not None:
            perpendicular = np.array([-edge_vector[1], edge_vector[0]])
            perpendicular = perpendicular / (np.linalg.norm(perpendicular) + 1e-10)
            # Reduce perturbation as solution improves to maintain precision
            perturbation_scale = 1e-5 * (1 - min_area / MAX_THEORETICAL_AREA + 0.1)
            result += perpendicular * perturbation_scale
        
        return result

    def find_smallest_triangles(pts, min_area_val=None, threshold_factor=1.2):
        n = pts.shape[0]
        triangles = []  # (area, i, j, k, cross)
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    dx1 = pts[j,0] - pts[i,0]
                    dy1 = pts[j,1] - pts[i,1]
                    dx2 = pts[k,0] - pts[i,0]
                    dy2 = pts[k,1] - pts[i,1]
                    cross = dx1 * dy2 - dy1 * dx2
                    area = 0.5 * abs(cross)
                    triangles.append((area, i, j, k, cross))
        
        # Sort by area
        triangles.sort(key=lambda x: x[0])
        
        # If no triangles found, return empty list
        if not triangles:
            return []
        
        # Find the minimum area
        min_area = triangles[0][0]
        
        # Adaptive threshold: include all triangles with area <= threshold_factor * min_area
        # But ensure we include at least 3 triangles to avoid empty gradients
        threshold = max(min_area * threshold_factor, triangles[min(2, len(triangles)-1)][0])
        
        # Filter triangles based on threshold
        relevant_triangles = [t for t in triangles if t[0] <= threshold]
        
        return relevant_triangles

    def improve(points: np.ndarray) -> np.ndarray:
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)
        initial_min_area = best_score_overall
n        # Adaptive run count based on initial solution quality
        num_runs = max(3, min(8, int(5 + 3 * (initial_min_area / MAX_THEORETICAL_AREA))))
        
        # Run multiple independent optimizations with different seeds
        for run_idx in range(num_runs):
            np.random.seed(42 + run_idx)
            current = points.copy()
            best = points.copy()
            best_score = get_smallest_triangle_area(best)
            current_score = best_score

            max_rounds = 200
            initial_temp = 0.1
            cooling_rate = 0.98
            early_stop_patience = 50
            stagnation_limit = 80  # New parameter for stagnation detection

            temp = initial_temp
            last_improvement = 0

            for round_idx in range(max_rounds):
                # Adaptive threshold factor based on current solution quality
                progress_factor = current_score / MAX_THEORETICAL_AREA
                threshold_factor = 1.0 + 0.2 * (1 - progress_factor)
                
                # Find relevant triangles using adaptive threshold
                relevant_triangles = find_smallest_triangles(current, min_area_val=current_score, threshold_factor=threshold_factor)
                if not relevant_triangles:
                    break
                
                min_area = relevant_triangles[0][0]

                # Compute weighted gradients for each point
                gradients = np.zeros_like(current)
                total_weights = np.zeros(current.shape[0])
                
                # Compute softmax weights based on relative area
                areas = [t[0] for t in relevant_triangles]
                min_area_val = min(areas)
                # Adaptive beta based on solution quality
                beta = 2.0 + 3.0 * (min_area_val / MAX_THEORETICAL_AREA)
                weights = np.exp(-beta * np.array(areas) / (min_area_val + 1e-10))
                weights = weights / (np.sum(weights) + 1e-10)
                
                for idx, (area, i, j, k, cross) in enumerate(relevant_triangles):
                    weight = weights[idx]
                    A_pt, B_pt, C_pt = current[i], current[j], current[k]

                    grad_A = np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]])
                    grad_B = np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[0]])
                    grad_C = np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]])

                    if cross < 0:
                        grad_A, grad_B, grad_C = -grad_A, -grad_B, -grad_C

                    gradients[i] += weight * grad_A
                    gradients[j] += weight * grad_B
                    gradients[k] += weight * grad_C
                    
                    total_weights[i] += weight
                    total_weights[j] += weight
                    total_weights[k] += weight

                # Normalize by total weight for each point (stable averaging)
                for idx in range(current.shape[0]):
                    if total_weights[idx] > 1e-10:
                        gradients[idx] /= (total_weights[idx] + 1e-10)

                # Adaptive step scaling based on proximity to theoretical maximum
                progress_factor = 1.0 - min_area / MAX_THEORETICAL_AREA
                step_scale = min_area * (1.5 + 0.5 * progress_factor)
                step = step_scale * (temp / initial_temp)
                
                # Adaptive noise magnitude
                noise_factor = 0.1 * (1 - min_area / MAX_THEORETICAL_AREA)**2
                noise_magnitude = noise_factor * (temp / initial_temp) * step_scale

                candidate = current.copy()
                
                # Apply movement to all points with non-zero gradients
                for idx in range(current.shape[0]):
                    if total_weights[idx] > 1e-10:
                        # Normalize gradient direction
                        grad_norm = np.linalg.norm(gradients[idx])
                        if grad_norm > 1e-10:
                            direction = gradients[idx] / grad_norm
                            noise = np.random.randn(2) * noise_magnitude
                            candidate[idx] += step * direction + noise

                # Project out-of-bound points instead of rejecting
                for idx in range(candidate.shape[0]):
                    candidate[idx] = project_to_triangle(candidate[idx])

                score = get_smallest_triangle_area(candidate)
                if score <= 1e-10:
                    temp *= cooling_rate
                    continue

                delta = score - current_score
                if delta > 0 or np.random.rand() < np.exp(delta / temp):
                    current, current_score = candidate, score
                    if score > best_score:
                        best, best_score = candidate, score
                        last_improvement = round_idx

                # Stagnation-triggered perturbation to escape deep local optima
                if round_idx - last_improvement > stagnation_limit:
                    # Find the absolute smallest triangle
                    smallest_triangles = find_smallest_triangles(current, min_area_val=current_score, threshold_factor=1.01)
                    if smallest_triangles:
                        _, i, j, k, _ = smallest_triangles[0]
                        # Perturb points in smallest triangle by 5-10% of min_area
                        perturbation_scale = 0.05 * min_area * (1 + np.random.rand())
                        for idx in [i, j, k]:
                            direction = np.random.randn(2)
                            direction = direction / (np.linalg.norm(direction) + 1e-10)
                            current[idx] += direction * perturbation_scale
                            # Project back to triangle if needed
                            current[idx] = project_to_triangle(current[idx])
                    last_improvement = round_idx

                temp *= cooling_rate
                if round_idx - last_improvement > early_stop_patience:
                    break

            # Final refinement phase for precision tuning
            refinement_rounds = 50
            refinement_step = 0.1 * best_score
            
            # Adaptive refinement threshold
            refinement_threshold = 1.0 + 0.01 * (1 - best_score / MAX_THEORETICAL_AREA)
            
            for _ in range(refinement_rounds):
                # Focus only on the absolute smallest triangle
                relevant_triangles = find_smallest_triangles(best, min_area_val=best_score, threshold_factor=refinement_threshold)
                if not relevant_triangles:
                    break
                
                min_area = relevant_triangles[0][0]
                gradients = np.zeros_like(best)
                
                # Only consider the smallest triangle(s) for precise tuning
                for area, i, j, k, cross in relevant_triangles:
                    A_pt, B_pt, C_pt = best[i], best[j], best[k]

                    grad_A = np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]])
                    grad_B = np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[0]])
                    grad_C = np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]])

                    if cross < 0:
                        grad_A, grad_B, grad_C = -grad_A, -grad_B, -grad_C

                    gradients[i] += grad_A
                    gradients[j] += grad_B
                    gradients[k] += grad_C

                # Normalize gradients
                for idx in range(best.shape[0]):
                    grad_norm = np.linalg.norm(gradients[idx])
                    if grad_norm > 1e-10:
                        gradients[idx] /= grad_norm

                # Apply noiseless movement
                candidate = best.copy()
                for idx in range(best.shape[0]):
                    if np.linalg.norm(gradients[idx]) > 1e-10:
                        candidate[idx] += refinement_step * gradients[idx]

                # Project out-of-bound points
                for idx in range(candidate.shape[0]):
                    candidate[idx] = project_to_triangle(candidate[idx])

                score = get_smallest_triangle_area(candidate)
                if score > best_score:
                    best, best_score = candidate, score

            # Update overall best
            if best_score > best_score_overall:
                best_overall = best.copy()
                best_score_overall = best_score

        return best_overall

    return improve