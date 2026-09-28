import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random
from scipy.stats import qmc

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    L = B[0] - A[0]
    H = C[1]

    def generate_config(rows, hex_shift=False):
        points = []
        for i, (y_rel, k) in enumerate(rows):
            y = y_rel
            width = L * (1 - y/H)
            if k == 1:
                x_vals = [L/2]
            else:
                step = width / (k - 1)
                base_x = (L - width) / 2
                if hex_shift and i % 2 == 1:
                    # Optimized hex shift for equilateral triangle packing
                    base_x += step * 0.33
                x_vals = [base_x + j * step for j in range(k)]
            for x in x_vals:
                points.append([x, y])
        return np.array(points)

    # Generate asymmetric initial configurations
    asymmetric_starts = []
    
    # Pattern 1: 1-3-4-2-1
    rows1 = [
        (4*H/5, 1),
        (3*H/5, 3),
        (2*H/5, 4),
        (H/5, 2),
        (0, 1)
    ]
    
    # Pattern 2: 2-3-3-2-1
    rows2 = [
        (4*H/5, 2),
        (3*H/5, 3),
        (2*H/5, 3),
        (H/5, 2),
        (0, 1)
    ]
    
    # Pattern 3: Hexagonal 1-2-3-3-2
    rows3 = [
        (4*H/5, 1),
        (3*H/5, 2),
        (2*H/5, 3),
        (H/5, 3),
        (0, 2)
    ]

    # Pattern 4: 1-3-3-3-1 (new)
    rows4 = [
        (4*H/5, 1),
        (3*H/5, 3),
        (2*H/5, 3),
        (H/5, 3),
        (0, 1)
    ]

    # Pattern 5: 2-2-3-2-2 (new)
    rows5 = [
        (4*H/5, 2),
        (3*H/5, 2),
        (2*H/5, 3),
        (H/5, 2),
        (0, 2)
    ]

    # Pattern 6: Hexagonal optimized 1-2-3-2-3 (new)
    rows6 = [
        (4*H/5, 1),
        (3*H/5, 2),
        (2*H/5, 3),
        (H/5, 2),
        (0, 3)
    ]

    for rows in [rows1, rows2, rows3, rows4, rows5, rows6]:
        base = generate_config(rows, hex_shift=(rows in [rows3, rows6]))
        for _ in range(2):
            perturbed = base + np.random.uniform(-0.02, 0.02, base.shape)
            for j in range(11):
                if not is_inside_triangle(perturbed[j], A, B, C):
                    orig_pert = perturbed[j] - base[j]
                    for _ in range(10):
                        perturbed[j] = base[j] + orig_pert * 0.5
                        if is_inside_triangle(perturbed[j], A, B, C):
                            break
                        orig_pert = perturbed[j] - base[j]
            asymmetric_starts.append(perturbed)
    
    # Generate Sobol sequences
    sobol = qmc.Sobol(d=2, scramble=False)
    sample = sobol.random_base2(m=6)[:55]
    sobol_starts = []
    for start_idx in range(0, 55, 11):
        config = []
        for (u, v) in sample[start_idx:start_idx+11]:
            if u + v > 1:
                u, v = 1 - u, 1 - v
            x = A[0] + u * (B[0] - A[0]) + v * (C[0] - A[0])
            y = A[1] + u * (B[1] - A[1]) + v * (C[1] - A[1])
            config.append([x, y])
        sobol_starts.append(np.array(config))

    all_starts = asymmetric_starts[:5] + sobol_starts[:5]

    best_config = None
    best_min_area = -1

    # Simulated Annealing parameters
    initial_temp = 0.01
    cooling_rate = 0.95
    temp_steps = 100
    iterations_per_temp = 1100  # 100 per point

    for start_config in all_starts:
        current = start_config.copy()
        current_min_area = get_smallest_triangle_area(current)
        step_size = 0.05
        temperature = initial_temp

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = current.copy()

        # Track fitness history for plateau detection
        fitness_history = []
        plateau_threshold = 10

        for _ in range(temp_steps):
            accepted = 0
            total_moves = 0

            for __ in range(iterations_per_temp):
                # Adaptive move type ratio based on recent improvement
                improvement_rate = max(0.01, accepted / max(1, total_moves))
                move_ratio = max(0.3, min(0.9, 0.7 - 0.4 * improvement_rate))

                if random.random() < move_ratio:
                    # Single-point move with systematic grid sampling
                    i = random.randint(0, 10)
                    angle = random.randint(0, 35) * 10 * (np.pi/180)  # 36 directions
                    dx = step_size * np.cos(angle)
                    dy = step_size * np.sin(angle)
                    candidate_point = current[i] + np.array([dx, dy])
                    
                    if not is_inside_triangle(candidate_point, A, B, C):
                        continue
                        
                    candidate_config = current.copy()
                    candidate_config[i] = candidate_point
                    new_min_area = get_smallest_triangle_area(candidate_config)
                    delta = new_min_area - current_min_area

                    if delta >= 0 or random.random() < np.exp(delta / temperature):
                        current = candidate_config
                        current_min_area = new_min_area
                        accepted += 1
                    total_moves += 1

                else:
                    # Multi-point move with independent directions
                    k = random.choice([2, 3])
                    indices = random.sample(range(11), k)
                    candidate_config = current.copy()
                    valid = True
                    
                    for idx in indices:
                        angle = random.uniform(0, 2 * np.pi)
                        dx = step_size * np.cos(angle)
                        dy = step_size * np.sin(angle)
                        candidate_point = current[idx] + np.array([dx, dy])
                        if not is_inside_triangle(candidate_point, A, B, C):
                            valid = False
                            break
                        candidate_config[idx] = candidate_point
                    
                    if not valid:
                        continue
                        
                    new_min_area = get_smallest_triangle_area(candidate_config)
                    delta = new_min_area - current_min_area

                    if delta >= 0 or random.random() < np.exp(delta / temperature):
                        current = candidate_config
                        current_min_area = new_min_area
                        accepted += 1
                    total_moves += 1

            # Adaptive step size adjustment with tiered response
            if total_moves > 0:
                acceptance_rate = accepted / total_moves
                
                # Dynamic adjustment based on acceptance rate
                if acceptance_rate > 0.6:  # Too high - be more aggressive
                    step_size *= 1.2
                elif acceptance_rate > 0.4:  # Good range
                    step_size *= 1.05
                elif acceptance_rate > 0.2:  # A bit low
                    step_size *= 0.9
                else:  # Too low - be conservative
                    step_size *= 0.7
                
                step_size = max(1e-5, min(step_size, 0.1))

            # Cool temperature
            temperature *= cooling_rate

            # Track global best
            if current_min_area > best_min_area:
                best_min_area = current_min_area
                best_config = current.copy()

            # Check for fitness plateau instead of step_size threshold
            fitness_history.append(current_min_area)
            if len(fitness_history) > plateau_threshold:
                fitness_history.pop(0)
                if max(fitness_history) - min(fitness_history) < 1e-7:
                    break  # no significant improvement

    return best_config