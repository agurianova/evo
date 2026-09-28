import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    def get_min_triangle_indices(points):
        n = points.shape[0]
        min_areas = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                    (points[j,1]-points[i,1])*(points[k,0]-points[i,0]))
                    min_areas.append((area, i, j, k))
        min_areas.sort(key=lambda x: x[0])
        return min_areas

    def hexagonal_lattice_seeding(num_points):
        A, B, C = get_unit_triangle()
        
        # Calculate triangle dimensions
        base = np.linalg.norm(B - A)
        height = np.linalg.norm(C - A)
        
        # Create hexagonal grid within triangle
        grid_points = []
        rows = 5  # Enough rows to generate more points than needed
        cols = 5
        
        # Calculate grid spacing based on triangle dimensions
        dx = base / (cols + 1)
        dy = height * math.sqrt(3) / 2 / (rows + 1)
        
        for i in range(1, rows + 1):
            y = i * dy
            # Alternate row offset for hexagonal pattern
            x_offset = (dx / 2) if i % 2 == 0 else 0
            for j in range(1, cols + 1):
                x = j * dx + x_offset
                # Convert to barycentric coordinates
                s = x / base
                t = y / height
                if s + t <= 1:
                    point = A + s*(B - A) + t*(C - A)
                    grid_points.append(point)
        
        # Add points near vertices for better coverage
        grid_points.extend([
            A + 0.1*(B - A) + 0.1*(C - A),
            B - 0.1*(B - A) + 0.1*(C - A),
            C + 0.1*(B - A) - 0.1*(C - A)
        ])
        
        # Select num_points closest to grid vertices
        points_list = []
        min_dist = 1e-5
        
        # Start with a point near the centroid
        if grid_points:
            centroid = np.array([0.5, height/3])
            closest_idx = min(range(len(grid_points)), 
                             key=lambda i: np.linalg.norm(grid_points[i] - centroid))
            points_list.append(grid_points[closest_idx])
            grid_points.pop(closest_idx)
        
        # Greedily select remaining points maximizing minimum distance
        while len(points_list) < num_points and grid_points:
            best_point = None
            max_min_dist = -1
            
            for point in grid_points:
                min_dist_to_existing = min(np.linalg.norm(point - p) for p in points_list)
                if min_dist_to_existing > max_min_dist:
                    max_min_dist = min_dist_to_existing
                    best_point = point
            
            if best_point is not None:
                points_list.append(best_point)
                grid_points.remove(best_point)

        # If we don't have enough points, fall back to random
        while len(points_list) < num_points:
            s = random.random() * 0.8
            t = random.random() * 0.8
            if s + t > 1:
                s = 1 - s
                t = 1 - t
            point = A + s*(B - A) + t*(C - A)
            
            too_close = False
            for p in points_list:
                if np.linalg.norm(point - p) < min_dist:
                    too_close = True
                    break
            if not too_close:
                points_list.append(point)

        return np.array(points_list)

    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate initial points using hexagonal lattice seeding
    points = hexagonal_lattice_seeding(11)

    # Optimization parameters
    max_iter = 800
    initial_step_size = 0.05
    step_size = initial_step_size
    min_step = 1e-5
    decay = 0.99  # Slower decay rate
    
    # Simulated annealing parameters
    temperature = 0.05
    temp_decay = 0.995

    for iter in range(max_iter):
        # Get top 3 smallest triangles
        all_triangles = get_min_triangle_indices(points)
        top_triangles = all_triangles[:3]
        
        current_min = top_triangles[0][0]

        best_new_min = current_min
        best_move = None
        
        # Try moving points in top 3 triangles with 8 directions each
        for area, i, j, k in top_triangles:
            for idx in [i, j, k]:
                # Get the other two points
                if idx == i:
                    p1, p2 = points[j], points[k]
                elif idx == j:
                    p1, p2 = points[i], points[k]
                else:
                    p1, p2 = points[i], points[j]

                # Generate 8 directions around the gradient
                dx = p1[1] - p2[1]
                dy = p2[0] - p1[0]
                norm = np.sqrt(dx*dx + dy*dy)
                if norm < 1e-10:
                    continue
                dx, dy = dx/norm, dy/norm
                
                # Sample 8 directions (45 degree increments)
                directions = []
                for angle in range(0, 360, 45):
                    rad = math.radians(angle)
                    dir_x = dx * math.cos(rad) - dy * math.sin(rad)
                    dir_y = dx * math.sin(rad) + dy * math.cos(rad)
                    directions.append(np.array([dir_x, dir_y]))

                for disp_dir in directions:
                    disp = disp_dir * step_size
                    new_point = points[idx] + disp

                    # Check if inside triangle
                    if not is_inside_triangle(new_point, A, B, C):
                        continue

                    # Check distinctness
                    too_close = False
                    for other_idx in range(11):
                        if other_idx == idx:
                            continue
                        if np.linalg.norm(new_point - points[other_idx]) < 1e-5:
                            too_close = True
                            break
                    if too_close:
                        continue

                    # Test new configuration
                    new_points = points.copy()
                    new_points[idx] = new_point
                    new_min_area = get_smallest_triangle_area(new_points)

                    # Simulated annealing acceptance
                    if new_min_area > best_new_min:
                        # Always accept improvements
                        if new_min_area > best_new_min:
                            best_new_min = new_min_area
                            best_move = (idx, disp)
                    else:
                        # Accept worsening with probability exp(-delta/temperature)
                        delta = new_min_area - current_min
                        if delta < 0 and random.random() < math.exp(delta / temperature):
                            best_new_min = new_min_area
                            best_move = (idx, disp)

        if best_move is not None:
            idx, disp = best_move
            points[idx] += disp
            # Reset step size when improvement found
            step_size = initial_step_size
        else:
            step_size *= decay
            
        # Update temperature
        temperature *= temp_decay

        # Early termination if step size too small
        if step_size < min_step:
            break

    return points