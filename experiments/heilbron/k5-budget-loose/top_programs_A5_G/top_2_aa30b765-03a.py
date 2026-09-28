import random
import math
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Generate 11 distinct random points inside the triangle
    points = []
    while len(points) < 11:
        u = random.random()
        v = random.random() * (1 - u)
        w = 1 - u - v
        P = w * A + u * B + v * C
        valid = True
        for p in points:
            if np.linalg.norm(P - p) < 1e-5:
                valid = False
                break
        if valid:
            points.append(P)
    points = np.array(points)

    # Compute initial min_area
    current_min_area = get_smallest_triangle_area(points)
    best_min_area = current_min_area
    best_points = points.copy()

    # Parameters for simulated annealing
    max_iter = 10000
    initial_step = 0.15
    initial_temperature = 0.0005
    cooling_rate = 0.9995
    temperature = initial_temperature

    for iter in range(max_iter):
        idx = random.randint(0, 10)
        old_point = points[idx].copy()

        step = initial_step * (1 - iter / max_iter)
        displacement = np.random.uniform(-step, step, size=2)
        new_point = old_point + displacement

        # Check if new_point is inside the triangle and distinct
        if is_inside_triangle(new_point, A, B, C):
            too_close = False
            for j in range(11):
                if j == idx:
                    continue
                if np.linalg.norm(new_point - points[j]) < 1e-5:
                    too_close = True
                    break
            
            if not too_close:
                # Attempt the move
                points[idx] = new_point
                new_min_area = get_smallest_triangle_area(points)

                if new_min_area >= current_min_area:
                    current_min_area = new_min_area
                    if new_min_area > best_min_area:
                        best_min_area = new_min_area
                        best_points = points.copy()
                else:
                    delta = new_min_area - current_min_area
                    if random.random() < math.exp(delta / temperature):
                        current_min_area = new_min_area
                    else:
                        points[idx] = old_point  # Revert move

        # Update temperature regardless of move success
        temperature *= cooling_rate

    return best_points