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

    # Generate Sobol starts with proper barycentric mapping
    sobol = qmc.Sobol(d=2, scramble=False)
    sample = sobol.random_base2(m=7)[:121]  # 128 points, take 121 for 11 starts
    sobol_starts = []
    for start_idx in range(0, 121, 11):
        config = []
        for (u, v) in sample[start_idx:start_idx+11]:
            # Proper barycentric mapping for uniform triangle distribution
            r1 = np.sqrt(u)
            r2 = v
            x = (1 - r1) * A[0] + r1 * (1 - r2) * B[0] + r1 * r2 * C[0]
            y = (1 - r1) * A[1] + r1 * (1 - r2) * B[1] + r1 * r2 * C[1]
            config.append([x, y])
        sobol_starts.append(np.array(config))

    all_starts = sobol_starts

    best_config = None
    best_min_area = -1
    directions_per_point = 100
    max_iter = 1500
    step_init = 0.05
    decay = 0.99  # Changed from 0.95 to 0.99 for slower step decay
    temperature = 0.1
    temp_decay = 0.999

    for config in all_starts:
        current = config.copy()
        current_min_area = get_smallest_triangle_area(current)
        step = step_init
        no_improve_count = 0  # Track iterations without improvement

        for _ in range(max_iter):
            # Identify critical points (in triangles near min area)
            critical_points = set()
            n = 11
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        # Compute triangle area
                        area = 0.5 * abs((current[j,0]-current[i,0])*(current[k,1]-current[i,1]) - 
                                       (current[k,0]-current[i,0])*(current[j,1]-current[i,1]))
                        if area <= current_min_area + 1e-5:
                            critical_points.add(i)
                            critical_points.add(j)
                            critical_points.add(k)
            critical_points = list(critical_points)

            best_improvement = 0
            best_candidate = None
            improvement_found = False

            # Evaluate single-point moves on critical points only
            for i in critical_points:
                for _ in range(directions_per_point):
                    angle = random.uniform(0, 2 * np.pi)
                    dx = step * np.cos(angle)
                    dy = step * np.sin(angle)
                    candidate_point = current[i] + np.array([dx, dy])
                    if not is_inside_triangle(candidate_point, A, B, C):
                        continue
                    candidate_config = current.copy()
                    candidate_config[i] = candidate_point
                    new_min_area = get_smallest_triangle_area(candidate_config)
                    if new_min_area > current_min_area:
                        improvement = new_min_area - current_min_area
                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_candidate = candidate_config.copy()

            # Evaluate multi-point moves with enhanced strategy
            if random.random() < 0.5 and len(critical_points) >= 2:  # Increased probability to 0.5
                best_multi_improvement = 0
                best_multi_candidate = None
                for _ in range(5):  # Try 5 different multi-point moves
                    k = random.choice([2, 3, 4])
                    if k > len(critical_points):
                        continue
                    indices = random.sample(critical_points, k)
                    candidate_config = current.copy()
                    valid = True
                    for idx in indices:
                        angle = random.uniform(0, 2 * np.pi)
                        dx = step * np.cos(angle)
                        dy = step * np.sin(angle)
                        candidate_point = current[idx] + np.array([dx, dy])
                        if not is_inside_triangle(candidate_point, A, B, C):
                            valid = False
                            break
                        candidate_config[idx] = candidate_point
                    if not valid:
                        continue
                    new_min_area = get_smallest_triangle_area(candidate_config)
                    improvement = new_min_area - current_min_area
                    if improvement > best_multi_improvement:
                        best_multi_improvement = improvement
                        best_multi_candidate = candidate_config.copy()

                if best_multi_candidate is not None and best_multi_improvement > best_improvement:
                    best_improvement = best_multi_improvement
                    best_candidate = best_multi_candidate

            # Apply best greedy move if found
            if best_candidate is not None:
                current = best_candidate
                current_min_area += best_improvement
                step = min(step * 1.1, step_init * 10)  # Maintain original step growth
                improvement_found = True

            # Simulated annealing exploration
            if best_candidate is None:
                for i in range(11):
                    angle = random.uniform(0, 2 * np.pi)
                    dx = step * np.cos(angle)
                    dy = step * np.sin(angle)
                    candidate_point = current[i] + np.array([dx, dy])
                    if not is_inside_triangle(candidate_point, A, B, C):
                        continue
                    candidate_config = current.copy()
                    candidate_config[i] = candidate_point
                    new_min_area = get_smallest_triangle_area(candidate_config)
                    delta = new_min_area - current_min_area
                    if delta > 0 or (temperature > 1e-5 and random.random() < np.exp(delta / temperature)):
                        current = candidate_config
                        current_min_area = new_min_area
                        if delta > 0:
                            improvement_found = True
                        break

            # Update improvement tracking and step size
            if improvement_found:
                no_improve_count = 0
                if current_min_area > best_min_area:
                    best_min_area = current_min_area
                    best_config = current.copy()
            else:
                no_improve_count += 1
                if no_improve_count >= 100:  # Reset step after prolonged stagnation
                    step = step_init
                    no_improve_count = 0

            # Update temperature and step decay
            temperature *= temp_decay
            step *= decay
            if step < 1e-5:
                break

    return best_config