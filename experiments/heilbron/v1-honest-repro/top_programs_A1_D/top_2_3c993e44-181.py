from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.spatial import Delaunay
import random
import scipy.stats

np.random.seed(42)

def entrypoint():
    A_big, B_big, C_big = get_unit_triangle()

    def reflect_point(p, a, b):
        """Reflect point p across the line defined by points a and b."""
        ab = b - a
        if np.linalg.norm(ab) < 1e-10:
            return p
        ab_norm = ab / np.linalg.norm(ab)
        ap = p - a
        proj = np.dot(ap, ab_norm) * ab_norm
        return a + 2 * proj - ap

    def apply_symmetry(config):
        """Try reflecting points across symmetry axes and return the best configuration."""
        best_config = config.copy()
        best_score = get_smallest_triangle_area(config)
        
        # For equilateral triangle, symmetry axes go from vertices to midpoints of opposite sides
        mid_BC = (B_big + C_big) / 2
        mid_AC = (A_big + C_big) / 2
        mid_AB = (A_big + B_big) / 2
        
        axes = [
            (A_big, mid_BC),
            (B_big, mid_AC),
            (C_big, mid_AB)
        ]
        
        for a, b in axes:
            reflected = np.array([reflect_point(p, a, b) for p in config])
            
            # Ensure all points are inside the triangle
            for i in range(len(reflected)):
                if not is_inside_triangle(reflected[i], A_big, B_big, C_big):
                    # Project to boundary if outside
                    centroid = (A_big + B_big + C_big) / 3
                    direction = centroid - reflected[i]
                    step = 0.1
                    while not is_inside_triangle(reflected[i], A_big, B_big, C_big) and step > 1e-5:
                        reflected[i] += step * direction
                        step *= 0.5
            
            score = get_smallest_triangle_area(reflected)
            if score > best_score:
                best_score = score
                best_config = reflected.copy()
        
        return best_config

    def project_to_boundary(point, A, B, C):
        """Project a point to the nearest boundary if outside the triangle."""
        if is_inside_triangle(point, A, B, C):
            return point.copy()
        
        # Check distance to each edge and project to closest one
        edges = [(A, B), (B, C), (C, A)]
        min_dist = float('inf')
        closest_point = point.copy()
        
        for (p1, p2) in edges:
            # Vector from p1 to p2
            v = p2 - p1
            # Vector from p1 to point
            w = point - p1
            # Project w onto v
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 == 0:
                continue
            b = c1 / c2
            
            # Find closest point on line segment
            if b < 0:
                proj = p1
            elif b > 1:
                proj = p2
            else:
                proj = p1 + b * v
            
            # Check if this is closer than previous best
            dist = np.linalg.norm(point - proj)
            if dist < min_dist:
                min_dist = dist
                closest_point = proj
        
        return closest_point

    def get_adaptive_k_smallest_triangles(config, base_proportion=0.1):
        """Select triangles with area below adaptive proportion threshold based on area distribution skewness."""
        areas = []
        indices = []
        n = config.shape[0]
        for i in range(n):
            for j in range(i + 1, n):
                for l in range(j + 1, n):
                    p1, p2, p3 = config[i], config[j], config[l]
                    area2_val = abs(p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1]))
                    areas.append(area2_val)
                    indices.append((i, j, l))
        
        if len(areas) < 3:
            return indices[:1] if indices else []
        
        # Calculate skewness of area distribution
        skewness = scipy.stats.skew(areas)
        
        # Use skewness to determine target proportion (more skewed = focus more on smallest triangles)
        # Bounded between 0.05 and 0.25 to prevent extreme sensitivity
        target_proportion = 0.05 + 0.15 * (1 - min(max(skewness, 0), 2))
        
        # Sort areas
        sorted_indices = np.argsort(areas)
        sorted_areas = [areas[i] for i in sorted_indices]
        
        # Find threshold: adaptive proportion of smallest areas
        threshold_index = min(int(len(sorted_areas) * target_proportion), len(sorted_areas)-1)
        threshold = sorted_areas[threshold_index]
        
        # Return all triangles below threshold
        result = []
        for idx in sorted_indices:
            if areas[idx] <= threshold:
                result.append(indices[idx])
            else:
                break
        
        # Ensure we return at least one triangle
        return result if result else [indices[0]]

    def move_point_inside(point, direction, step, A, B, C):
        candidate = point + step * direction
        if is_inside_triangle(candidate, A, B, C):
            return candidate, step
        else:
            # Binary search to find the maximum valid step
            low, high = 0.0, step
            for _ in range(10):
                mid = (low + high) / 2
                candidate = point + mid * direction
                if is_inside_triangle(candidate, A, B, C):
                    low = mid
                else:
                    high = mid
            return point + low * direction, low

    def generate_adaptive_directions(triangle_points, num_directions_base=8):
        """Generate directions based on the geometry of the triangle with Constructor-aware enhancements."""
        directions = []
        
        # Get the three edges of the triangle
        p1, p2, p3 = triangle_points
        edges = [(p2 - p1), (p3 - p2), (p1 - p3)]
        
        # Calculate triangle aspect ratio to determine direction count
        edge_lengths = [np.linalg.norm(edge) for edge in edges]
        aspect_ratio = max(edge_lengths) / min(edge_lengths) if min(edge_lengths) > 1e-5 else 1.0
        num_directions = min(12, max(6, int(num_directions_base * aspect_ratio)))
        
        # For each edge, compute normal directions
        for edge in edges:
            if np.linalg.norm(edge) > 1e-10:
                normal = np.array([-edge[1], edge[0]])
                normal = normal / np.linalg.norm(normal)
                
                # Add the normal and some variations around it
                for i in range(num_directions // 3):
                    angle = (i - num_directions // 6) * np.pi / (num_directions // 3)
                    rotated = np.array([
                        normal[0] * np.cos(angle) - normal[1] * np.sin(angle),
                        normal[0] * np.sin(angle) + normal[1] * np.cos(angle)
                    ])
                    directions.append(rotated)
        
        # Add Constructor-specific directions targeting row patterns
        # Convert to barycentric coordinates to identify horizontal directions
        def cartesian_to_barycentric(p):
            v0 = B_big - A_big
            v1 = C_big - A_big
            v2 = p - A_big
            d00 = np.dot(v0, v0)
            d01 = np.dot(v0, v1)
            d11 = np.dot(v1, v1)
            d20 = np.dot(v2, v0)
            d21 = np.dot(v2, v1)
            denom = d00 * d11 - d01 * d01
            if abs(denom) < 1e-10:
                return np.array([0.33, 0.33, 0.34])
            v = (d11 * d20 - d01 * d21) / denom
            w = (d00 * d21 - d01 * d20) / denom
            u = 1.0 - v - w
            return np.array([u, v, w])
        
        # Calculate average barycentric height of the triangle points
        bary_coords = [cartesian_to_barycentric(p) for p in triangle_points]
        avg_height = np.mean([1 - bc[0] for bc in bary_coords])
        
        # If points are at similar heights (suggesting row pattern), add horizontal directions
        if max([1 - bc[0] for bc in bary_coords]) - min([1 - bc[0] for bc in bary_coords]) < 0.1:
            # Horizontal direction in barycentric coordinates (constant height)
            horizontal_dir = B_big - A_big
            horizontal_dir = horizontal_dir / np.linalg.norm(horizontal_dir)
            directions.append(horizontal_dir)
            directions.append(-horizontal_dir)
        
        # Add some random exploration directions
        for _ in range(num_directions - len(directions)):
            angle = np.random.uniform(0, 2 * np.pi)
            directions.append(np.array([np.cos(angle), np.sin(angle)]))
        
        return directions

    def improve(points: np.ndarray) -> np.ndarray:
        # Parameters for multi-start optimization - now adaptive based on initial quality
        base_runs = 3
        initial_score = get_smallest_triangle_area(points)
        # More runs for better initial configurations (indicating harder problem)
        num_runs = base_runs + min(3, int(initial_score / 0.005))
        
        best_overall = points.copy()
        best_overall_score = initial_score

        # Track improvement history for adaptive temperature scheduling
        improvement_history = []
        ema_alpha = 0.2  # Exponential moving average factor

        for run in range(num_runs):
            # Each run starts from a different configuration
            if run == 0:
                current = points.copy()
            else:
                # Perturb the original points for diversity
                current = points.copy() + np.random.uniform(-0.01, 0.01, points.shape)
                # Ensure all points are inside the triangle
                for i in range(len(current)):
                    if not is_inside_triangle(current[i], A_big, B_big, C_big):
                        current[i] = project_to_boundary(current[i], A_big, B_big, C_big)

            # Parameters for simulated annealing - now adaptive
            base_temp = 0.1
            # Adjust initial temperature based on initial score (harder problems need more exploration)
            initial_temp = base_temp * (1.0 + 2.0 * (0.0365 - initial_score) / 0.0365)
            step_size_factor = 5.0
            base_cooling_rate = 0.95
            min_temp = 1e-6
            
            # Parameters for multi-triangle targeting
            base_symmetry_prob = 0.3
            
            # Track best for this run
            best = current.copy()
            current_score = get_smallest_triangle_area(current)
            best_score = current_score
            
            # Track improvement history for restarts and temperature scheduling
            no_improve_count = 0
            max_no_improve = 15  # Will be made adaptive later

            # Simulated annealing main loop
            temp = initial_temp
            while temp > min_temp:
                # Select triangles adaptively based on area distribution
                top_triangles = get_adaptive_k_smallest_triangles(current)
                
                # Randomly select a triangle from the targeted set
                triangle_indices = random.choice(top_triangles)
                
                # Get the triangle points
                triangle_points = [current[i] for i in triangle_indices]
                
                # Generate adaptive directions
                directions = generate_adaptive_directions(triangle_points)
                
                # Try moving each point in the triangle
                improved_this_step = False
                for idx in triangle_indices:
                    for direction in directions:
                        # Try different step sizes - decoupled from temperature
                        step_size = step_size_factor * temp
                        while step_size > 1e-5:
                            candidate_points = current.copy()
                            new_point, actual_step = move_point_inside(
                                current[idx], direction, step_size, A_big, B_big, C_big
                            )
                            candidate_points[idx] = new_point
                            
                            candidate_score = get_smallest_triangle_area(candidate_points)
                            
                            # Simulated annealing acceptance criterion
                            delta = candidate_score - current_score
                            if delta > 0 or (delta > -1e-7 and np.random.rand() < np.exp(delta / temp)):
                                current = candidate_points
                                current_score = candidate_score
                                if current_score > best_score:
                                    best = current.copy()
                                    best_score = current_score
                                    no_improve_count = 0
                                    
                                    # Update improvement history
                                    if improvement_history:
                                        improvement_history[0] = 0.9 * improvement_history[0] + 0.1 * delta
                                    else:
                                        improvement_history = [delta]
                                improved_this_step = True
                                break  # Move to next direction after accepting a move
                            
                            if actual_step < step_size * 0.9:  # If we hit the boundary
                                break
                            
                            step_size *= 0.5  # Try smaller step
                
                # Periodically try symmetry-based improvements
                symmetry_prob = base_symmetry_prob
                # Increase symmetry probability if configuration shows partial symmetry
                if best_score > initial_score * 0.9:
                    symmetry_prob = min(0.7, symmetry_prob * 1.5)
                    
                if np.random.rand() < symmetry_prob:
                    symmetric_points = apply_symmetry(current)
                    symmetric_score = get_smallest_triangle_area(symmetric_points)
                    if symmetric_score > current_score:
                        current = symmetric_points
                        current_score = symmetric_score
                        if current_score > best_score:
                            best = current.copy()
                            best_score = current_score
                        improved_this_step = True

                # Adaptive cooling rate based on improvement history
                if improvement_history:
                    avg_improvement = improvement_history[0]
                    # If improving well, cool slower to explore more
                    if avg_improvement > 0.0001:
                        cooling_rate = max(0.90, base_cooling_rate - 0.03)
                    # If stuck, cool faster to intensify search
                    elif avg_improvement < 1e-6:
                        cooling_rate = min(0.98, base_cooling_rate + 0.02)
                    else:
                        cooling_rate = base_cooling_rate
                else:
                    cooling_rate = base_cooling_rate

                # Track improvement for restart logic
                if not improved_this_step:
                    no_improve_count += 1
                    if no_improve_count >= max_no_improve:
                        # Perturb to escape local optimum
                        perturbation = np.random.uniform(-0.01, 0.01, current.shape)
                        current = best.copy() + perturbation
                        # Ensure points stay inside
                        for i in range(len(current)):
                            if not is_inside_triangle(current[i], A_big, B_big, C_big):
                                current[i] = project_to_boundary(current[i], A_big, B_big, C_big)
                        current_score = get_smallest_triangle_area(current)
                        no_improve_count = 0
                else:
                    no_improve_count = 0

                # Cool the temperature
                temp *= cooling_rate

            # After each run, apply symmetry one final time for good measure
            symmetric_best = apply_symmetry(best)
            symmetric_score = get_smallest_triangle_area(symmetric_best)
            if symmetric_score > best_score:
                best = symmetric_best
                best_score = symmetric_score

            # Update overall best if this run was better
            if best_score > best_overall_score:
                best_overall = best.copy()
                best_overall_score = best_score

        return best_overall

    return improve