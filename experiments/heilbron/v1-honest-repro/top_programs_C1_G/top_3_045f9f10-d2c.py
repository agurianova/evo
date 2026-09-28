import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    np.random.seed(42)
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Boundary initialization: two points per edge at 1/3 and 2/3 positions
    boundary_points = [
        (2*A + B)/3, (A + 2*B)/3,
        (2*B + C)/3, (B + 2*C)/3,
        (2*C + A)/3, (C + 2*A)/3
    ]
    
    # Interior points: symmetric barycentric grid (sums to 1)
    interior_bary = [
        [0.34, 0.33, 0.33],
        [0.33, 0.34, 0.33],
        [0.33, 0.33, 0.34],
        [0.32, 0.34, 0.34],
        [0.34, 0.32, 0.34]
    ]
    interior_points = [
        u*A + v*B + w*C 
        for u, v, w in interior_bary
    ]

    # Combine and apply symmetry-breaking noise
    points = boundary_points + interior_points
    for i in range(len(points)):
        noise = np.random.uniform(-0.005, 0.005, size=2)
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
    max_step = 0.1  # Increased from 0.05
    step_size = max_step
    
    # Adaptive step_size tracking
    acceptance_window = 100
    acceptance_count = 0

    for iteration in range(total_iterations):
        # Temperature schedule
        temp = initial_temp * (cooling_factor ** iteration)

        # Identify critical points (involved in minimal-area triangles)
        critical_points = set()
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = 0.5 * abs(
                        (current_points[j,0] - current_points[i,0]) * (current_points[k,1] - current_points[i,1]) -
                        (current_points[k,0] - current_points[i,0]) * (current_points[j,1] - current_points[i,1])
                    )
                    if abs(area - current_min_area) < 1e-10:
                        critical_points.update([i, j, k])

        # Multi-point perturbation (10% chance)
        if np.random.rand() < 0.1:
            num_moves = np.random.choice([2, 3])
            # Prioritize critical points for multi-move
            if critical_points:
                indices = list(critical_points)
                np.random.shuffle(indices)
                selected_indices = indices[:num_moves]
                if len(selected_indices) < num_moves:
                    non_critical = [i for i in range(11) if i not in critical_points]
                    np.random.shuffle(non_critical)
                    selected_indices += non_critical[:num_moves - len(selected_indices)]
            else:
                selected_indices = np.random.choice(11, num_moves, replace=False).tolist()

            candidate = current_points.copy()
            step_scale = 1.0 / num_moves  # Scale step for coordinated moves
            for idx in selected_indices:
                dx = np.random.uniform(-step_size * step_scale, step_size * step_scale)
                dy = np.random.uniform(-step_size * step_scale, step_size * step_scale)
                candidate[idx] += [dx, dy]
        else:
            # Single-point move (prioritize critical points)
            if critical_points:
                idx = np.random.choice(list(critical_points))
            else:
                idx = np.random.randint(0, 11)

            dx = np.random.uniform(-step_size, step_size)
            dy = np.random.uniform(-step_size, step_size)
            candidate = current_points.copy()
            candidate[idx] += [dx, dy]

        # Validate constraints
        if not is_inside_triangle(candidate, A, B, C):
            continue
        
        duplicate = False
        for i in range(11):
            for j in range(i+1, 11):
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

        # Acceptance criterion (simulated annealing)
        accept = False
        if delta > 0:
            accept = True
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