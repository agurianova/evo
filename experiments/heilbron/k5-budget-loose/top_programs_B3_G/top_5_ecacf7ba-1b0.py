import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area
import scipy.optimize

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    sqrt3 = np.sqrt(3)
    B0 = B[0]

    points = []
    for _ in range(11):
        u = random.random()
        v = random.random()
        if u + v > 1:
            u, v = 1 - u, 1 - v
        w = 1 - u - v
        P = u * A + v * B + w * C
        points.append(P)
    x0 = np.array(points).flatten()

    def objective(x):
        pts = x.reshape(11, 2)
        min_area = get_smallest_triangle_area(pts)
        return -min_area

    constraints = []
    for i in range(11):
        constraints.append({'type': 'ineq', 'fun': lambda x, i=i: x[2*i+1]})
        constraints.append({'type': 'ineq', 'fun': lambda x, i=i: sqrt3 * x[2*i] - x[2*i+1]})
        constraints.append({'type': 'ineq', 'fun': lambda x, i=i: sqrt3 * (B0 - x[2*i]) - x[2*i+1]})

    res = scipy.optimize.minimize(
        objective,
        x0,
        method='SLSQP',
        constraints=constraints,
        options={'maxiter': 1000, 'ftol': 1e-8, 'disp': False}
    )

    return res.x.reshape(11, 2) if res.success else x0.reshape(11, 2)