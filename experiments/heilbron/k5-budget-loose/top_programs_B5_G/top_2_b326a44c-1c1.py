import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(123)
random.seed(123)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    height = C[1]  

    num_restarts = 10
    max_iter = 10000
    initial_step = 0.1 * height

    best_config = None
    best_min_area = -1.0

    for _ in range(num_restarts):
        # Generate valid random initial configuration
        while True:
            points = []
            for _ in range(11):
                u = random.random()
                v = random.random()
                if u + v > 1:
                    u, v = 1 - u, 1 - v
                P = (1 - u - v) * A + u * B + v * C
                points.append(P)
            points = np.array(points)
            
            # Check distinctness
            dists = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
            np.fill_diagonal(dists, np.inf)
            if np.min(dists) < 1e-5:
                continue
            
            min_area = get_smallest_triangle_area(points)
            if min_area > 0:  
                break

        current_config = points
        current_min_area = min_area

        # Hill-climbing optimization
        for iter_idx in range(max_iter):
            step = initial_step * (1 - iter_idx / max_iter)
            idx = random.randint(0, 10)
            angle = random.uniform(0, 2 * np.pi)
            dx = step * np.cos(angle)
            dy = step * np.sin(angle)
            new_point = current_config[idx] + np.array([dx, dy])

            # Validate new point
            if not is_inside_triangle(new_point, A, B, C):
                continue
            
            new_config = current_config.copy()
            new_config[idx] = new_point
            
            # Check distinctness
            dists = np.linalg.norm(new_config - new_point, axis=1)
            dists[idx] = np.inf
            if np.min(dists) < 1e-5:
                continue

            new_min_area = get_smallest_triangle_area(new_config)
            if new_min_area > current_min_area:
                current_config = new_config
                current_min_area = new_min_area

        # Update best configuration
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = current_config

    return best_config