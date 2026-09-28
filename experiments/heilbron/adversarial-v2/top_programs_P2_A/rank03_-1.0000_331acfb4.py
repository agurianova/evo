import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import math

np.random.seed(42)

def calculate_gradient(points, triangle_vertices, epsilon=1e-5):
    """Calculate numerical gradient of minimum triangle area with respect to each point's position"""
    base_score = get_smallest_triangle_area(points)
    gradients = np.zeros_like(points)
    
    for i in range(len(points)):
        for dim in range(2):
            # Perturb point in positive direction
            points_plus = points.copy()
            points_plus[i, dim] += epsilon
            if not is_inside_triangle(points_plus[i], *triangle_vertices):
                # Project back to triangle
                points_plus[i] = project_to_triangle(points_plus[i], *triangle_vertices)
            score_plus = get_smallest_triangle_area(points_plus)
            
            # Perturb point in negative direction
            points_minus = points.copy()
            points_minus[i, dim] -= epsilon
            if not is_inside_triangle(points_minus[i], *triangle_vertices):
                # Project back to triangle
                points_minus[i] = project_to_triangle(points_minus[i], *triangle_vertices)
            score_minus = get_smallest_triangle_area(points_minus)
            
            # Central difference approximation
            gradients[i, dim] = (score_plus - score_minus) / (2 * epsilon)
    
    return gradients

def project_to_triangle(point, A, B, C):
    """Project point back into the triangle if it's outside"""
    if is_inside_triangle(point, A, B, C):
        return point.copy()
    
    # Try all three edges
    edges = [(A, B), (B, C), (C, A)]
    projections = []
    
    for (p1, p2) in edges:
        v = p2 - p1
        w = point - p1
        c1 = np.dot(w, v)
        c2 = np.dot(v, v)
        if c2 == 0:
            b = p1
        else:
            b = max(0, min(1, c1/c2))
            b = p1 + b * v
        
        dist = np.linalg.norm(point - b)
        projections.append((dist, b))
    
    # Return closest projection
    _, closest = min(projections, key=lambda x: x[0])
    return closest

def generate_symmetric_initialization(A, B, C, n_points=11):
    """Generate a symmetric initialization based on concentric triangles"""
    # For 11 points, use 3 concentric triangles (1 center, 3 inner, 7 outer)
    center = (A + B + C) / 3.0
    
    # Calculate triangle height for scaling
    height = np.linalg.norm(C - A) * math.sqrt(3)/2
    
    # Generate points on 3 concentric triangles
    points = [center]
    
    # Inner triangle (3 points)
    inner_radius = 0.25 * height
    for i in range(3):
        angle = 2 * math.pi * i / 3
        x = center[0] + inner_radius * math.cos(angle)
        y = center[1] + inner_radius * math.sin(angle)
        point = np.array([x, y])
        if is_inside_triangle(point, A, B, C):
            points.append(point)
        else:
            points.append(project_to_triangle(point, A, B, C))
    
    # Outer triangle (7 points)
    outer_radius = 0.75 * height
    for i in range(7):
        angle = 2 * math.pi * i / 7
        x = center[0] + outer_radius * math.cos(angle)
        y = center[1] + outer_radius * math.sin(angle)
        point = np.array([x, y])
        if is_inside_triangle(point, A, B, C):
            points.append(point)
        else:
            points.append(project_to_triangle(point, A, B, C))
    
    return np.array(points[:n_points])

def optimize_configuration(initial_config, triangle_vertices, max_iter=500):
    """Optimize a configuration using gradient-based search focused on critical triangles"""
    A, B, C = triangle_vertices
    current = initial_config.copy()
    current_min_area = get_smallest_triangle_area(current)
    
    # Adaptive parameters
    step_size = 0.02
    threshold_factor = 1.05  # Consider triangles within 5% of min area as critical
    no_improve_count = 0
    max_no_improve = 100
    
    for _ in range(max_iter):
        # Find critical triangles (those with area close to minimum)
        min_area = current_min_area
n        critical_points = set()
        areas_triplets = []
        
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = 0.5 * abs((current[j,0]-current[i,0])*(current[k,1]-current[i,1]) - 
                                   (current[j,1]-current[i,1])*(current[k,0]-current[i,0]))
                    areas_triplets.append((area, (i, j, k)))
        
        # Use threshold to identify critical triangles
        threshold = threshold_factor * min_area
        critical_triplets = [(area, triplet) for area, triplet in areas_triplets 
                            if area < threshold and area > 1e-10]
        
        # Identify points in critical triangles
        for _, triplet in critical_triplets:
            critical_points.update(triplet)
        
        if not critical_points:
            break
        
        # Calculate gradient for critical points
        gradients = calculate_gradient(current, triangle_vertices)
        
        # Evaluate best improvement among critical points
        best_config = current.copy()
        best_min_area = current_min_area
        improvement_found = False
        
        # Try moving each critical point in gradient direction
        for i in critical_points:
            # Normalize gradient for this point
            grad_norm = np.linalg.norm(gradients[i])
            if grad_norm > 1e-5:
                direction = gradients[i] / grad_norm
                
                # Try different step sizes
                for scale in [0.5, 1.0, 1.5, 2.0]:
                    candidate = current.copy()
                    candidate[i] += step_size * scale * direction
                    
                    # Project back to triangle if needed
                    if not is_inside_triangle(candidate[i], A, B, C):
                        candidate[i] = project_to_triangle(candidate[i], A, B, C)
                    
                    # Check validity and score
                    min_area_candidate = get_smallest_triangle_area(candidate)
                    
                    if min_area_candidate > best_min_area:
                        best_config = candidate
                        best_min_area = min_area_candidate
                        improvement_found = True

        if improvement_found:
            current = best_config
            current_min_area = best_min_area
            no_improve_count = 0
            
            # Increase step size if we're making progress
            step_size = min(step_size * 1.1, 0.1)
        else:
            no_improve_count += 1
            # Decrease step size if no improvement
            step_size = max(step_size * 0.9, 1e-4)

        # Early stopping if stuck
        if no_improve_count >= max_no_improve:
            break

    return current

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    triangle_vertices = (A, B, C)
    
    # Generate multiple symmetric initializations
    best_config = None
    best_min_area = -1
    n_restarts = 5
    
    for _ in range(n_restarts):
        # Generate symmetric initialization
        initial_config = generate_symmetric_initialization(A, B, C)
        
        # Optimize the configuration
        optimized_config = optimize_configuration(initial_config, triangle_vertices)
        
        # Check if this is the best so far
        min_area = get_smallest_triangle_area(optimized_config)
        if min_area > best_min_area:
            best_config = optimized_config
            best_min_area = min_area

    return best_config