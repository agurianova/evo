import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import random

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Hexagonal lattice initialization with noise
    def hexagonal_lattice_init(n, A, B, C):
        # Calculate triangle height and width
        width = np.linalg.norm(B - A)
        height = np.linalg.norm(C - (A+B)/2)
        
        # Create hexagonal grid points
        points = []
        rows = 4  # For n=11, 4 rows works well
        points_per_row = [2, 3, 3, 3]  # Total 11 points
        
        # Convert triangle to coordinate system with A at origin, AB along x-axis
        base_vec = B - A
        height_vec = C - A
        
        for row in range(rows):
            y_pos = row * height / (rows - 1) if rows > 1 else 0
            num_points = points_per_row[row]
            
            for col in range(num_points):
                x_pos = (col + 0.5 * (row % 2)) * width / (num_points + (row % 2) * 0.5)
                
                # Convert back to triangle coordinates
                u = x_pos / width
                v = y_pos / height
                
                # Ensure inside triangle
                if u + v > 1:
                    u = 1 - u
                    v = 1 - v
                
                P = A + u * (B - A) + v * (C - A)
                
                # Add controlled noise
                noise = np.random.normal(0, 0.02, 2)
                P += noise
                
                points.append(P)

        return np.array(points)

    def triangle_area(p1, p2, p3):
        return 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1]))

    def find_critical_triplet(points):
        n = len(points)
        min_area = float('inf')
        critical_triplet = None
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = triangle_area(points[i], points[j], points[k])
                    if area < min_area:
                        min_area = area
                        critical_triplet = (i, j, k)
        
        return critical_triplet, min_area

    def compute_gradient_directions(points, triplet):
        i, j, k = triplet
        p_i, p_j, p_k = points[i], points[j], points[k]

        # Compute signed area
        s_val = 0.5 * ((p_j[0]-p_i[0])*(p_k[1]-p_i[1]) - (p_j[1]-p_i[1])*(p_k[0]-p_i[0]))

        # Compute gradient directions for each point
        dir_i = np.array([p_j[1]-p_k[1], p_k[0]-p_j[0]])
        dir_j = np.array([p_k[1]-p_i[1], p_i[0]-p_k[0]])
        dir_k = np.array([p_i[1]-p_j[1], p_j[0]-p_i[0]])

        # Flip directions if necessary to increase area
        if s_val < 0:
            dir_i, dir_j, dir_k = -dir_i, -dir_j, -dir_k

        # Normalize
        norm_i = np.linalg.norm(dir_i)
        norm_j = np.linalg.norm(dir_j)
        norm_k = np.linalg.norm(dir_k)

        if norm_i > 1e-8:
            dir_i = dir_i / norm_i
        if norm_j > 1e-8:
            dir_j = dir_j / norm_j
        if norm_k > 1e-8:
            dir_k = dir_k / norm_k

        return dir_i, dir_j, dir_k

    def project_to_triangle(point, A, B, C):
        # Simple projection: if outside, move toward nearest edge
        if is_inside_triangle(point, A, B, C):
            return point
        
        # Calculate distances to each edge and project to closest one
        def distance_to_line(p, a, b):
            # Distance from point p to line segment ab
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / np.dot(ab, ab)
            t = max(0, min(1, t))
            projection = a + t * ab
n            return np.linalg.norm(p - projection), projection
        
        d1, proj1 = distance_to_line(point, A, B)
        d2, proj2 = distance_to_line(point, B, C)
        d3, proj3 = distance_to_line(point, C, A)
        
        if d1 <= d2 and d1 <= d3:
            return proj1
        elif d2 <= d1 and d2 <= d3:
            return proj2
        else:
            return proj3

    # Parameters
    n_starts = 10
    max_iter = 2000
    initial_temp = 0.1
    cooling_rate = 0.995
    min_temp = 1e-6
    base_step = 0.03
    max_no_improve = 300

    best_overall_min = -1
    best_overall_points = None

    for start in range(n_starts):
        # Generate initial configuration using hexagonal lattice
        points = hexagonal_lattice_init(11, A, B, C)
        
        # Ensure valid configuration
        if not is_inside_triangle(points, A, B, C):
            # Project any points outside the triangle
            for i in range(len(points)):
                points[i] = project_to_triangle(points[i], A, B, C)
        
        # Check for degenerate triangles
        min_area = get_smallest_triangle_area(points)
        if min_area <= 0:
            continue

        current_points = points.copy()
        current_min = min_area
        best_min = current_min
        best_points = current_points.copy()

        temp = initial_temp
        no_improve_count = 0
        iter_count = 0

        while temp > min_temp and no_improve_count < max_no_improve and iter_count < max_iter:
            iter_count += 1

            # Find critical triplet (smallest triangle)
            critical_triplet, min_area_val = find_critical_triplet(current_points)
            if critical_triplet is None:
                temp *= cooling_rate
                continue

            # Compute gradient directions
            dir_i, dir_j, dir_k = compute_gradient_directions(current_points, critical_triplet)
            i, j, k = critical_triplet

            # Adaptive step size
            step = base_step * (temp / initial_temp)

            # Create candidate by moving points along gradients
            candidate = current_points.copy()
            candidate[i] += step * dir_i
            candidate[j] += step * dir_j
            candidate[k] += step * dir_k

            # Project points back to triangle if necessary
            for idx in [i, j, k]:
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

            # Check validity
            candidate_min = get_smallest_triangle_area(candidate)
            if candidate_min <= 0:
                temp *= cooling_rate
                continue

            # Simulated annealing acceptance
            if candidate_min > best_min:
                best_min = candidate_min
                best_points = candidate.copy()
                current_points = candidate.copy()
                current_min = candidate_min
                no_improve_count = 0
            else:
                delta = current_min - candidate_min
                if random.random() < np.exp(-delta / temp):
                    current_points = candidate.copy()
                    current_min = candidate_min
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            temp *= cooling_rate

        # Final validation
        if best_min > best_overall_min:
            # Ensure all points are inside triangle
            for i in range(len(best_points)):
                best_points[i] = project_to_triangle(best_points[i], A, B, C)
            
            # Check distinctness and non-degeneracy
            if is_inside_triangle(best_points, A, B, C) and get_smallest_triangle_area(best_points) > 0:
                best_overall_min = best_min
                best_overall_points = best_points.copy()

    return best_overall_points