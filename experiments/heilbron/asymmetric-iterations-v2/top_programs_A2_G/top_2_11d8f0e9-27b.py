import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def triangle_area(a, b, c):
    return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

def grid_symmetric_points():
    A, B, C = get_unit_triangle()
    M = np.array([(A[0] + B[0]) / 2, 0])
    H = C[1]
    base_width = B[0]
    epsilon = 0.01
    points = []

    # Randomize row structure
    n_points = 11
    k_min, k_max = 2, 4  # Number of rows between 2 and 4
    k = random.randint(k_min, k_max)
    
    # Generate random partition of 11 points into k rows
    rows = []
    remaining = n_points
    for i in range(k-1):
        low = max(1, remaining - 7*(k-i-1))
        high = min(7, remaining - 1*(k-i-1))
        num = random.randint(low, high)
        rows.append(num)
        remaining -= num
    rows.append(remaining)

    # Generate random y-levels in [0.1, 0.9] relative to H
    y_rel = [random.uniform(0.1, 0.9) for _ in range(k)]
    y_rel.sort(reverse=True)  # Top row first
    y_levels = [y * H for y in y_rel]

    # Place points in each row
    for i, (num, y) in enumerate(zip(rows, y_levels)):
        half_width = (base_width / 2) * (H - y) / H
        if num > 1:
            spacing = (2 * half_width * 0.9) / (num - 1)
            x_start = M[0] - half_width * 0.9
            xs = [x_start + j * spacing for j in range(num)]
        else:
            xs = [M[0]]
        
        for x in xs:
            points.append([x, y - epsilon * (x - M[0])**2])

    return np.array(points)

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

def simulated_annealing(initial_config, initial_temp, base_step, cooling_rate=0.9995, n_iterations=200000):
    current = initial_config.copy()
    current_min_area = get_smallest_triangle_area(current)
    temp = initial_temp
    stagnation_counter = 0

    for iteration in range(n_iterations):
        # Identify smallest triangles (top 5)
        triangles = []
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = triangle_area(current[i], current[j], current[k])
                    triangles.append((area, i, j, k))
        triangles.sort(key=lambda x: x[0])
        top5 = triangles[:5]

        # 30% chance to use top-5 triangles instead of only smallest
        if random.random() < 0.3:
            _, i, j, k = random.choice(top5)
            min_tri = (i, j, k)
        else:
            _, i, j, k = top5[0]
            min_tri = (i, j, k)

        current_step = base_step * np.sqrt(temp / initial_temp)

        # Generate move with 60% one-point, 20% two-point, 20% three-point
        r = random.random()
        if r < 0.6:
            # Move one point
            i = random.choice(min_tri)
            angle = random.uniform(0, 2 * np.pi)
            dx = current_step * np.cos(angle)
            dy = current_step * np.sin(angle)
            candidate = current.copy()
            candidate[i] += [dx, dy]
        elif r < 0.8:
            # Move two points (push-pull)
            i, j = random.sample(min_tri, 2)
            angle = random.uniform(0, 2 * np.pi)
            dx = current_step * np.cos(angle)
            dy = current_step * np.sin(angle)
            candidate = current.copy()
            candidate[i] += [dx, dy]
            candidate[j] -= [dx, dy]
        else:
            # Move all three points away from centroid
            candidate = current.copy()
            centroid = (current[i] + current[j] + current[k]) / 3.0
            for idx in min_tri:
                vec = current[idx] - centroid
                norm = np.linalg.norm(vec)
                if norm > 1e-5:
                    vec = vec / norm
                else:
                    angle = random.uniform(0, 2 * np.pi)
                    vec = np.array([np.cos(angle), np.sin(angle)])
                candidate[idx] += current_step * vec

        if not is_inside_triangle(candidate, *get_unit_triangle()):
            continue
        
        new_min_area = get_smallest_triangle_area(candidate)
        if new_min_area <= 0:
            continue

        delta = current_min_area - new_min_area
        improved = new_min_area > current_min_area
        
        if improved or random.random() < np.exp(-delta / temp):
            current = candidate
            current_min_area = new_min_area
            stagnation_counter = 0
        else:
            stagnation_counter += 1

        # Stagnation-triggered basin escape with adaptive radius
        if stagnation_counter > 1000:
            extra = stagnation_counter - 1000
            radius = 0.1 + 0.0001 * extra
            radius = min(radius, 0.5)  # Cap at 0.5

            candidate = current.copy()
            for idx in range(11):
                angle = random.uniform(0, 2 * np.pi)
                dx = radius * np.cos(angle)
                dy = radius * np.sin(angle)
                candidate[idx] += [dx, dy]
            if is_inside_triangle(candidate, *get_unit_triangle()):
                current = candidate
                current_min_area = get_smallest_triangle_area(current)
                temp = initial_temp
            stagnation_counter = 0

        temp *= cooling_rate

    return current, current_min_area

def entrypoint() -> np.ndarray:
    num_starts = 20
    best_config = None
    best_min_area = -1.0

    for _ in range(num_starts):
        config = grid_symmetric_points()
        base_step, initial_temp = pilot_run(config)
        improved_config, min_area = simulated_annealing(config, initial_temp, base_step)
        if min_area > best_min_area:
            best_min_area = min_area
            best_config = improved_config

    return best_config