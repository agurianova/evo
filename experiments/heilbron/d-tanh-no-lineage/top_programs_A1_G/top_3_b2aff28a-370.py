import random
import numpy as np
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Precompute triangle dimensions
    base = B[0] - A[0]
    height = C[1]

    # Define diverse row patterns (each sums to 11 points)
    patterns = [
        [4, 3, 3, 1],
        [3, 3, 3, 2],
        [4, 4, 2, 1],
        [5, 3, 2, 1],
        [4, 3, 2, 2],
        [3, 4, 2, 2],
        [5, 2, 2, 2],
        [3, 3, 4, 1],
        [4, 2, 3, 2],
        [3, 2, 3, 3]
    ]

    def generate_initial_grid(points_per_row, base, height):
        n_rows = len(points_per_row)
        points = []
        for i in range(n_rows):
            y = (i + 0.5) * (height / n_rows)
            width = base * (1 - y / height)
            x0 = (base - width) / 2
            spacing = width / (points_per_row[i] - 1) if points_per_row[i] > 1 else 0
            
            for j in range(points_per_row[i]):
                x = x0 + j * spacing
                # Apply larger perturbation with validation
                for _ in range(20):
                    dx = random.uniform(-0.15, 0.15)
                    dy = random.uniform(-0.15, 0.15)
                    candidate = np.array([x + dx, y + dy])
                    
                    if not is_inside_triangle([candidate], A, B, C):
                        continue
                    distinct = True
                    for p in points:
                        if np.linalg.norm(candidate - p) < 0.001:
                            distinct = False
                            break
                    if distinct:
                        points.append(candidate)
                        break
                else:
                    points.append(np.array([x, y]))
        return np.array(points)

    best_config = None
    best_min_area = -1

    for seed in range(10):
        np.random.seed(seed)
        random.seed(seed)
        
        # Select grid pattern for this seed
        points_per_row = patterns[seed % len(patterns)]
        
        # Generate and validate initial grid
        points = generate_initial_grid(points_per_row, base, height)
        if not is_inside_triangle(points, A, B, C):
            continue
        
        # Initial min area
        current_min_area = get_smallest_triangle_area(points)
        
        # Simulated annealing parameters
        T0 = 0.01
        step_size0 = 0.2
        alpha = 0.999  # Slower cooling rate for temperature
        beta = 0.9995  # Separate decay for step size (slower decay)
        num_iterations = 5000

        for iter in range(num_iterations):
            # Recompute min area and critical points
            min_area_val = float('inf')
            critical_set = set()
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        a, b, c = points[i], points[j], points[k]
                        area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        if area < min_area_val - 1e-9:
                            min_area_val = area
                            critical_set = {i, j, k}
                        elif abs(area - min_area_val) <= 1e-9:
                            critical_set.update([i, j, k])
            current_min_area = min_area_val

            # Adaptive critical point bias (70% → 30%)
            dynamic_bias = max(0.3, 0.7 - 0.4 * (iter / num_iterations))
            
            # Select points to perturb
            if critical_set and random.random() < dynamic_bias:
                num_points = random.choice([2, 3])
                if num_points > len(critical_set):
                    num_points = len(critical_set)
                indices = random.sample(list(critical_set), num_points)
            else:
                num_points = random.choice([1, 2])
                indices = random.sample(range(11), num_points)

            old_points = [points[i].copy() for i in indices]
            
            # Exponential cooling (slower decay)
            T = T0 * (alpha ** iter)
            step_size = step_size0 * (beta ** iter)  # Decoupled step size decay

            # Generate candidate move
            deltas = np.random.uniform(-step_size, step_size, size=(num_points, 2))
            new_points = points.copy()
            for i, idx in enumerate(indices):
                new_points[idx] = old_points[i] + deltas[i]
            
            if not is_inside_triangle(new_points, A, B, C):
                continue
            
            # Check distinctness
            distinct = True
            for i in range(11):
                for j in range(i+1, 11):
                    if np.linalg.norm(new_points[i] - new_points[j]) < 0.001:
                        distinct = False
                        break
                if not distinct:
                    break
            if not distinct:
                continue

            # Evaluate candidate
            new_min_area = get_smallest_triangle_area(new_points)
            if new_min_area <= 0:
                continue

            # Simulated annealing acceptance
            delta_area = new_min_area - current_min_area
            if delta_area >= 0:
                current_min_area = new_min_area
                points = new_points
            else:
                if T > 1e-9 and random.random() < math.exp(delta_area / T):
                    current_min_area = new_min_area
                    points = new_points

        # Track best configuration
        final_area = get_smallest_triangle_area(points)
        if final_area > best_min_area:
            best_min_area = final_area
            best_config = points.copy()

    return best_config