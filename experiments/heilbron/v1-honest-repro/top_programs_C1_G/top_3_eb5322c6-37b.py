import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

# Convert Cartesian to barycentric coordinates
def cartesian_to_barycentric(p, A, B, C):
    area_ABC = 0.5 * np.abs((B[0]-A[0])*(C[1]-A[1]) - (C[0]-A[0])*(B[1]-A[1]))
    u = 0.5 * np.abs((B[0]-p[0])*(C[1]-p[1]) - (C[0]-p[0])*(B[1]-p[1])) / area_ABC
    v = 0.5 * np.abs((C[0]-p[0])*(A[1]-p[1]) - (A[0]-p[0])*(C[1]-p[1])) / area_ABC
    w = 1.0 - u - v
    return np.array([u, v, w])

# Convert barycentric to Cartesian coordinates
def barycentric_to_cartesian(bary, A, B, C):
    return bary[0] * A + bary[1] * B + bary[2] * C

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Create initial configuration using barycentric coordinates
    # Using a 4-4-3 pattern which is known to be better for 11 points
    points_bary = []
    
    # Base row (4 points)
    for i in range(4):
        u = 0.1 + 0.8 * i / 3.0
        v = 0.05
        w = 1.0 - u - v
        points_bary.append(np.array([u, v, w]))
    
    # Middle row (4 points)
    for i in range(4):
        u = 0.15 + 0.7 * i / 3.0
        v = 0.35
        w = 1.0 - u - v
        points_bary.append(np.array([u, v, w]))
    
    # Top row (3 points)
    for i in range(3):
        u = 0.25 + 0.5 * i / 2.0
        v = 0.65
        w = 1.0 - u - v
        points_bary.append(np.array([u, v, w]))
    
    points_bary = np.array(points_bary)
    points = np.array([barycentric_to_cartesian(b, A, B, C) for b in points_bary])
    
    # Simulated annealing optimization
    current_score = get_smallest_triangle_area(points)
    target_score = 0.0365
    best_points = points.copy()
    best_score = current_score
    
    # Optimization parameters
    max_iter = 1000
    initial_temp = 0.1
    cooling_rate = 0.99
    temperature = initial_temp
    
    for iter in range(max_iter):
        # Adaptive noise magnitude based on progress
        progress = current_score / target_score
        noise_magnitude = 0.05 * (1.0 - progress)
        noise_magnitude = max(0.005, min(0.05, noise_magnitude))
        
        # Select points to perturb - focus on critical triangles
        min_area, min_indices = get_min_triangle(points)
        
        # With 60% probability, perturb points in the smallest triangle
        if np.random.rand() < 0.6:
            points_to_perturb = min_indices
        else:
            # Otherwise pick a random point
            points_to_perturb = [np.random.randint(0, 11)]
        
        # Create candidate solution
        candidate_bary = points_bary.copy()
        for idx in points_to_perturb:
            # Apply Gaussian noise in barycentric space
            noise = np.random.normal(0, noise_magnitude, 3)
            candidate_bary[idx] += noise
            
            # Project back to valid simplex (u+v+w=1, u,v,w>=0)
            candidate_bary[idx] = np.clip(candidate_bary[idx], 0.01, 0.99)
            total = np.sum(candidate_bary[idx])
            candidate_bary[idx] /= total
        
        # Convert to Cartesian for evaluation
        candidate = np.array([barycentric_to_cartesian(b, A, B, C) for b in candidate_bary])
        
        # Evaluate candidate
        candidate_score = get_smallest_triangle_area(candidate)
        
        # Update best solution if improved
        if candidate_score > best_score:
            best_points = candidate.copy()
            best_score = candidate_score
        
        # Simulated annealing acceptance
        delta = candidate_score - current_score
        if delta > 0 or np.random.rand() < np.exp(delta / temperature):
            points = candidate.copy()
            points_bary = candidate_bary.copy()
            current_score = candidate_score
        
        # Cool temperature
        temperature *= cooling_rate

    return best_points

def get_min_triangle(points):
    n = points.shape[0]
    min_area = float('inf')
    min_indices = None
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = get_smallest_triangle_area(points[[i,j,k]])
                if area < min_area:
                    min_area = area
                    min_indices = (i, j, k)
    return min_area, min_indices