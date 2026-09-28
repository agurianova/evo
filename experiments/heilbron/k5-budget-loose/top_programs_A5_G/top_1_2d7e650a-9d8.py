import math
import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint():
    tri = get_unit_triangle()
    A, B, C = tri
    base = np.linalg.norm(B - A)

    # Symmetric initialization using barycentric coordinates (avoids collinearity)
    points = [
        A,  # Vertex
        B,  # Vertex
        C,  # Vertex
        # Group 1: (0.2, 0.2, 0.6) permutations
        0.2*A + 0.2*B + 0.6*C,
        0.2*A + 0.6*B + 0.2*C,
        0.6*A + 0.2*B + 0.2*C,
        # Group 2: (0.3, 0.3, 0.4) permutations
        0.3*A + 0.3*B + 0.4*C,
        0.3*A + 0.4*B + 0.3*C,
        0.4*A + 0.3*B + 0.3*C,
        # Group 3: (0.4, 0.4, 0.2) variants
        0.4*A + 0.4*B + 0.2*C,
        0.4*A + 0.2*B + 0.4*C
    ]
    points = np.array(points)

    # Initial min_area evaluation
    current_min_area = get_smallest_triangle_area(points)

    # Simulated annealing parameters
    T0 = 0.01
    T = T0
    cooling_rate = 0.9999
    n_iterations = 100000

    for _ in range(n_iterations):
        # Adaptive step size with occasional large jumps
        if random.random() < 0.05:
            step_size = 0.3 * base  # Large jump for basin crossing
        else:
            step_size = 0.2 * base * (T / T0)  # Standard adaptive step
        
        # Randomly perturb one point
        idx = random.randint(0, 10)
        dx = random.uniform(-step_size, step_size)
        dy = random.uniform(-step_size, step_size)
        new_point = points[idx] + np.array([dx, dy])

        # Ensure new point stays inside triangle
        if not is_inside_triangle(new_point, A, B, C):
            continue

        # Evaluate new configuration
        new_points = points.copy()
        new_points[idx] = new_point
        new_min_area = get_smallest_triangle_area(new_points)

        # Metropolis acceptance criterion
        delta = new_min_area - current_min_area
        if delta >= 0 or random.random() < math.exp(delta / T):
            points = new_points
            current_min_area = new_min_area

        # Cool down
        T *= cooling_rate

    # Local search phase to ensure local optimality
    local_search_step = 0.01 * base
    max_passes = 10
    for _ in range(max_passes):
        improved = False
        for i in range(11):
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    new_point = points[i] + np.array([dx, dy]) * local_search_step
                    if not is_inside_triangle(new_point, A, B, C):
                        continue
                    new_points = points.copy()
                    new_points[i] = new_point
                    new_min_area = get_smallest_triangle_area(new_points)
                    if new_min_area > current_min_area:
                        points = new_points
                        current_min_area = new_min_area
                        improved = True
                        break
                if improved:
                    break
            if improved:
                break
        if not improved:
            break

    return points