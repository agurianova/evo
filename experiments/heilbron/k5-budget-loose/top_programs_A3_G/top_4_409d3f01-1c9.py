import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)


def entrypoint() -> np.ndarray:
    # Get triangle vertices
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate initial configuration (5-row grid as in parent)
    points = []
    rows = 5
    count = 0
    for row in range(rows):
        num_points = rows - row
        v = (row + 0.5) / rows
        for i in range(num_points):
            if count >= 11:
                break
            u = (i + 0.5) / num_points * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            points.append(P)
            count += 1
        if count >= 11:
            break
    current_config = np.array(points)
    
    # Initialize optimization parameters
    iterations = 10000
    initial_temp = 0.001
    cooling_rate = 0.999
    step_size = 0.05
    
    # Evaluate initial configuration
    current_min_area = get_smallest_triangle_area(current_config)
    best_config = current_config.copy()
    best_min_area = current_min_area
    temperature = initial_temp
    
    # Simulated annealing
    for _ in range(iterations):
        # Select random point to perturb
        idx = np.random.randint(0, 11)
        
        # Generate random perturbation
        dx = np.random.uniform(-step_size, step_size)
        dy = np.random.uniform(-step_size, step_size)
        new_point = current_config[idx] + np.array([dx, dy])
        
        # Check if new point is inside triangle
        if not is_inside_triangle(new_point, A, B, C):
            continue
        
        # Create new configuration
        new_config = current_config.copy()
        new_config[idx] = new_point
        
        # Evaluate new configuration
        new_min_area = get_smallest_triangle_area(new_config)
        
        # Acceptance criteria
        delta = new_min_area - current_min_area
        if delta > 0 or np.random.rand() < np.exp(delta / temperature):
            current_config = new_config
            current_min_area = new_min_area
            
            # Update best configuration
            if new_min_area > best_min_area:
                best_config = new_config.copy()
                best_min_area = new_min_area
        
        # Cool down
        temperature *= cooling_rate
    
    return best_config