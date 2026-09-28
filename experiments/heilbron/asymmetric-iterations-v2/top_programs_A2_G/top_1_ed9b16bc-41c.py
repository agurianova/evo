import numpy as np
import random
from collections import deque
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def triangle_area(a, b, c):
    return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

def grid_symmetric_points():
    A, B, C = get_unit_triangle()
    M = np.array([(A[0] + B[0]) / 2, 0])
    tri_height = C[1]
    
    # Generate asymmetric row heights with sorted offsets
    base_offsets = [0.1, 0.5, 0.9]
    offsets = [x + random.uniform(-0.03, 0.03) for x in base_offsets]
    offsets.sort()  # Ensure valid ordering
    y_bottom = offsets[0] * tri_height
    y_mid = offsets[1] * tri_height
    y_top = offsets[2] * tri_height
    
    points = []
    
    # Top row: 1 point (centered)
    width_top = (tri_height - y_top) * (B[0] - A[0]) / tri_height
    x_top = M[0]
    points.append(np.array([x_top, y_top]))
    
    # Middle row: 3 points
    width_mid = (tri_height - y_mid) * (B[0] - A[0]) / tri_height
    step_mid = width_mid / 3  # 3 points: 2 intervals
    for i in [-1, 0, 1]:
        x = M[0] + i * step_mid
        points.append(np.array([x, y_mid]))
    
    # Bottom row: 7 points
    width_bottom = (tri_height - y_bottom) * (B[0] - A[0]) / tri_height
    step_bottom = width_bottom / 6  # 7 points: 6 intervals
    for i in [-3, -2, -1, 0, 1, 2, 3]:
        x = M[0] + i * step_bottom
        points.append(np.array([x, y_bottom]))
    
    return np.array(points)

def pilot_run(config, n=1000):
    improving_deltas = []
    worsening_deltas = []
    config_pilot = config.copy()
    
    # Initialize step size based on current min_area
    current_min_area = get_smallest_triangle_area(config_pilot)
    step_size = 0.5 * np.sqrt(current_min_area)
    step_size = np.clip(step_size, 0.01, 0.1)

    for _ in range(n):
        current_min_area = get_smallest_triangle_area(config_pilot)
        
        # Find smallest triangles
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
        
        angle = random.uniform(0, 2 * np.pi)
        dx = step_size * np.cos(angle)
        dy = step_size * np.sin(angle)
        candidate = config_pilot.copy()
        candidate[vertex] += [dx, dy]

        if not is_inside_triangle(candidate, *get_unit_triangle()):
            continue
        
        new_min_area = get_smallest_triangle_area(candidate)
        if new_min_area <= 0:
            continue
            
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

        # Adaptive triangle selection parameters
        top_k = max(3, min(7, 3 + int(4 * (temp / initial_temp))))
        smallest_prob = 0.8 - 0.3 * (1 - temp / initial_temp)
        smallest_prob = max(0.5, min(0.8, smallest_prob))

        # Find smallest triangles (up to top_k)
        min_triangles = []
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = triangle_area(current[i], current[j], current[k])
                    min_triangles.append((area, i, j, k))
        min_triangles.sort(key=lambda x: x[0])
        top_triangles = min_triangles[:top_k]

        # Select triangle based on adaptive probability
        if random.random() < smallest_prob:
            tri = top_triangles[0]
        else:
            tri = random.choice(top_triangles)
        
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
    num_starts = 30  # Increased from 20 to 30 for better resistance-quality balance
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