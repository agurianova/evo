import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

# Triangle parameters for symmetry
AXIS_X = 0.7598

def create_symmetric_points(base_points):
    """Create full 11-point configuration from 6 base points (1 axis + 5 left)"""
    axis_point = base_points[0]
    left_points = base_points[1:]
    
    # Ensure axis point stays on symmetry axis
    axis_point[0] = AXIS_X
    
    # Create symmetric right points
    right_points = np.array([
        [2*AXIS_X - p[0], p[1]] 
        for p in left_points
    ])
    
    return np.vstack([axis_point, left_points, right_points])

def is_valid_symmetric_configuration(base_points, A, B, C):
    """Check if base points generate valid full configuration"""
    full_points = create_symmetric_points(base_points)
    
    # Check all points are distinct
    for i in range(len(full_points)):
        for j in range(i+1, len(full_points)):
            if np.linalg.norm(full_points[i] - full_points[j]) < 1e-5:
                return False
    
    # Check all points inside triangle
    return is_inside_triangle(full_points, A, B, C)

def optimize_chain(seed):
    np.random.seed(seed)
    A, B, C = get_unit_triangle()

    # Generate initial symmetric configuration (6 base points: 1 axis + 5 left)
    base_points = []
    
    # Axis point (x=AXIS_X)
    while len(base_points) < 1:
        a = np.random.rand()
        b = np.random.rand() * (1 - a)
        c = 1 - a - b
        x = a * A[0] + b * B[0] + c * C[0]
        y = a * A[1] + b * B[1] + c * C[1]
        # Force to symmetry axis
        p = np.array([AXIS_X, y])
        
        if is_inside_triangle(p, A, B, C):
            base_points.append(p)

    # Left-side points (x < AXIS_X)
    while len(base_points) < 6:
        a = np.random.rand()
        b = np.random.rand() * (1 - a)
        c = 1 - a - b
        x = a * A[0] + b * B[0] + c * C[0]
        y = a * A[1] + b * B[1] + c * C[1]
        p = np.array([x, y])

        # Only keep if left of axis and distinct
        if x >= AXIS_X:
            continue
            
        valid = True
        for q in base_points:
            if np.linalg.norm(p - q) < 1e-5:
                valid = False
                break
        
        if valid and is_inside_triangle(p, A, B, C):
            base_points.append(p)

    base_points = np.array(base_points)
    current = create_symmetric_points(base_points)
    current_min_area = get_smallest_triangle_area(current)

    # Enhanced simulated annealing parameters
    T = 0.1  # Increased from 0.001
    cooling_rate = 0.995
    iterations = 100000  # Increased from 20,000

    for i in range(iterations):
        # Choose which base point to move (0=axis, 1-5=left)
        idx = np.random.randint(0, 6)
        old_base_point = base_points[idx].copy()

        # Generate a temperature-scaled random step (adaptive step size)
        angle = np.random.uniform(0, 2 * np.pi)
        r = np.random.uniform(0, 0.1 * T)  # Step size scales with temperature
        dx = r * np.cos(angle)
        dy = r * np.sin(angle)
        new_base_point = old_base_point + np.array([dx, dy])

        # Special constraints for different point types
        if idx == 0:  # Axis point
            new_base_point[0] = AXIS_X  # Must stay on axis
        else:  # Left-side point
            if new_base_point[0] >= AXIS_X:
                # Reflect back to left side if crossed axis
                new_base_point[0] = 2 * AXIS_X - new_base_point[0]

        # Check validity of new configuration
        base_points[idx] = new_base_point
        if not is_valid_symmetric_configuration(base_points, A, B, C):
            base_points[idx] = old_base_point
            continue

        candidate = create_symmetric_points(base_points)
        new_min_area = get_smallest_triangle_area(candidate)

        # Skip if degenerate
        if new_min_area <= 0:
            base_points[idx] = old_base_point
            continue

        # Acceptance criterion
        if new_min_area > current_min_area:
            current = candidate
            current_min_area = new_min_area
        else:
            delta = new_min_area - current_min_area
            if np.random.rand() < np.exp(delta / T):
                current = candidate
                current_min_area = new_min_area
            else:
                base_points[idx] = old_base_point

        # Cool down
        T *= cooling_rate
        if T < 1e-6:
            break

    # Final hill-climbing to ensure local optimality
    improved = True
    while improved:
        improved = False
        for idx in range(6):
            old_base_point = base_points[idx].copy()

            # Try small deterministic steps in multiple directions
            for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
                r = 0.001
                dx = r * np.cos(angle)
                dy = r * np.sin(angle)
                new_base_point = old_base_point + np.array([dx, dy])

                if idx == 0:
                    new_base_point[0] = AXIS_X
                else:
                    if new_base_point[0] >= AXIS_X:
                        new_base_point[0] = 2 * AXIS_X - new_base_point[0]

                base_points[idx] = new_base_point
                if not is_valid_symmetric_configuration(base_points, A, B, C):
                    base_points[idx] = old_base_point
                    continue

                candidate = create_symmetric_points(base_points)
                new_min_area = get_smallest_triangle_area(candidate)

                if new_min_area > current_min_area:
                    current = candidate
                    current_min_area = new_min_area
                    improved = True
                    break

                base_points[idx] = old_base_point

    return current, current_min_area

def entrypoint() -> np.ndarray:
    best_config = None
    best_min_area = -1

    # Multi-start approach with different seeds
    for seed in range(5):
        config, min_area = optimize_chain(seed)
        if min_area > best_min_area:
            best_config = config
            best_min_area = min_area

    return best_config