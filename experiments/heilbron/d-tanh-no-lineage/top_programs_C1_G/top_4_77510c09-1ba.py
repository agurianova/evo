import numpy as np
import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

def entrypoint() -> np.ndarray:
    np.random.seed(42)
    random.seed(42)
    
    A, B, C = get_unit_triangle()
    n = 11

    # Multi-start initialization: generate 10 configurations with different offsets
    best_points = None
    best_min_area = -1
    for offset in np.linspace(0, 0.9, 10):
        points_list = []
        for i in range(n):
            u = (i + offset) / n
            v = (i * 1.618033988749894 + offset) % 1.0
            r1 = np.sqrt(u)
            r2 = v
            P = (1 - r1) * A + r1 * (1 - r2) * B + r1 * r2 * C
            points_list.append(P)
        points_candidate = np.array(points_list)
        if not is_inside_triangle(points_candidate, A, B, C):
            continue
        min_area = get_smallest_triangle_area(points_candidate)
        if min_area > best_min_area:
            best_min_area = min_area
            best_points = points_candidate

    if best_points is None:
        # Fallback: use last candidate
        best_points = points_candidate

    points = best_points
    current_min_area = best_min_area

    # Set up optimization parameters
    n_points = len(points)
    max_iter = 1000
    initial_temperature = 0.1
    temperature = initial_temperature
    initial_step = 0.01

    for iter in range(max_iter):
        # Determine move type: with probability p_random do random move, else greedy
        p_random = 0.5 * (temperature / initial_temperature)
        candidate_points = None

        if random.random() < p_random:
            # Random perturbation: move one random point in a random direction
            idx = random.randint(0, n_points-1)
            direction = np.random.randn(2)
            direction = direction / np.linalg.norm(direction)
            step_size = initial_step * (0.999 ** iter) * (1 + 0.5 * random.random())
            candidate_points = points.copy()
            new_point = points[idx] + step_size * direction
            if not is_inside_triangle(new_point.reshape(1,2), A, B, C):
                temp_step = step_size
                while temp_step > 1e-8:
                    temp_point = points[idx] + temp_step * direction
                    if is_inside_triangle(temp_point.reshape(1,2), A, B, C):
                        new_point = temp_point
                        break
                    temp_step *= 0.5
                else:
                    new_point = points[idx]
            candidate_points[idx] = new_point
        else:
            # Greedy move: find the smallest triangle and move its vertices
            min_area_val = float('inf')
            min_indices = (0, 1, 2)
            for i in range(n_points):
                for j in range(i + 1, n_points):
                    for k in range(j + 1, n_points):
                        Ax, Ay = points[i]
                        Bx, By = points[j]
                        Cx, Cy = points[k]
                        area = 0.5 * abs((Bx - Ax) * (Cy - Ay) - (Cx - Ax) * (By - Ay))
                        if area < min_area_val:
                            min_area_val = area
                            min_indices = (i, j, k)

            i, j, k = min_indices
            base_jk = points[k] - points[j]
            normal_jk = np.array([-base_jk[1], base_jk[0]])
            normal_jk = normal_jk / np.linalg.norm(normal_jk)
            d_i = np.dot(points[i] - points[j], normal_jk)
            dir_i = np.sign(d_i) * normal_jk

            base_ik = points[k] - points[i]
            normal_ik = np.array([-base_ik[1], base_ik[0]])
            normal_ik = normal_ik / np.linalg.norm(normal_ik)
            d_j = np.dot(points[j] - points[i], normal_ik)
            dir_j = np.sign(d_j) * normal_ik

            base_ij = points[j] - points[i]
            normal_ij = np.array([-base_ij[1], base_ij[0]])
            normal_ij = normal_ij / np.linalg.norm(normal_ij)
            d_k = np.dot(points[k] - points[i], normal_ij)
            dir_k = np.sign(d_k) * normal_ij

            step_size = initial_step * (0.999 ** iter)
            candidate_points = points.copy()

            # Move point i
            new_point = points[i] + step_size * dir_i
            if not is_inside_triangle(new_point.reshape(1, 2), A, B, C):
                temp_step = step_size
                while temp_step > 1e-8:
                    temp_point = points[i] + temp_step * dir_i
                    if is_inside_triangle(temp_point.reshape(1, 2), A, B, C):
                        new_point = temp_point
                        break
                    temp_step *= 0.5
                else:
                    new_point = points[i]
            candidate_points[i] = new_point

            # Move point j
            new_point = points[j] + step_size * dir_j
            if not is_inside_triangle(new_point.reshape(1, 2), A, B, C):
                temp_step = step_size
                while temp_step > 1e-8:
                    temp_point = points[j] + temp_step * dir_j
                    if is_inside_triangle(temp_point.reshape(1, 2), A, B, C):
                        new_point = temp_point
                        break
                    temp_step *= 0.5
                else:
                    new_point = points[j]
            candidate_points[j] = new_point

            # Move point k
            new_point = points[k] + step_size * dir_k
            if not is_inside_triangle(new_point.reshape(1, 2), A, B, C):
                temp_step = step_size
                while temp_step > 1e-8:
                    temp_point = points[k] + temp_step * dir_k
                    if is_inside_triangle(temp_point.reshape(1, 2), A, B, C):
                        new_point = temp_point
                        break
                    temp_step *= 0.5
                else:
                    new_point = points[k]
            candidate_points[k] = new_point

        candidate_min_area = get_smallest_triangle_area(candidate_points)
        delta = candidate_min_area - current_min_area

        # Acceptance criterion
        if delta >= 0:
            accept = True
        else:
            if random.random() < np.exp(delta / temperature):
                accept = True
            else:
                accept = False

        if accept:
            points = candidate_points
            current_min_area = candidate_min_area

        # Update temperature
        temperature *= 0.995

    return points