import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Generate geometrically justified initial configuration
    points = []
    # Center point
    P_center = (A + B + C) / 3.0
    points.append(P_center)

    # 5 rings with equal area spacing
    n_rings = 5
    a_vals = [1 - np.sqrt(i / (n_rings + 1)) for i in range(1, n_rings + 1)]
    fractions = [0.6] * n_rings  # Constant spread fraction

    for i in range(n_rings):
        a_i = a_vals[i]
        s = 1 - a_i  # u + v = s
        u_left = s / 2 * (1 + fractions[i])
        v_left = s / 2 * (1 - fractions[i])
        P_left = a_i * A + u_left * B + v_left * C
        P_right = a_i * A + v_left * B + u_left * C
        points.append(P_left)
        points.append(P_right)

    # Apply independent initial perturbation with increased magnitude
    for i in range(11):
        V = np.random.uniform(-0.05, 0.05, 2)
        candidate = points[i] + V
        for attempt in range(5):
            if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                break
            candidate = 0.9 * candidate + 0.1 * points[i]
        else:
            candidate = points[i]
        points[i] = candidate

    current = np.array(points)
    best = current.copy()
    best_min_area = get_smallest_triangle_area(best)

    # Simulated annealing parameters
    T = 0.5
    max_iter = 20000
    base_cooling_rate = 0.9998
    stagnation_counter = 0

    for iter_index in range(max_iter):
        prev_best = best_min_area
        n = len(current)

        # Compute global minimum triangle area
        min_area = float('inf')
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    x1, y1 = current[i]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area < min_area:
                        min_area = area

        # Adaptive threshold for near-minimal triangle selection
        multiplier = 1.1 + 0.1 * (1 - iter_index / max_iter)
        threshold = min_area * multiplier

        # Count near-minimal triangles per point
        count = np.zeros(n, dtype=int)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    x1, y1 = current[i]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area <= threshold:
                        count[i] += 1
                        count[j] += 1
                        count[k] += 1

        # Weighted random selection of point to move
        total_count = count.sum()
        if total_count == 0:
            idx = np.random.randint(0, n)
        else:
            probabilities = count / total_count
            idx = np.random.choice(n, p=probabilities)

        # Adaptive step size with gap-aware scaling
        gap_factor = max(0, (0.0365 - min_area) / 0.0365)
        base_step = T * (0.3 + 0.2 * gap_factor)
        min_step = 0.001 * (1 - iter_index / max_iter) ** 2
        step_size = max(min_step, base_step)

        # Geometry-aware directional sampling
        near_min_triangles = []
        for j in range(n):
            if j == idx: continue
            for k in range(j + 1, n):
                if k == idx: continue
                x1, y1 = current[idx]
                x2, y2 = current[j]
                x3, y3 = current[k]
                area_val = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                if area_val <= threshold:
                    near_min_triangles.append((j, k))

        candidate_directions = []
        for (j, k) in near_min_triangles:
            signed_area = 0.5 * ((current[j,0]-current[idx,0])*(current[k,1]-current[idx,1]) - 
                                (current[k,0]-current[idx,0])*(current[j,1]-current[idx,1]))
            if abs(signed_area) < 1e-10:
                continue
            sign = 1 if signed_area > 0 else -1
            dir_vec = np.array([sign * (current[j,1] - current[k,1]), 
                               sign * (current[k,0] - current[j,0])])
            norm = np.linalg.norm(dir_vec)
            if norm > 1e-10:
                dir_vec /= norm
                candidate_directions.append(dir_vec)

        if candidate_directions:
            composite_dir = np.mean(candidate_directions, axis=0)
            norm = np.linalg.norm(composite_dir)
            if norm > 1e-10:
                composite_dir /= norm
                base_angle = np.arctan2(composite_dir[1], composite_dir[0])
                angles = base_angle + np.linspace(-np.pi/4, np.pi/4, 8)
            else:
                angles = np.linspace(0, 2*np.pi, 8, endpoint=False)
        else:
            angles = np.linspace(0, 2*np.pi, 8, endpoint=False)

        # Evaluate candidate moves
        best_candidate = None
        best_new_min_area = -1
        for angle in angles:
            direction = np.array([np.cos(angle), np.sin(angle)])
            disp = step_size * direction
            candidate = current[idx] + disp
            candidate_temp = candidate.copy()
            for attempt in range(5):
                if is_inside_triangle(candidate_temp.reshape(1, 2), A, B, C):
                    break
                candidate_temp = 0.9 * candidate_temp + 0.1 * current[idx]
            else:
                continue

            new_config = current.copy()
            new_config[idx] = candidate_temp
            new_min_area_temp = get_smallest_triangle_area(new_config)
            if new_min_area_temp > best_new_min_area:
                best_new_min_area = new_min_area_temp
                best_candidate = candidate_temp

        if best_candidate is None:
            # Fallback to random move if all directions failed
            direction = np.random.randn(2)
            direction /= np.linalg.norm(direction)
            disp = step_size * direction
            candidate = current[idx] + disp
            for attempt in range(5):
                if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                    break
                candidate = 0.9 * candidate + 0.1 * current[idx]
            else:
                continue
            new_config = current.copy()
            new_config[idx] = candidate
            new_min_area = get_smallest_triangle_area(new_config)
        else:
            new_config = current.copy()
            new_config[idx] = best_candidate
            new_min_area = best_new_min_area

        # Acceptance criterion
        delta = new_min_area - min_area
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            current = new_config
            if new_min_area > best_min_area:
                best = current.copy()
                best_min_area = new_min_area

        # Stagnation handling with global perturbation
        if best_min_area > prev_best:
            stagnation_counter = 0
            current_cooling_rate = base_cooling_rate
        else:
            stagnation_counter += 1
            current_cooling_rate = base_cooling_rate

        # Trigger global perturbation on stagnation
        if stagnation_counter > 1000:
            for i in range(n):
                disp = np.random.uniform(-0.1, 0.1, 2) * T
                candidate = current[i] + disp
                for attempt in range(5):
                    if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                        break
                    candidate = 0.9 * candidate + 0.1 * current[i]
                else:
                    candidate = current[i]
                current[i] = candidate
            stagnation_counter = 0

        T *= current_cooling_rate

    return best.astype(np.float32)