import numpy as np

# G's original point configuration
_G_POINTS = np.array([[1.1872581390255146, 0.30006656387464076], [0.00741021362035143, 0.012831326965731969], [0.7311582745227236, 1.2663942977829616], [0.4939522219024318, 0.5775280346589481], [0.6264471777582592, 2.4154475511916903e-08], [0.9222361432084993, 0.7864503446719178], [1.4971265157174685, 0.035238461836738566], [0.8037231429278632, 0.35973407314963135], [0.3333984121869694, 0.2510128164309754], [0.5693564195156566, 0.9403845549382497], [0.9847664039007104, 0.052415910691650275]], dtype=np.float64)

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import random


def _d_entrypoint():
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
        
        # Slower buffer decay: allows more gradual boundary approach
        buffer_val = buffer_base * (0.99 ** iteration)
        
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
        
        # Slower buffer decay
        buffer_val = buffer_base * (0.99 ** iteration)
        
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
        
        # Enhanced temperature schedule
        initial_temp = best_score * 100.0

        # Helper for triangle area computation
        def triangle_area(p0, p1, p2):
            v1 = p1 - p0
            v2 = p2 - p0
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            signed = 0.5 * cross
            return signed, abs(signed)

        for iter in range(max_iter):
            # LINEAR SCALING for k_smallest - maintains balanced exploration throughout
            k_smallest = max(3, min(10, int(3 + 7 * (1 - best_score/0.0365))))
            
            # ADD STAGNATION RESPONSE - broadens search when stuck
            k_smallest += int(3 * no_improve_count / max_no_improve)

            # IMPROVED TEMPERATURE DECAY - maintains exploration longer
            temp_decay = 0.95 + 0.045 * np.sqrt(max(0, 1 - (0.0365 - best_score)/0.0365))

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
            
            # DYNAMICALLY ADJUSTED weight cap based on current min_area (REVERSED DIRECTION)
            weight_cap = 200 - 150 * (best_score / 0.0365)
            
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

                # Weight by inverse area with dynamic cap
                weight = min(weight_cap, 1.0 / (abs_val + 1e-10))
                total_weight += weight

                # Accumulate weighted gradients
                gradient[i] += weight * dir0
                gradient[j] += weight * dir1
                gradient[k] += weight * dir2

            # Normalize by total weight
            if total_weight > 0:
                gradient /= total_weight

            # ADAPTIVE step size decay based on stagnation patterns
            step_decay = 0.995 + 0.004 * (no_improve_count / max_no_improve)
            step = base_step_factor * triangle_side * (step_decay ** step_counter)

            # Create candidate by applying gradient
            candidate = current.copy()
            
            # ADD ADAPTIVE ORTHOGONAL EXPLORATION - increases exploration when stuck
            orthogonal_prob = 0.05 + 0.2 * (no_improve_count / max_no_improve)
            if random.random() < orthogonal_prob:
                for i in range(len(candidate)):
                    if np.linalg.norm(gradient[i]) > 1e-10:
                        # Rotate gradient by 90 degrees
                        gradient[i] = np.array([-gradient[i][1], gradient[i][0]])

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
                
                # ADAPTIVE perturbation scale based on problem difficulty
                base_perturbation = 0.1 + 0.05 * (1 - best_score / 0.0365)
                stagnation_factor = 1 + no_improve_count / max_no_improve
                perturbation_scale = base_perturbation * triangle_side * stagnation_factor
                for i in range(len(current)):
                    current[i] += perturbation_scale * np.random.uniform(-1, 1, size=2)
                    current[i] = project_to_triangle(current[i], iter, max_iter)
                
                no_improve_count = 0
                step_counter = 0

        return best_config, best_score

    def improve(points: np.ndarray) -> np.ndarray:
        # ADAPTIVE restart strategy based on initial difficulty (INVERTED FORMULA)
        initial_min_area = get_smallest_triangle_area(points)
        n_starts = max(3, min(8, 3 + int(5 * initial_min_area/0.0365)))
        
        best_config = None
        best_score = -1
        
        for i in range(n_starts):
            # CONFIGURATION-DEPENDENT seeds for better diversity
            config_hash = hash(tuple(np.round(points, 3).flatten())) % 10000
            seed = config_hash + i * 10000
            
            # Run optimization
            config, score = optimize_configuration(points.copy(), seed=seed)
            
            # Update best if improved
            if score > best_score:
                best_config = config
                best_score = score
                
        return best_config

    return improve

def entrypoint():
    """D's improvement of G's points, as a valid G program."""
    improve_fn = _d_entrypoint()
    improved = improve_fn(_G_POINTS.copy())
    return np.asarray(improved, dtype=np.float64)