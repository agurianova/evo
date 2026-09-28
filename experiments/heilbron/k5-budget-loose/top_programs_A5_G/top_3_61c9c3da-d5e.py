import numpy as np
import math
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    # Generate boundary points with asymmetric spacing
    points = []
    # AB edge (A to B)
    for t in [0.2, 0.5, 0.75]:
        points.append((1 - t) * A + t * B)
    # BC edge (B to C)
    for t in [0.3, 0.6, 0.85]:
        points.append((1 - t) * B + t * C)
    # CA edge (C to A)
    for t in [0.15, 0.4, 0.7]:
        points.append((1 - t) * C + t * A)

    # Interior points with asymmetric barycentric weights
    points.append(0.5 * A + 0.2 * B + 0.3 * C)  # First interior point
    points.append(0.2 * A + 0.6 * B + 0.2 * C)  # Second interior point

    points = np.array(points)

    # Tiny perturbation to break potential collinearity
    points += np.random.uniform(-1e-4, 1e-4, size=(11, 2))

    # Ensure all points remain inside triangle after perturbation
    for i in range(11):
        if not is_inside_triangle(points[i], A, B, C):
            # Revert perturbation for this point if outside
            points[i] -= np.random.uniform(-1e-4, 1e-4, size=2)

    # Hill climbing optimization
    current_min_area = get_smallest_triangle_area(points)
    step_size = 0.1
    min_step = 1e-5
    decay = 0.9

    while step_size > min_step:
        improved = False
        for i in range(11):
            original = points[i].copy()
            best_move = None
            best_area = current_min_area

            # Try 4 random directions
            for _ in range(4):
                angle = random.uniform(0, 2 * math.pi)
                dx = step_size * math.cos(angle)
                dy = step_size * math.sin(angle)
                new_pos = original + np.array([dx, dy])

                # Check distinctness from all other points
                too_close = False
                for j in range(11):
                    if i == j:
                        continue
                    if np.linalg.norm(new_pos - points[j]) < 1e-5:
                        too_close = True
                        break
                if too_close:
                    continue

                # Check triangle containment
                if not is_inside_triangle(new_pos, A, B, C):
                    continue

                # Evaluate new configuration
                points[i] = new_pos
                new_area = get_smallest_triangle_area(points)
                if new_area > best_area:
                    best_area = new_area
                    best_move = (dx, dy)
                # Revert for next trial
                points[i] = original

            # Apply best move if found
            if best_move is not None:
                points[i] = original + np.array(best_move)
                current_min_area = best_area
                improved = True

        # Reduce step size if no improvement
        if not improved:
            step_size *= decay

    return points