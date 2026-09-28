import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.optimize import differential_evolution
import random

np.random.seed(42)
random.seed(42)

def project_point(P, A, B, C):
    v0 = B - A
    v1 = C - A
    v2 = P - A

    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)

    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-10:
        return A

    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w

    if u < 0:
        u = 0
        denom = v + w
        if denom > 0:
            v /= denom
            w /= denom
        else:
            v = 0.5
            w = 0.5
    if v < 0:
        v = 0
        denom = u + w
        if denom > 0:
            u /= denom
            w /= denom
        else:
            u = 0.5
            w = 0.5
    if w < 0:
        w = 0
        denom = u + v
        if denom > 0:
            u /= denom
            v /= denom
        else:
            u = 0.5
            v = 0.5

    return u * A + v * B + w * C

def project_points(points, A, B, C):
    return np.array([project_point(p, A, B, C) for p in points])

def random_point_in_triangle(A, B, C):
    r1, r2 = np.random.random(), np.random.random()
    u = 1 - np.sqrt(r1)
    v = np.sqrt(r1) * (1 - r2)
    w = np.sqrt(r1) * r2
    return u * A + v * B + w * C

def farthest_point_insertion(n, A, B, C, num_candidates=1000):
    points = [random_point_in_triangle(A, B, C)]
    for _ in range(1, n):
        best_candidate = None
        best_min_dist = -1
        candidates = [random_point_in_triangle(A, B, C) for _ in range(num_candidates)]
        for cand in candidates:
            min_dist = min(np.linalg.norm(cand - p) for p in points)
            if min_dist > best_min_dist:
                best_min_dist = min_dist
                best_candidate = cand
        points.append(best_candidate)
    return np.array(points)

def entrypoint():
    tri = get_unit_triangle()
    A, B, C = tri

    # Generate multiple initial configurations via farthest-point insertion
    initial_configs = []
    for _ in range(5):
        config = farthest_point_insertion(11, A, B, C, num_candidates=1000)
        initial_configs.append(config)

    # Define objective function with projection
    def objective(x):
        pts = x.reshape(11, 2)
        pts = project_points(pts, A, B, C)
        min_area = get_smallest_triangle_area(pts)
        return -min_area

    best_score = float('inf')
    best_points = None

    # Optimization bounds (slightly larger than triangle)
    bounds = [(-0.1, 1.6), (-0.1, 1.4)] * 11

    for init in initial_configs:
        res = differential_evolution(
            objective,
            bounds,
            x0=init.flatten(),
            maxiter=1000,
            popsize=20,
            tol=1e-8,
            mutation=(0.5, 1.5),
            recombination=0.7,
            seed=42,
            init='random',
            workers=1
        )
        if res.fun < best_score:
            best_score = res.fun
            optimized_points = res.x.reshape(11, 2)
            # Final projection to ensure feasibility
            optimized_points = project_points(optimized_points, A, B, C)
            best_points = optimized_points

    # Final validity check
    if best_points is None or not is_inside_triangle(best_points, A, B, C) or get_smallest_triangle_area(best_points) <= 1e-10:
        return initial_configs[0]  # fallback to first initial config
    return best_points