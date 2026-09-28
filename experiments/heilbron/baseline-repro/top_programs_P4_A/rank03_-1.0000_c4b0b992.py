import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def project_barycentric(a, b, c, threshold=1e-8):
    coords = np.array([a, b, c])
    coords = np.maximum(coords, 0)
    total = np.sum(coords)
    if total < threshold:
        return 1/3, 1/3, 1/3
    return coords / total

def mutate_pattern(pattern, p_split=0.5):
    pattern = list(pattern)
    n = len(pattern)
    
    # Find indices eligible for splitting (rows with >=2 points)
    can_split = [i for i, size in enumerate(pattern) if size >= 2]
    # Find indices eligible for merging (adjacent rows)
    can_merge = [i for i in range(n-1)]

    if not can_split and not can_merge:
        return tuple(pattern)

    if can_split and (not can_merge or random.random() < p_split):
        # Split a row
        idx = random.choice(can_split)
        size = pattern[idx]
        j = random.randint(1, size-1)
        new_pattern = pattern[:idx] + [j, size-j] + pattern[idx+1:]
    else:
        # Merge two adjacent rows
        idx = random.choice(can_merge)
        merged_size = pattern[idx] + pattern[idx+1]
        new_pattern = pattern[:idx] + [merged_size] + pattern[idx+2:]
        
    return tuple(new_pattern)

def entrypoint() -> np.ndarray:
    base_seed = 42
    n_restarts = 50
    best_points = None
    best_min_area = -1

    # Expanded literature-based Heilbronn configurations with mutation capability
    candidate_patterns = [
        (4, 3, 2, 2),
        (3, 3, 3, 1, 1),
        (3, 4, 2, 1, 1),
        (5, 3, 2, 1),
        (4, 4, 2, 1),
        (3, 3, 2, 2, 1),  # New pattern
        (4, 2, 2, 2, 1)   # New pattern
    ]

    # Pattern performance tracking with exploration guarantees
    pattern_counts = {pattern: 1 for pattern in candidate_patterns}
    pattern_values = {pattern: 0.0 for pattern in candidate_patterns}
    pattern_history = {pattern: [] for pattern in candidate_patterns}
    best_history = []

    for restart in range(n_restarts):
        # Dynamic seed for exploration diversity
        current_seed = base_seed + restart + random.randint(0, 1000)
        np.random.seed(current_seed)
        random.seed(current_seed)
        
        # Enhanced pattern selection with exploration guarantee
        selected_pattern = None
        max_ucb = -float('inf')
        
        for pattern in candidate_patterns:
            count = pattern_counts[pattern]
            avg = pattern_values[pattern] / count
            exploration = math.sqrt(2 * math.log(restart + 1) / count)
            ucb = avg + 0.5 * exploration
            
            if ucb > max_ucb:
                max_ucb = ucb
                selected_pattern = pattern

        # Apply pattern mutation with 20% probability
        if random.random() < 0.2:
            selected_pattern = mutate_pattern(selected_pattern)

        rows = selected_pattern
        total_rows = len(rows)
        points = []
        A, B, C = get_unit_triangle()
        
        for i, num_points in enumerate(rows):
            c_weight = i / (total_rows - 1) if total_rows > 1 else 0
            base_length = 1 - c_weight
            step = base_length / (num_points - 1) if num_points > 1 else 0

            # Literature-informed row shifts for triangle maximization
            if num_points >= 3:
                row_shift = 0.5 * step
            else:
                row_shift = 0

            for j in range(num_points):
                # Regenerate until distinct and valid
                max_tries = 10
                for _ in range(max_tries):
                    a_weight = j * step + row_shift
                    a_weight = max(0, min(a_weight, base_length))
                    b_weight = base_length - a_weight

                    # Adaptive perturbation based on row position
                    perturbation = 0.03 * base_length * (1 - c_weight)
                    da = random.uniform(-perturbation, perturbation)
                    db = random.uniform(-perturbation, perturbation)
                    a1 = a_weight + da
                    b1 = b_weight + db
                    c1 = c_weight

                    a1, b1, c1 = project_barycentric(a1, b1, c1)
                    P = a1 * A + b1 * B + c1 * C
                    
                    # Check distinctness from existing points
