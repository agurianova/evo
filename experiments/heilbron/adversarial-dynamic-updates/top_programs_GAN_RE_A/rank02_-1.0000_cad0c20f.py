import random

from helper import get_unit_triangle
import numpy as np

np.random.seed(123)
random.seed(123)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    points = []
    row_counts = [3, 3, 2, 2, 1]
    num_rows = len(row_counts)
    r = 1.5  # Geometric progression ratio

    for row_index, num_points in enumerate(row_counts):
        v = (row_index + 0.5) / num_rows
        for i in range(num_points):
            if num_points == 1:
                u = (1 - v) * 0.5
            else:
                numerator = r**i - 1
                denominator = r**(num_points - 1) - 1
                u = (1 - v) * numerator / denominator

            P = (1 - u - v) * A + u * B + v * C
            perturbation = np.random.uniform(-0.01, 0.01, size=2)
            P = P + perturbation
            points.append(P)

    return np.array(points)