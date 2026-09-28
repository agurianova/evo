import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def generate_random_config(n, A, B, C):
    points = []
    for _ in range(n):
        while True:
            u = np.random.rand()
            v = np.random.rand() * (1 - u)
            P = (1 - u - v) * A + u * B + v * C
            if len(points) == 0:
                break
            min_dist = min(np.linalg.norm(P - p) for p in points)
            if min_dist > 1e-5:
                break
        points.append(P)
    return np.array(points)

def hill_climb(initial, A, B, C, max_iter=50000):
    current = initial.copy()
    current_area = get_smallest_triangle_area(current)
    step = 0.1
    no_improve_count = 0
    
    for _ in range(max_iter):
        idx = np.random.randint(0, 11)
        pert = step * (2 * np.random.rand(2) - 1)
        candidate = current.copy()
        candidate[idx] += pert
        
        if not is_inside_triangle(candidate, A, B, C):
            no_improve_count += 1
            continue
        
        min_dist_sq = float('inf')
        for j in range(11):
            if j == idx:
                continue
            d_sq = np.sum((candidate[idx] - candidate[j])**2)
            if d_sq < min_dist_sq:
                min_dist_sq = d_sq
        if min_dist_sq < 1e-10:
            no_improve_count += 1
            continue
        
        new_area = get_smallest_triangle_area(candidate)
        if new_area < 1e-10:
            no_improve_count += 1
            continue
        
        if new_area > current_area:
            current = candidate
            current_area = new_area
            no_improve_count = 0
        else:
            no_improve_count += 1

        if no_improve_count > 1000:
            step *= 0.5
            no_improve_count = 0
            if step < 1e-6:
                break
                
    return current, current_area

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    restarts = 5
    best_config = None
    best_area = -1
    
    for r in range(restarts):
        np.random.seed(42 + r)
        random.seed(42 + r)
        config = generate_random_config(11, A, B, C)
        area = get_smallest_triangle_area(config)
        current, current_area = hill_climb(config, A, B, C, max_iter=50000)
        
        if current_area > best_area:
            best_area = current_area
            best_config = current
            
    return best_config