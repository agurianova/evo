import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(12345)
random.seed(12345)

def entrypoint():
    tri = get_unit_triangle()
    A, B, C = tri

    def generate_random_points(n, A, B, C):
        points = []
        while len(points) < n:
            u = random.random()
            v = random.random() * (1 - u)
            P = (1 - u - v) * A + u * B + v * C
            if len(points) == 0:
                points.append(P)
            else:
                too_close = False
                for p in points:
                    if np.linalg.norm(P - p) < 1e-8:
                        too_close = True
                        break
                if not too_close:
                    points.append(P)
        return np.array(points)

    def hill_climbing(points, A, B, C, max_iter=100000):
        points = np.array(points)
        current_min_area = get_smallest_triangle_area(points)
        step_size = 0.1
        decay = 0.99995

        for i_iter in range(max_iter):
            current_step = step_size * (decay ** i_iter)
            if current_step < 1e-6:
                current_step = 1e-6

            idx = random.randint(0, 10)
            angle = random.uniform(0, 2 * np.pi)
            dx = current_step * np.cos(angle)
            dy = current_step * np.sin(angle)
            new_point = points[idx] + np.array([dx, dy])

            if not is_inside_triangle(new_point, A, B, C):
                continue

            new_points = points.copy()
            new_points[idx] = new_point
            new_min_area = get_smallest_triangle_area(new_points)

            if new_min_area > current_min_area:
                points = new_points
                current_min_area = new_min_area

        return points

    best_config = None
    best_min_area = -1

    for restart in range(10):
        points = generate_random_points(11, A, B, C)
        points = hill_climbing(points, A, B, C, max_iter=100000)
        min_area = get_smallest_triangle_area(points)
        if min_area > best_min_area:
            best_min_area = min_area
            best_config = points

    return best_config