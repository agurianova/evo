import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    points = []
    for _ in range(11):
        r1, r2 = random.random(), random.random()
        s = 1 - np.sqrt(r1)
        t = np.sqrt(r1) * (1 - r2)
        u = np.sqrt(r1) * r2
        point = s * A + t * B + u * C
        points.append(point)
    points = np.array(points)

    steps = 10000
    initial_temp = 0.001
    base_step = 0.05

    current_min = get_smallest_triangle_area(points)

    for i in range(steps):
        current_step = base_step * (1 - i / steps)
        temp = initial_temp * (1 - i / steps)

        idx = random.randint(0, 10)
        angle = random.uniform(0, 2 * np.pi)
        dx = current_step * np.cos(angle)
        dy = current_step * np.sin(angle)
        step = np.array([dx, dy])
        new_point = points[idx] + step

        if not is_inside_triangle(new_point, A, B, C):
            new_point = points[idx] - step
            if not is_inside_triangle(new_point, A, B, C):
                continue

        new_points = np.copy(points)
        new_points[idx] = new_point
        new_min = get_smallest_triangle_area(new_points)

        delta = new_min - current_min
        if delta > 0 or (temp > 1e-10 and random.random() < np.exp(delta / temp)):
            points = new_points
            current_min = new_min

    return points