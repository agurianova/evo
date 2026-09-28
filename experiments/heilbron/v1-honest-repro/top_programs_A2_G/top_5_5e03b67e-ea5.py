import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Generate hexagonal grid initialization
    d = 0.3  # Grid step size
    points = []
    y = 0.0
    row_index = 0
    
    # Generate grid points within bounding box
    while y < 1.3161:
        x_start = d/2 if row_index % 2 == 1 else 0.0
        x = x_start
        while x < 1.5197:
            points.append([x, y])
            x += d
        y += d * np.sqrt(3)/2
        row_index += 1

    # Filter points inside triangle and sort by y then x
    valid_points = []
    for p in points:
        if is_inside_triangle(np.array(p), A, B, C):
            valid_points.append(p)
    
    # Sort by vertical position (bottom to top) then horizontal
    valid_points = sorted(valid_points, key=lambda p: (p[1], p[0]))
    
    # Take first 11 points or fallback to parent's method if insufficient
    if len(valid_points) < 11:
        rows = [4, 3, 2, 1, 1]
        total_rows = len(rows)
        valid_points = []
        for i, num_points in enumerate(rows):
            v = (i + 0.5) / total_rows
            for j in range(num_points):
                u = (j + 0.5) / num_points * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                valid_points.append(P)
    else:
        valid_points = valid_points[:11]

    points = np.array(valid_points)

    # Apply scaled symmetry-breaking perturbations (±0.01*d)
    for i in range(11):
        perturbation = np.random.uniform(-0.01*d, 0.01*d, size=2)
        new_point = points[i] + perturbation
        if is_inside_triangle(new_point, A, B, C):
            points[i] = new_point

    # Initial quality assessment
    current_min_area = get_smallest_triangle_area(points)
    T0 = 0.1 * current_min_area  # Initial temperature

    # Local search with simulated annealing
    max_iter = 50000
    initial_step = 0.05
    decay_step = 0.9999  # Slower decay for extended exploration
    decay_temp = 0.9999

    for it in range(max_iter):
        # Temperature schedule
        T = T0 * (decay_temp ** it)
        
        # Step size schedule
        step_size = initial_step * (decay_step ** it)
        
        # Random point and direction
        idx = random.randint(0, 10)
        direction = np.random.uniform(-1, 1, 2)
        direction = direction / np.linalg.norm(direction)
        
        # Generate candidate move
        new_point = points[idx] + step_size * direction
        if not is_inside_triangle(new_point, A, B, C):
            continue

        # Evaluate new configuration
        new_points = points.copy()
        new_points[idx] = new_point
        new_min_area = get_smallest_triangle_area(new_points)
        delta = new_min_area - current_min_area

        # Simulated annealing acceptance
        if delta > 0 or random.random() < np.exp(delta / T):
            points = new_points
            current_min_area = new_min_area

    return points