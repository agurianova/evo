import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Precompute reflection matrix for symmetry enforcement
    M = (B + C) / 2.0
    D = M - A
    norm_D = np.linalg.norm(D)
    if norm_D < 1e-10:
        d = np.array([1.0, 0.0])
    else:
        d = D / norm_D
    R = 2 * np.outer(d, d) - np.eye(2)

    # Generate symmetric initial configuration (center + 5 pairs)
    points = []
    # Center point (on symmetry axis)
    a_center = 1/3.0
    u_center = 1/3.0
    v_center = 1/3.0
    P_center = (1 - u_center - v_center) * A + u_center * B + v_center * C
    points.append(P_center)

    # 5 symmetric pairs
    fractions = [0.3] * 5
    a_vals = [0.1, 0.3, 0.5, 0.7, 0.9]  # Heights from base (a = weight for apex)
    for i in range(5):
        a_i = a_vals[i]
        s = 1 - a_i  # u + v = s
        u_left = s / 2 * (1 + fractions[i])
        v_left = s / 2 * (1 - fractions[i])
        P_left = a_i * A + u_left * B + v_left * C
        P_right = a_i * A + v_left * B + u_left * C  # Symmetric counterpart
        points.append(P_left)
        points.append(P_right)

    # Assign symmetry partners
    partner = np.zeros(11, dtype=int)
    partner[0] = 0  # Center point
    for i in range(5):
        idx_left = 1 + 2 * i
        idx_right = 1 + 2 * i + 1
        partner[idx_left] = idx_right
        partner[idx_right] = idx_left

    # Apply symmetric perturbation with reduced magnitude
    for i in range(11):
        if partner[i] == i:  # Center point
            V = np.random.uniform(-0.02, 0.02, 2)
            proj = np.dot(V, d) * d  # Project onto symmetry axis
            candidate = points[i] + proj
            for attempt in range(5):
                if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                    break
                candidate = 0.9 * candidate + 0.1 * points[i]
            else:
                candidate = points[i]
            points[i] = candidate
        else:
            if i < partner[i]:  # Process each pair once
                V = np.random.uniform(-0.02, 0.02, 2)
                candidate_i = points[i] + V
                candidate_partner = points[partner[i]] + R @ V

                # Project candidate_i to triangle
                for attempt in range(5):
                    if is_inside_triangle(candidate_i.reshape(1, 2), A, B, C):
                        break
                    candidate_i = 0.9 * candidate_i + 0.1 * points[i]
                else:
                    candidate_i = points[i]

                # Project candidate_partner to triangle
                for attempt in range(5):
                    if is_inside_triangle(candidate_partner.reshape(1, 2), A, B, C):
                        break
                    candidate_partner = 0.9 * candidate_partner + 0.1 * points[partner[i]]
                else:
                    candidate_partner = points[partner[i]]

                points[i] = candidate_i
                points[partner[i]] = candidate_partner

    current = np.array(points)
    best = current.copy()
    best_min_area = get_smallest_triangle_area(best)

    # Simulated annealing parameters
    T = 0.5  # Increased from 0.2
    max_iter = 20000
    cooling_rate = 0.9998

    for iter_index in range(max_iter):
        n = len(current)

        # Global perturbation with symmetry enforcement (more frequent and larger steps)
        if iter_index % 500 == 0 and iter_index > 0:
            for i in range(n):
                if i < partner[i] or partner[i] == i:
                    disp = np.random.uniform(-0.15, 0.15, 2)  # Increased from 0.1
                    candidate_i = current[i] + disp
                    for attempt in range(5):
                        if is_inside_triangle(candidate_i.reshape(1, 2), A, B, C):
                            break
                        candidate_i = 0.9 * candidate_i + 0.1 * current[i]
                    else:
                        candidate_i = current[i]

                    if partner[i] != i:
                        disp_partner = R @ disp
                        candidate_partner = current[partner[i]] + disp_partner
                        for attempt in range(5):
                            if is_inside_triangle(candidate_partner.reshape(1, 2), A, B, C):
                                break
                            candidate_partner = 0.9 * candidate_partner + 0.1 * current[partner[i]]
                        else:
                            candidate_partner = current[partner[i]]
                    else:
                        candidate_partner = candidate_i

                    current[i] = candidate_i
                    if partner[i] != i:
                        current[partner[i]] = candidate_partner

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
        threshold = min_area * 1.2 if min_area < 0.02 else min_area * 1.1

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

        # Adaptive step size with increased factor
        min_step = 0.005 * (1 - iter_index / max_iter) ** 2
        base_step = T * 0.3  # Increased from 0.1
        step_size = max(min_step, base_step)

        # 8-directional sampling with symmetry enforcement
        best_candidate_idx = None
        best_candidate_partner = None
        best_new_min_area = -1
        for angle in range(0, 360, 45):
            rad = np.radians(angle)
            direction = np.array([np.cos(rad), np.sin(rad)])
            disp = step_size * direction

            candidate_idx = current[idx] + disp
            candidate_temp_idx = candidate_idx.copy()
            for attempt in range(5):
                if is_inside_triangle(candidate_temp_idx.reshape(1, 2), A, B, C):
                    break
                candidate_temp_idx = 0.9 * candidate_temp_idx + 0.1 * current[idx]
            else:
                continue

            if partner[idx] != idx:
                disp_partner = R @ disp
                candidate_partner = current[partner[idx]] + disp_partner
                candidate_temp_partner = candidate_partner.copy()
                for attempt in range(5):
                    if is_inside_triangle(candidate_temp_partner.reshape(1, 2), A, B, C):
                        break
                    candidate_temp_partner = 0.9 * candidate_temp_partner + 0.1 * current[partner[idx]]
                else:
                    continue
            else:
                candidate_temp_partner = candidate_temp_idx

            new_config = current.copy()
            new_config[idx] = candidate_temp_idx
            if partner[idx] != idx:
                new_config[partner[idx]] = candidate_temp_partner

            new_min_area_temp = get_smallest_triangle_area(new_config)
            if new_min_area_temp > best_new_min_area:
                best_new_min_area = new_min_area_temp
                best_candidate_idx = candidate_temp_idx
                best_candidate_partner = candidate_temp_partner

        if best_candidate_idx is None:
            continue

        # Acceptance criterion
        new_config = current.copy()
        new_config[idx] = best_candidate_idx
        if partner[idx] != idx:
            new_config[partner[idx]] = best_candidate_partner
        new_min_area = best_new_min_area

        delta = new_min_area - min_area
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            current = new_config
            if new_min_area > best_min_area:
                best = current.copy()
                best_min_area = new_min_area

        # Cool down
        T *= cooling_rate

    return best.astype(np.float32)