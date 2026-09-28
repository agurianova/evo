import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def to_barycentric(point, A, B, C):
    """Convert Cartesian coordinates to barycentric coordinates."""
    v0 = B - A
    v1 = C - A
    v2 = point - A
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

def to_cartesian(bary, A, B, C):
    """Convert barycentric coordinates to Cartesian coordinates."""
    u, v, w = bary
    return u * A + v * B + w * C

def clamp_barycentric(bary):
    """Clamp barycentric coordinates to ensure point is inside triangle."""
    u, v, w = bary
    # If any coordinate is negative, project to the nearest edge
    if u < 0:
        # Project to edge BC
        total = v + w
        v, w = v / total, w / total
        u = 0
    if v < 0:
        # Project to edge AC
        total = u + w
        u, w = u / total, w / total
        v = 0
    if w < 0:
        # Project to edge AB
        total = u + v
        u, v = u / total, v / total
        w = 0
    # Ensure coordinates sum to 1
    total = u + v + w
    return np.array([u, v, w]) / total

def project_to_triangle(point, A, B, C):
    """Project a point to the nearest point inside the triangle."""
    bary = to_barycentric(point, A, B, C)
    clamped = clamp_barycentric(bary)
    return to_cartesian(clamped, A, B, C)

def optimize_configuration(points, A, B, C, restarts=3):
    """Optimize the configuration using simulated annealing with multiple restarts."""
    best_points = points.copy()
    best_score = get_smallest_triangle_area(points)
    
    for _ in range(restarts):
        current_points = points.copy()
        current_score = best_score
        
        # Simulated annealing parameters
        T = 0.01  # Initial temperature
        cooling_rate = 0.98
        iterations = 50
        
        for i in range(iterations):
            # Generate candidate by perturbing 1-2 random points
            candidate = current_points.copy()
            num_perturb = np.random.choice([1, 2], p=[0.7, 0.3])
            indices = np.random.choice(11, size=num_perturb, replace=False)
            
            # Adaptive step size
            step_size = 0.01 * (T / 0.01) ** 0.5
            
            for idx in indices:
                # Gaussian perturbation
                perturbation = np.random.normal(0, step_size, size=2)
                candidate[idx] += perturbation
                
                # Ensure point stays inside triangle
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
            
            # Check for near-collinear points
            min_area = get_smallest_triangle_area(candidate)
            if min_area < 0.001:
                continue
                
            # Simulated annealing acceptance
            delta = min_area - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current_points = candidate
                current_score = min_area
                
                if min_area > best_score:
                    best_points = candidate.copy()
                    best_score = min_area
            
            # Cool down
            T *= cooling_rate
    
    return best_points

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Define row structure (4 rows with 4,3,3,1 points)
    row_points = [4, 3, 3, 1]
    row_heights = [0.2, 0.4, 0.7, 0.9]  # Non-uniform row heights
    
    # Generate initial points
    points = []
    for i, (num_points, height) in enumerate(zip(row_points, row_heights)):
        for j in range(num_points):
            # Position within row (from left to right)
            pos = (j + 0.5) / num_points
            
            # Barycentric coordinates
            v = height
            u = pos * (1 - height)
            w = 1 - u - v
            
            # Convert to Cartesian coordinates
            P = u * A + v * B + w * C
            
            # Add perturbation to break symmetry
            perturbation = np.random.normal(0, 0.005, size=2)
            P = P + perturbation
            
            # Ensure point is inside triangle
            P = project_to_triangle(P, A, B, C)
            points.append(P)
    
    # Convert to numpy array
    points = np.array(points)
    
    # Local optimization with multiple restarts
    optimized_points = optimize_configuration(points, A, B, C, restarts=3)
    
    # Final validation check
    if not is_inside_triangle(optimized_points, A, B, C) or get_smallest_triangle_area(optimized_points) < 0.001:
        return points
    
    return optimized_points