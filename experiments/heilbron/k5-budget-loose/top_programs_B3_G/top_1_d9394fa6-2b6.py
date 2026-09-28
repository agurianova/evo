import numpy as np
from scipy.optimize import differential_evolution
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    axis_x = (A[0] + B[0]) / 2.0

    def project_to_segment(p, a, b):
        ap = p - a
        ab = b - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
        t = max(0.0, min(1.0, t))
        return a + t * ab

    def project_point(p):
        if is_inside_triangle(p, A, B, C):
            return p
        p_ab = project_to_segment(p, A, B)
        p_bc = project_to_segment(p, B, C)
        p_ca = project_to_segment(p, C, A)
        d_ab = np.linalg.norm(p - p_ab)
        d_bc = np.linalg.norm(p - p_bc)
        d_ca = np.linalg.norm(p - p_ca)
        if d_ab <= d_bc and d_ab <= d_ca:
            return p_ab
        elif d_bc <= d_ab and d_bc <= d_ca:
            return p_bc
        else:
            return p_ca

    best_points = None
    best_min_area = -1.0

    for seed in range(10):
        np.random.seed(seed)
        random.seed(seed)

        # Generate symmetric initial configuration
        left_points = []
        while len(left_points) < 5:
            r1 = np.sqrt(np.random.random())
            r2 = np.random.random()
            P = (1 - r1) * A + r1 * (1 - r2) * B + r1 * r2 * C
            if P[0] < axis_x:  # Strictly left of axis
                left_points.append(P)
        center_y = np.random.random() * C[1]  # y in [0, height]
        center_point = np.array([axis_x, center_y])

        # Prepare optimization parameters (11D: 5 left points × 2D + center y)
        x0 = []
        for pt in left_points:
            x0.extend([pt[0], pt[1]])
        x0.append(center_y)
        x0 = np.array(x0)

        # Objective function with symmetry and projection
        def objective(params):
            left_pts = []
            for i in range(5):
                x, y = params[2*i], params[2*i+1]
                left_pts.append([x, y])
            center_y = params[10]
            center_pt = [axis_x, center_y]
            
            # Build full configuration via reflection
            right_pts = [[2*axis_x - x, y] for x, y in left_pts]
            all_pts = np.array(left_pts + [center_pt] + right_pts)
            
            # Project all points to triangle
            projected_pts = np.array([project_point(pt) for pt in all_pts])
            min_area = get_smallest_triangle_area(projected_pts)
            return -min_area

        # Optimization bounds
        bounds = []
        for _ in range(5):
            bounds.extend([(0, B[0]), (0, C[1])])  # x in [0, base], y in [0, height]
        bounds.append((0, C[1]))  # center_y

        # Run global optimization
        res = differential_evolution(
            objective, bounds, maxiter=1000, popsize=15, tol=1e-6, seed=seed
        )
        
        # Build configuration from best parameters
        params_best = res.x
        left_pts = []
        for i in range(5):
            x, y = params_best[2*i], params_best[2*i+1]
            left_pts.append([x, y])
        center_y = params_best[10]
        center_pt = [axis_x, center_y]
        right_pts = [[2*axis_x - x, y] for x, y in left_pts]
        all_pts = np.array(left_pts + [center_pt] + right_pts)
        projected_pts = np.array([project_point(pt) for pt in all_pts])

        # Resistance validation: hill climbing to local optimum
        current_points = projected_pts
        current_min_area = get_smallest_triangle_area(current_points)
        for _ in range(5):  # Max restarts
            improved = False
            for _ in range(100):  # Perturbation trials
                idx = np.random.randint(0, 11)
                perturbation = np.random.normal(0, 0.02, size=2)
                candidate = current_points.copy()
                candidate[idx] += perturbation
                
                # Project candidate points
                for j in range(11):
                    candidate[j] = project_point(candidate[j])
                
                min_area_candidate = get_smallest_triangle_area(candidate)
                if min_area_candidate > current_min_area:
                    improved = True
                    current_points = candidate
                    current_min_area = min_area_candidate
                    break  # Restart search from improvement
            
            if not improved:
                break

        # Track best configuration across restarts
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_points = current_points

    return best_points