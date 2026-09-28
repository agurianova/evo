import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    # Generate initial configuration with symmetric row pattern [1,2,3,3,2] (top to bottom)
    rows = [1, 2, 3, 3, 2]
    total_rows = len(rows)
    points = []
    for i, m in enumerate(rows):
        v = 1 - (i + 0.5) / total_rows
        for j in range(m):
            u = (j + 0.5) / m * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            points.append(P)
    current = np.array(points)
    current_min_area = get_smallest_triangle_area(current)

    # Simulated annealing parameters
    T = 0.01
    T_min = 1e-6
    alpha = 0.995
    steps_per_temp = 50

    while T > T_min:
        for step in range(steps_per_temp):
            i = random.randint(0, 10)
            angle = random.uniform(0, 2 * np.pi)
            step_size = T * random.uniform(0, 10)
            dx = step_size * np.cos(angle)
            dy = step_size * np.sin(angle)
            new_point = current[i] + np.array([dx, dy])

            # Check triangle containment
            if not is_inside_triangle(new_point, A, B, C):
                continue

            # Check distinctness with tolerance
            distinct = True
            for j in range(11):
                if j == i:
                    continue
                if np.linalg.norm(new_point - current[j]) < 1e-5:
                    distinct = False
                    break
            if not distinct:
                continue

            candidate = current.copy()
            candidate[i] = new_point
            new_min_area = get_smallest_triangle_area(candidate)

            # Acceptance criterion
            if new_min_area > current_min_area:
                current = candidate
                current_min_area = new_min_area
            else:
                delta = new_min_area - current_min_area
                if random.random() < np.exp(delta / T):
                    current = candidate
                    current_min_area = new_min_area

        T *= alpha

    return current