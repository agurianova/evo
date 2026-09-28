import numpy as np
import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    side_length = np.linalg.norm(B - A)

    def correct_boundary(P, A, B, C, side_length):
        for _ in range(10):
            if is_inside_triangle(np.array([P]), A, B, C):
                return P
            v0 = B - A
            v1 = C - A
            v2 = P - A
            d00 = np.dot(v0, v0)
            d01 = np.dot(v0, v1)
            d11 = np.dot(v1, v1)
            d20 = np.dot(v2, v0)
            d21 = np.dot(v2, v1)
            denom = d00 * d11 - d01 * d01
            if abs(denom) < 1e-10:
                return (A + B + C) / 3
            v = (d11 * d20 - d01 * d21) / denom
            w = (d00 * d21 - d01 * d20) / denom
            u = 1 - v - w

            min_step = 0.001 * side_length
            max_step = 0.01 * side_length

            if u < 0:
                BC = C - B
                t = np.dot(P - B, BC) / (np.dot(BC, BC) + 1e-10)
                D = B + t * BC
                direction = A - D
                if np.linalg.norm(direction) < 1e-10:
                    direction = np.array([-BC[1], BC[0]])
                else:
                    direction = direction / np.linalg.norm(direction)
                step = 0.2 * (-u) / side_length
                step = min(max_step, max(min_step, step))
                P = D + step * direction
            elif v < 0:
                AC = C - A
                t = np.dot(P - A, AC) / (np.dot(AC, AC) + 1e-10)
                D = A + t * AC
                direction = B - D
                if np.linalg.norm(direction) < 1e-10:
                    direction = np.array([-AC[1], AC[0]])
                else:
                    direction = direction / np.linalg.norm(direction)
                step = 0.2 * (-v) / side_length
                step = min(max_step, max(min_step, step))
                P = D + step * direction
            elif w < 0:
                AB = B - A
                t = np.dot(P - A, AB) / (np.dot(AB, AB) + 1e-10)
                D = A + t * AB
                direction = C - D
                if np.linalg.norm(direction) < 1e-10:
                    direction = np.array([-AB[1], AB[0]])
                else:
                    direction = direction / np.linalg.norm(direction)
                step = 0.2 * (-w) / side_length
                step = min(max_step, max(min_step, step))
                P = D + step * direction
            else:
                break
        return P

    best_points = None
    best_min_area = -1

    n_restarts = 50
    candidate_row_structures = [
        [3, 3, 3, 2],
        [4, 3, 2, 2],
        [5, 3, 2, 1],
        [4, 4, 2, 1],
        [3, 3, 2, 2, 1],
        [4, 3, 3, 1],
        [5, 2, 2, 2],
        [3, 4, 2, 2],
        [4, 4, 3],
        [5, 4, 1, 1],
        [6, 3, 2],
        [3, 3, 4, 1]
    ]

    for restart in range(n_restarts):
        points_per_row = random.choice(candidate_row_structures)
        rows = len(points_per_row)
        offsets = np.random.uniform(0.2, 0.8, size=rows)

        points = []
        for i in range(rows):
            num_pts = points_per_row[i]
            v = (i + 0.5) / rows
            for j in range(num_pts):
                u = (j + offsets[i]) / num_pts * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                mag = 0.03 * (rows - i) / rows
                P += np.random.uniform(-mag, mag, size=2)
                points.append(P)
        points = np.array(points, dtype=np.float32)

        for i in range(len(points)):
            if not is_inside_triangle(np.array([points[i]]), A, B, C):
                points[i] = correct_boundary(points[i], A, B, C, side_length)

        current_min_area = get_smallest_triangle_area(points)
        T0 = max(1e-5, 0.5 * current_min_area)
        warm_up_iters = 1000
        n_iterations = 10000

        for it in range(n_iterations):
            if it < 0.3 * n_iterations:
                probs = [0.4, 0.4, 0.2]
            elif it < 0.7 * n_iterations:
                probs = [0.6, 0.3, 0.1]
            else:
                probs = [0.7, 0.25, 0.05]

            k = np.random.choice([1, 2, 3], p=probs)
            indices = np.random.choice(11, size=k, replace=False)
            new_points = points.copy()
            valid_move = True

            for idx in indices:
                dists = np.linalg.norm(points - points[idx], axis=1)
                dists = dists[dists > 1e-8]
                min_dist = np.min(dists) if len(dists) > 0 else 0.01 * side_length
                
                step_length = max(0.001 * side_length, 0.8 * min_dist)
                delta = np.random.uniform(-step_length, step_length, size=2)
                new_point = points[idx] + delta
                
                if not is_inside_triangle(np.array([new_point]), A, B, C):
                    valid_move = False
                    break
                new_points[idx] = new_point

            if not valid_move:
                continue

            new_min_area = get_smallest_triangle_area(new_points)
            if new_min_area < 1e-8:
                continue

            if it < warm_up_iters:
                T_accept = T0
            else:
                decay_factor = 5.0
                T_accept = T0 * np.exp(-decay_factor * (it - warm_up_iters) / (n_iterations - warm_up_iters))

            if new_min_area > current_min_area:
                points = new_points
                current_min_area = new_min_area
                accepted = True
            else:
                delta_area = new_min_area - current_min_area
                if np.random.random() < np.exp(delta_area / T_accept):
                    points = new_points
                    current_min_area = new_min_area
                    accepted = True
                else:
                    accepted = False

        local_iterations = 1000
        step_size_initial = 0.01 * side_length
        for loc_it in range(local_iterations):
            step_size = step_size_initial * (1 - loc_it / local_iterations)
            idx = np.random.randint(0, 11)
            new_points = points.copy()
            delta = np.random.uniform(-step_size, step_size, size=2)
            new_point = points[idx] + delta
            
            if not is_inside_triangle(np.array([new_point]), A, B, C):
                continue
                
            new_points[idx] = new_point
            new_min_area = get_smallest_triangle_area(new_points)
            
            if new_min_area >= current_min_area - 1e-10:
                points = new_points
                current_min_area = new_min_area

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_points = points.copy()

    return best_points