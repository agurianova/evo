import random
import math

from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np


def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    base_seed = 42
    
    # Generate multiple initial configurations and select best
    best_initial = None
    best_initial_min_area = -1
    
    for trial in range(10):
        np.random.seed(base_seed + trial)
        random.seed(base_seed + trial)
        
        rows = [3, 3, 3, 2]
        v_vals = [0.1, 0.3, 0.6, 0.85]
        points = []
        
        for i in range(len(rows)):
            k = rows[i]
            v = v_vals[i]
            for j in range(k):
                u = (j + 1) / (k + 1) * (1 - v)
                P0 = (1 - u - v) * A + u * B + v * C
                
                # Generate valid point with perturbation
                found = False
                for _ in range(100):
                    perturbation = np.random.uniform(-0.05, 0.05, size=2)
                    P = P0 + perturbation
                    if is_inside_triangle(P, A, B, C):
                        points.append(P)
                        found = True
                        break
                
                if not found:
                    # Fallback to unperturbed if needed (should rarely happen)
                    points.append(P0)

        # Validate and score configuration
        points = np.array(points)
        min_area = get_smallest_triangle_area(points)
        
        # Skip degenerate configurations
        if min_area <= 1e-10:
            continue
            
        if min_area > best_initial_min_area:
            best_initial = points
            best_initial_min_area = min_area

    # If all trials degenerate, use last trial (shouldn't happen)
    if best_initial is None:
        best_initial = points

    # Simulated annealing parameters
    points = best_initial
    current_min_area = best_initial_min_area
    best_points = points.copy()
    best_min_area = current_min_area
    
    n_steps = 10000
    initial_temp = 0.01
    cooling_factor = 0.995
    step_size_initial = 0.05
    no_improve_count = 0
    early_stopping_patience = 1000

    T = initial_temp
    for step_index in range(n_steps):
        # Adaptive step size decay
        step_size = step_size_initial * (1 - step_index / n_steps)
        
        # Random point and direction
        idx = random.randint(0, len(points) - 1)
        direction = np.random.uniform(-1, 1, size=2)
        direction = direction / np.linalg.norm(direction)
        step = step_size * direction
        new_point = points[idx] + step

        # Boundary check
        if not is_inside_triangle(new_point, A, B, C):
            continue

        # Evaluate candidate
        new_points = points.copy()
        new_points[idx] = new_point
        new_min_area = get_smallest_triangle_area(new_points)

        # Track best configuration
        if new_min_area > best_min_area:
            best_points = new_points.copy()
            best_min_area = new_min_area
            no_improve_count = 0
        else:
            no_improve_count += 1

        # Simulated annealing acceptance
        delta = new_min_area - current_min_area
        if delta > 0 or random.random() < math.exp(delta / T):
            points = new_points
            current_min_area = new_min_area

        # Cooling
        T *= cooling_factor

        # Early stopping
        if no_improve_count > early_stopping_patience:
            break

    return best_points