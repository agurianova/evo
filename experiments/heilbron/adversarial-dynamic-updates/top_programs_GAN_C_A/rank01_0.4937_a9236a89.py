import random

from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    rows = 4
    row_points = [4, 3, 2, 2]  # Total 11 points
    points = []
    
    for i in range(rows):
        v = (i + 0.5) / rows
        num_in_row = row_points[i]
        for j in range(num_in_row):
            u = (j + 0.5) / num_in_row * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            perturbation = np.random.uniform(-0.01, 0.01, size=2)
            P_perturbed = P + perturbation
            points.append(P_perturbed)

    current = np.array(points)
    current_score = get_smallest_triangle_area(current)

    n_iterations = 1000
    step_size = 0.005
    for _ in range(n_iterations):
        idx = np.random.randint(0, 11)
        step = np.random.normal(0, step_size, size=2)
        candidate = current.copy()
        candidate[idx] += step

        if not is_inside_triangle(candidate[idx], A, B, C):
            continue

        score = get_smallest_triangle_area(candidate)
        if score > current_score:
            current = candidate
            current_score = score

    return current