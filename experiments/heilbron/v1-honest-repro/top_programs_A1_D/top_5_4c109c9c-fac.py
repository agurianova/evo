from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.spatial import Delaunay
import random

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

    def calculate_symmetry_score(config):
        """Calculate how well the configuration aligns with symmetry axes."""
        # For equilateral triangle, symmetry axes go from vertices to midpoints of opposite sides
        mid_BC = (B_big + C_big) / 2
        mid_AC = (A_big + C_big) / 2
        mid_AB = (A_big + B_big) / 2
        
        axes = [
            (A_big, mid_BC),
            (B_big, mid_AC),
            (C_big, mid_AB)
        ]
        
        total_score = 0.0
        n_points = len(config)
        
        for a, b in axes:
            # Reflect all points
            reflected = np.array([reflect_point(p, a, b) for p in config])
            
            # For each reflected point, find closest original point
            score = 0.0
            for rp in reflected:
                distances = np.linalg.norm(config - rp, axis=1)
                min_dist = np.min(distances)
                # Score is higher when reflected points align with existing points
                score += 1.0 / (1.0 + min_dist)
            
            total_score += score / n_points
        
        # Normalize by number of axes
        return total_score / 3.0

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

    def get_adaptive_k_smallest_triangles(config, current_min_area):
        """Select triangles with area below an adaptive threshold based on current min_area."""
        # Calculate adaptive target proportion: more aggressive when far from optimal
        # Target proportion ranges from 0.05 (near optimal) to 0.2 (far from optimal)
        optimal_area = 0.0365
        distance_from_optimal = optimal_area - current_min_area
        target_proportion = 0.05 + 0.15 * (distance_from_optimal / optimal_area)
        target_proportion = max(0.05, min(0.2, target_proportion))
        
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
        
        # Sort areas
        sorted_areas = sorted(areas)
        
        # Find threshold: target proportion of smallest areas
        threshold_index = min(int(len(sorted_areas) * target_proportion), len(sorted_areas)-1)
        threshold = sorted_areas[threshold_index]
        
        # Return all triangles below threshold
        result = []
        for area, idx in zip(areas, indices):
            if area <= threshold:
                result.append(idx)
        
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

    def generate_adaptive_directions(triangle_points, num_directions=10):
        """Generate directions based on the geometry of the triangle."""
        directions = []
        
        # Get the three edges of the triangle
        p1, p2, p3 = triangle_points
        edges = [(p2 - p1), (p3 - p2), (p1 - p3)]
        
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
        
        # Add some random exploration directions
        for _ in range(num_directions - len(directions)):
            angle = np.random.uniform(0, 2 * np.pi)
            directions.append(np.array([np.cos(angle), np.sin(angle)]))
        
        return directions

    def improve(points: np.ndarray) -> np.ndarray:
        # Parameters for multi-start optimization
        num_runs = 4  # Increased from 3 to allow more exploration
        best_overall = points.copy()
        best_overall_score = get_smallest_triangle_area(points)

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

            # Parameters for simulated annealing
            initial_temp = 0.1
            step_size_factor = 5.0
            min_temp = 1e-6
            
            # Track best for this run
            best = current.copy()
            current_score = get_smallest_triangle_area(current)
            best_score = current_score
            
            # Track improvement history for restarts and adaptation
            no_improve_count = 0
            max_no_improve = 15
            improvement_rate = 0.0  # Tracks recent improvement frequency
            improvement_history = []
            
            # Simulated annealing main loop
            temp = initial_temp
            while temp > min_temp:
                # Calculate adaptive cooling rate based on improvement history
                adaptive_cooling_rate = max(0.9, 0.95 - 0.05 * (no_improve_count / max_no_improve))
                
                # Calculate adaptive symmetry probability based on symmetry score
                symmetry_score = calculate_symmetry_score(current)
                symmetry_prob = 0.1 + 0.4 * symmetry_score  # Range from 0.1 to 0.5
                symmetry_prob = min(0.5, max(0.1, symmetry_prob))

                # Select triangles adaptively based on area distribution and current min_area
                top_triangles = get_adaptive_k_smallest_triangles(current, current_score)
                
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
                        # Try different step sizes - decoupled from temperature but with improvement rate
                        step_size = step_size_factor * temp * (1 + 0.25 * improvement_rate)
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
                                    improvement_history.append(1)
                                else:
                                    improvement_history.append(0)
                                improved_this_step = True
                                break  # Move to next direction after accepting a move
                            
                            if actual_step < step_size * 0.9:  # If we hit the boundary
                                break
                            
                            step_size *= 0.5  # Try smaller step
                
                # Periodically try symmetry-based improvements
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

                # Track improvement for restart logic and adaptation
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

                # Update improvement rate (last 20 steps)
                improvement_history = improvement_history[-20:]
                if improvement_history:
                    improvement_rate = sum(improvement_history) / len(improvement_history)

                # Cool the temperature
                temp *= adaptive_cooling_rate

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