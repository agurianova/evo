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

    def generate_row_configs(n_points=11, min_rows=3, max_rows=6, n_configs=15):
        configs = []
        for _ in range(n_configs):
            r = random.randint(min_rows, max_rows)
            dividers = sorted(random.sample(range(1, n_points), r-1))
            counts = [dividers[0]]
            for i in range(1, r-1):
                counts.append(dividers[i] - dividers[i-1])
            counts.append(n_points - dividers[-1])
            y_positions = [H * (r-1 - i) / (r-1) for i in range(r)]
            rows = list(zip(y_positions, counts))
            configs.append(rows)
        return configs

    def generate_config_from_rows(rows):
        points = []
        for y_rel, k in rows:
            y = y_rel
            width = L * (1 - y/H)
            if k == 1:
                x_vals = [L/2]
            else:
                step = width / (k - 1)
                base_x = (L - width) / 2
                x_vals = [base_x + j * step for j in range(k)]
            for x in x_vals:
                points.append([x, y])
        return np.array(points)

    def generate_voronoi_start(n=11, n_samples=1000, n_iters=5):
        points = []
        for _ in range(n):
            u, v = np.random.random(2)
            if u + v > 1:
                u, v = 1 - u, 1 - v
            x = A[0] + u * (B[0] - A[0]) + v * (C[0] - A[0])
            y = A[1] + u * (B[1] - A[1]) + v * (C[1] - A[1])
            points.append([x, y])
        points = np.array(points)

        samples = []
        for _ in range(n_samples):
            u, v = np.random.random(2)
            if u + v > 1:
                u, v = 1 - u, 1 - v
            x = A[0] + u * (B[0] - A[0]) + v * (C[0] - A[0])
            y = A[1] + u * (B[1] - A[1]) + v * (C[1] - A[1])
            samples.append([x, y])
        samples = np.array(samples)

        for _ in range(n_iters):
            dists = np.linalg.norm(samples[:, np.newaxis, :] - points[np.newaxis, :, :], axis=2)
            assignments = np.argmin(dists, axis=1)

            new_points = []
            for i in range(n):
                mask = (assignments == i)
                if np.any(mask):
                    centroid = np.mean(samples[mask], axis=0)
                    new_points.append(centroid)
                else:
                    new_points.append(points[i])
            points = np.array(new_points)

        return points

    row_configs = generate_row_configs(n_configs=15)
    row_starts = []
    for rows in row_configs:
        base = generate_config_from_rows(rows)
        perturbed = base + np.random.uniform(-0.02, 0.02, base.shape)
        for j in range(11):
            if not is_inside_triangle(perturbed[j], A, B, C):
                orig_pert = perturbed[j] - base[j]
                for _ in range(10):
                    perturbed[j] = base[j] + orig_pert * 0.5
                    if is_inside_triangle(perturbed[j], A, B, C):
                        break
                    orig_pert = perturbed[j] - base[j]
        row_starts.append(perturbed)

    sobol = qmc.Sobol(d=2, scramble=False)
    sample = sobol.random_base2(m=7)[:110]
    sobol_starts = []
    for start_idx in range(0, 110, 11):
        config = []
        for (u, v) in sample[start_idx:start_idx+11]:
            if u + v > 1:
                u, v = 1 - u, 1 - v
            point = (1 - u - v) * A + u * B + v * C
            config.append(point)
        sobol_starts.append(np.array(config))

    voronoi_starts = []
    for _ in range(5):
        config = generate_voronoi_start()
        voronoi_starts.append(config)

    all_starts = row_starts + sobol_starts + voronoi_starts

    best_config = None
    best_min_area = -1

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
                single_point_ratio = 0.6

                before_min_area = current_min_area

                if random.random() < single_point_ratio:
                    min_area = current_min_area
                    critical_points = set()
                    for i in range(11):
                        for j in range(i+1, 11):
                            for k in range(j+1, 11):
                                area_val = 0.5 * abs((current[j,0]-current[i,0])*(current[k,1]-current[i,1]) - (current[k,0]-current[i,0])*(current[j,1]-current[i,1]))
                                if area_val <= min_area * 1.0001:
                                    critical_points.add(i)
                                    critical_points.add(j)
                                    critical_points.add(k)
                    critical_points = list(critical_points)
                    if critical_points:
                        i = random.choice(critical_points)
                    else:
                        i = random.randint(0, 10)

                    angle = random.randint(0, 35) * 10 * (np.pi/180)
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