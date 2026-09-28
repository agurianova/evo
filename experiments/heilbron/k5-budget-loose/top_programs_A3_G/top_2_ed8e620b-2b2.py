import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area
from scipy.optimize import differential_evolution, minimize

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()

    def transform(x):
        points = []
        for i in range(11):
            u = x[2*i]
            v = x[2*i+1] * (1 - u)
            point = (1 - u - v) * A + u * B + v * C
            points.append(point)
        return np.array(points)

    def objective(x):
        x = np.clip(x, 0, 1)
        points = transform(x)
        min_area = get_smallest_triangle_area(points)
        min_area = max(min_area, 0.0)
        if min_area < 1e-10:
            min_area = 0.0
        return -min_area

    bounds = [(0, 1)] * 22
    best_x = None
    best_value = np.inf

    num_global_runs = 25
    for i in range(num_global_runs):
        res = differential_evolution(
            objective, bounds,
            seed=42 + i,
            popsize=5,
            maxiter=200,
            tol=1e-6,
            updating='immediate',
            workers=1
        )
        if res.fun < best_value:
            best_value = res.fun
            best_x = res.x

    res_local = minimize(
        objective, best_x, method='COBYLA',
        bounds=bounds,
        options={'maxiter': 1000, 'tol': 1e-8}
    )
    if res_local.fun < best_value:
        best_x = res_local.x

    return transform(best_x)