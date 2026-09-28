import random
import math
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate initial random points inside triangle
    points = []
    for _ in range(11):
        while True:
            u = random.random()
            v = random.random()
            if u + v <= 1:
                break
        P = (1 - u - v) * A + u * B + v * C
        points.append(P)
    points = np.array(points)
    
    current_min = get_smallest_triangle_area(points)
    best_min = current_min
    best_points = points.copy()
    
    # Simulated annealing parameters
    initial_temp = 0.0001
    cooling_rate = 0.9995
    steps = 10000
    step_size = 0.05
    
    current_temp = initial_temp
    current_points = points
    
    for step in range(steps):
        # Select random point to perturb
        idx = random.randint(0, 10)
        
        # Generate random displacement
        dx = random.uniform(-step_size, step_size)
        dy = random.uniform(-step_size, step_size)
        displacement = np.array([dx, dy])
        
        new_points = current_points.copy()
        new_points[idx] += displacement
        
        # Reject if point moves outside triangle
        if not is_inside_triangle(new_points[idx], A, B, C):
            continue
            
        new_min = get_smallest_triangle_area(new_points)
        delta = new_min - current_min
        
        # Acceptance criterion
        if delta >= 0:
            accept = True
        else:
            accept_prob = math.exp(delta / current_temp)
            accept = random.random() < accept_prob

        if accept:
            current_points = new_points
            current_min = new_min
            if new_min > best_min:
                best_min = new_min
                best_points = new_points.copy()

        # Cool temperature
        current_temp *= cooling_rate

    return best_points