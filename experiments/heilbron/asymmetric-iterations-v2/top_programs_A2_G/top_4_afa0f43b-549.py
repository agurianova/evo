import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def triangle_area(a, b, c):
    return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

def generate_symmetric_points(n=11):
    A, B, C = get_unit_triangle()
    M = np.array([(A[0] + B[0]) / 2, 0])  # Midpoint of base
    
    # Generate axis point (on symmetry line x = M[0])
    y_axis = random.uniform(0, C[1])
    axis_point = np.array([M[0], y_axis])
    
    points_left = []
    while len(points_left) < 5:
        s = random.random()
        t = random.random()
        if s + t > 1:
            s = 1 - s
            t = 1 - t
        x = M[0] * (1 - s)
        y = C[1] * t
        if x >= M[0] - 1e-10:  # Avoid axis points in left half
            continue
        points_left.append(np.array([x, y]))
    
    # Mirror left points to right half
    points_right = [np.array([2*M[0] - p[0], p[1]]) for p in points_left]
    return np.array([axis_point] + points_left + points_right)

def pilot_run(config, n=1000):
    worsening_deltas = []
    config_pilot = config.copy()
    
    for _ in range(n):
        current_min_area = get_smallest_triangle_area(config_pilot)
        
        # Find smallest triangle indices
        min_area_val = float('inf')
        min_tri = None
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = triangle_area(config_pilot[i], config_pilot[j], config_pilot[k])
                    if area < min_area_val:
                        min_area_val = area
                        min_tri = (i, j, k)

        # Generate trial move
        if random.random() < 0.8:
            i = random.choice(min_tri)
            angle = random.uniform(0, 2 * np.pi)
            dx = 0.05 * np.cos(angle)
            dy = 0.05 * np.sin(angle)
            candidate = config_pilot.copy()
            candidate[i] += [dx, dy]
        else:
            i, j = random.sample(min_tri, 2)
            angle = random.uniform(0, 2 * np.pi)
            dx = 0.05 * np.cos(angle)
            dy = 0.05 * np.sin(angle)
            candidate = config_pilot.copy()
            candidate[i] += [dx, dy]
            candidate[j] -= [dx, dy]

        if not is_inside_triangle(candidate, *get_unit_triangle()):
            continue
        
        new_min_area = get_smallest_triangle_area(candidate)
        if new_min_area < current_min_area:
            worsening_deltas.append(current_min_area - new_min_area)

    # Calculate parameters
    avg_delta = np.mean(worsening_deltas) if worsening_deltas else 0.001
    initial_temp = -avg_delta / np.log(0.8)
    target_delta = -initial_temp * np.log(0.44)
    base_step = 0.05 * (target_delta / avg_delta) if avg_delta > 0 else 0.05
    return base_step, initial_temp

def simulated_annealing(initial_config, initial_temp, base_step, cooling_rate=0.9995, n_iterations=50000):
    current = initial_config.copy()
    current_min_area = get_smallest_triangle_area(current)
    temp = initial_temp

    for iteration in range(n_iterations):
        # Periodic large perturbation to escape shallow optima
        if iteration % 5000 == 0:
            candidate = current.copy()
            for i in range(11):
                angle = random.uniform(0, 2 * np.pi)
                r = 0.1
                dx = r * np.cos(angle)
                dy = r * np.sin(angle)
                candidate[i] += [dx, dy]
            if is_inside_triangle(candidate, *get_unit_triangle()):
                current = candidate
                current_min_area = get_smallest_triangle_area(current)
                temp = initial_temp  # Reset temperature
            continue

        current_step = base_step * np.sqrt(temp / initial_temp)

        # Identify smallest triangle
        min_area_val = float('inf')
        min_tri = None
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = triangle_area(current[i], current[j], current[k])
                    if area < min_area_val:
                        min_area_val = area
                        min_tri = (i, j, k)

        # Generate move targeting smallest triangle
        if random.random() < 0.8:
            i = random.choice(min_tri)
            angle = random.uniform(0, 2 * np.pi)
            dx = current_step * np.cos(angle)
            dy = current_step * np.sin(angle)
            candidate = current.copy()
            candidate[i] += [dx, dy]
        else:
            i, j = random.sample(min_tri, 2)
            angle = random.uniform(0, 2 * np.pi)
            dx = current_step * np.cos(angle)
            dy = current_step * np.sin(angle)
            candidate = current.copy()
            candidate[i] += [dx, dy]
            candidate[j] -= [dx, dy]

        if not is_inside_triangle(candidate, *get_unit_triangle()):
            continue
        
        new_min_area = get_smallest_triangle_area(candidate)
        if new_min_area <= 0:
            continue

        delta = current_min_area - new_min_area
        if new_min_area > current_min_area or random.random() < np.exp(-delta / temp):
            current = candidate
            current_min_area = new_min_area

        temp *= cooling_rate

    return current, current_min_area

def entrypoint() -> np.ndarray:
    num_starts = 100
    best_config = None
    best_min_area = -1.0

    for _ in range(num_starts):
        config = generate_symmetric_points(11)
        base_step, initial_temp = pilot_run(config)
        improved_config, min_area = simulated_annealing(config, initial_temp, base_step)
        if min_area > best_min_area:
            best_min_area = min_area
            best_config = improved_config

    return best_config