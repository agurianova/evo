import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate initial grid with asymmetric row pattern
    row_counts = [4, 3, 2, 1, 1]  # Total 11 points
    points = []
    for row, num_points in enumerate(row_counts):
        v = (row + 0.5) / len(row_counts)
        for i in range(num_points):
            u = (i + 0.5) / num_points * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            perturbation = np.random.uniform(-0.01, 0.01, size=2)
            P = P + perturbation
            points.append(P)
    
    current_points = np.array(points)
    current_min_area = get_smallest_triangle_area(current_points)

    # Local search parameters
    max_iter = 50
    step = 0.01
    min_step = 1e-5

    for _ in range(max_iter):
        improved = False
        for i in range(len(current_points)):
            best_point = current_points[i].copy()
            best_min_area = current_min_area
            
            # Evaluate 8 movement directions
            directions = [
                (step, 0), (-step, 0), (0, step), (0, -step),
                (step, step), (step, -step), (-step, step), (-step, -step)
            ]
            
            for dx, dy in directions:
                candidate = current_points[i] + np.array([dx, dy])
                if not is_inside_triangle(candidate, A, B, C):
                    continue
                
                new_points = current_points.copy()
                new_points[i] = candidate
                new_min_area = get_smallest_triangle_area(new_points)
                
                if new_min_area > best_min_area:
                    best_min_area = new_min_area
                    best_point = candidate

            if best_min_area > current_min_area:
                current_points[i] = best_point
                current_min_area = best_min_area
                improved = True

        # Reduce step size if no improvement
        if not improved:
            step *= 0.9
            if step < min_step:
                break

    return current_points