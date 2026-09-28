import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def find_critical_triplet(points):
    n = len(points)
    min_area = float('inf')
    critical_triplet = None
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                a, b, c = points[i], points[j], points[k]
                area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                if area_val < min_area:
                    min_area = area_val
                    critical_triplet = (i, j, k)
                    
    return critical_triplet, min_area

def compute_gradient_directions(points, triplet):
    i, j, k = triplet
    p_i, p_j, p_k = points[i], points[j], points[k]
    
    # Compute signed area
    s_val = 0.5 * ((p_j[0]-p_i[0])*(p_k[1]-p_i[1]) - (p_j[1]-p_i[1])*(p_k[0]-p_i[0]))
    
    # Compute gradient directions for each point
    dir_i = np.array([p_j[1]-p_k[1], p_k[0]-p_j[0]])
    if s_val < 0:
        dir_i = -dir_i
    
    dir_j = np.array([p_k[1]-p_i[1], p_i[0]-p_k[0]])
    if s_val < 0:
        dir_j = -dir_j

    dir_k = np.array([p_i[1]-p_j[1], p_j[0]-p_i[0]])
    if s_val < 0:
        dir_k = -dir_k

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

    return i, j, k, dir_i, dir_j, dir_k

def generate_symmetric_configuration(A, B, C):
    # Create a symmetric configuration with points on boundary and interior
    points = []
    
    # Add vertices
    points.append(A)
    points.append(B)
    points.append(C)
    
    # Add edge points (symmetrically placed)
    edge_points = 2  # points per edge
    for t in np.linspace(1/(edge_points+1), edge_points/(edge_points+1), edge_points):
        # AB edge
        points.append((1-t)*A + t*B)
        # BC edge
        points.append((1-t)*B + t*C)
        # CA edge
        points.append((1-t)*C + t*A)
    
    # Add interior symmetric points using centroid and rotation
    centroid = (A + B + C) / 3
    radius = 0.2 * np.linalg.norm(B - A)
    
    # Two interior points with rotational symmetry
    angle = 2 * np.pi / 5  # For 5-fold symmetry
    for i in range(2):
        theta = i * angle
        offset = np.array([radius * np.cos(theta), radius * np.sin(theta)])
        interior_point = centroid + offset
n        # Project back to triangle if needed
        if not is_inside_triangle(interior_point, A, B, C):
            # Simple projection back to centroid if outside
            interior_point = centroid
        points.append(interior_point)

    return np.array(points)

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Generate symmetric initial configuration
    points = generate_symmetric_configuration(A, B, C)
    
    # Simulated annealing parameters
    initial_temp = 0.05
    temp = initial_temp
    cooling_rate = 0.99
    min_temp = 1e-6
    base_step = 0.03
    max_iter = 300
    max_no_improve = 30
    
    no_improve_count = 0
    iter_count = 0
    current_area = get_smallest_triangle_area(points)
    
    while temp > min_temp and no_improve_count < max_no_improve and iter_count < max_iter:
        iter_count += 1

        # Find critical triplet (smallest triangle)
        critical_triplet, min_area = find_critical_triplet(points)
        if critical_triplet is None:
            temp *= cooling_rate
            continue

        # Compute gradient directions
        i, j, k, dir_i, dir_j, dir_k = compute_gradient_directions(points, critical_triplet)

        # Adaptive step size based on temperature
        step = base_step * (temp / initial_temp)

        # Create candidate by moving points along gradient directions
        candidate = points.copy()
        candidate[i] += step * dir_i
        candidate[j] += step * dir_j
        candidate[k] += step * dir_k

        # Check constraints
        if not is_inside_triangle(candidate, A, B, C):
            # Try smaller step
            step *= 0.5
            candidate = points.copy()
            candidate[i] += step * dir_i
            candidate[j] += step * dir_j
            candidate[k] += step * dir_k
            
            if not is_inside_triangle(candidate, A, B, C):
                temp *= cooling_rate
                no_improve_count += 1
                continue

        # Calculate new area
        new_area = get_smallest_triangle_area(candidate)
        if new_area <= 0:  # Degenerate triangle
            temp *= cooling_rate
            no_improve_count += 1
            continue

        # Simulated annealing acceptance
        if new_area > current_area:
            points, current_area = candidate, new_area
            no_improve_count = 0
        else:
            delta = current_area - new_area
            if np.random.rand() < np.exp(-delta / temp):
                points, current_area = candidate, new_area
                no_improve_count = 0
            else:
                no_improve_count += 1

        temp *= cooling_rate

    return points