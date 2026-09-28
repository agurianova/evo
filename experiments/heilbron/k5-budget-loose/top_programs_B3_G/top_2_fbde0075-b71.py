import numpy as np
from scipy.optimize import differential_evolution
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random


def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    base = B[0] - A[0]
    height = C[1]
    center_x = (A[0] + B[0]) / 2

    def build_points_from_state(state):
        left_points = []
        for i in range(5):
            x = state[2*i]
            y = state[2*i+1]
            left_points.append([x, y])
        center = [center_x, state[10]]
        right_points = [[base - x, y] for [x, y] in left_points]
        return np.array(left_points + [center] + right_points)

    def project_points_inside(points):
        projected = np.zeros_like(points)
        for i, (x, y) in enumerate(points):
            y_clamped = np.clip(y, 0, height)
            x_min = (center_x / height) * y_clamped
            x_max = base - x_min
            x_clamped = np.clip(x, x_min, x_max)
            projected[i] = [x_clamped, y_clamped]
        return projected

    def local_search(points, max_rounds=50):
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        for _ in range(max_rounds):
            candidate = best.copy()
            idx = np.random.randint(0, 11)
            candidate[idx] += np.random.normal(0, 0.02, size=2)
            candidate = project_points_inside(candidate)
            
            score = get_smallest_triangle_area(candidate)
            if score > best_score:
                best = candidate
                best_score = score
        return best

    def generate_symmetric_initial():
        y_levels = [i * height / 5 for i in range(6)]
        center_y = y_levels[2]
        left_levels = [0, 1, 3, 4, 5]
        fractions = [0.1, 0.2, 0.3, 0.4, 0.45]
        state = []
        
        for i, level_idx in enumerate(left_levels):
            y = y_levels[level_idx]
            x_min = (center_x / height) * y
            x = x_min + fractions[i] * (center_x - x_min)
            state.extend([x, y])
        state.append(center_y)
        return np.array(state)

    best_config = None
    best_area = -1

    for restart in range(10):
        np.random.seed(restart)
        random.seed(restart)
        
        init_state = generate_symmetric_initial()

        def objective(state):
            points = build_points_from_state(state)
            points = project_points_inside(points)
            min_area = get_smallest_triangle_area(points)
            return -min_area

        bounds = [(0, base)] * 10 + [(0, height)]
        
        res = differential_evolution(
            objective,
            bounds,
            maxiter=1000,
            popsize=15,
            tol=1e-6,
            mutation=(0.5, 1.5),
            recombination=0.7,
            seed=restart,
            disp=False
        )

        config = build_points_from_state(res.x)
        config = project_points_inside(config)
        config = local_search(config, max_rounds=50)
        
        area = get_smallest_triangle_area(config)
        if area > best_area:
            best_area = area
            best_config = config

    return best_config