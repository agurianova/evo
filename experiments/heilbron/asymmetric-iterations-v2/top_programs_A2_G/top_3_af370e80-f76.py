import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random
from scipy.stats import qmc

np.random.seed(42)
random.seed(42)

def generate_compositions(n, k):
    if k == 1:
        yield [n]
    else:
        for i in range(1, n - k + 2):
            for rest in generate_compositions(n - i, k - 1):
                yield [i] + rest

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    L = B[0] - A[0]
    H = C[1]

    def generate_config(rows, hex_shift=False, shift_value=0.4):
        points = []
        for i, k in enumerate(rows):
            y_rel = H * (1 - (i + 0.5) / len(rows))
            width = L * (1 - y_rel / H)
            if k == 1:
                x_vals = [L / 2]
            else:
                step = width / (k - 1)
                base_x = (L - width) / 2
                if hex_shift and i % 2 == 1:
                    base_x += step * shift_value
                x_vals = [base_x + j * step for j in range(k)]
            for x in x_vals:
                points.append([x, y_rel])
        return np.array(points)

    # Generate dynamic row patterns (3-6 rows)
    all_patterns = []
    for r in range(3, 7):
        for comp in generate_compositions(11, r):
            all_patterns.append(comp)
    random.shuffle(all_patterns)
    patterns = all_patterns[:20]

    asymmetric_starts = []
    for rows in patterns:
        hex_shift = random.random() < 0.5
        shift_value = random.uniform(0.3, 0.5) if hex_shift else 0.0
        base = generate_config(rows, hex_shift, shift_value)
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

    # Generate Sobol sequences with corrected barycentric transformation
    sobol = qmc.Sobol(d=2, scramble=False)
    sample = sobol.random_base2(m=7)[:330]  # Generate 330 points (30*11)
    sobol_starts = []
    for start_idx in range(0, 330, 11):
        config = []
        for (u0, v0) in sample[start_idx:start_idx + 11]:
            u = 1 - np.sqrt(1 - u0)
            v = v0
            x = (1 - u) * A[0] + u * (1 - v) * B[0] + u * v * C[0]
            y = (1 - u) * A[1] + u * (1 - v) * B[1] + u * v * C[1]
            config.append([x, y])
        sobol_starts.append(np.array(config))

    all_starts = asymmetric_starts[:20] + sobol_starts[:10]

    best_config = None
    best_min_area = -1

    # Simulated Annealing parameters
    initial_temp = 0.08
    cooling_rate = 0.92
    temp_steps = 100
    iterations_per_temp = 1100
    target_acceptance = 0.4

    for start_config in all_starts:
        current = start_config.copy()
        current_min_area = get_smallest_triangle_area(current)
        step_size = 0.05
        temperature = initial_temp

        start_best = current_min_area
        no_improve_count = 0
        stall_count = 0

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = current.copy()

        for _ in range(temp_steps):
            accepted = 0
            total_moves = 0

            for __ in range(iterations_per_temp):
                single_point_ratio = 0.3 if stall_count > 50 else 0.4

                before_min_area = current_min_area

                if random.random() < single_point_ratio:
                    i = random.randint(0, 10)
                    angle = random.randint(0, 35) * 10 * (np.pi / 180)
                    dx = step_size * np.cos(angle)
                    dy = step_size * np.sin(angle)
                    candidate_point = current[i] + np.array([dx, dy])
                    
                    if not is_inside_triangle(candidate_point, A, B, C):
                        stall_count += 1
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
                        stall_count += 1
                        continue
                        
                    new_min_area = get_smallest_triangle_area(candidate_config)
                    delta = new_min_area - current_min_area

                    if delta >= 0 or random.random() < np.exp(delta / temperature):
                        current = candidate_config
                        current_min_area = new_min_area
                        accepted += 1
                    total_moves += 1

                if current_min_area > before_min_area:
                    stall_count = 0
                else:
                    stall_count += 1

            if total_moves > 0:
                acceptance_rate = accepted / total_moves
                if acceptance_rate > target_acceptance:
                    step_size *= 1.25
                else:
                    step_size *= 0.75
                step_size = max(1e-5, min(step_size, 0.1))

            temperature *= cooling_rate

            if current_min_area > best_min_area:
                best_min_area = current_min_area
                best_config = current.copy()

            if current_min_area > start_best:
                start_best = current_min_area
                no_improve_count = 0
            else:
                no_improve_count += 1

            if no_improve_count >= 30:
                break

    return best_config