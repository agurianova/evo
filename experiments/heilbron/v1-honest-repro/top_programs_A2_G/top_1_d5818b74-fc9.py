import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    best_config = None
    best_min_area = -1.0

    num_restarts = 10
    for restart in range(num_restarts):
        # Generate random initial configuration
        points = []
        for i in range(11):
            u = random.random()
            v = random.random()
            if u + v > 1:
                u, v = 1 - u, 1 - v
            w = 1 - u - v
            P = u * A + v * B + w * C
            points.append(P)
        points = np.array(points)

        # Compute initial min_area
        current_min_area = get_smallest_triangle_area(points)
        step = 0.15  # initial step size (10% of triangle side)
        trials_without_improve = 0
        max_trials_without_improve = 1000

        # Hill-climbing loop
        while step > 1e-6:
            i = random.randint(0, 10)
            old_point = points[i].copy()

            # Random direction
            dx, dy = np.random.uniform(-1, 1, 2)
            norm = np.sqrt(dx*dx + dy*dy)
            if norm < 1e-8:
                continue
            dx, dy = dx / norm, dy / norm
            candidate = old_point + step * np.array([dx, dy])

            # Check containment
            if not is_inside_triangle(candidate, A, B, C):
                trials_without_improve += 1
                if trials_without_improve >= max_trials_without_improve:
                    step *= 0.5
                    trials_without_improve = 0
                continue

            # Evaluate candidate
            points[i] = candidate
            new_min_area = get_smallest_triangle_area(points)

            if new_min_area > current_min_area:
                current_min_area = new_min_area
                trials_without_improve = 0
            else:
                points[i] = old_point
                trials_without_improve += 1

            # Step decay logic
            if trials_without_improve >= max_trials_without_improve:
                step *= 0.5
                trials_without_improve = 0

        # Track best configuration
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config