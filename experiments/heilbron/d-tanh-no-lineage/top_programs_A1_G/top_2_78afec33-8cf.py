import random
import numpy as np
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Precompute triangle dimensions
    base = B[0] - A[0]  # Since flat-bottomed, A[0]=0, B[0]=base
    height = C[1]      # Height from base
    
    def generate_initial_grid():
        n_rows = 3
        points_per_row = [4, 4, 3]
        points = []
        for i in range(n_rows):
            y = (i + 0.5) * (height / n_rows)
            width = base * (1 - y / height)
            x0 = (base - width) / 2
            spacing = width / (points_per_row[i] - 1) if points_per_row[i] > 1 else 0
            
            for j in range(points_per_row[i]):
                x = x0 + j * spacing
                # Apply perturbation with validity checks
                for _ in range(10):
                    dx = random.uniform(-0.01, 0.01)
                    dy = random.uniform(-0.01, 0.01)
                    candidate = np.array([x + dx, y + dy])
                    
                    # Check inside triangle and distinctness
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
                    points.append(np.array([x, y]))  # Fallback to unperturbed
        return np.array(points)

    best_config = None
    best_min_area = -1

    for seed in range(10):
        np.random.seed(seed)
        random.seed(seed)
        
        # Generate and validate initial grid
        points = generate_initial_grid()
        if not is_inside_triangle(points, A, B, C):
            continue
        
        # Initial min area
        current_min_area = get_smallest_triangle_area(points)
        
        # Simulated annealing parameters
        T0 = 0.001
        step_size0 = 0.1
        num_iterations = 5000

        for iter in range(num_iterations):
            # Recompute min area and critical points via brute force
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

            # Select point to perturb (80% bias to critical points)
            if critical_set and random.random() < 0.8:
                idx = random.choice(list(critical_set))
            else:
                idx = random.randint(0, 10)

            old_point = points[idx].copy()
            frac = iter / num_iterations
            step_size = step_size0 * (1 - frac)
            T = T0 * (1 - frac)

            # Generate and validate candidate
            delta = np.random.uniform(-step_size, step_size, size=2)
            candidate = old_point + delta
            
            if not is_inside_triangle([candidate], A, B, C):
                continue
            
            distinct = True
            for i in range(11):
                if i == idx:
                    continue
                if np.linalg.norm(candidate - points[i]) < 0.001:
                    distinct = False
                    break
            if not distinct:
                continue

            # Evaluate candidate
            points[idx] = candidate
            new_min_area = get_smallest_triangle_area(points)
            if new_min_area <= 0:
                points[idx] = old_point
                continue

            # Simulated annealing acceptance
            delta_area = new_min_area - current_min_area
            if delta_area >= 0:
                current_min_area = new_min_area
            else:
                if T > 1e-9 and random.random() < math.exp(delta_area / T):
                    current_min_area = new_min_area
                else:
                    points[idx] = old_point

        # Track best configuration across seeds
        final_area = get_smallest_triangle_area(points)
        if final_area > best_min_area:
            best_min_area = final_area
            best_config = points.copy()

    return best_config