import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    np.random.seed(42)
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Asymmetric boundary initialization: 3 points per edge at variable positions
    boundary_points = []
    # AB edge (A to B)
    for t in [0.15, 0.45, 0.75]:
        boundary_points.append(A + t * (B - A))
    # BC edge (B to C)
    for t in [0.25, 0.55, 0.85]:
        boundary_points.append(B + t * (C - B))
    # CA edge (C to A)
    for t in [0.35, 0.65, 0.95]:
        boundary_points.append(C + t * (A - C))

    # Asymmetric interior points (avoid centroid clustering)
    interior_bary = [
        [0.2, 0.3, 0.5],
        [0.5, 0.2, 0.3]
    ]
    interior_points = [
        u * A + v * B + w * C
        for u, v, w in interior_bary
    ]

    # Combine and apply larger symmetry-breaking noise
    points = boundary_points + interior_points
    for i in range(len(points)):
        noise = np.random.uniform(-0.01, 0.01, size=2)
        P_noisy = points[i] + noise
        if is_inside_triangle(P_noisy, A, B, C):
            points[i] = P_noisy

    points = np.array(points)
    current_points = points
    current_min_area = get_smallest_triangle_area(current_points)

    # Enhanced exploration parameters
    total_iterations = 30000
    initial_temp = 0.2
    cooling_factor = 0.9995
    min_step = 0.005
    max_step = 0.065  # Calibrated to 5% of triangle height (1.3161)
    step_size = max_step
    
    # Adaptive step_size tracking
    acceptance_window = 100
    acceptance_count = 0
    last_improvement = 0  # Track last improvement for adaptive temperature

    for iteration in range(total_iterations):
        # Adaptive temperature schedule
        if (iteration - last_improvement) > 100:
            temp = initial_temp
        else:
            temp = initial_temp * (cooling_factor ** iteration)

        # Count minimal-area triangle participation per point
        critical_count = [0] * 11
        for i in range(11):
            for j in range(i + 1, 11):
                for k in range(j + 1, 11):
                    area = 0.5 * abs(
                        (current_points[j, 0] - current_points[i, 0]) * (current_points[k, 1] - current_points[i, 1]) -
                        (current_points[k, 0] - current_points[i, 0]) * (current_points[j, 1] - current_points[i, 1])
                    )
                    if abs(area - current_min_area) < 1e-10:
                        critical_count[i] += 1
                        critical_count[j] += 1
                        critical_count[k] += 1

        # Multi-point perturbation (35% chance)
        if np.random.rand() < 0.35:
            num_moves = np.random.choice([2, 3])
            # Weighted selection by critical_count
            weights = np.array(critical_count, dtype=float)
            if weights.sum() == 0:
                weights = np.ones(11)
            weights /= weights.sum()
            selected_indices = np.random.choice(11, num_moves, replace=False, p=weights)

            candidate = current_points.copy()
            step_scale = 1.0 / num_moves
            for idx in selected_indices:
                dx = np.random.uniform(-step_size * step_scale, step_size * step_scale)
                dy = np.random.uniform(-step_size * step_scale, step_size * step_scale)
                candidate[idx] += [dx, dy]
        else:
            # Single-point move: weighted by critical_count
            weights = np.array(critical_count, dtype=float)
            if weights.sum() == 0:
                weights = np.ones(11)
            weights /= weights.sum()
            idx = np.random.choice(11, p=weights)

            dx = np.random.uniform(-step_size, step_size)
            dy = np.random.uniform(-step_size, step_size)
            candidate = current_points.copy()
            candidate[idx] += [dx, dy]

        # Validate constraints
        if not is_inside_triangle(candidate, A, B, C):
            continue
        
        duplicate = False
        for i in range(11):
            for j in range(i + 1, 11):
                if np.linalg.norm(candidate[i] - candidate[j]) < 1e-10:
                    duplicate = True
                    break
            if duplicate:
                break
        if duplicate:
            continue

        # Evaluate candidate
        new_min_area = get_smallest_triangle_area(candidate)
        delta = new_min_area - current_min_area

        # Acceptance criterion
        accept = False
        if delta > 0:
            accept = True
            last_improvement = iteration  # Record improvement
        elif temp > 0 and np.random.rand() < np.exp(delta / temp):
            accept = True
            
        if accept:
            current_points = candidate
            current_min_area = new_min_area
            acceptance_count += 1

        # Adaptive step_size adjustment
        if (iteration + 1) % acceptance_window == 0:
            acceptance_rate = acceptance_count / acceptance_window
            acceptance_count = 0
            if acceptance_rate > 0.5:
                step_size = min(step_size * 1.1, max_step)
            elif acceptance_rate < 0.2:
                step_size = max(step_size * 0.9, min_step)

    return current_points