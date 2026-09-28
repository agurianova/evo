from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import math
import heapq

np.random.seed(42)

def entrypoint():
    """Return an improve(points) -> improved_points callable."""
    A, B, C = get_unit_triangle()
    triangle_vertices = np.array([A, B, C])
    
    # Calculate triangle width for proper scaling
    triangle_width = np.linalg.norm(B - A)
    
    # Function to project a point to the nearest location inside the triangle
    def project_to_triangle(point):
        """Project point to the nearest location inside the triangle using edge distance calculation."""
        # Calculate distance to each edge and find closest point
        def point_to_line_distance(p, a, b):
            # Vector from a to b
            ab = b - a
            # Vector from a to p
            ap = p - a
            # Length squared of ab
            ab_length_sq = np.dot(ab, ab)
            # Check if ab is a point
            if ab_length_sq < 1e-10:
                return a, np.linalg.norm(ap)
            # Calculate projection factor
            t = max(0.0, min(1.0, np.dot(ap, ab) / ab_length_sq))
            # Calculate projection point
            projection = a + t * ab
            # Distance from p to projection
            distance = np.linalg.norm(p - projection)
            return projection, distance
        
        # Get the three edges
        edges = [(A, B), (B, C), (C, A)]
        
        # Find closest point on any edge
        min_distance = float('inf')
        closest_point = None
        
        for edge in edges:
            proj, dist = point_to_line_distance(point, edge[0], edge[1])
            if dist < min_distance:
                min_distance = dist
                closest_point = proj
        
        # Check if point is inside triangle (using barycentric coordinates)
        v0 = B - A
        v1 = C - A
        v2 = point - A

        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01

        if abs(denom) < 1e-10:
            return (A + B + C) / 3

        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w

        # If inside triangle, return original point
        if u >= 0 and v >= 0 and w >= 0:
            return point

        # Otherwise return closest point on boundary
        return closest_point

    def get_triangle_area(a, b, c):
        """Calculate area of triangle given three points."""
        return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    def update_triangle_cache(points, cache, modified_indices):
        """Update the triangle cache with only affected triangles."""
        n = len(points)
        affected_triangles = set()

        # Find all triangles involving modified points
        for i in modified_indices:
            for j in range(n):
                if j == i: continue
                for k in range(j+1, n):
                    if k == i: continue
                    affected_triangles.add(tuple(sorted([i, j, k])))

        # Recalculate areas for affected triangles
        for i, j, k in affected_triangles:
            area = get_triangle_area(points[i], points[j], points[k])
            # Update cache
            cache[(i, j, k)] = area

        return cache

    def get_smallest_triangles(cache, num_triangles):
        """Get the smallest triangles from the cache."""
        # Use heapq to get the smallest triangles efficiently
        smallest = heapq.nsmallest(num_triangles, cache.items(), key=lambda x: x[1])
        return [(area, i, j, k) for ((i, j, k), area) in smallest]

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)

        # CONFIGURABLE PARAMETERS - can be evolved over time
        config = {
            'triangle_selection_coeff': 5.0,  # Was hardcoded 5
            'gradient_min_ratio': 0.3,
            'gradient_max_ratio': 0.9,
            'success_rate_low_threshold': 0.2,
            'success_rate_high_threshold': 0.5,
            'success_rate_low_multiplier': 0.8,
            'success_rate_high_multiplier': 1.2,
            'degeneracy_perturbation_base': 0.05,
            'global_perturbation_base': 0.05,
            'reheating_base_factor': 0.5,
            'reheating_progress_factor': 0.3,
            'max_no_improve': 100,  # Increased from 50
            'refinement_steps': 200,
            'refinement_step_base': 0.001
        }

        # Initialize triangle cache with all triangles
        n = len(best)
        triangle_cache = {}
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = get_triangle_area(best[i], best[j], best[k])
                    triangle_cache[(i, j, k)] = area

        # Simulated annealing parameters
        initial_temp = 0.02
        cooling_rate = 0.995
        current_temp = initial_temp

        # Track improvement for dynamic stopping
        min_improvement_threshold = 1e-6
        last_score = best_score
        no_improve_count = 0

        # Track step size adaptation
        success_count = 0
        total_attempts = 0
        step_size_multiplier = 1.0

        # Main optimization loop
        for _round in range(500):
            # Calculate current min_area for adaptive scaling
            current_min_area = get_smallest_triangle_area(best)
            
            # Adaptive triangle selection based on landscape flatness
            # Calculate how flat the landscape is (ratio of smallest to 5th smallest)
            smallest_triangles = get_smallest_triangles(triangle_cache, 5)
            if len(smallest_triangles) >= 5:
                flatness_ratio = smallest_triangles[0][0] / smallest_triangles[4][0]
            else:
                flatness_ratio = 0.5  # Default if not enough triangles
            
            # Adjust number of triangles based on flatness and headroom
            improvement_headroom = 0.0365 - current_min_area
            num_triangles = max(1, min(15, int(config['triangle_selection_coeff'] * 
                                        (0.0365 - current_min_area) / 0.0365 * 
                                        (1.0 + 2.0 * flatness_ratio))
                              )
                           )

            # Get smallest triangles from cache
            top_triangles = get_smallest_triangles(triangle_cache, num_triangles)
            
            # Randomly select one of the top triangles to improve
            selected_triangle = top_triangles[np.random.randint(0, len(top_triangles))]
            min_score, i, j, k = selected_triangle
            a, b, c = best[i], best[j], best[k]

            # Calculate signed area to determine correct gradient direction
            signed_area = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

            # Analytical gradient for increasing triangle area
            grad_a = np.array([0.5 * (b[1] - c[1]), 0.5 * (c[0] - b[0])])
            grad_b = np.array([0.5 * (c[1] - a[1]), 0.5 * (a[0] - c[0])])
            grad_c = np.array([0.5 * (a[1] - b[1]), 0.5 * (b[0] - a[0])])
            
            candidate = best.copy()
            modified_indices = {i, j, k}
            
            # CORRECTED exploration-exploitation balance
            gradient_ratio = config['gradient_min_ratio'] + 
                            (config['gradient_max_ratio'] - config['gradient_min_ratio']) * 
                            (current_temp / initial_temp)
            gradient_ratio = min(config['gradient_max_ratio'], max(config['gradient_min_ratio'], gradient_ratio))
            random_ratio = 1 - gradient_ratio

            # Step size scaled by triangle dimensions
            improvement_headroom = 0.0365 - current_min_area
            step_size = current_temp * 2.5 * improvement_headroom * step_size_multiplier * triangle_width

            # Perturb all three vertices of the selected triangle
            for idx, grad in zip([i, j, k], [grad_a, grad_b, grad_c]):
                # DEGENERATE TRIANGLE HANDLING
                if min_score < 1e-6:
                    # Calculate perpendicular direction based on aspect ratio
                    vec1 = b - a
                    vec2 = c - a
                    aspect_ratio = max(np.linalg.norm(vec1), np.linalg.norm(vec2)) / 
                                 max(min(np.linalg.norm(vec1), np.linalg.norm(vec2)), 1e-10)
                    # Scale perturbation based on aspect ratio
                    perturbation = np.random.normal(0, 
                                                  config['degeneracy_perturbation_base'] * aspect_ratio, 
                                                  size=2)
                elif np.linalg.norm(grad) > 1e-5:
                    # Normalize direction and scale
                    direction = -grad / np.linalg.norm(grad)  # Move opposite to gradient to increase area
                    perturbation = direction * step_size * gradient_ratio + 
                                 np.random.normal(0, step_size * random_ratio, size=2)
                else:
                    # If gradient is zero (degenerate triangle), use random perturbation
                    perturbation = np.random.normal(0, step_size, size=2)
                
                candidate[idx] += perturbation
                
                # Project back to triangle if needed
                if not is_inside_triangle(candidate[idx], A, B, C):
                    candidate[idx] = project_to_triangle(candidate[idx])

            # Update triangle cache for candidate
            candidate_cache = update_triangle_cache(candidate, triangle_cache.copy(), modified_indices)
            
            # Check validity of candidate
            valid_candidate = True
            # Check for near-zero areas in affected triangles
            for idx in modified_indices:
                for j1 in range(n):
                    if j1 == idx: continue
                    for k1 in range(j1+1, n):
                        if k1 == idx: continue
                        area = candidate_cache.get(tuple(sorted([idx, j1, k1])), float('inf'))
                        if area < 1e-8:
                            valid_candidate = False
                            break
                    if not valid_candidate:
                        break
                if not valid_candidate:
                    break

            # Skip invalid candidates
            if not valid_candidate or not is_inside_triangle(candidate, A, B, C):
                # Track attempt but skip
                total_attempts += 1
                # Cool down
                current_temp *= cooling_rate
                continue
                
            score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing: accept worse solutions with some probability
            accepted = False
            if score > best_score or np.random.rand() < math.exp((score - best_score) / current_temp):
                best = candidate
                best_score = score
                triangle_cache = candidate_cache  # Update cache with accepted solution
                accepted = True
                success_count += 1
            
            total_attempts += 1

            # Adaptive step size based on recent success rate
            if _round > 0 and _round % 50 == 0:
                if total_attempts > 0:
                    success_rate = success_count / total_attempts
                    if success_rate < config['success_rate_low_threshold']:
                        step_size_multiplier *= config['success_rate_low_multiplier']
                    elif success_rate > config['success_rate_high_threshold']:
                        step_size_multiplier *= config['success_rate_high_multiplier']
                # Reset counters
                success_count = 0
                total_attempts = 0

            # DYNAMIC STOPPING CRITERION
            improvement = best_score - last_score
            if improvement < min_improvement_threshold:
                no_improve_count += 1
            else:
                no_improve_count = 0
            last_score = best_score

            # Cool down
            current_temp *= cooling_rate
            
            # Periodic global perturbation to escape local optima - scaled with headroom
            if _round > 0 and _round % 50 == 0:
                for i in range(len(best)):
                    # Increased strength and added temperature dependency
                    best[i] += np.random.normal(0, 
                                              config['global_perturbation_base'] * 
                                              improvement_headroom * 
                                              (current_temp/initial_temp), 
                                              size=2)
                    if not is_inside_triangle(best[i], A, B, C):
                        best[i] = project_to_triangle(best[i])
                # Recalculate cache after global perturbation
                triangle_cache = {}
                for i in range(n):
                    for j in range(i+1, n):
                        for k in range(j+1, n):
                            area = get_triangle_area(best[i], best[j], best[k])
                            triangle_cache[(i, j, k)] = area
                # Recalculate score after global perturbation
                best_score = get_smallest_triangle_area(best)

            # Reheating when stuck in local optimum
            if no_improve_count > config['max_no_improve'] * 0.6 and _round > 100:
                # Increased reheating strength
                current_temp = initial_temp * (config['reheating_base_factor'] + 
                                           config['reheating_progress_factor'] * 
                                           (no_improve_count / config['max_no_improve']))
                no_improve_count = 0

            # Temperature-based stopping criterion
            if current_temp < 1e-7 or (no_improve_count > config['max_no_improve'] and _round > 100):
                break

        # FINAL REFINEMENT PHASE - deterministic gradient-based improvements
        refinement_best = best.copy()
        refinement_best_score = best_score
        refinement_triangle_cache = triangle_cache.copy()

        for refinement_step in range(config['refinement_steps']):
            # Get smallest triangle
            smallest_triangles = get_smallest_triangles(refinement_triangle_cache, 1)
            if not smallest_triangles:
                break
            
            min_score, i, j, k = smallest_triangles[0]
            if min_score <= 1e-8:  # Skip degenerate cases
                break

            # Calculate gradients
            a, b, c = refinement_best[i], refinement_best[j], refinement_best[k]
            grad_a = np.array([0.5 * (b[1] - c[1]), 0.5 * (c[0] - b[0])])
            grad_b = np.array([0.5 * (c[1] - a[1]), 0.5 * (a[0] - c[0])])
            grad_c = np.array([0.5 * (a[1] - b[1]), 0.5 * (b[0] - a[0])])

            # Adaptive step size for refinement
            refinement_step_size = config['refinement_step_base'] * min_score

            # Move points in gradient direction (opposite to gradient to increase area)
            candidate = refinement_best.copy()
            modified_indices = {i, j, k}

            for idx, grad in zip([i, j, k], [grad_a, grad_b, grad_c]):
                if np.linalg.norm(grad) > 1e-5:
                    direction = -grad / np.linalg.norm(grad)
                    candidate[idx] += direction * refinement_step_size

                # Project back to triangle if needed
                if not is_inside_triangle(candidate[idx], A, B, C):
                    candidate[idx] = project_to_triangle(candidate[idx])

            # Update cache
            candidate_cache = update_triangle_cache(candidate, refinement_triangle_cache.copy(), modified_indices)
            
            # Check validity
            valid_refinement = True
            for idx in modified_indices:
                for j1 in range(n):
                    if j1 == idx: continue
                    for k1 in range(j1+1, n):
                        if k1 == idx: continue
                        area = candidate_cache.get(tuple(sorted([idx, j1, k1])), float('inf'))
                        if area < 1e-8:
                            valid_refinement = False
                            break
                    if not valid_refinement:
                        break
                if not valid_refinement:
                    break

            if not valid_refinement or not is_inside_triangle(candidate, A, B, C):
                continue

            score = get_smallest_triangle_area(candidate)
            if score > refinement_best_score:
                refinement_best = candidate
                refinement_best_score = score
                refinement_triangle_cache = candidate_cache

        return refinement_best

    return improve