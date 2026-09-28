import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(123)
random.seed(123)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()

    # Multi-start initialization with randomized grid patterns
    best_initial_points = None
    best_initial_min_area = -1
    
    for _ in range(50):  # Increased from 10 to 50
        # Randomize grid structure
        num_rows = random.randint(3, 5)
        # Distribute 11 points across rows (minimum 1 per row)
        points_per_row = [1] * num_rows
        remaining = 11 - num_rows
        for _ in range(remaining):
            idx = random.randint(0, num_rows - 1)
            points_per_row[idx] += 1
        
        # Generate sorted v_vals in (0.05, 0.95)
        v_vals = np.sort(np.random.uniform(0.05, 0.95, num_rows))
        
        points = []
        valid_config = True
        
        for i in range(num_rows):
            k = points_per_row[i]
            v = v_vals[i]
            for j in range(k):
                u = (j + 1) / (k + 1) * (1 - v)
                P0 = (1 - u - v) * A + u * B + v * C
                
                # Generate valid point with larger perturbation (±0.1 instead of ±0.05)
                for attempt in range(100):
                    perturbation = np.random.uniform(-0.1, 0.1, size=2)
                    P = P0 + perturbation
                    if is_inside_triangle(P, A, B, C):
                        points.append(P)
                        break
                else:
                    points.append(P0)
                    
        points = np.array(points)
        min_area = get_smallest_triangle_area(points)
        
        # Skip degenerate configurations
        if min_area < 0.01:
            continue
            
        if min_area > best_initial_min_area:
            best_initial_min_area = min_area
            best_initial_points = points

    # If all initializations degenerate, use last config (shouldn't happen)
    if best_initial_points is None:
        best_initial_points = points
        
    points = best_initial_points
    current_min_area = best_initial_min_area
    n_points = len(points)
    
    # Simulated annealing with improved parameters
    T = 0.1  # Increased from 0.01
    total_steps = 10000
    step_size = 0.05  # Initial step size
    no_improve_count = 0

    for step in range(total_steps):
        idx = random.randint(0, n_points - 1)
        direction = np.random.uniform(-1, 1, size=2)
        direction = direction / np.linalg.norm(direction)
        
        new_point = points[idx] + step_size * direction

        if not is_inside_triangle(new_point, A, B, C):
            # Update step_size and T for next iteration
            T *= 0.999
            step_size *= 0.9999
            continue

        new_points = points.copy()
        new_points[idx] = new_point
        new_min_area = get_smallest_triangle_area(new_points)

        # Always accept improvements
        if new_min_area > current_min_area:
            points = new_points
            current_min_area = new_min_area
            no_improve_count = 0
        else:
            # Simulated annealing acceptance
            delta = new_min_area - current_min_area
            if random.random() < np.exp(delta / T):
                points = new_points
                current_min_area = new_min_area
                no_improve_count = 0
            else:
                no_improve_count += 1

        # Cooling and step size decay
        T *= 0.999
        step_size *= 0.9999

        # Early stopping (increased threshold)
        if no_improve_count > 2000:  # Increased from 1000
            break

    return points