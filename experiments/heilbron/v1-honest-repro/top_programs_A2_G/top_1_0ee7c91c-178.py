import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(123)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    S = B[0] - A[0]
    H = C[1]

    # Hexagonal grid initialization with 11 points (4,3,2,1,1 rows)
    d = (2.0 / 9.0) * S * 0.95
    h = (np.sqrt(3) / 2) * d
    rows = [4, 3, 2, 1, 1]

    points = []
    for i, num_points in enumerate(rows):
        y = h / 2 + i * h
        row_offset = (d / 2) if (i % 2 == 1) else 0.0
        total_width = (num_points - 1) * d
        start_x = (S - total_width) / 2.0 + row_offset
        for j in range(num_points):
            x = start_x + j * d
            points.append([x, y])
    
    points = np.array(points)
    # Small asymmetric perturbation to break symmetry
    perturbation = np.random.uniform(-0.01 * d, 0.01 * d, size=(11, 2))
    points += perturbation

    # Simulated annealing optimization
    current_min_area = get_smallest_triangle_area(points)
    max_iter = 50000
    initial_step = 0.05
    step_decay = 0.9999
    initial_temp = 0.001
    temp_decay = 0.9995
    T = initial_temp

    for it in range(max_iter):
        step_size = initial_step * (step_decay ** it)
        idx = np.random.randint(0, 11)
        direction = np.random.uniform(-1, 1, 2)
        direction = direction / np.linalg.norm(direction)
        new_point = points[idx] + step_size * direction

        if not is_inside_triangle(new_point, A, B, C):
            continue

        new_points = points.copy()
        new_points[idx] = new_point
        new_min_area = get_smallest_triangle_area(new_points)
        delta = new_min_area - current_min_area

        # Accept if improvement or probabilistically based on temperature
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            points = new_points
            current_min_area = new_min_area

        T = T * temp_decay

    return points