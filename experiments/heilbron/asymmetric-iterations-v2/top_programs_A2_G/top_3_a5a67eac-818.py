import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def triangle_area(a, b, c):
    return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

def flexible_initialization():
    A, B, C = get_unit_triangle()
    base = B[0] - A[0]
    height = C[1]
    M = np.array([base / 2, 0])
    
    # Predefined partitions of 11 points into 3 rows
    partitions = [(1, 3, 7), (1, 4, 6), (2, 3, 6), (2, 4, 5), (3, 4, 4)]
    n_top, n_mid, n_bottom = random.choice(partitions)
    
    # Randomized row heights within meaningful ranges
    y_top = random.uniform(0.8, 0.95) * height
    y_mid = random.uniform(0.4, 0.6) * height
    y_bottom = random.uniform(0.05, 0.2) * height
    
    points = []
    
    # Helper to compute valid x-range at given y
    def get_x_bounds(y):
        x_min = (base * y) / (2 * height)
        x_max = base - (base * y) / (2 * height)
        return x_min, x_max
    
    # Top row
    if n_top > 0:
        width_top = (height - y_top) * base / height
        x_min, x_max = get_x_bounds(y_top)
        if n_top == 1:
            x = (x_min + x_max) / 2
            points.append(np.array([x, y_top]))
        else:
            step = (x_max - x_min) / (n_top - 1)
            for i in range(n_top):
                x = x_min + i * step
                # Add 10% horizontal jitter
                jitter = random.uniform(-0.1, 0.1) * step
                x = np.clip(x + jitter, x_min, x_max)
                points.append(np.array([x, y_top]))

    # Middle row
    if n_mid > 0:
        width_mid = (height - y_mid) * base / height
        x_min, x_max = get_x_bounds(y_mid)
        if n_mid == 1:
            x = (x_min + x_max) / 2
            points.append(np.array([x, y_mid]))
        else:
            step = (x_max - x_min) / (n_mid - 1)
            for i in range(n_mid):
                x = x_min + i * step
                jitter = random.uniform(-0.1, 0.1) * step
                x = np.clip(x + jitter, x_min, x_max)
                points.append(np.array([x, y_mid]))

    # Bottom row
    if n_bottom > 0:
        width_bottom = (height - y_bottom) * base / height
        x_min, x_max = get_x_bounds(y_bottom)
        if n_bottom == 1:
            x = (x_min + x_max) / 2
            points.append(np.array([x, y_bottom]))
        else:
            step = (x_max - x_min) / (n_bottom - 1)
            for i in range(n_bottom):
                x = x_min + i * step
                jitter = random.uniform(-0.1, 0.1) * step
                x = np.clip(x + jitter, x_min, x_max)
                points.append(np.array([x, y_bottom]))

    return np.array(points)

def pilot_run(config, n=1000):
    improving_deltas = []
    worsening_deltas = []
    config_pilot = config.copy()
    
    for _ in range(n):
        current_min_area = get_smallest_triangle_area(config_pilot)
        
        # Find top 5 smallest triangles
        min_triangles = []
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = triangle_area(config_pilot[i], config_pilot[j], config_pilot[k])
                    min_triangles.append((area, i, j, k))
        min_triangles.sort(key=lambda x: x[0])
        top5_triangles = min_triangles[:5]
        
        # Generate trial move targeting top-5 triangles
        tri = random.choice(top5_triangles)
        i, j, k = tri[1], tri[2], tri[3]
        vertex = random.choice([i, j, k])
        
        # Adaptive step size based on current min_area
        step_size = 0.5 * np.sqrt(current_min_area)
        angle = random.uniform(0, 2 * np.pi)
        dx = step_size * np.cos(angle)
        dy = step_size * np.sin(angle)
        candidate = config_pilot.copy()
        candidate[vertex] += [dx, dy]

        if not is_inside_triangle(candidate, *get_unit_triangle()):
            continue
        
        new_min_area = get_smallest_triangle_area(candidate)
        delta = new_min_area - current_min_area
        
        if delta > 0:
            improving_deltas.append(delta)
        elif delta < 0:
            worsening_deltas.append(-delta)

    # Base step from improving moves
    if improving_deltas:
        base_step = np.clip(np.median(improving_deltas) * 5, 0.01, 0.1)
    else:
        base_step = 0.05

    # Initial temperature from worsening moves
    avg_worsening = np.mean(worsening_deltas) if worsening_deltas else 0.001
    initial_temp = -avg_worsening / np.log(0.8)
    return base_step, initial_temp

def simulated_annealing(initial_config, initial_temp, base_step, cooling_rate=0.9995, max_iterations=200000):
    current = initial_config.copy()
    current_min_area = get_smallest_triangle_area(current)
    temp = initial_temp
    last_improvement = 0

    for iteration in range(max_iterations):
        # Adaptive basin escape: trigger after 1000 iterations without improvement
        if iteration - last_improvement > 1000:
            candidate = current.copy()
            for i in range(11):
                angle = random.uniform(0, 2 * np.pi)
                r = 0.15 * np.sqrt(temp / initial_temp)  # Temperature-scaled step
                dx = r * np.cos(angle)
                dy = r * np.sin(angle)
                candidate[i] += [dx, dy]
            if is_inside_triangle(candidate, *get_unit_triangle()):
                current = candidate
                current_min_area = get_smallest_triangle_area(current)
                last_improvement = iteration
            continue

        current_step = base_step * np.sqrt(temp / initial_temp)

        # Find top 5 smallest triangles
        min_triangles = []
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = triangle_area(current[i], current[j], current[k])
                    min_triangles.append((area, i, j, k))
        min_triangles.sort(key=lambda x: x[0])
        top5_triangles = min_triangles[:5]

        # Adaptive probability: starts at 80% for smallest triangle, decays to 50%
        prob_smallest = 0.8 - 0.3 * (1 - temp / initial_temp)
        if random.random() < prob_smallest:
            tri = top5_triangles[0]
        else:
            tri = random.choice(top5_triangles)
        
        i, j, k = tri[1], tri[2], tri[3]
        vertex = random.choice([i, j, k])

        angle = random.uniform(0, 2 * np.pi)
        dx = current_step * np.cos(angle)
        dy = current_step * np.sin(angle)
        candidate = current.copy()
        candidate[vertex] += [dx, dy]

        if not is_inside_triangle(candidate, *get_unit_triangle()):
            continue
        
        new_min_area = get_smallest_triangle_area(candidate)
        if new_min_area <= 0:
            continue

        delta = new_min_area - current_min_area
        if delta > 0:
            current = candidate
            current_min_area = new_min_area
            last_improvement = iteration
        elif random.random() < np.exp(delta / temp):
            current = candidate
            current_min_area = new_min_area

        temp *= cooling_rate

    return current, current_min_area

def entrypoint() -> np.ndarray:
    num_starts = 30  # Increased for higher-quality resistant configurations
    best_config = None
    best_min_area = -1.0

    for _ in range(num_starts):
        config = flexible_initialization()
        base_step, initial_temp = pilot_run(config)
        improved_config, min_area = simulated_annealing(config, initial_temp, base_step)
        if min_area > best_min_area:
            best_min_area = min_area
            best_config = improved_config

    return best_config