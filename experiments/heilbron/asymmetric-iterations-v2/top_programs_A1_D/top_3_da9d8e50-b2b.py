from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import random


def entrypoint():
    A, B, C = get_unit_triangle()
    triangle_side = np.linalg.norm(B - A)
    
    # Precompute triangle vectors for barycentric calculations
    AB = B - A
    AC = C - A
    tri_area = 0.5 * abs(AB[0]*AC[1] - AB[1]*AC[0])

    def cartesian_to_barycentric(p):
        """Convert Cartesian coordinates to barycentric coordinates"""
        v0 = C - A
        v1 = B - A
        v2 = p - A
        
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w
        
        return np.array([u, v, w])

    def barycentric_to_cartesian(bary, iteration, max_iterations, buffer_base=0.01, buffer_sigmoid_param=8.0):
        """Convert barycentric coordinates to Cartesian coordinates with adaptive edge buffer"""
        u, v, w = bary
        
        # Sigmoid buffer decay for smarter boundary management
        sigmoid_factor = 1 / (1 + np.exp(buffer_sigmoid_param * (iteration / max_iterations - 0.5)))
        buffer_val = buffer_base * sigmoid_factor
        
        # Ensure minimum distance from each edge
        u = max(buffer_val, u)
        v = max(buffer_val, v)
        w = max(buffer_val, w)
        total = u + v + w
        if total > 0:
            u, v, w = u/total, v/total, w/total
        return A * u + B * v + C * w

    def project_to_triangle(p, iteration, max_iterations, buffer_base=0.01, buffer_sigmoid_param=8.0):
        """Project point to nearest valid position inside triangle with adaptive buffer"""
        bary = cartesian_to_barycentric(p)
        
        # Sigmoid buffer decay for smarter boundary management
        sigmoid_factor = 1 / (1 + np.exp(buffer_sigmoid_param * (iteration / max_iterations - 0.5)))
        buffer_val = buffer_base * sigmoid_factor
        
        # Clamp to [buffer, 1] range and ensure u+v+w=1
        bary = np.clip(bary, buffer_val, 1)
        total = np.sum(bary)
        if total > 0:
            bary = bary / total
        
        return barycentric_to_cartesian(bary, iteration, max_iterations, buffer_base, buffer_sigmoid_param)

    def optimize_configuration(points, seed=None, max_iter=10000):
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
            
        # Configuration parameters
        base_step_factor = 0.05  # Now relative to triangle side length
        
        # Adaptive parameters - key innovation: exploration INCREASES as solution improves
        initial_min_area = get_smallest_triangle_area(points)
        max_no_improve = max(300, min(1000, int(700 * initial_min_area / 0.0365)))
        
        # Initialize with current configuration
        current = points.copy()
        best_score = get_smallest_triangle_area(current)
        best_config = current.copy()
        no_improve_count = 0
        step_counter = 0
        
        # NEW: Sigmoid-scaled temperature parameters based on initial problem difficulty
        # More difficult problems (lower initial_min_area) get higher initial temperature for better exploration
        temp_initial_factor = 120.0 * (1.0 / (1 + np.exp(-10.0 * (initial_min_area/0.0365 - 0.5))))
        temp_decay_base = 0.985 + 0.007 * (initial_min_area/0.0365)
        temp_decay_factor = 0.006
        initial_temp = best_score * temp_initial_factor

        # Helper for triangle area computation
        def triangle_area(p0, p1, p2):
            v1 = p1 - p0
            v2 = p2 - p0
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            signed = 0.5 * cross
            return signed, abs(signed)

        # NEW: Targeted local search for smallest triangle
        def local_search_smallest_triangle(config, max_local_iter=100):
            """Focuses optimization on the smallest triangle by fixing all other points"""
            local_config = config.copy()
            current_score = get_smallest_triangle_area(local_config)
            
            # Find the absolute smallest triangle
            n = 11
            smallest_area = float('inf')
            smallest_tri = None
            
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        _, abs_val = triangle_area(local_config[i], local_config[j], local_config[k])
                        if abs_val < smallest_area:
                            smallest_area = abs_val
                            smallest_tri = (i, j, k)

            if smallest_tri is None:
                return local_config, current_score

            i, j, k = smallest_tri
            points_to_optimize = [i, j, k]
            
            # Adaptive step size for local search - smaller as solution improves
            local_step = 0.02 * triangle_side * (1.0 - current_score / 0.0365)
            
            for _ in range(max_local_iter):
                # Try small random perturbations to the three points
                candidate = local_config.copy()
                improved = False
                
                for idx in points_to_optimize:
                    # Try perturbation in random direction
                    direction = np.random.uniform(-1, 1, 2)
                    direction = direction / (np.linalg.norm(direction) + 1e-10)
                    
                    # Adaptive step size based on current progress
                    step = local_step * (0.5 + 0.5 * (current_score / smallest_area))
                    candidate[idx] = local_config[idx] + step * direction
                    
                    # Project to ensure triangle containment
                    candidate[idx] = project_to_triangle(candidate[idx], step_counter, max_iter)
                    
                    # Evaluate
                    new_score = get_smallest_triangle_area(candidate)
                    if new_score > current_score:
                        current_score = new_score
                        local_config = candidate.copy()
                        improved = True
                        break  # Start over with new configuration

                if not improved:
                    # Try decreasing step size if no improvement
                    local_step *= 0.95

            return local_config, current_score

        for iter in range(max_iter):
            # Dynamic k_smallest - INCREASES as solution improves (opposite of previous)
            k_smallest = max(5, min(15, int(10 * best_score / 0.0365)))

            # Adaptive temperature decay based on current min_area
            temp_decay = temp_decay_base + temp_decay_factor * (best_score / 0.0365)

            # Find k smallest triangles by absolute area
            n = 11
            triangle_data = []
            
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        signed, abs_val = triangle_area(current[i], current[j], current[k])
                        triangle_data.append((abs_val, signed, i, j, k))
            
            # Sort and take k smallest
            triangle_data.sort(key=lambda x: x[0])
            smallest_triangles = triangle_data[:k_smallest]

            # NEW: Exponential weighting based on proximity to minimum area
            # Gives higher priority to triangles closer to the current minimum
            min_area_val = smallest_triangles[0][0]
            for idx in range(len(smallest_triangles)):
                area_val, signed, i, j, k = smallest_triangles[idx]
                # Exponential weighting: triangles closer to min get higher weight
                weight_factor = np.exp(-(area_val - min_area_val) / (min_area_val + 1e-10))
                smallest_triangles[idx] = (area_val, signed, i, j, k, weight_factor)

            if not smallest_triangles:
                break

            # Adaptive weight cap - DECREASES as solution improves (opposite of previous)
            weight_cap = max(50, 200 - 150 * (best_score / 0.0365))

            # Compute combined gradient from multiple small triangles
            gradient = np.zeros_like(current)
            total_weight = 0
            
            for item in smallest_triangles:
                if len(item) == 6:  # With weight factor
                    abs_val, signed, i, j, k, weight_factor = item
                else:
                    abs_val, signed, i, j, k = item
                    weight_factor = 1.0
                
                p0, p1, p2 = current[i], current[j], current[k]
                
                # Compute gradient directions for area increase
                dir0 = np.sign(signed) * np.array([p1[1] - p2[1], p2[0] - p1[0]])
                dir1 = np.sign(signed) * np.array([p2[1] - p0[1], p0[0] - p2[0]])
                dir2 = np.sign(signed) * np.array([p0[1] - p1[1], p1[0] - p0[0]])

                # Normalize directions
                dir0 = dir0 / (np.linalg.norm(dir0) + 1e-10)
                dir1 = dir1 / (np.linalg.norm(dir1) + 1e-10)
                dir2 = dir2 / (np.linalg.norm(dir2) + 1e-10)

                # Weight by inverse area with adaptive cap and proximity factor
                weight = min(weight_cap, 1.0 / (abs_val + 1e-10)) * weight_factor
                total_weight += weight

                # Accumulate weighted gradients
                gradient[i] += weight * dir0
                gradient[j] += weight * dir1
                gradient[k] += weight * dir2

            # Normalize by total weight
            if total_weight > 0:
                gradient /= total_weight

            # Current step size with adaptive scaling based on triangle geometry
            # Adaptive step decay - slower decay when solution is better
            step_decay = 0.99 + 0.009 * (best_score / 0.0365)
            step = base_step_factor * triangle_side * (step_decay ** step_counter)

            # Create candidate by applying gradient
            candidate = current.copy()
            candidate += step * gradient

            # Project all points to ensure triangle containment with adaptive buffer
            for i in range(len(candidate)):
                candidate[i] = project_to_triangle(candidate[i], iter, max_iter)

            # Evaluate candidate
            new_score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            if new_score > best_score:
                current = candidate
                best_score = new_score
                best_config = candidate
                no_improve_count = 0
            else:
                # Calculate acceptance probability for worse solutions
                delta = best_score - new_score
                temp = initial_temp * (temp_decay ** step_counter)
                if temp > 1e-8 and random.random() < np.exp(-delta / temp):
                    current = candidate
                no_improve_count += 1

            step_counter += 1

            # Enhanced restart with adaptive perturbation to escape deep local minima
            if no_improve_count >= max_no_improve:
                # NEW: Reverse perturbation logic - DECREASES with solution quality
                # Was harmful pattern: base_perturbation = 0.05 + 0.15 * (best_score / 0.0365)
                base_perturbation = 0.2 - 0.15 * (best_score / 0.0365)
                stagnation_factor = 1 + no_improve_count / max_no_improve
                perturbation_scale = base_perturbation * triangle_side * stagnation_factor
                
                # Start from best configuration but add significant perturbation
                current = best_config.copy()
                for i in range(len(current)):
                    current[i] += perturbation_scale * np.random.uniform(-1, 1, size=2)
                    current[i] = project_to_triangle(current[i], iter, max_iter)
                
                no_improve_count = 0
                step_counter = 0

            # NEW: Trigger local search when improvement stalls
            if no_improve_count >= max_no_improve * 0.7:
                local_config, local_score = local_search_smallest_triangle(current)
                if local_score > best_score:
                    current = local_config
                    best_score = local_score
                    best_config = local_config.copy()
                    no_improve_count = 0

        return best_config, best_score

    def improve(points: np.ndarray) -> np.ndarray:
        # Run multiple independent optimizations and return the best result
        # Adaptive restart count - MORE restarts for HARDER problems
        initial_min_area = get_smallest_triangle_area(points)
        n_starts = max(3, min(10, int(7 * (0.0365 - initial_min_area) / 0.0365)))
        
        best_config = None
        best_score = -1
        
        for i in range(n_starts):
            # Use different seed for each start
            seed = 42 + i
            
            # Run optimization
            config, score = optimize_configuration(points.copy(), seed=seed)
            
            # Update best if improved
            if score > best_score:
                best_config = config
                best_score = score
                
        return best_config

    return improve