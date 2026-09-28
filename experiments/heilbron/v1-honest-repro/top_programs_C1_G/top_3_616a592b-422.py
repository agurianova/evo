import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import scipy.optimize


def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    s = B[0]
    H = C[1]

    # Hardcoded symmetric configuration for side=1 triangle, scaled to unit area
    initial_points_std = np.array([
        [0.5, 0.288675],
        [0.2, 0.1],
        [0.8, 0.1],
        [0.5, 0.5],
        [0.3, 0.2],
        [0.7, 0.2],
        [0.4, 0.3],
        [0.6, 0.3],
        [0.1, 0.2],
        [0.9, 0.2],
        [0.5, 0.1]
    ])
    initial_points = initial_points_std * s

    # Barycentric projection helper
    def project_to_triangle(p):
        denom = (B[1]-C[1])*(A[0]-C[0]) + (C[0]-B[0])*(A[1]-C[1])
        u = ((B[1]-C[1])*(p[0]-C[0]) + (C[0]-B[0])*(p[1]-C[1])) / denom
        v = ((C[1]-A[1])*(p[0]-C[0]) + (A[0]-C[0])*(p[1]-C[1])) / denom
        w = 1 - u - v
        
        u = max(0, u)
        v = max(0, v)
        w = max(0, w)
        total = u + v + w
        if total < 1e-10:
            return np.array([A[0]+B[0]+C[0], A[1]+B[1]+C[1]]) / 3.0
        u, v, w = u/total, v/total, w/total
        return u*A + v*B + w*C

    # Robustness RNG (fixed seed for determinism)
    robust_rng = np.random.RandomState(42)

    # Objective with projection and robustness
    def objective(x_flat):
        pts = x_flat.reshape(11, 2)
        projected_pts = np.array([project_to_triangle(p) for p in pts])
        
        base_area = get_smallest_triangle_area(projected_pts)
        
        # Evaluate robustness with 2 perturbations
        perturbed_areas = [base_area]
        for _ in range(2):
            noise = robust_rng.uniform(-0.005, 0.005, size=(11, 2))
            perturbed_pts = projected_pts + noise
            if is_inside_triangle(perturbed_pts, A, B, C):
                perturbed_areas.append(get_smallest_triangle_area(perturbed_pts))
            else:
                perturbed_areas.append(0.0)
        robust_area = min(perturbed_areas)
        
        combined = 0.8 * base_area + 0.2 * robust_area
        return -combined

    # Configure basin hopping with loose bounds
    x_min, x_max = -10, s + 10
    y_min, y_max = -10, H + 10
    bounds = [(x_min, x_max)] * 11 + [(y_min, y_max)] * 11
    minimizer_kwargs = {
        'method': 'L-BFGS-B',
        'bounds': bounds
    }

    result = scipy.optimize.basinhopping(
        objective,
        initial_points.flatten(),
        niter=500,
        T=1.0,
        stepsize=0.01,
        minimizer_kwargs=minimizer_kwargs,
        interval=50
    )

    # Project final points to ensure validity
    final_points = result.x.reshape(11, 2)
    projected_final = np.array([project_to_triangle(p) for p in final_points])
    return projected_final