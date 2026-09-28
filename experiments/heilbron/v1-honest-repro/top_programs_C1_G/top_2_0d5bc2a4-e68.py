import random

from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate grid with 4 rows: [4, 3, 2, 2] points
    rows = [4, 3, 2, 2]
    total_rows = len(rows)
    points = []
    for i_row, num_points in enumerate(rows):
        v = (i_row + 0.5) / total_rows
        for i in range(num_points):
            u = (i + 0.5) / num_points * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            points.append(P)
    points = np.array(points)
    
    # Add initial perturbation to break collinearity (larger magnitude than parent)
    perturbation = np.random.uniform(-0.01, 0.01, size=points.shape)
    points += perturbation

    # Local search to maximize minimum triangle area
    step_size = 0.01
    min_step = 1e-5
    max_iter = 1000
    current_min = get_smallest_triangle_area(points)

    for it in range(max_iter):
        order = np.random.permutation(len(points))
        improved = False
        for i in order:
            original_point = points[i].copy()
            best_point = original_point
            best_min = current_min

            # Try 8 directions around current point
            for dx in [-step_size, 0, step_size]:
                for dy in [-step_size, 0, step_size]:
                    if dx == 0 and dy == 0:
                        continue
                    candidate = original_point + np.array([dx, dy])
                    if not is_inside_triangle(candidate, A, B, C):
                        continue
                    
                    # Evaluate candidate
                    points[i] = candidate
                    new_min = get_smallest_triangle_area(points)
                    
                    if new_min > best_min:
                        best_min = new_min
                        best_point = candidate
                    
                    # Revert to original for next candidate
                    points[i] = original_point

            # Update point if improvement found
            if not np.array_equal(best_point, original_point):
                points[i] = best_point
                current_min = best_min
                improved = True

        # Reduce step size if no improvement
        if not improved:
            step_size *= 0.9
            if step_size < min_step:
                break

    return points