import random
import math
import numpy as np
from scipy.stats import qmc
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    best_config = None
    best_min_area = -1.0

    num_restarts = 10
    initial_step = 0.05
    min_step = 1e-6
    no_improve_limit = 1000
    max_iter = 100000

    # Parameters for simulated annealing
    initial_temp = 0.0045
    cooling_rate = 0.99995

    for restart in range(num_restarts):
        # Generate initial configuration using Sobol
        sampler = qmc.Sobol(d=2, scramble=False)
        sample = sampler.random(n=11)
        points = []
        for (u,v) in sample:
            if u + v > 1:
                u, v = 1 - u, 1 - v
            w = 1 - u - v
            P = w * A + u * B + v * C
            points.append(P)
        points = np.array(points)
        min_area = get_smallest_triangle_area(points)
        if min_area <= 1e-10:
            # Fallback to random if degenerate
            for _ in range(1000):
                points = []
                for j in range(11):
                    s = random.random()
                    t = random.random()
                    if s + t > 1:
                        s = 1 - s
                        t = 1 - t
                    u = s
                    v = t
                    w = 1 - u - v
                    P = w * A + u * B + v * C
                    points.append(P)
                points = np.array(points)
                min_area = get_smallest_triangle_area(points)
                if min_area > 1e-10:
                    break

        # Simulated annealing
        step_size = initial_step
        no_improve_count = 0
        current_min_area = min_area
        current_temp = initial_temp

        for it in range(max_iter):
            i = random.randint(0, 10)
            angle = random.uniform(0, 2 * math.pi)
            r = step_size * math.sqrt(random.random())
            dx = r * math.cos(angle)
            dy = r * math.sin(angle)
            new_point = points[i] + np.array([dx, dy])

            if not is_inside_triangle(new_point, A, B, C):
                no_improve_count += 1
                continue

            new_points = points.copy()
            new_points[i] = new_point
            new_min_area = get_smallest_triangle_area(new_points)

            if new_min_area > current_min_area:
                points = new_points
                current_min_area = new_min_area
                no_improve_count = 0
            else:
                delta = current_min_area - new_min_area  # positive
                if random.random() < math.exp(-delta / current_temp):
                    points = new_points
                    current_min_area = new_min_area
                no_improve_count += 1

            current_temp *= cooling_rate

            if no_improve_count >= no_improve_limit:
                step_size *= 0.9
                no_improve_count = 0
                if step_size < min_step:
                    break

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points

    return best_config