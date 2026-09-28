import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def compute_area_gradient(points, i, j, k):
    '''Compute gradient directions for increasing triangle area'''
    a, b, c = points[i], points[j], points[k]
    
    # Area = 0.5 * |(b_x - a_x)(c_y - a_y) - (b_y - a_y)(c_x - a_x)|
    # For gradient calculation, we assume counterclockwise ordering (positive area)
    area_val = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
    
    # Gradient with respect to point a
    grad_a = np.array([-(c[1]-b[1]), c[0]-b[0]])
    # Gradient with respect to point b
    grad_b = np.array([c[1]-a[1], -(c[0]-a[0])])
    # Gradient with respect to point c
    grad_c = np.array([a[1]-b[1], -(a[0]-b[0])])
    
    # Normalize gradients
    norm_a = np.linalg.norm(grad_a)
    norm_b = np.linalg.norm(grad_b)
    norm_c = np.linalg.norm(grad_c)
    
    if norm_a > 1e-8:
        grad_a = grad_a / norm_a
    if norm_b > 1e-8:
        grad_b = grad_b / norm_b
    if norm_c > 1e-8:
        grad_c = grad_c / norm_c
    
    return grad_a, grad_b, grad_c

def enforce_symmetry(points, axis_x=0.7598):
    '''Enforce reflection symmetry across vertical axis of triangle'''
    symmetric_points = points.copy()
    for i in range(len(points)):
        # Reflect point across vertical axis (x = axis_x)
        dx = points[i, 0] - axis_x
        symmetric_points[i, 0] = axis_x - dx
        
        # Find closest original point to this reflection
        min_dist = float('inf')
        closest_idx = -1
        for j in range(len(points)):
            dist = np.linalg.norm(symmetric_points[i] - points[j])
            if dist < min_dist:
                min_dist = dist
                closest_idx = j
        
        # If not already symmetric, adjust the pair
        if min_dist > 1e-5:
            # Average position to maintain symmetry
            midpoint = (points[i] + symmetric_points[i]) / 2
            symmetric_points[i] = midpoint
            symmetric_points[closest_idx] = midpoint
            
    return symmetric_points

def generate_initial_configuration():
    '''Generate structured initial configuration based on Heilbronn problem knowledge'''
    A, B, C = get_unit_triangle()
    
    # Center of the triangle
    center = (A + B + C) / 3
    
    # Known good pattern for n=11: 1 center point, 2 rings (3+7 points)
    config = np.zeros((11, 2))
    
    # Center point (slightly perturbed)
    config[0] = center + np.array([0.01, -0.005])
    
    # First ring (3 points) - equilateral triangle around center
    radius1 = 0.25
    for i in range(3):
        angle = 2 * np.pi * i / 3 + np.pi/6
        offset = radius1 * np.array([np.cos(angle), np.sin(angle)])
        config[i+1] = center + offset
    
    # Second ring (7 points) - hexagonal pattern with one additional point
    radius2 = 0.45
    for i in range(6):
        angle = 2 * np.pi * i / 6 + np.pi/12
        offset = radius2 * np.array([np.cos(angle), np.sin(angle)])
        config[i+4] = center + offset
    
    # Additional point for 11th point (between two hex points)
    angle = 2 * np.pi * 6 / 6 + np.pi/12 + np.pi/12
    offset = radius2 * np.array([np.cos(angle), np.sin(angle)])
    config[10] = center + offset
    
    # Project all points into the triangle and enforce symmetry
    config = enforce_symmetry(config)
    
    # Ensure all points are inside the triangle
    for i in range(11):
        if not is_inside_triangle(config[i], A, B, C):
            # Find closest point on boundary
            t = 0.0
            best_point = config[i].copy()
            best_dist = float('inf')
            
            # Sample along edges
            for edge in [(A, B), (B, C), (C, A)]:
                for t in np.linspace(0, 1, 100):
                    p = edge[0] * (1-t) + edge[1] * t
                    dist = np.linalg.norm(config[i] - p)
                    if dist < best_dist:
                        best_dist = dist
                        best_point = p
            
            config[i] = best_point
    
    return config

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Start with structured initialization
    current = generate_initial_configuration()
    current_area = get_smallest_triangle_area(current)
    
    # Multi-scale optimization
    base_step = 0.05
    min_step = 1e-6
    improvement_threshold = 1e-8
    max_no_improve = 30
    no_improve_count = 0
    
    # Main optimization loop
    while base_step > min_step and no_improve_count < max_no_improve:
        improved = False
        current_area = get_smallest_triangle_area(current)
        
        # Find all critical triplets (smallest triangles)
        n = 11
        min_area_val = current_area
        critical_triplets = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = current[i], current[j], current[k]
                    area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    if abs(area_val - min_area_val) < 1e-10:
                        critical_triplets.append((i, j, k))

        # Process each critical triplet
        for triplet in critical_triplets:
            i, j, k = triplet
            
            # Compute gradient directions for area increase
            grad_i, grad_j, grad_k = compute_area_gradient(current, i, j, k)
            
            # Adaptive step size based on current bottleneck severity
            step_size = base_step * (min_area_val / 0.0365)
            
            # Try moving points in gradient directions
            candidate = current.copy()
            candidate[i] += step_size * grad_i
            candidate[j] += step_size * grad_j
            candidate[k] += step_size * grad_k
            
            # Enforce symmetry
            candidate = enforce_symmetry(candidate)
            
            # Check constraints
            valid = True
            for idx in range(11):
                if not is_inside_triangle(candidate[idx], A, B, C):
                    valid = False
                    break
            
            if valid:
                new_area = get_smallest_triangle_area(candidate)
                if new_area > current_area + improvement_threshold:
                    current = candidate
                    current_area = new_area
                    improved = True

        # Also try symmetry-preserving global adjustments
        if not improved:
            candidate = current.copy()
            # Slightly adjust all points outward from center
            center = np.mean(current, axis=0)
            for i in range(11):
                direction = current[i] - center
n                if np.linalg.norm(direction) > 1e-8:
                    direction = direction / np.linalg.norm(direction)
                    candidate[i] += base_step * 0.2 * direction
            
            # Enforce symmetry and constraints
            candidate = enforce_symmetry(candidate)
            valid = all(is_inside_triangle(candidate[i], A, B, C) for i in range(11))
            
            if valid:
                new_area = get_smallest_triangle_area(candidate)
                if new_area > current_area + improvement_threshold:
                    current = candidate
                    current_area = new_area
                    improved = True

        if improved:
            no_improve_count = 0
        else:
            no_improve_count += 1
            base_step *= 0.9

    return current