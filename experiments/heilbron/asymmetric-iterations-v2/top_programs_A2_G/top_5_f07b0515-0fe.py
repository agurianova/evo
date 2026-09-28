import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    def generate_lattice_points(n=11):
        A, B, C = get_unit_triangle()
        m = 4  # For 10 lattice points
        points = []
        
        # Generate 10 triangular lattice points
        for i in range(0, m):
            for j in range(0, m - i):
                u = i / (m - 1)
                v = j / (m - 1)
                w = 1 - u - v
                point = u * A + v * B + w * C
                points.append(point)
        
        # Add centroid as 11th point
        centroid = (A + B + C) / 3.0
        points.append(centroid)
        
        # Apply small perturbations while maintaining validity
        perturbed_points = []
        for p in points:
            for _ in range(10):  # Max 10 attempts per point
                dx = random.uniform(-0.01, 0.01)
                dy = random.uniform(-0.01, 0.01)
                candidate = p + np.array([dx, dy])
                if is_inside_triangle(candidate, A, B, C):
                    perturbed_points.append(candidate)
                    break
            else:
                perturbed_points.append(p)  # Fallback to original
        return np.array(perturbed_points)

    def simulated_annealing(initial_config, initial_temp=0.005, cooling_rate=0.9995, n_iterations=50000, step=0.01):
        current = initial_config.copy()
        current_min_area = get_smallest_triangle_area(current)
        temp = initial_temp

        for _ in range(n_iterations):
            # 50% chance for single-point move, 50% for two-point symmetric move
            if random.random() < 0.5:
                # Single-point perturbation
                i = np.random.randint(0, 11)
                angle = np.random.uniform(0, 2 * np.pi)
                dx = step * np.cos(angle)
                dy = step * np.sin(angle)
                candidate = current.copy()
                candidate[i] += [dx, dy]
            else:
                # Two-point symmetric perturbation
                i, j = np.random.choice(11, 2, replace=False)
                angle = np.random.uniform(0, 2 * np.pi)
                dx = step * np.cos(angle)
                dy = step * np.sin(angle)
                candidate = current.copy()
                candidate[i] += [dx, dy]
                candidate[j] -= [dx, dy]

            # Validate candidate configuration
            if not is_inside_triangle(candidate, *get_unit_triangle()):
                continue
            new_min_area = get_smallest_triangle_area(candidate)
            if new_min_area <= 0:  # Ensures distinctness and non-degeneracy
                continue

            # Acceptance logic
            if new_min_area > current_min_area:
                current = candidate
                current_min_area = new_min_area
            else:
                delta = current_min_area - new_min_area
                if random.random() < np.exp(-delta / temp):
                    current = candidate
                    current_min_area = new_min_area

            # Cool temperature
            temp *= cooling_rate

        return current, current_min_area

    num_starts = 100
    best_config = None
    best_min_area = -1.0

    for _ in range(num_starts):
        config = generate_lattice_points(11)
        improved_config, min_area = simulated_annealing(config)
        if min_area > best_min_area:
            best_min_area = min_area
            best_config = improved_config

    return best_config