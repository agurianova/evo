import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import numpy as np
import cma

np.random.seed(123)
random.seed(123)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Candidate row structures for n=11 (must sum to 11)
    candidate_structures = [
        [1, 3, 3, 3, 1],
        [1, 4, 4, 2],
        [2, 3, 4, 2],
        [1, 2, 4, 3, 1],
        [1, 3, 4, 3],
        [2, 4, 3, 2]
    ]
    
    best_initial_min_area = -1
    best_initial_points = None
    
    for structure in candidate_structures:
        points = []
        num_rows = len(structure)
        # Create vertical levels from top (v=1) to bottom (v=0)
        v_levels = [1 - i/(num_rows-1) if num_rows > 1 else 1 for i in range(num_rows)]
        
        for i in range(num_rows):
            num_points = structure[i]
            v = v_levels[i]
            for j in range(num_points):
                phase = np.random.uniform(0, 1)
                # Symmetric spacing within row
                if num_points == 1:
                    u_val = 0.5 * (1 - v)
                else:
                    u_val = 0.5 * (1 - np.cos(np.pi * (j + phase) / (num_points - 1))) * (1 - v)
                P = (1 - u_val - v) * A + u_val * B + v * C
                
                # Apply symmetry-breaking perturbation
                max_attempts = 10
                for _ in range(max_attempts):
                    perturbation = np.random.uniform(-0.05, 0.05, size=2)
                    P_pert = P + perturbation
                    if is_inside_triangle(P_pert, A, B, C):
                        points.append(P_pert)
                        break
                else:
                    points.append(P)
        
        # Verify we have 11 distinct points
        if len(points) != 11:
            continue
            
        points_arr = np.array(points)
        min_area = get_smallest_triangle_area(points_arr)
        if min_area > best_initial_min_area:
            best_initial_min_area = min_area
            best_initial_points = points_arr

    # Use best initial configuration
    initial_points = best_initial_points.flatten()
    
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
        points = flat_points.reshape(11, 2)
        bary_coords = cartesian_to_barycentric(points)
        
        # Calculate constraint violation (negative barycentric coordinates)
        violation_per_point = np.sum(np.maximum(-bary_coords, 0), axis=1)
        total_violation = np.sum(violation_per_point)
        
        # Apply soft penalty for violations
        if total_violation > 1e-10:
            return 1000.0 * total_violation
        else:
            min_area = get_smallest_triangle_area(points)
            return -min_area

    # CMA-ES parameters with population size scaled to dimensionality
    options = {
        'seed': 123,
        'maxiter': 300,
        'popsize': 88,  # 4 × 22 dimensions
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
    
    # Final constraint adjustment (only fix points outside triangle)
    bary_best = cartesian_to_barycentric(best_points)
    bary_best = np.maximum(bary_best, 0)
    bary_best = bary_best / np.sum(bary_best, axis=1, keepdims=True)
    final_points = barycentric_to_cartesian(bary_best)
    
    return final_points