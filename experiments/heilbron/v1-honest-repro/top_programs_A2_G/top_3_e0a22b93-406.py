import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def generate_random_config(n, min_dist=1e-5):
    A, B, C = get_unit_triangle()
    points = []
    for _ in range(n):
        while True:
            u = random.random()
            v = random.random()
            if u + v > 1:
                u = 1 - u
                v = 1 - v
            P = (1 - u - v) * A + u * B + v * C
            too_close = False
            for p in points:
                if np.linalg.norm(P - p) < min_dist:
                    too_close = True
                    break
            if not too_close:
                break
        points.append(P)
    return np.array(points)

def entrypoint() -> np.ndarray:
    base_seed = 42
    best_config = None
    best_area = -1

    for restart in range(10):
        seed = base_seed + restart
        random.seed(seed)
        np.random.seed(seed)

        config = generate_random_config(11)
        current_config = config
        current_area = get_smallest_triangle_area(current_config)

        step_size = 0.1
        no_improve_count = 0
        max_no_improve = 500

        for _ in range(100000):
            idx = random.randint(0, 10)
            delta = np.random.uniform(-step_size, step_size, 2)
            new_config = current_config.copy()
            new_config[idx] += delta

            if not is_inside_triangle(new_config, *get_unit_triangle()):
                continue

            moved_point = new_config[idx]
            too_close = False
            for j in range(11):
                if j == idx:
                    continue
                if np.linalg.norm(moved_point - new_config[j]) < 1e-5:
                    too_close = True
                    break
            if too_close:
                continue

            new_area = get_smallest_triangle_area(new_config)
            if new_area > current_area:
                current_config = new_config
                current_area = new_area
                no_improve_count = 0
            else:
                no_improve_count += 1

            if no_improve_count >= max_no_improve:
                step_size *= 0.9
                no_improve_count = 0
                if step_size < 1e-6:
                    break

        if current_area > best_area:
            best_config = current_config
            best_area = current_area

    return best_config