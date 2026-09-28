import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.optimize import minimize

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri

    # Generate initial grid with asymmetric pattern and non-uniform spacing
    rows = 5
    row_pattern = [4, 3, 2, 1, 1]  # Total 11 points
    points = []
    for row in range(rows):
        num_points = row_pattern[row]
        v = (row + 0.5) / rows
        # Generate sorted random u values in [0, 1-v]
        u_vals = sorted([random.uniform(0, 1 - v) for _ in range(num_points)])
        for i in range(num_points):
            u = u_vals[i]
            P0 = (1 - u - v) * A + u * B + v * C
            # Row-dependent perturbation magnitude
            scale = 0.01 * (1 - row / rows)
            perturbation = np.random.uniform(-scale, scale, size=2)
            P = P0 + perturbation
            # Ensure point remains inside triangle
            if not is_inside_triangle(P, A, B, C):
                P = P0
            points.append(P)
    initial_points = np.array(points)

    # Objective function for optimization (minimize negative min_area)
    def objective(flat_points):
        points = flat_points.reshape(11, 2)
        if not is_inside_triangle(points, A, B, C):
            return 1e6  # Large penalty for boundary violations
        min_area = get_smallest_triangle_area(points)
        return -min_area

    # Run local search to maximize min_area
    res = minimize(
        objective,
        initial_points.flatten(),
        method='Nelder-Mead',
        options={'maxiter': 1000, 'xatol': 1e-6, 'fatol': 1e-6}
    )

    optimized_points = res.x.reshape(11, 2)

    # Validate final configuration
    if (is_inside_triangle(optimized_points, A, B, C) and 
        get_smallest_triangle_area(optimized_points) > 0):
        return optimized_points
    return initial_points