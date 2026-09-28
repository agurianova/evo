import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)


def generate_random_valid_config(A, B, C):
    while True:
        points = []
        for _ in range(11):
            u = np.random.random()
            v = np.random.random() * (1 - u)
            w = 1 - u - v
            P = w * A + u * B + v * C
            points.append(P)
        points = np.array(points)
        
        # Check distinctness
        min_dist = float('inf')
        for i in range(11):
            for j in range(i+1, 11):
                d = np.linalg.norm(points[i] - points[j])
                if d < min_dist:
                    min_dist = d
        if min_dist < 1e-5:
            continue
        
        # Check non-degeneracy
        min_area = get_smallest_triangle_area(points)
        if min_area < 1e-10:
            continue
        
        return points

def hill_climb(config, A, B, C, max_iterations, step_size_initial, step_size_min, decay, patience):
    current = config.copy()
    current_min_area = get_smallest_triangle_area(current)
    step_size = step_size_initial
    no_improve_count = 0

    for _ in range(max_iterations):
        idx = np.random.randint(0, 11)
        direction = np.random.uniform(-1, 1, size=2)
        direction = direction / np.linalg.norm(direction)
        step = direction * step_size
        new_point = current[idx] + step

        # Check if inside triangle
        if not is_inside_triangle(new_point, A, B, C):
            no_improve_count += 1
            if no_improve_count >= patience:
                break
            continue

        # Check distinctness
        too_close = False
        for j in range(11):
            if j == idx:
                continue
            if np.linalg.norm(new_point - current[j]) < 1e-5:
                too_close = True
                break
        if too_close:
            no_improve_count += 1
            if no_improve_count >= patience:
                break
            continue

        # Evaluate new configuration
        new_config = current.copy()
        new_config[idx] = new_point
        new_min_area = get_smallest_triangle_area(new_config)

        # Check non-degeneracy
        if new_min_area < 1e-10:
            no_improve_count += 1
            if no_improve_count >= patience:
                break
            continue

        # Accept improvement
        if new_min_area > current_min_area:
            current = new_config
            current_min_area = new_min_area
            no_improve_count = 0
        else:
            no_improve_count += 1

        # Step decay
        step_size = max(step_size_min, step_size * decay)

        # Termination check
        if no_improve_count >= patience:
            break

    return current, current_min_area

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    num_restarts = 5
    max_iterations = 10000
    step_size_initial = 0.1
    step_size_min = 1e-5
    decay = 0.999
    patience = 1000
    
    best_config = None
    best_min_area = -1
    
    for _ in range(num_restarts):
        config = generate_random_valid_config(A, B, C)
        config, min_area = hill_climb(
            config, A, B, C,
            max_iterations,
            step_size_initial,
            step_size_min,
            decay,
            patience
        )
        if min_area > best_min_area:
            best_config = config
            best_min_area = min_area

    return best_config