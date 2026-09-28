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

    def barycentric_to_cartesian(bary, iteration, max_iterations, buffer_base=0.01):
        """Convert barycentric coordinates to Cartesian coordinates with adaptive edge buffer"""
        u, v, w = bary
        # Sigmoid buffer decay for smarter boundary management
        buffer_val = buffer_base * (1 / (1 + np.exp(5 * (iteration/max_iterations - 0.5))))
        
        # Ensure minimum distance from each edge
        u = max(buffer_val, u)
        v = max(buffer_val, v)
        w = max(buffer_val, w)
        total = u + v + w
        if total > 0:
            u, v, w = u/total, v/total, w/total
        return A * u + B * v + C * w

    def project_to_triangle(p, iteration, max_iterations, buffer_base=0.01):
        """Project point to nearest valid position inside triangle with adaptive buffer"""
        bary = cartesian_to_barycentric(p)
        
        # Sigmoid buffer decay for smarter boundary management
        buffer_val = buffer_base * (1 / (1 + np.exp(5 * (iteration/max_iterations - 0.5))))
        
        # Clamp to [buffer, 1] range and ensure u+v+w=1
        bary = np.clip(bary, buffer_val, 1)
        total = np.sum(bary)
        if total > 0:
            bary = bary / total
        
        return barycentric_to_cartesian(bary, iteration, max_iterations, buffer_base)

    def optimize_configuration(points, seed=None, max_iter=10000):
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
            
        # Configuration parameters
        base_step_factor = 0.05  # Now relative to triangle side length
        max_no_improve = 500
        
        # Initialize with current configuration
        current = points.copy()
        best_score = get_smallest_triangle_area(current)
        best_config = current.copy()
        no_improve_count = 0
        step_counter = 0
        
        # Calculate initial min area for adaptive parameters
        current_min_area = best_score
        
        # Enhanced temperature schedule with adaptive decay
        initial_temp = best_score * 100.0
        temp_decay = 0.99 + 0.005 * (current_min_area / 0.0365)  # Adaptive cooling

        # Helper for triangle area computation
        def triangle_area(p0, p1, p2):
            v1 = p1 - p0
            v2 = p2 - p0
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            signed = 0.5 * cross
            return signed, abs(signed)

        for iter in range(max_iter):
            # Calculate adaptive k_smallest based on current min area
            current_min_area = get_smallest_triangle_area(current)
            k_smallest = max(3, min(10, int(10 * (0.0365 - current_min_area) / 0.0365)))

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

            if not smallest_triangles:
                break

            # Compute combined gradient from multiple small triangles
            gradient = np.zeros_like(current)
            total_weight = 0
            
            # Adaptive weight cap based on optimization progress
            weight_cap = 50 + 150 * (current_min_area / 0.0365)
            
            for abs_val, signed, i, j, k in smallest_triangles:
                p0, p1, p2 = current[i], current[j], current[k]
                
                # Compute gradient directions for area increase
                dir0 = np.sign(signed) * np.array([p1[1] - p2[1], p2[0] - p1[0]])
                dir1 = np.sign(signed) * np.array([p2[1] - p0[1], p0[0] - p2[0]])
                dir2 = np.sign(signed) * np.array([p0[1] - p1[1], p1[0] - p0[0]])

                # Normalize directions
                dir0 = dir0 / (np.linalg.norm(dir0) + 1e-10)
                dir1 = dir1 / (np.linalg.norm(dir1) + 1e-10)
                dir2 = dir2 / (np.linalg.norm(dir2) + 1e-10)

                # Weight by inverse area with adaptive cap
                weight = min(weight_cap, 1.0 / (abs_val + 1e-10))
                total_weight += weight

                # Accumulate weighted gradients
                gradient[i] += weight * dir0
                gradient[j] += weight * dir1
                gradient[k] += weight * dir2

            # Normalize by total weight
            if total_weight > 0:
                gradient /= total_weight

            # Adaptive step decay based on stagnation
            step_decay = 0.995 + 0.004 * (no_improve_count / max_no_improve)
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
                # Start from best configuration but add significant perturbation
                current = best_config.copy()
                
                # Adaptive base perturbation based on problem hardness
                base_perturbation = 0.1 + 0.05 * (1 - current_min_area / 0.0365)
                stagnation_factor = 1 + no_improve_count / max_no_improve
                perturbation_scale = base_perturbation * triangle_side * stagnation_factor
                for i in range(len(current)):
                    current[i] += perturbation_scale * np.random.uniform(-1, 1, size=2)
                    current[i] = project_to_triangle(current[i], iter, max_iter)
                
                no_improve_count = 0
                step_counter = 0

        return best_config, best_score

    def improve(points: np.ndarray) -> np.ndarray:
        # Run multiple independent optimizations and return the best result
        n_starts = 3
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