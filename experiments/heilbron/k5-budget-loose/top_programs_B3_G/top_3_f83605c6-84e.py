import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.optimize import differential_evolution
import random

np.random.seed(42)
random.seed(42)

def project_simplex(y, z=1.0):
    """Project y onto the simplex: sum(x_i)=z, x_i>=0."""
    n = len(y)
    u = np.sort(y)[::-1]
    cssv = np.cumsum(u) - z
    ind = np.arange(1, n+1)
    cond = (u - cssv / ind) > 0
    rho = ind[cond][-1]
    theta = cssv[cond][-1] / rho
    w = np.maximum(y - theta, 0)
    return w

def project_to_triangle(p, A, B, C):
    v1 = B - A
    v2 = C - A
    M = np.column_stack((v1, v2))
    try:
        sol = np.linalg.solve(M, p - A)
        v, w = sol
        u = 1 - v - w
    except np.linalg.LinAlgError:
        return (A + B + C) / 3.0
    y = np.array([u, v, w])
    y_proj = project_simplex(y)
    return y_proj[0]*A + y_proj[1]*B + y_proj[2]*C

def project_points_to_triangle(points, A, B, C):
    return np.array([project_to_triangle(p, A, B, C) for p in points])

def farthest_point_insertion(tri, n=11):
    A, B, C = tri
    points = []
    u = random.random()
    v = random.random() * (1 - u)
    p = (1-u-v)*A + u*B + v*C
    points.append(p)
    for i in range(1, n):
        best_candidate = None
        best_min_dist = -1
        for j in range(1000):
            u = random.random()
            v = random.random() * (1 - u)
            candidate = (1-u-v)*A + u*B + v*C
            min_dist = min(np.linalg.norm(candidate - p) for p in points)
            if min_dist > best_min_dist:
                best_min_dist = min_dist
                best_candidate = candidate
        points.append(best_candidate)
    return np.array(points)

def entrypoint():
    tri = get_unit_triangle()
    A, B, C = tri

    # Generate 5 initial configurations with different seeds
    best_initial = None
    best_initial_score = -1
    for i in range(5):
        np.random.seed(42 + i)
        random.seed(42 + i)
        points = farthest_point_insertion(tri, n=11)
        if not is_inside_triangle(points, A, B, C):
            continue
        score = get_smallest_triangle_area(points)
        if score > best_initial_score:
            best_initial = points
            best_initial_score = score

    # Fallback to Sobol if all initializations failed
    if best_initial is None:
        sobol = np.random.rand(11, 2)
        points = []
        for (x, y) in sobol:
            u = x
            v = y * (1 - x)
            P = (1 - u - v) * A + u * B + v * C
            points.append(P)
        best_initial = np.array(points)

    # Reset seed for optimization phase
    np.random.seed(42)
    random.seed(42)

    # Define objective with projection
    def objective(x):
        pts = x.reshape(11, 2)
        pts = project_points_to_triangle(pts, A, B, C)
        min_area = get_smallest_triangle_area(pts)
        return -min_area

    # Bounding box of the triangle
    x_min, x_max = 0, 1.5197
    y_min, y_max = 0, 1.3161
    bounds = [(x_min, x_max), (y_min, y_max)] * 11

    # Run global optimization
    res = differential_evolution(
        objective, 
        bounds,
        popsize=15,
        maxiter=50,
        seed=42,
        tol=0.01
    )
    best = res.x.reshape(11, 2)
    best = project_points_to_triangle(best, A, B, C)
    best_score = get_smallest_triangle_area(best)

    # Local search polish to ensure resistance
    current = best
    current_score = best_score
    no_improve_count = 0
    max_no_improve = 1000
    for _ in range(10000):
        if no_improve_count >= max_no_improve:
            break
        idx = np.random.randint(0, 11)
        perturbation = np.random.normal(0, 0.01, size=2)
        candidate = current.copy()
        candidate[idx] += perturbation
        candidate = project_points_to_triangle(candidate, A, B, C)
        score = get_smallest_triangle_area(candidate)
        if score > current_score:
            current = candidate
            current_score = score
            no_improve_count = 0
        else:
            no_improve_count += 1

    # Final validation
    if not is_inside_triangle(current, A, B, C) or get_smallest_triangle_area(current) <= 1e-10:
        return best_initial
    return current