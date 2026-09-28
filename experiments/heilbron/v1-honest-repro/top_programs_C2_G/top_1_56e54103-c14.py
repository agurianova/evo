import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import numpy as np
import cma

np.random.seed(123)
random.seed(123)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate all valid row patterns (4-6 rows, 1-5 points per row, sum=11)
    patterns = []
    # 4 rows
    for a in range(1, 6):
        for b in range(1, 6):
            for c in range(1, 6):
                d = 11 - a - b - c
                if 1 <= d <= 5:
                    patterns.append([a, b, c, d])
    # 5 rows
    for a in range(1, 6):
        for b in range(1, 6):
            for c in range(1, 6):
                for d in range(1, 6):
                    e = 11 - a - b - c - d
                    if 1 <= e <= 5:
                        patterns.append([a, b, c, d, e])
    # 6 rows
    for a in range(1, 6):
        for b in range(1, 6):
            for c in range(1, 6):
                for d in range(1, 6):
                    for e in range(1, 6):
                        f = 11 - a - b - c - d - e
                        if 1 <= f <= 5:
                            patterns.append([a, b, c, d, e, f])

    # Generate initial candidates and compute min_area
    candidate_list = []  # (min_area, points)
    for row_counts in patterns:
        num_rows = len(row_counts)
        v_levels = [1 - i/(num_rows-1) if num_rows>1 else 1.0 for i in range(num_rows)]
        points = []
        for i in range(num_rows):
            num_points = row_counts[i]
            v = v_levels[i]
            for j in range(num_points):
                u_val = 0.5 * (1 - np.cos(np.pi * j / num_points)) * (1 - v)
                P = (1 - u_val - v) * A + u_val * B + v * C
                points.append(P)
        points = np.array(points)
        min_area = get_smallest_triangle_area(points)
        if min_area < 1e-9:
            min_area = 1e-9
        candidate_list.append((min_area, points))
    
    # Select top 3 candidates by min_area
    candidate_list.sort(key=lambda x: x[0], reverse=True)
    top3 = candidate_list[:3]

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
        penalty = 0.0
        for i in range(11):
            bary = cartesian_to_barycentric(points[i])
            neg_parts = np.minimum(bary, 0)
            penalty += np.sum(np.abs(neg_parts))
        min_area = get_smallest_triangle_area(points)
        if penalty > 0:
            return -min_area + 1000 * penalty
        return -min_area

    options = {
        'seed': 123,
        'maxiter': 300,
        'popsize': 88,
        'AdaptSigma': True,
        'verb_disp': 0,
        'verb_log': 0
    }

    best_solution = None
    best_min_area = -1

    for _, initial_points in top3:
        initial_flat = initial_points.flatten()
        res = cma.fmin(
            fitness_function,
            initial_flat,
            0.05,
            options=options
        )
        candidate_solution = res[0].reshape(11, 2)
        
        # Final constraint safeguard
        for i in range(11):
            if not is_inside_triangle(candidate_solution[i], A, B, C):
                bary = cartesian_to_barycentric(candidate_solution[i])
                bary = np.maximum(bary, 0)
                bary = bary / np.sum(bary)
                candidate_solution[i] = barycentric_to_cartesian(bary)

        min_area_optimized = get_smallest_triangle_area(candidate_solution)
        if min_area_optimized > best_min_area:
            best_min_area = min_area_optimized
            best_solution = candidate_solution

    return best_solution