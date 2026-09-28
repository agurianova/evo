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

    def distance_to_line(p, a, b):
        """Calculate perpendicular distance from point p to line segment ab."""
        num = abs((b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0]))
        den = np.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)
        return num / den

    def add_boundary_repulsion(point, A, B, C, best_score):
        """Add a small force pushing points away from triangle boundaries with adaptive threshold."""
        # Adaptive threshold based on current solution quality
        threshold = 0.01 + 0.015 * (0.0365 - best_score)
        
        d1 = distance_to_line(point, A, B)
        d2 = distance_to_line(point, B, C)
        d3 = distance_to_line(point, C, A)
        
        min_dist = min(d1, d2, d3)
        
        # If very close to boundary, add repulsion
        if min_dist < threshold:
            repulsion = 0.01 * (threshold - min_dist)  # Strength proportional to proximity
            
            # Direction away from closest boundary
            if min_dist == d1:  # Closest to AB
                # Calculate normal consistently using vector math
                dir_ab = B - A
                normal = np.array([-dir_ab[1], dir_ab[0]])
                normal = normal / (np.linalg.norm(normal) + 1e-10)
            elif min_dist == d2:  # Closest to BC
                # Normal vector perpendicular to BC
                dir_bc = C - B
                normal = np.array([-dir_bc[1], dir_bc[0]])
                normal = normal / (np.linalg.norm(normal) + 1e-10)
            else:  # Closest to CA
                # Normal vector perpendicular to CA
                dir_ca = A - C
                normal = np.array([-dir_ca[1], dir_ca[0]])
                normal = normal / (np.linalg.norm(normal) + 1e-10)
            
            return point + repulsion * normal
        
        return point

    def triangle_area(p0, p1, p2):
        v1 = p1 - p0
        v2 = p2 - p0
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        signed = 0.5 * cross
        return signed, abs(signed)

    def update_triangle_cache(cache, points, modified_indices):
        """Update only triangles affected by modified points."""
        n = len(points)
        for i in modified_indices:
            for j in range(n):
                if j == i:
                    continue
                for k in range(j+1, n):
                    if k == i:
                        continue
                    idx = tuple(sorted([i, j, k]))
                    _, area = triangle_area(points[idx[0]], points[idx[1]], points[idx[2]])
                    cache[idx] = area

    def get_k_smallest_triangles(cache, k):
        """Get k smallest triangles from cache."""
        sorted_triangles = sorted(cache.items(), key=lambda x: x[1])
        return [(area, i, j, k) for ((i, j, k), area) in sorted_triangles[:k]]

    def improve(points: np.ndarray) -> np.ndarray:
        base_step = 0.01
        decay = 0.999
        max_iter = 10000
        max_no_improve = 500

        current = points.copy()
        best_score = get_smallest_triangle_area(current)
        best_config = current.copy()
        no_improve_count = 0
        step_counter = 0
        
        # Initialize triangle area cache
        triangle_cache = {}
        n = 11
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    _, area = triangle_area(current[i], current[j], current[k])
                    triangle_cache[(i, j, k)] = area

        # Initialize adaptive temperature for simulated annealing with higher multiplier
        initial_temp = max(0.005, best_score * 8)  # Increased from *5 to *8 with higher minimum
        temp_decay = 0.9999

        for _ in range(max_iter):
            # Calculate area ratio for adaptive parameter tuning
            min_area = min(triangle_cache.values())
            max_area = max(triangle_cache.values())
            area_ratio = min_area / max_area if max_area > 0 else 1.0
            
            # INCREASED k_smallest_count multiplier from 10 to 20
            k_smallest_count = max(3, int(20 * area_ratio))
            
            # Get k smallest triangles from cache
            k_smallest = get_k_smallest_triangles(triangle_cache, k_smallest_count)
            
            if not k_smallest:
                break

            # Randomly select one of the k smallest triangles to optimize
            _, i, j, k = random.choice(k_smallest)
            p0, p1, p2 = current[i], current[j], current[k]

            # Compute gradient directions for area increase
            signed, area_val = triangle_area(p0, p1, p2)
            
            # ADAPTIVE threshold for near-degenerate triangles based on current solution quality
            degenerate_threshold = max(1e-8, 0.001 * best_score)
            
            if area_val < degenerate_threshold:
                # Use random perturbation instead of gradient direction
                dir0 = np.random.uniform(-1, 1, size=2)
                dir1 = np.random.uniform(-1, 1, size=2)
                dir2 = np.random.uniform(-1, 1, size=2)
                
                # Normalize directions
                dir0 = dir0 / (np.linalg.norm(dir0) + 1e-10)
                dir1 = dir1 / (np.linalg.norm(dir1) + 1e-10)
                dir2 = dir2 / (np.linalg.norm(dir2) + 1e-10)
            else:
                dir0 = np.sign(signed) * np.array([p1[1] - p2[1], p2[0] - p1[0]])
                dir1 = np.sign(signed) * np.array([p2[1] - p0[1], p0[0] - p2[0]])
                dir2 = np.sign(signed) * np.array([p0[1] - p1[1], p1[0] - p0[0]])

                # Normalize directions
                dir0 = dir0 / (np.linalg.norm(dir0) + 1e-10)
                dir1 = dir1 / (np.linalg.norm(dir1) + 1e-10)
                dir2 = dir2 / (np.linalg.norm(dir2) + 1e-10)

            # NON-LINEAR scaling factor for more effective adjustments
            scaling_factor = 0.1 + 0.9 * (1 - area_ratio)**2
            step = max(1e-6, best_score * scaling_factor) * (decay ** step_counter)

            candidate = current.copy()
            candidate[i] += step * dir0
            candidate[j] += step * dir1
            candidate[k] += step * dir2

            # Apply boundary repulsion before projection with adaptive threshold
            for idx in range(len(candidate)):
                candidate[idx] = add_boundary_repulsion(candidate[idx], A, B, C, best_score)

            # Project all points to ensure they're inside the triangle
            for idx in range(len(candidate)):
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

            # Update triangle cache for modified points
            modified_indices = [i, j, k]
            update_triangle_cache(triangle_cache, candidate, modified_indices)

            # Evaluate candidate using cache
            new_score = min(triangle_cache.values())
            
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

            # ENHANCED restart perturbation with adaptive scaling
            if no_improve_count >= max_no_improve:
                # Reset to best configuration with adaptive perturbation
                current = best_config.copy()
                # Adaptive perturbation magnitude based on solution quality
                perturbation_magnitude = 0.08 * (1 + 0.5 * (0.0365 - best_score) / 0.0365) * \
                                    (1 + no_improve_count / max_no_improve)
                for i in range(len(current)):
                    perturbation = np.random.uniform(-perturbation_magnitude, perturbation_magnitude, size=2)
                    current[i] += perturbation
                    current[i] = project_to_triangle(current[i], A, B, C)
                
                # Update cache after restart
                update_triangle_cache(triangle_cache, current, list(range(len(current))))
                
                no_improve_count = 0
                step_counter = 0

            # ADAPTED global exploration phase with linear decay
            if step_counter % 1000 == 0 and step_counter > 0:
                # Linear decay instead of exponential
                perturbation_magnitude = 0.1 * (1 - step_counter / max_iter)
                for i in range(len(current)):
                    perturbation = np.random.uniform(-perturbation_magnitude, perturbation_magnitude, size=2)
                    current[i] += perturbation
                    current[i] = project_to_triangle(current[i], A, B, C)
                
                # Update cache after global exploration
                update_triangle_cache(triangle_cache, current, list(range(len(current))))
                
                new_score = min(triangle_cache.values())
                if new_score > best_score:
                    best_score = new_score
                    best_config = current.copy()

        return best_config

    return improve