from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import random


def entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_triangle(point, A, B, C):
        """Project point to the closest point inside triangle ABC using barycentric coordinates."""
        # Convert to barycentric coordinates
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
            return point  # Degenerate triangle, shouldn't happen
        
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1 - v - w
        
        # Clamp to [0,1] and renormalize if outside
        if u < 0:
            u = 0
            sum_vw = v + w
            if sum_vw > 0:
                v /= sum_vw
                w /= sum_vw
            else:
                v = 0.5
                w = 0.5
        if v < 0:
            v = 0
            sum_uw = u + w
            if sum_uw > 0:
                u /= sum_uw
                w /= sum_uw
            else:
                u = 0.5
                w = 0.5
        if w < 0:
            w = 0
            sum_uv = u + v
            if sum_uv > 0:
                u /= sum_uv
                v /= sum_uv
            else:
                u = 0.5
                v = 0.5
        
        # Ensure they sum to 1
        total = u + v + w
        if abs(total - 1) > 1e-10:
            u, v, w = u/total, v/total, w/total
        
        return u * A + v * B + w * C

    def compute_triangle_area_cache(points):
        """Compute cache of triangle areas for all combinations"""
        n = len(points)
        cache = {}
        
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    v1 = points[j] - points[i]
                    v2 = points[k] - points[i]
                    cross = v1[0] * v2[1] - v1[1] * v2[0]
                    area = 0.5 * abs(cross)
                    cache[(i, j, k)] = area
                    
        return cache

    def update_triangle_area_cache(cache, points, modified_indices):
        """Update cache for triangles affected by modified points"""
        n = len(points)
        modified_set = set(modified_indices)
        
        # Update all triangles that include any modified point
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    if i in modified_set or j in modified_set or k in modified_set:
                        v1 = points[j] - points[i]
                        v2 = points[k] - points[i]
                        cross = v1[0] * v2[1] - v1[1] * v2[0]
                        area = 0.5 * abs(cross)
                        cache[(i, j, k)] = area

    def get_k_smallest_triangles(cache, k):
        """Get k smallest triangles from cache"""
        sorted_triangles = sorted(cache.items(), key=lambda x: x[1])
        return [(area, i, j, k) for ((i, j, k), area) in sorted_triangles[:k]]

    def compute_gradient_for_all_points(points, triangle_cache):
        """Compute gradient for all points based on contribution to minimum triangle area"""
        n = len(points)
        gradients = np.zeros((n, 2))
        min_area = min(triangle_cache.values())
        
        # Find all triangles with area close to min_area (within 10%)
        critical_triangles = []
        for (i, j, k), area in triangle_cache.items():
            if area <= min_area * 1.1:  # Consider triangles within 10% of min area
                critical_triangles.append((i, j, k))
        
        for (i, j, k) in critical_triangles:
            p0, p1, p2 = points[i], points[j], points[k]
            
            # Compute signed area
            v1 = p1 - p0
            v2 = p2 - p0
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            signed_area = 0.5 * cross
            
            # Compute gradient directions
            dir0 = np.sign(signed_area) * np.array([p1[1] - p2[1], p2[0] - p1[0]])
            dir1 = np.sign(signed_area) * np.array([p2[1] - p0[1], p0[0] - p2[0]])
            dir2 = np.sign(signed_area) * np.array([p0[1] - p1[1], p1[0] - p0[0]])

            # Scale by importance (closer to min area = more important)
            area_diff = triangle_cache[(i, j, k)] - min_area
            # Use inverse distance with small epsilon to avoid division by zero
            scale = 1.0 / (area_diff + 1e-5)
            # Cap scale to prevent extreme values
            scale = min(10.0, scale)

            # Normalize and scale
            dir0 = dir0 / (np.linalg.norm(dir0) + 1e-10) * scale
            dir1 = dir1 / (np.linalg.norm(dir1) + 1e-10) * scale
            dir2 = dir2 / (np.linalg.norm(dir2) + 1e-10) * scale

            # Accumulate gradients
            gradients[i] += dir0
            gradients[j] += dir1
            gradients[k] += dir2

        # Normalize gradients
        for i in range(n):
            norm = np.linalg.norm(gradients[i])
            if norm > 1e-10:
                gradients[i] /= norm

        return gradients

    def improve(points: np.ndarray) -> np.ndarray:
        base_step = 0.01
        decay = 0.999
        max_iter = 10000
        max_no_improve = 500
        
        # Initialize adaptive temperature for simulated annealing
        current = points.copy()
        best_score = get_smallest_triangle_area(current)
        best_config = current.copy()
        no_improve_count = 0
        step_counter = 0
        
        # Initialize triangle area cache
        triangle_cache = compute_triangle_area_cache(current)
        
        # Adaptive temperature scheduling
        initial_temp = max(0.001, best_score * 10)  # Reduced from 15 to 10 for better balance
        temp = initial_temp
        temp_decay = 0.99995
        
        # Adaptive global exploration parameters
        base_perturbation = 0.1
        perturbation_magnitude = base_perturbation
        stagnation_threshold = max_no_improve // 2

        # Track acceptance rate for temperature adjustment
        acceptance_count = 0
        total_moves = 0

        # Helper for triangle area computation
        def triangle_area(p0, p1, p2):
            v1 = p1 - p0
            v2 = p2 - p0
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            signed = 0.5 * cross
            return signed, abs(signed)

        for _ in range(max_iter):
            # Adaptive k_smallest_count: slow decay from 10 to 3
            k_smallest_count = max(3, 10 - int(step_counter / (max_iter / 20)))
            
            # Get k smallest triangles from cache
            k_smallest = get_k_smallest_triangles(triangle_cache, k_smallest_count)
            
            if not k_smallest:
                break

            # Randomly select one of the k smallest triangles to optimize
            _, i, j, k = random.choice(k_smallest)
            p0, p1, p2 = current[i], current[j], current[k]

            # Compute gradient directions for area increase
            signed, _ = triangle_area(p0, p1, p2)
            dir0 = np.sign(signed) * np.array([p1[1] - p2[1], p2[0] - p1[0]])
            dir1 = np.sign(signed) * np.array([p2[1] - p0[1], p0[0] - p2[0]])
            dir2 = np.sign(signed) * np.array([p0[1] - p1[1], p1[0] - p0[0]])

            # Normalize directions
            dir0 = dir0 / (np.linalg.norm(dir0) + 1e-10)
            dir1 = dir1 / (np.linalg.norm(dir1) + 1e-10)
            dir2 = dir2 / (np.linalg.norm(dir2) + 1e-10)

            # Fixed step size with decay (independent of best_score)
            step = base_step * (decay ** step_counter)

            candidate = current.copy()
            candidate[i] += step * dir0
            candidate[j] += step * dir1
            candidate[k] += step * dir2

            # Project all points to ensure they're inside the triangle
            modified_indices = []
            for idx in range(len(candidate)):
                original = candidate[idx].copy()
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
                if not np.array_equal(original, candidate[idx]):
                    modified_indices.append(idx)

            # Compute candidate score using temporary cache
            temp_cache = triangle_cache.copy()
            if modified_indices:
                update_triangle_area_cache(temp_cache, candidate, modified_indices)
            else:
                update_triangle_area_cache(temp_cache, candidate, [i, j, k])
            
            new_score = min(area for area in temp_cache.values())
            current_score = min(area for area in triangle_cache.values())
            
            # Simulated annealing acceptance
            delta = new_score - current_score
            accepted = False
            
            if new_score > best_score:
                current = candidate
                triangle_cache = temp_cache  # Only update cache when accepting
                best_score = new_score
                best_config = candidate
                no_improve_count = 0
                accepted = True
                
                # Reset perturbation magnitude after improvement
                perturbation_magnitude = base_perturbation
            else:
                # Calculate acceptance probability for worse solutions
                if delta > 0 or (temp > 1e-8 and random.random() < np.exp(delta / temp)):
                    current = candidate
                    triangle_cache = temp_cache  # Only update cache when accepting
                    accepted = True
                no_improve_count += 1

            # Track acceptance rate for temperature adjustment
            total_moves += 1
            if accepted:
                acceptance_count += 1

            step_counter += 1

            # Adaptive temperature scheduling based on acceptance rate
            if step_counter % 100 == 0 and step_counter > 0:
                acceptance_rate = acceptance_count / max(1, total_moves)
                # Target acceptance rate is around 0.4-0.6 for good exploration
                if acceptance_rate < 0.3:
                    initial_temp *= 0.9  # Reduce temperature if too few acceptances
                elif acceptance_rate > 0.7:
                    initial_temp *= 1.1  # Increase temperature if too many acceptances
                acceptance_count = 0
                total_moves = 0

            # Adaptive restart magnitude based on stagnation depth
            stagnation_factor = no_improve_count / max_no_improve
            # Scale perturbation from base_perturbation to 0.5 based on stagnation
            perturbation_magnitude = base_perturbation + (0.5 - base_perturbation) * min(1.0, stagnation_factor ** 2)

            # Restart if stuck in local minimum
            if no_improve_count >= max_no_improve:
                # Reset to best configuration with significant perturbation
                current = best_config.copy()
                for i in range(len(current)):
                    perturbation = np.random.uniform(-perturbation_magnitude, perturbation_magnitude, size=2)
                    current[i] += perturbation
                    current[i] = project_to_triangle(current[i], A, B, C)
                
                # Update cache after restart
                update_triangle_area_cache(triangle_cache, current, list(range(len(current))))
                
                new_score = min(area for area in triangle_cache.values())
                if new_score > best_score:
                    best_score = new_score
                    best_config = current.copy()
                
                no_improve_count = 0
                step_counter = 0
                # Reset temperature after restart
                initial_temp = max(0.001, best_score * 10)
                temp = initial_temp

            # Adaptive global exploration based on stagnation
            if no_improve_count >= stagnation_threshold * 0.8:
                # First try global gradient ascent
                gradients = compute_gradient_for_all_points(current, triangle_cache)
                gradient_candidate = current.copy()
                
                # Apply gradient with adaptive step size
                gradient_step = base_step * 5 * (decay ** (step_counter/2))
                for i in range(len(gradient_candidate)):
                    gradient_candidate[i] += gradient_step * gradients[i]
                    gradient_candidate[i] = project_to_triangle(gradient_candidate[i], A, B, C)
                
                # Compute score for gradient candidate
                gradient_cache = triangle_cache.copy()
                update_triangle_area_cache(gradient_cache, gradient_candidate, list(range(len(gradient_candidate))))
                gradient_score = min(area for area in gradient_cache.values())
                
                # Accept if better
                if gradient_score > best_score:
                    current = gradient_candidate
                    triangle_cache = gradient_cache
                    best_score = gradient_score
                    best_config = gradient_candidate
                    no_improve_count = 0
                else:
                    # If gradient didn't help, do random perturbation
                    for i in range(len(current)):
                        perturbation = np.random.uniform(-perturbation_magnitude, perturbation_magnitude, size=2)
                        current[i] += perturbation
                        current[i] = project_to_triangle(current[i], A, B, C)
                    
                    # Update cache after global exploration
                    update_triangle_area_cache(triangle_cache, current, list(range(len(current))))
                    
                    new_score = min(area for area in triangle_cache.values())
                    if new_score > best_score:
                        best_score = new_score
                        best_config = current.copy()

        return best_config

    return improve