import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import itertools

# Constants for the unit-area equilateral triangle
TRIANGLE_BASE = 1.5197
TRIANGLE_HEIGHT = 1.3161

# Expanded pattern set based on Heilbronn literature and known records for n=11
INIT_PATTERNS = [
    (5, 4, 2, 0),  # Original 5-4-2 pattern
    (6, 3, 2, 0),  # Original 6-3-2 pattern
    (4, 4, 3, 0),  # Original 4-4-3 pattern
    (7, 3, 1, 0),  # Original 7-3-1 pattern
    (5, 5, 1, 0),  # Original 5-5-1 pattern
    (5, 3, 3, 0),  # Literature-suggested 5-3-3 pattern
    (4, 3, 4, 0),  # Literature-suggested 4-3-4 pattern
    (3, 5, 3, 0),  # Literature-suggested 3-5-3 pattern
    (3, 4, 4, 0),  # Alternative asymmetric pattern
]

# Known good configurations for n=11 from Heilbronn literature
LITERATURE_CONFIGS = [
    # Format: [(x1,y1), (x2,y2), ...]
    # These would be filled with actual coordinates from literature
    # Placeholder for demonstration:
    None,  # Will be populated during initialization
]

# Asymmetry parameters
ASYMMETRY_FACTOR = 0.01  # 1% of base width for controlled asymmetry


def project_to_triangle(P, A, B, C):
    """Project point P to the nearest point on the triangle boundary."""
    if is_inside_triangle(np.array([P]), A, B, C):
        return P

    edges = [(A, B), (B, C), (C, A)]
    min_dist = float('inf')
    best_point = None

    for (V1, V2) in edges:
        v = V2 - V1
        w = P - V1
        c1 = np.dot(w, v)
        c2 = np.dot(v, v)
        if c2 == 0:
            t = 0
        else:
            t = c1 / c2
        t = max(0, min(1, t))
        projection = V1 + t * v
        dist = np.linalg.norm(P - projection)
        if dist < min_dist:
            min_dist = dist
            best_point = projection

    return best_point

