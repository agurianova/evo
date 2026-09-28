import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri

    def generate_random_config():
        max_attempts = 1000
        for _ in range(max_attempts):
            points = []
            for _ in range(11):
                u = random.random()
                v = random.random() * (1 - u)
                P = (1 - u - v) * A + u * B + v * C
                points.append(P)
            points = np.array(points)
            
            min_dist = float('inf')
            for i in range(11):
                for j in range(i + 1, 11):
                    d = np.linalg.norm(points[i] - points[j])
                    if d < min_dist:
                        min_dist = d
            if min_dist < 1e-5:
                continue
            
            min_area = get_smallest_triangle_area(points)
            if min_area > 0:
                return points
        raise RuntimeError("Failed to generate valid config")

    def optimize_config(initial_points):
        current = initial_points.copy()
        best = current.copy()
        current_min_area = get_smallest_triangle_area(current)
        best_min_area = current_min_area

        T = 0.01
        cooling_rate = 0.995
        max_iter = 100000

        for _ in range(max_iter):
            idx = random.randint(0, 10)
            dx = random.uniform(-0.05, 0.05)
            dy = random.uniform(-0.05, 0.05)
            new_point = current[idx] + np.array([dx, dy])

            if not is_inside_triangle(new_point, A, B, C):
                continue

            valid = True
            for j in range(11):
                if j == idx:
                    continue
                d = np.linalg.norm(new_point - current[j])
                if d < 1e-5:
                    valid = False
                    break
            if not valid:
                continue

            new_config = current.copy()
            new_config[idx] = new_point
            new_min_area = get_smallest_triangle_area(new_config)

            if new_min_area > best_min_area:
                best = new_config.copy()
                best_min_area = new_min_area

            if new_min_area > current_min_area:
                current = new_config
                current_min_area = new_min_area
            else:
                delta = current_min_area - new_min_area
                if random.random() < np.exp(-delta / T):
                    current = new_config
                    current_min_area = new_min_area

            T *= cooling_rate

        final_config = best.copy()
        current_min_area = best_min_area
        step = 0.01
        consecutive_rejects = 0
        max_greedy_iter = 10000

        for _ in range(max_greedy_iter):
            idx = random.randint(0, 10)
            dx = random.uniform(-step, step)
            dy = random.uniform(-step, step)
            new_point = final_config[idx] + np.array([dx, dy])

            if not is_inside_triangle(new_point, A, B, C):
                consecutive_rejects += 1
                continue

            valid = True
            for j in range(11):
                if j == idx:
                    continue
                d = np.linalg.norm(new_point - final_config[j])
                if d < 1e-5:
                    valid = False
                    break
            if not valid:
                consecutive_rejects += 1
                continue

            new_config = final_config.copy()
            new_config[idx] = new_point
            new_min_area = get_smallest_triangle_area(new_config)

            if new_min_area > current_min_area:
                final_config = new_config
                current_min_area = new_min_area
                consecutive_rejects = 0
            else:
                consecutive_rejects += 1

            if consecutive_rejects >= 500:
                step *= 0.9
                consecutive_rejects = 0
                if step < 1e-6:
                    break

        return final_config

    best_config = None
    best_min_area = -1
    num_restarts = 5

    for restart in range(num_restarts):
        np.random.seed(42 + restart)
        random.seed(42 + restart)
        
        initial_config = generate_random_config()
        optimized_config = optimize_config(initial_config)
        min_area = get_smallest_triangle_area(optimized_config)

        if min_area > best_min_area:
            best_min_area = min_area
            best_config = optimized_config

    return best_config