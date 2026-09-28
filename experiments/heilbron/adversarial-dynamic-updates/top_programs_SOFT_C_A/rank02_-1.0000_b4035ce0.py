import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Asymmetric initial placement (breaks grid symmetry)
    rows = [4, 3, 2, 1, 1]  # Point counts per row (base to top)
    v_positions = [0.0, 0.2, 0.45, 0.7, 0.95]  # Non-uniform vertical spacing
    offsets = [0.2, 0.1, 0.3, 0.0, 0.4]  # Horizontal symmetry-breaking offsets

    points = []
    for i, (num_points, v, offset) in enumerate(zip(rows, v_positions, offsets)):
        for j in range(num_points):
            u = ((j + offset) / num_points) * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            points.append(P)
    
    points = np.array(points)
    current_min_area = get_smallest_triangle_area(points)
    n_points = len(points)
    
    # Local search to maximize min_area (resistance enhancement)
    max_passes = 10
    step_size = 0.01
    min_step = 1e-5
    directions = np.array([(step_size, 0), (-step_size, 0), (0, step_size), (0, -step_size)])

    for _ in range(max_passes):
        improved = False
        for i in range(n_points):
            for d in directions:
                new_point = points[i] + d
                
                # Validity checks
                if not is_inside_triangle(new_point, A, B, C):
                    continue
                if np.any(np.linalg.norm(points - new_point, axis=1) < 1e-5):
                    continue

                # Evaluate improvement
                new_points = points.copy()
                new_points[i] = new_point
                new_min_area = get_smallest_triangle_area(new_points)
                
                if new_min_area > current_min_area + 1e-9:
                    points = new_points
                    current_min_area = new_min_area
                    improved = True
        
        # Adaptive step reduction
        if not improved:
            step_size *= 0.5
            directions = directions * 0.5
            if step_size < min_step:
                break

    return points