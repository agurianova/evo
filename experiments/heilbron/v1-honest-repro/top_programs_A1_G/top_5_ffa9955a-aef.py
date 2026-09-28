import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(123)
random.seed(123)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate initial configuration with symmetry-breaking perturbation
    points = []
    rows = 5
    count = 0
    for row in range(rows):
        num_points = rows - row
        v = (row + 0.5) / rows
        for i in range(num_points):
            if count >= 11:
                break
            u = (i + 0.5) / num_points * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            perturbation = np.random.uniform(-0.1, 0.1, size=2)
            P = P + perturbation
            points.append(P)
            count += 1
        if count >= 11:
            break
    
    points = np.array(points)
    current_min_area = get_smallest_triangle_area(points)
    max_iter = 20000
    step_size = 0.05
    min_distance = 1e-5

    for iter in range(max_iter):
        i = random.randint(0, 10)
        angle = random.uniform(0, 2 * np.pi)
        dx = step_size * np.cos(angle)
        dy = step_size * np.sin(angle)
        candidate = points.copy()
        candidate[i] += [dx, dy]

        # Validate containment
        if not is_inside_triangle(candidate[i], A, B, C):
            continue
        
        # Validate distinctness
        too_close = False
        for j in range(11):
            if i == j:
                continue
            if np.linalg.norm(candidate[i] - candidate[j]) < min_distance:
                too_close = True
                break
        if too_close:
            continue

        new_min_area = get_smallest_triangle_area(candidate)
        if new_min_area > current_min_area:
            points = candidate
            current_min_area = new_min_area

        # Adaptive step size reduction
        if iter % 1000 == 0 and iter > 0:
            step_size *= 0.9

    return points