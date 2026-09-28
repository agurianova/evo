import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import numpy as np
import cma

np.random.seed(123)
random.seed(123)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
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

    # Define 20 diverse row patterns (4-6 rows, 1-5 points per row)
    candidates = [
        [1, 2, 3, 3, 2],
        [1, 3, 3, 3, 1],
        [1, 4, 4, 2],
        [2, 3, 4, 2],
        [2, 2, 3, 2, 2],
        [3, 3, 3, 2],
        [1, 2, 3, 5],
        [1, 2, 4, 4],
        [1, 3, 3, 4],
        [2, 2, 3, 4],
        [2, 3, 3, 3],
        [1, 1, 3, 3, 3],
        [1, 2, 2, 3, 3],
        [1, 3, 2, 3, 2],
        [2, 2, 2, 3, 2],
        [1, 4, 3, 3],
        [1, 5, 3, 2],
        [2, 4, 3, 2],
        [1, 3, 4, 3],
        [2, 2, 4, 3]
    ]

    # Helper function to generate deterministic initial points
    def generate_initial_points(row_counts):
        num_rows = len(row_counts)
        if num_rows == 1:
            v_levels = [1.0]
        else:
            v_levels = [1 - i/(num_rows-1) for i in range(num_rows)]
        points = []
        for i in range(num_rows):
            num_points = row_counts[i]
            v = v_levels[i]
            for j in range(num_points):
                phase = 0.0  # Deterministic placement (no symmetry breaking)
                u_val = 0.5 * (1 - np.cos(np.pi * (j + phase) / num_points)) * (1 - v)
                P = (1 - u_val - v) * A + u_val * B + v * C
                points.append(P)
        return np.array(points)

    # Evaluate all candidate patterns
    candidate_configs = []  # (min_area, points, row_counts)
    for row_counts in candidates:
        points = generate_initial_points(row_counts)
        min_area = get_smallest_triangle_area(points)
        if min_area < 1e-9:
            min_area = 1e-9
        candidate_configs.append((min_area, points, row_counts))

    # Select top 3 candidates by initial quality
    candidate_configs.sort(key=lambda x: x[0], reverse=True)
    top3 = candidate_configs[:3]

    best_overall = None
    best_min_area = -1

    # CMA-ES parameters
    options = {
        'seed': 123,
        'maxiter': 300,
        'popsize': 88,
        'AdaptSigma': True,
        'verb_disp': 0,
        'verb_log': 0
    }

    # Run multi-start optimization
    for run_idx, (min_area_init, initial_points, row_counts) in enumerate(top3):
        # Reset seeds for independent runs
        np.random.seed(123 + run_idx)
        random.seed(123 + run_idx)

        initial_flat = initial_points.flatten()
        
        # Run CMA-ES
        res = cma.fmin(
            fitness_function,
            initial_flat,
            0.05,
            options=options
        )

        best_points = res[0].reshape(11, 2)
        
        # Final constraint safeguard
        for i in range(11):
            if not is_inside_triangle(best_points[i], A, B, C):
                bary = cartesian_to_barycentric(best_points[i])
                bary = np.maximum(bary, 0)
                bary = bary / np.sum(bary)
                best_points[i] = barycentric_to_cartesian(bary)

        min_area_final = get_smallest_triangle_area(best_points)
        if min_area_final > best_min_area:
            best_min_area = min_area_final
            best_overall = best_points

    return best_overall