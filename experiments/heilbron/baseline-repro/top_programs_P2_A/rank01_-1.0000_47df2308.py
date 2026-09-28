import numpy as np
from scipy.optimize import minimize
from helper import get_unit_triangle, get_smallest_triangle_area

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Expanded pattern set with 8 configurations covering diverse topologies
    candidate_patterns = [
        [3, 3, 3, 2],  # Validated high-quality configuration for n=11
        [4, 3, 2, 2],  # Alternative literature pattern
        [3, 3, 2, 2, 1], # Original pattern for comparison
        [5, 3, 3],      # New: k=3 non-increasing composition
        [4, 4, 2, 1],   # New: k=4 non-increasing composition
        [4, 3, 2, 1, 1],# New: k=5 non-increasing composition
        [3, 3, 3, 1, 1],# New: k=5 non-increasing composition
        [4, 2, 2, 2, 1] # New: k=5 non-increasing composition
    ]
    
    best_config = None
    best_area = -1

    # Adaptive restart magnitudes: larger initial step for exploration
    restart_magnitudes = [0.2, 0.1, 0.05, 0.02, 0.01]

    for pattern in candidate_patterns:
        total_rows = len(pattern)
        points_bary = []
        
        # Generate base grid with adaptive top-row vertex placement
        for i, num_pts in enumerate(pattern):
            if total_rows > 1:
                if i == total_rows - 1:  # Top row
                    if num_pts == 1:
                        v = 1.0  # Allow vertex placement for single-point rows
                    else:
                        v = 1 - 1e-5  # Prevent collapse for multi-point rows
                else:
                    v = i / (total_rows - 1)
            else:
                v = 0
            for j in range(num_pts):
                u = (j + 0.5) / num_pts * (1 - v)
                points_bary.append((u, v))

        x0_base = np.array(points_bary).flatten()
        
        # Multiple restarts with adaptive perturbation magnitudes
        for restart_idx in range(5):
            mag = restart_magnitudes[restart_idx]
            x0 = x0_base + np.random.uniform(-mag, mag, size=22)
            
            # Hard projection for initial feasibility
            for i in range(11):
                u, v = x0[2*i], x0[2*i+1]
                if u < 0: u = 0
                if v < 0: v = 0
                if u + v > 1:
                    scale = 1.0 / (u + v)
                    u, v = u * scale, v * scale
                x0[2*i], x0[2*i+1] = u, v

            # Objective with boundary penalty and adversarial robustness
            def objective(x):
                points = []
                for i in range(11):
                    u, v = x[2*i], x[2*i+1]
                    P = (1 - u - v) * A + u * B + v * C
                    points.append(P)
                points_arr = np.array(points)
                min_area = get_smallest_triangle_area(points_arr)
                
                # Evaluate robustness against small perturbations
                robust_min = min_area
                for _ in range(3):
                    perturbation = np.random.uniform(-0.0005, 0.0005, size=(11, 2))
                    perturbed_points = points_arr + perturbation
n                    area_pert = get_smallest_triangle_area(perturbed_points)
                    if area_pert < robust_min:
                        robust_min = area_pert

                # Compute minimum barycentric boundary distance
                d_min = 1.0
                for i in range(11):
                    u, v = x[2*i], x[2*i+1]
                    w = 1 - u - v
                    d = min(u, v, w)
                    if d < d_min:
                        d_min = d
                
                # Strengthened boundary penalty (weight=1.0)
                penalty = 0.0
                if d_min < 0.05:
                    penalty = 1.0 * (0.05 - d_min)
                
                return -robust_min + penalty

            # Constraints for triangle containment
            constraints = []
            for i in range(11):
                constraints.append({'type': 'ineq', 'fun': lambda x, i=i: x[2*i]})          # u ≥ 0
                constraints.append({'type': 'ineq', 'fun': lambda x, i=i: x[2*i+1]})         # v ≥ 0
                constraints.append({'type': 'ineq', 'fun': lambda x, i=i: 1 - x[2*i] - x[2*i+1]})  # u+v ≤ 1

            # Optimize with tight convergence
            res = minimize(
                objective, x0,
                method='SLSQP',
                bounds=[(0, 1)] * 22,
                constraints=constraints,
                options={'ftol': 1e-9, 'maxiter': 1000}
            )

            if res.success:
                points = []
                for i in range(11):
                    u, v = res.x[2*i], res.x[2*i+1]
                    points.append((1 - u - v) * A + u * B + v * C)
                area = get_smallest_triangle_area(np.array(points))
                
                if area > best_area:
                    best_area = area
                    best_config = np.array(points)

    # Fallback with adaptive vertex placement
    if best_config is None:
        pattern = candidate_patterns[0]
        total_rows = len(pattern)
        points = []
        for i, num_pts in enumerate(pattern):
            if total_rows > 1:
                if i == total_rows - 1:
                    if num_pts == 1:
                        v = 1.0
                    else:
                        v = 1 - 1e-5
                else:
                    v = i / (total_rows - 1)
            else:
                v = 0
            for j in range(num_pts):
                u = (j + 0.5) / num_pts * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                points.append(P)
        best_config = np.array(points)

    return best_config