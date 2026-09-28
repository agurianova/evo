import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.optimize import differential_evolution

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()

    # Convert (s,t) in [0,1]x[0,1] to barycentric (u,v) with u+v<=1
    def st_to_bary(s, t):
        u = s * (1 - t)
        v = t
        return u, v

    def objective(x):
        points = []
        for i in range(11):
            s, t = x[2*i], x[2*i+1]
            u, v = st_to_bary(s, t)
            pt = (1 - u - v) * A + u * B + v * C
            points.append(pt)
        points = np.array(points)

        # Enforce distinctness via minimum distance penalty
        min_dist = float('inf')
        for i in range(11):
            for j in range(i+1, 11):
                d = np.linalg.norm(points[i] - points[j])
                if d < min_dist:
                    min_dist = d
        if min_dist < 1e-5:
            return 1e6  # Invalid configuration penalty

        min_area = get_smallest_triangle_area(points)
        return -min_area  # Minimize negative area (maximize area)

    # Box constraints: s,t ∈ [0,1] for all points
    bounds = [(0, 1)] * 22

    # Run multiple DE trials for global exploration
    best_x = None
    best_value = -np.inf
    for run in range(5):
        np.random.seed(42 + run)
        res = differential_evolution(
            objective, bounds,
            strategy='best1bin',
            popsize=15,
            maxiter=100,
            tol=1e-4,
            disp=False
        )
        if -res.fun > best_value:
            best_value = -res.fun
            best_x = res.x

    # Convert to Cartesian points
    points = []
    for i in range(11):
        s, t = best_x[2*i], best_x[2*i+1]
        u, v = st_to_bary(s, t)
        pt = (1 - u - v) * A + u * B + v * C
        points.append(pt)
    points = np.array(points)

    # Local search to improve resistance (small perturbations)
    current_min_area = get_smallest_triangle_area(points)
    r0 = 0.05
    for level in range(5):
        r = r0 / (2 ** level)
        improved = True
        while improved:
            improved = False
            for i in range(11):
                for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
                    rad = np.radians(angle)
                    dx = r * np.cos(rad)
                    dy = r * np.sin(rad)
                    new_pt = points[i] + np.array([dx, dy])
                    
                    # Skip if outside triangle or too close to other points
                    if not is_inside_triangle(new_pt, A, B, C):
                        continue
                    too_close = False
                    for j in range(11):
                        if i == j: continue
                        if np.linalg.norm(new_pt - points[j]) < 1e-5:
                            too_close = True
                            break
                    if too_close:
                        continue

                    # Test new configuration
                    new_points = points.copy()
                    new_points[i] = new_pt
                    new_min_area = get_smallest_triangle_area(new_points)
                    if new_min_area > current_min_area:
                        points = new_points
                        current_min_area = new_min_area
                        improved = True
                        break  # Restart search from improved config
                if improved:
                    break

    return points