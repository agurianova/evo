import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

A, B, C = get_unit_triangle()
center_x = (A[0] + B[0]) / 2

def project_point(p, A, B, C):
    if is_inside_triangle(p, A, B, C):
        return p
    edges = [(A, B), (B, C), (C, A)]
    min_dist = float('inf')
    best_point = None
    for (v1, v2) in edges:
        v = v2 - v1
        w = p - v1
        c1 = np.dot(w, v)
        c2 = np.dot(v, v)
        if c2 < 1e-10:
            b = 0
        else:
            b = c1 / c2
        if b < 0:
            proj = v1
        elif b > 1:
            proj = v2
        else:
            proj = v1 + b * v
        dist = np.linalg.norm(p - proj)
        if dist < min_dist:
            min_dist = dist
            best_point = proj
    return best_point

def is_similar(config1, config2, threshold=0.05):
    c1 = config1[np.lexsort((config1[:,1], config1[:,0]))]
    c2 = config2[np.lexsort((config2[:,1], config2[:,0]))]
    return np.linalg.norm(c1 - c2) < threshold

def generate_symmetric_random_points(n):
    points_left = []
    for _ in range((n-1)//2):
        while True:
            r1, r2 = np.random.rand(2)
            sqrt_r1 = np.sqrt(r1)
            b1 = 1 - sqrt_r1
            b2 = sqrt_r1 * (1 - r2)
            b3 = sqrt_r1 * r2
            point = b1 * A + b2 * B + b3 * C
            if point[0] < center_x:
                points_left.append(point)
                break
    points_right = [[2*center_x - p[0], p[1]] for p in points_left]
    axis_point = [center_x, np.random.uniform(0, C[1])]
    return np.array(points_left + points_right + [axis_point])

def hill_climb(points, max_iter=10000):
    current = points.copy()
    current_min_area = get_smallest_triangle_area(current)
    best = current.copy()
    best_min_area = current_min_area

    initial_temp = 0.01
    cooling_rate = 0.995
    initial_step = 0.15

    for i in range(max_iter):
        T = initial_temp * (cooling_rate ** i)
        step = initial_step * (T / initial_temp)

        # Find smallest triangle indices
        n = current.shape[0]
        min_area = float('inf')
        min_indices = None
        for i1 in range(n):
            for i2 in range(i1+1, n):
                for i3 in range(i2+1, n):
                    x1, y1 = current[i1]
                    x2, y2 = current[i2]
                    x3, y3 = current[i3]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area < min_area:
                        min_area = area
                        min_indices = (i1, i2, i3)
        
        if min_indices is None:
            continue
            
        candidate = current.copy()
        for idx in min_indices:
            dx = step * (np.random.rand(2) - 0.5) * 2
            candidate[idx] += dx
            candidate[idx] = project_point(candidate[idx], A, B, C)

        new_min_area = get_smallest_triangle_area(candidate)
        delta = new_min_area - current_min_area
        
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            current = candidate
            current_min_area = new_min_area
            if new_min_area > best_min_area:
                best = candidate
                best_min_area = new_min_area

    return best, best_min_area

def entrypoint() -> np.ndarray:
    best_points = None
    best_area = -1
    master_seed = 42
    num_restarts = 50
    max_attempts = 100
    stored_initials = []

    for restart in range(num_restarts):
        base_seed = master_seed + restart
        attempt = 0
        while attempt < max_attempts:
            np.random.seed(base_seed + attempt)
            points = generate_symmetric_random_points(11)
            
            similar_found = False
            for stored in stored_initials:
                if is_similar(points, stored):
                    similar_found = True
                    break
                    
            if not similar_found:
                stored_initials.append(points)
                break
            attempt += 1

        points, area = hill_climb(points, max_iter=10000)
        if area > best_area:
            best_area = area
            best_points = points

    return best_points