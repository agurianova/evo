import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Asymmetric row counts for 5 rows [4,3,2,1,1] summing to 11 points
    row_counts = [4, 3, 2, 1, 1]
    rows = len(row_counts)
    points = []
    
    for row_idx, num_points in enumerate(row_counts):
        v = (row_idx + 0.5) / rows
        for i in range(num_points):
            u = (i + 0.5) / num_points * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            # Row-dependent perturbation: larger magnitude for bottom rows
            magnitude = 0.01 * (rows - row_idx) / rows
            perturbation = np.random.uniform(-magnitude, magnitude, size=2)
            P = P + perturbation
            points.append(P)

    current_points = np.array(points)
    current_min_area = get_smallest_triangle_area(current_points)
    
    # Local search parameters
    initial_step = 0.01
    step = initial_step
    max_iterations = 500
    
    for _ in range(max_iterations):
        improved = False
        for i in range(11):
            old_point = current_points[i].copy()
            directions = np.array([
                [step, 0], [-step, 0],
                [0, step], [0, -step],
                [step, step], [step, -step],
                [-step, step], [-step, -step]
            ])
            best_new_point = old_point
            best_new_min_area = current_min_area
            
            for d in directions:
                new_point = old_point + d
                if not is_inside_triangle(new_point, A, B, C):
                    continue
                
                candidate = current_points.copy()
                candidate[i] = new_point
                new_min_area = get_smallest_triangle_area(candidate)
                
                if new_min_area > best_new_min_area:
                    best_new_min_area = new_min_area
                    best_new_point = new_point

            if best_new_min_area > current_min_area:
                current_points[i] = best_new_point
                current_min_area = best_new_min_area
                improved = True

        if not improved:
            step *= 0.9
            if step < 1e-5:
                break

    return current_points