import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Asymmetric 5-row grid initialization [4,3,2,1,1] with optimized vertical spacing
    rows = 5
    row_counts = [4, 3, 2, 1, 1]
    v_positions = [0.0, 0.2, 0.4, 0.7, 1.0]  # Uneven spacing to avoid grid artifacts
    best_config = None
    best_min_area = -1
    restarts = 5

    for _ in range(restarts):
        points = []
        for i in range(rows):
            v = v_positions[i]
            num_points = row_counts[i]
            row_length = 1 - v
            for j in range(num_points):
                u = (j + 0.5) * row_length / num_points
                P = (1 - u - v) * A + u * B + v * C
                
                # Increased perturbation for effective symmetry breaking
                perturbation = np.random.uniform(-0.01, 0.01, 2)
                P_perturbed = P + perturbation
                if not is_inside_triangle(P_perturbed, A, B, C):
                    P_perturbed = P
                points.append(P_perturbed)

        points = np.array(points)
        
        # Enhanced SA optimization
        current = points
        current_min = get_smallest_triangle_area(current)
        T = 0.1  # Increased initial temperature
        cooling_rate = 0.95
        iterations = 500000
        step_size = 0.1
        step_decay = (0.001 / 0.1) ** (1.0 / iterations)  # Independent geometric decay

        for _ in range(iterations):
            idx = np.random.randint(0, 11)
            displacement = np.random.uniform(-step_size, step_size, 2)
            candidate = current.copy()
            candidate[idx] += displacement

            if not is_inside_triangle(candidate[idx], A, B, C):
                continue

            new_min = get_smallest_triangle_area(candidate)

            if new_min > current_min:
                current, current_min = candidate, new_min
            else:
                delta = new_min - current_min
                if np.random.rand() < np.exp(delta / T):
                    current, current_min = candidate, new_min

            T *= cooling_rate
            step_size *= step_decay

        # Track best configuration across restarts
        if current_min > best_min_area:
            best_min_area = current_min
            best_config = current

    return best_config