n                    duplicate = False
                    for k in range(len(points)):
                        if np.linalg.norm(P - points[k]) < 1e-5:
                            duplicate = True
                            break
                    
                    if not duplicate:
                        break
                
                points.append(P)
        
        points = np.array(points)
        
        # Enhanced simulated annealing with adaptive parameters
        current_min_area = get_smallest_triangle_area(points)
        n_points = len(points)
        
        # Improved temperature initialization (addresses harmful insight)
        T0 = 0.5 * (0.0365 - current_min_area) + 0.1
        cooling_rate = 0.995
        max_iter = 150000
        no_improve_count = 0

        for iter in range(max_iter):
            T = T0 * (cooling_rate ** iter)
            
            # Adaptive step size with increased base multiplier (0.1 vs 0.05)
            step_size = 0.1 * math.sqrt(T / T0)
            if step_size < 0.001:
                step_size = 0.001

            idx = random.randrange(n_points)
            P_old = points[idx]

            v0 = B - A
            v1 = C - A
            v2 = P_old - A
            d00 = np.dot(v0, v0)
            d01 = np.dot(v0, v1)
            d11 = np.dot(v1, v1)
            d20 = np.dot(v2, v0)
            d21 = np.dot(v2, v1)
            denom = d00 * d11 - d01 * d01
            if abs(denom) < 1e-10:
                continue
            b0 = (d11 * d20 - d01 * d21) / denom
            c0 = (d00 * d21 - d01 * d20) / denom
            a0 = 1 - b0 - c0

            # Adaptive direction selection
            angle = random.uniform(0, 2 * math.pi)
            da = step_size * math.cos(angle)
            db = step_size * math.sin(angle)
            
            a1 = a0 + da
            b1 = b0 + db
            c1 = 1 - a1 - b1

            a1, b1, c1 = project_barycentric(a1, b1, c1)
            P_new = a1 * A + b1 * B + c1 * C

            # Reject moves outside triangle (critical for min_area improvement)
            if not is_inside_triangle(P_new, A, B, C):
                no_improve_count += 1
                continue

            new_points = np.copy(points)
            new_points[idx] = P_new
            new_min_area = get_smallest_triangle_area(new_points)

            if new_min_area > current_min_area:
                points = new_points
                current_min_area = new_min_area
                no_improve_count = 0
            else:
                delta = current_min_area - new_min_area
                if delta < 0:
                    continue
                if random.random() < math.exp(-delta / T):
                    points = new_points
                    current_min_area = new_min_area
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            # Adaptive reheating threshold (prevents premature convergence)
            adaptive_reheat = max(5000, int(10000 * (T0 / T)))
            if no_improve_count > adaptive_reheat:
                T = T0 * 0.5
                no_improve_count = 0

        # Adaptive hill climbing with increased base step size (0.005 vs 0.001)
        no_improve = 0
        max_no_improve = 200
        base_step = 0.005  # Increased for better basin escape
        step_multiplier = 1.0

        while no_improve < max_no_improve:
            improved = False
            step_size = base_step * step_multiplier
            
            # Dynamic direction selection
            directions = []
            for i in range(36):
                angle = i * math.pi / 18
                directions.append((step_size * math.cos(angle), step_size * math.sin(angle)))

            for idx in range(n_points):
                P_old = points[idx]
                v0 = B - A
                v1 = C - A
                v2 = P_old - A
                d00 = np.dot(v0, v0)
                d01 = np.dot(v0, v1)
                d11 = np.dot(v1, v1)
                d20 = np.dot(v2, v0)
                d21 = np.dot(v2, v1)
                denom = d00 * d11 - d01 * d01
                if abs(denom) < 1e-10:
                    continue
                b0 = (d11 * d20 - d01 * d21) / denom
                c0 = (d00 * d21 - d01 * d20) / denom
                a0 = 1 - b0 - c0

                for da, db in directions:
                    a1 = a0 + da
                    b1 = b0 + db
                    c1 = 1 - a1 - b1

                    a1, b1, c1 = project_barycentric(a1, b1, c1)
                    P_new = a1 * A + b1 * B + c1 * C

                    # Reject moves outside triangle
                    if not is_inside_triangle(P_new, A, B, C):
                        continue

                    new_points = np.copy(points)
                    new_points[idx] = P_new
                    new_min_area = get_smallest_triangle_area(new_points)

                    if new_min_area > current_min_area:
                        points = new_points
                        current_min_area = new_min_area
                        improved = True
                        no_improve = 0
                        step_multiplier = min(2.0, step_multiplier * 1.1)
                        break

                if improved:
                    break

            if not improved:
                no_improve += 1
                step_multiplier = max(0.5, step_multiplier * 0.95)

        # Update pattern tracking
        min_area = get_smallest_triangle_area(points)
        if rows in pattern_counts:
            pattern_counts[rows] += 1
            pattern_values[rows] += min_area
            pattern_history[rows].append(min_area)
        else:
            # Handle mutated patterns not in original list
            pattern_counts[rows] = 1
            pattern_values[rows] = min_area
            pattern_history[rows] = [min_area]

        # Track best configuration
        if min_area > best_min_area:
            best_min_area = min_area
            best_points = points

        best_history.append(best_min_area)

    return best_points