import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import numpy as np
import cma

np.random.seed(123)
random.seed(123)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Candidate row structures based on historical partitions for n=11
    candidates = [
        [1, 2, 3, 3, 2],
        [1, 3, 3, 3, 1],
        [1, 4, 4, 2],
        [2, 3, 4, 2],
        [2, 2, 3, 2, 2],
        [3, 3, 3, 2]
    ]
    
    best_min_area = -1
    best_points = None
    
    for row_counts in candidates:
        num_rows = len(row_counts)
        # Generate vertical levels from top (v=1) to bottom (v=0)
        v_levels = [1 - i/(num_rows-1) if num_rows>1 else 1.0 for i in range(num_rows)]
        
        points = []
        for i in range(num_rows):
            num_points = row_counts[i]
            v = v_levels[i]
            for j in range(num_points):
                phase = np.random.uniform(0, 1)
                u_val = 0.5 * (1 - np.cos(np.pi * (j + phase) / num_points)) * (1 - v)
                P = (1 - u_val - v) * A + u_val * B + v * C
                
                # Apply symmetry-breaking perturbation
                max_attempts = 5
                for _ in range(max_attempts):
                    perturbation = np.random.uniform(-0.05, 0.05, size=2)
                    P_pert = P + perturbation
                    if is_inside_triangle(P_pert, A, B, C):
                        points.append(P_pert)
                        break
                else:
                    points.append(P)
        
        points = np.array(points)
        min_area = get_smallest_triangle_area(points)
        # Skip degenerate configurations
        if min_area < 1e-9:
            min_area = 1e-9
        if min_area > best_min_area:
            best_min_area = min_area
            best_points = points

    # Convert to numpy array
    initial_points = best_points.flatten()
    
    # Precompute conversion matrix from Cartesian to barycentric
    T = np.array([
        [A[0], B[0], C[0]],
        [A[1], B[1], C[1]],
        [1, 1, 1]
    ])
    T_inv = np.linalg.inv(T)
    
    def cartesian_to_barycentric(pts):
        if pts.ndim == 1:
            homogeneous = np.array([pts[0], pts[1], 1.0])
            return T_inv @ homogeneous
        else:
            result = np.empty((pts.shape[0], 3))
            for i in range(pts.shape[0]):
                homogeneous = np.array([pts[i,0], pts[i,1], 1.0])
                result[i] = T_inv @ homogeneous
            return result
    
    def barycentric_to_cartesian(bary):
        if bary.ndim == 1:
            return A * bary[0] + B * bary[1] + C * bary[2]
        else:
            return np.array([A * b[0] + B * b[1] + C * b[2] for b in bary])
    
    def fitness_function(flat_points):
        # Reshape to (11, 2)
        points = flat_points.reshape(11, 2)
        
        # Compute constraint violation penalty
        penalty = 0.0
        for i in range(11):
            bary = cartesian_to_barycentric(points[i])
            neg_parts = np.minimum(bary, 0)
            penalty += np.sum(np.abs(neg_parts))
        
        # Calculate minimum triangle area
        min_area = get_smallest_triangle_area(points)
        
        # Apply soft penalty for constraint violations
        if penalty > 0:
            return -min_area + 1000 * penalty
        return -min_area

    # CMA-ES parameters with dimensionality-scaled population
    options = {
        'seed': 123,
        'maxiter': 300,
        'popsize': 88,  # 4 * 22 dimensions
        'AdaptSigma': True,
        'verb_disp': 0,
        'verb_log': 0
    }

    # Run CMA-ES optimization
    res = cma.fmin(
        fitness_function,
        initial_points,
        0.05,
        options=options
    )

    # Get the best solution and reshape
    best_points = res[0].reshape(11, 2)
    
    # Final constraint safeguard (soft penalty should prevent this)
    for i in range(11):
        if not is_inside_triangle(best_points[i], A, B, C):
            bary = cartesian_to_barycentric(best_points[i])
            bary = np.maximum(bary, 0)
            bary = bary / np.sum(bary)
            best_points[i] = barycentric_to_cartesian(bary)

    return best_points