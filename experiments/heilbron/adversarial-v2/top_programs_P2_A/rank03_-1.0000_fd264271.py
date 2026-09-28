import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import math

np.random.seed(42)

def hexagonal_grid_points(n, A, B, C, perturbation=0.05):
    # Convert to barycentric coordinates for the unit triangle
    # Create hexagonal grid in the unit equilateral triangle
    points = []
    
    # Find appropriate grid dimensions
    grid_size = int(math.sqrt(n * 2 / math.sqrt(3))) + 1
    
    for i in range(grid_size):
        for j in range(grid_size - i):
            # Hexagonal grid coordinates
            u = i / (grid_size - 1)
            v = j / (grid_size - 1) * (1 - u)
            w = 1 - u - v
n            # Add small perturbation to avoid symmetry
            if perturbation > 0:
                u += (np.random.rand() - 0.5) * perturbation
                v += (np.random.rand() - 0.5) * perturbation
                # Ensure barycentric coordinates remain valid
                total = u + v
                if total > 1:
                    u, v = u/total, v/total
                w = 1 - u - v

            P = w * A + u * B + v * C
            points.append(P)
            
            if len(points) >= n:
                return np.array(points)
    
    return np.array(points)

def compute_area_gradient(p0, p1, p2):
    # Compute the gradient direction to increase the area of triangle (p0,p1,p2)
    # Area = 0.5 * |(p1-p0) × (p2-p0)|
    # Gradient for p0: -0.5 * [(p1-p0) × (p2-p0)]_perp
    # Gradient for p1:  0.5 * [(p2-p0) × (p1-p0)]_perp
    # Gradient for p2:  0.5 * [(p1-p0) × (p2-p0)]_perp
    
    # Compute cross product component (z-component of 3D cross product)
    cross_z = (p1[0]-p0[0])*(p2[1]-p0[1]) - (p1[1]-p0[1])*(p2[0]-p0[0])
    
    # Perpendicular vector (rotated 90 degrees)
    perp = np.array([p2[1]-p1[1], p1[0]-p2[0]])
    
    # Normalize
    norm = np.linalg.norm(perp)
    if norm < 1e-10:
        return np.zeros(2), np.zeros(2), np.zeros(2)
    
    perp = perp / norm
    
    # Direction depends on sign of cross_z
    if cross_z < 0:
        perp = -perp
    
    # Gradients for each point
    grad_p0 = -perp
    grad_p1 = perp
    grad_p2 = perp
    
    return grad_p0, grad_p1, grad_p2

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    n_points = 11
    
    # Generate multiple hexagonal grid variations with different perturbations
    best_config = None
    best_min_area = -1
    
    for perturbation in [0.02, 0.05, 0.08, 0.12]:
        for _ in range(3):  # Multiple samples per perturbation level
            config = hexagonal_grid_points(n_points, A, B, C, perturbation)
            min_area = get_smallest_triangle_area(config)
            if min_area > best_min_area:
                best_min_area = min_area
                best_config = config.copy()

    # Simulated annealing to reach deep local optimum
    current_config = best_config.copy()
    current_min_area = best_min_area
    
    # Annealing parameters
    initial_temp = 0.1
    temp = initial_temp
    cooling_rate = 0.995
    min_temp = 1e-7
    base_step = 0.03
    max_no_improve = 30
    max_iter = 1000

    no_improve_count = 0
    iter_count = 0

    while temp > min_temp and no_improve_count < max_no_improve and iter_count < max_iter:
        iter_count += 1

        # Find critical triplet (smallest triangle)
        n = n_points
        min_area_val = float('inf')
        critical_triplet = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = current_config[i], current_config[j], current_config[k]
                    area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    if area_val < min_area_val:
                        min_area_val = area_val
                        critical_triplet = (i, j, k)

        if critical_triplet is None:
            temp *= cooling_rate
            continue

        i0, i1, i2 = critical_triplet
        p0, p1, p2 = current_config[i0], current_config[i1], current_config[i2]

        # Compute gradient directions to increase the area
        grad_p0, grad_p1, grad_p2 = compute_area_gradient(p0, p1, p2)

        # Adaptive step size based on temperature
        step = base_step * (temp / initial_temp)

        # Create candidate configuration
        candidate = current_config.copy()
        candidate[i0] += step * grad_p0
        candidate[i1] += step * grad_p1
        candidate[i2] += step * grad_p2

        # Check constraints - project back to triangle if needed
        for i in range(n_points):
            if not is_inside_triangle(candidate[i], A, B, C):
                # Convert to barycentric coordinates for projection
                v0 = B - A
                v1 = C - A
                v2 = candidate[i] - A
                
                d00 = np.dot(v0, v0)
                d01 = np.dot(v0, v1)
                d11 = np.dot(v1, v1)
                d20 = np.dot(v2, v0)
                d21 = np.dot(v2, v1)
                denom = d00 * d11 - d01 * d01
                
                if abs(denom) < 1e-10:
                    u = 0.5
                    v = 0.5
                else:
                    u = (d11 * d20 - d01 * d21) / denom
                    v = (d00 * d21 - d01 * d20) / denom
                
                # Clamp to triangle
                if u < 0:
                    u = 0
                    v = min(max(0, v), 1)
                if v < 0:
                    v = 0
                    u = min(max(0, u), 1)
                if u + v > 1:
                    scale = 1.0 / (u + v)
                    u *= scale
                    v *= scale
                
                candidate[i] = A + u * v0 + v * v1

        new_min_area = get_smallest_triangle_area(candidate)
        
        # Simulated annealing acceptance
        if new_min_area > current_min_area:
            current_config, current_min_area = candidate, new_min_area
            no_improve_count = 0
        else:
            delta = current_min_area - new_min_area
            if np.random.rand() < np.exp(-delta / temp):
                current_config, current_min_area = candidate, new_min_area
                no_improve_count = 0
            else:
                no_improve_count += 1

        temp *= cooling_rate

    return current_config