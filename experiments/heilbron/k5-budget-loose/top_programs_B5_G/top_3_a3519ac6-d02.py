import random
import numpy as np
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)


def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    n_points = 11
    min_dist = 1e-5
    trials = 10
    max_iterations = 50000
    initial_step_size = 0.1
    best_config = None
    best_min_area = -1.0

    for trial in range(trials):
        # Generate initial random configuration with distinct points
        config = []
        for _ in range(n_points):
            while True:
                r1, r2 = random.random(), random.random()
                if r1 + r2 > 1:
                    r1, r2 = 1 - r1, 1 - r2
                point = (1 - r1 - r2) * A + r1 * B + r2 * C
                # Check distinctness
                valid = True
                for p in config:
                    if np.linalg.norm(point - p) < min_dist:
                        valid = False
                        break
                if valid:
                    config.append(point)
                    break
        config = np.array(config)
        
        min_area = get_smallest_triangle_area(config)
        step_size = initial_step_size

        # Hill-climbing optimization
        for i in range(max_iterations):
            # Adaptive step size reduction
            if min_area > 0.03 and i % 100 == 0:
                step_size *= 0.99
            if i % 1000 == 0 and i > 0:
                step_size *= 0.95

            # Select random point to move
            idx = random.randint(0, n_points - 1)
            angle = random.uniform(0, 2 * math.pi)
            dx = step_size * math.cos(angle)
            dy = step_size * math.sin(angle)
            new_point = config[idx] + np.array([dx, dy])

            # Validate new point
            if not is_inside_triangle(new_point, A, B, C):
                continue
            too_close = False
            for j in range(n_points):
                if j == idx:
                    continue
                if np.linalg.norm(new_point - config[j]) < min_dist:
                    too_close = True
                    break
            if too_close:
                continue

            # Evaluate new configuration
            new_config = config.copy()
            new_config[idx] = new_point
            new_min_area = get_smallest_triangle_area(new_config)

            # Accept if improvement
            if new_min_area > min_area:
                config = new_config
                min_area = new_min_area

        # Track best configuration across trials
        if min_area > best_min_area:
            best_config = config
            best_min_area = min_area

    return best_config