def optimize_row_heights(row_counts, base, height):
    """Find optimal row heights through grid search over multipliers."""
    n_rows = len(row_counts)
    
    # Try different height multipliers to optimize initial configuration
    best_heights = None
    best_min_area = -1
    
    # Grid search over height multipliers
    for h_mult in np.linspace(0.8, 1.2, 5):
        row_heights = [height * (1 - np.sqrt(1 - h_mult * (k + 0.5) / n_rows)) for k in range(n_rows)]
        
        points = []
        for i, count in enumerate(row_counts):
            y = row_heights[i]
            width = base * (1 - y / height)
            
            if count % 2 == 1:
                # Odd count: place axis point and symmetric pairs
                points.append([base/2, y])
                num_pairs = count // 2
                for j in range(1, num_pairs + 1):
                    x_left = base/2 - j * (width / (count - 1))
                    x_right = base/2 + j * (width / (count - 1))
                    points.append([x_left, y])
                    points.append([x_right, y])
            else:
                # Even count: place symmetric pairs only
                num_pairs = count // 2
                for j in range(num_pairs):
                    x_left = base/2 - (j + 0.5) * (width / count)
                    x_right = base/2 + (j + 0.5) * (width / count)
                    points.append([x_left, y])
                    points.append([x_right, y])

        # Check if valid and compute min area
        points_arr = np.array(points)
        min_area = get_smallest_triangle_area(points_arr)
        if min_area > best_min_area:
            best_min_area = min_area
            best_heights = row_heights

    return best_heights

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Calculate triangle properties
    base = np.linalg.norm(B - A)
    height = TRIANGLE_HEIGHT

    best_points = None
    best_min_area = -1

    # Try literature configurations first if available
    for config in LITERATURE_CONFIGS:
        if config is not None:
            points = np.array(config)
            
            # Verify all points are inside triangle
            for i in range(len(points)):
                points[i] = project_to_triangle(points[i], A, B, C)

            min_area = get_smallest_triangle_area(points)
            if min_area > best_min_area:
                best_min_area = min_area
                best_points = points.copy()

    # Try multiple different initialization patterns
    for pattern in INIT_PATTERNS:
        # Unpack pattern (ignore last zero)
        row_counts = [count for count in pattern if count > 0]
        n_rows = len(row_counts)
        
        # Find optimal row heights through grid search
        row_heights = optimize_row_heights(row_counts, base, height)
        
        points = []
        for i, count in enumerate(row_counts):
            y = row_heights[i]
            width = base * (1 - y / height)
            
            if count % 2 == 1:
                # Odd count: place axis point and symmetric pairs
                points.append([base/2, y])
                num_pairs = count // 2
                for j in range(1, num_pairs + 1):
                    # Introduce controlled asymmetry
                    asymmetry = np.random.uniform(-ASYMMETRY_FACTOR * base, ASYMMETRY_FACTOR * base)
                    x_left = base/2 - j * (width / (count - 1)) + asymmetry
                    x_right = base/2 + j * (width / (count - 1)) + asymmetry
                    points.append([x_left, y])
                    points.append([x_right, y])
            else:
                # Even count: place symmetric pairs only
                num_pairs = count // 2
                for j in range(num_pairs):
                    # Introduce controlled asymmetry
                    asymmetry = np.random.uniform(-ASYMMETRY_FACTOR * base, ASYMMETRY_FACTOR * base)
                    x_left = base/2 - (j + 0.5) * (width / count) + asymmetry
                    x_right = base/2 + (j + 0.5) * (width / count) + asymmetry
                    points.append([x_left, y])
                    points.append([x_right, y])

        # Convert to numpy array
        current_points = np.array(points)
        
        # Verify all points are inside triangle using geometry-aware projection
        for i in range(len(current_points)):
            current_points[i] = project_to_triangle(current_points[i], A, B, C)

        # Optimization parameters
        initial_T = 0.005  # Reduced from 0.1 for finer exploration
        T = initial_T
        n_iter = 100000  # Increased from 50000
        base_step = 0.05  # Reduced from 0.2
        success_ema = 0.2  # Exponential moving average of improvement success rate
        no_improve_count = 0
        max_no_improve = 10000  # Early stopping threshold

        current_min_area = get_smallest_triangle_area(current_points)
        best_chain_points = current_points.copy()
        best_chain_min_area = current_min_area

        for iter_idx in range(n_iter):
            idx = np.random.randint(0, 11)
            old_point = current_points[idx].copy()

            # Adaptive step size based on success rate
            step = base_step * np.sqrt(T / initial_T)
            if success_ema > 0.4:
                step *= 1.1  # Increase step when finding improvements
            elif success_ema < 0.1:
                step *= 0.95  # Decrease step when stuck

            dx = np.random.uniform(-step, step)
            dy = np.random.uniform(-step, step)
            new_point = old_point + np.array([dx, dy])

            # Geometry-aware boundary projection
            new_point = project_to_triangle(new_point, A, B, C)
            
            candidate_points = current_points.copy()
            candidate_points[idx] = new_point
            new_min_area = get_smallest_triangle_area(candidate_points)

            # Track best configuration encountered
            if new_min_area > best_chain_min_area:
                best_chain_min_area = new_min_area
                best_chain_points = candidate_points.copy()
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Early stopping if no improvement for too long
            if no_improve_count > max_no_improve:
                break

            # Acceptance based on min area improvement
            delta = new_min_area - current_min_area
            if delta > 0 or np.random.random() < np.exp(delta / T):
                current_points = candidate_points
                current_min_area = new_min_area

            # Update success EMA for adaptive cooling
            current_success = 1.0 if delta > 0 else 0.0
            success_ema = 0.1 * current_success + 0.9 * success_ema
            
            # Adaptive cooling rate based on success_ema
            if success_ema < 0.1:
                cooling_factor = 0.9999
            elif success_ema > 0.5:
                cooling_factor = 0.99
            else:
                cooling_factor = 0.9999 - (0.9999 - 0.99) * (success_ema - 0.1) / 0.4
            
            T = T * cooling_factor

        # Update global best
        if best_chain_min_area > best_min_area:
            best_min_area = best_chain_min_area
            best_points = best_chain_points.copy()

    return best_points