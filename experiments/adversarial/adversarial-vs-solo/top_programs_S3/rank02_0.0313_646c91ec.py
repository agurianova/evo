import numpy as np
import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    side_length = np.linalg.norm(B - A)
    phi = (1 + np.sqrt(5)) / 2

    def clamp_to_triangle(P, A, B, C):
        T = np.array([B - A, C - A]).T
        try:
            coords = np.linalg.solve(T, P - A)
        except np.linalg.LinAlgError:
            return (A + B + C) / 3
        u, v = coords
        w = 1 - u - v
        bary = np.array([u, v, w])
        if u >= 0 and v >= 0 and w >= 0:
            return P
        bary = np.maximum(bary, 0)
        total = np.sum(bary)
        if total < 1e-8:
            return (A + B + C) / 3
        bary /= total
        return bary[0] * A + bary[1] * B + bary[2] * C

    def generate_hexagonal_lattice(A, B, C, side_length):
        min_x = min(A[0], B[0], C[0])
        max_x = max(A[0], B[0], C[0])
        min_y = min(A[1], B[1], C[1])
        max_y = max(A[1], B[1], C[1])
        d = 0.3
        points = []
        j = 0
        while len(points) < 11 and j < 100:
            y = min_y + j * (np.sqrt(3) / 2 * d)
            if y > max_y:
                break
            i = 0
            while len(points) < 11 and i < 100:
                x = min_x + i * d
                if j % 2 == 1:
                    x += d / 2
                if x > max_x:
                    break
                P = np.array([x, y])
                if is_inside_triangle(np.array([P]), A, B, C):
                    points.append(P)
                i += 1
            j += 1
        if len(points) < 11:
            points_per_row = [3, 3, 3, 2]
            rows = len(points_per_row)
            offsets = np.random.uniform(0.2, 0.8, size=rows)
            points = []
            for i in range(rows):
                num_pts = points_per_row[i]
                v = (i + 0.5) / rows
                for j in range(num_pts):
                    u = (j + offsets[i]) / num_pts * (1 - v)
                    P = (1 - u - v) * A + u * B + v * C
                    points.append(P)
            points = np.array(points, dtype=np.float32)
        return points

    best_points = None
    best_min_area = -1

    n_restarts = 20
    candidate_initializations = [
        [3, 3, 3, 2], [3, 3, 3, 2], [3, 3, 3, 2],
        [4, 3, 3, 1], [4, 3, 3, 1], [4, 3, 3, 1],
        [3, 2, 3, 2, 1], [3, 2, 3, 2, 1], [3, 2, 3, 2, 1],
        [4, 3, 2, 2], [5, 3, 2, 1], [4, 4, 2, 1], [3, 3, 2, 2, 1],
        "hexagonal"
    ]

    for restart in range(n_restarts):
        init = random.choice(candidate_initializations)
        if init == "hexagonal":
            points = generate_hexagonal_lattice(A, B, C, side_length)
        else:
            points_per_row = init
            rows = len(points_per_row)
            offsets = np.random.uniform(0.2, 0.8, size=rows)
            points = []
            for i in range(rows):
                num_pts = points_per_row[i]
                v = (i + 0.5) / rows
                for j in range(num_pts):
                    u = ((phi * j + offsets[i]) % 1) * (1 - v)
                    P = (1 - u - v) * A + u * B + v * C
                    points.append(P)
            points = np.array(points, dtype=np.float32)

        points += np.random.uniform(-0.01, 0.01, size=points.shape)
        for i in range(len(points)):
            points[i] = clamp_to_triangle(points[i], A, B, C)

        current_min_area = get_smallest_triangle_area(points)
        T0 = (0.01 * side_length) ** 2
        warm_up_iters = 1000
        n_iterations = 10000

        for it in range(n_iterations):
            if it < warm_up_iters:
                T_accept = T0
            else:
                decay_factor = 1.5
                T_accept = T0 * np.exp(-decay_factor * (it - warm_up_iters) / (n_iterations - warm_up_iters))

            k = np.random.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
            indices = np.random.choice(11, size=k, replace=False)
            new_points = points.copy()
            valid_move = True

            for idx in indices:
                dists = np.linalg.norm(points - points[idx], axis=1)
                dists = dists[dists > 1e-8]
                min_dist = np.min(dists) if len(dists) > 0 else 0.01 * side_length
                step_length = 0.5 * min_dist
                delta = np.random.uniform(-step_length, step_length, size=2)
                new_point = points[idx] + delta
                new_point = clamp_to_triangle(new_point, A, B, C)

                dists_to_others = np.linalg.norm(points - new_point, axis=1)
                dists_to_others[idx] = 1e10
                if np.min(dists_to_others) < 1e-8:
                    valid_move = False
                    break
                new_points[idx] = new_point

            if not valid_move:
                continue

            new_min_area = get_smallest_triangle_area(new_points)
            if new_min_area < 1e-8:
                continue

            if new_min_area > current_min_area:
                points = new_points
                current_min_area = new_min_area
            else:
                delta_area = new_min_area - current_min_area
                if np.random.random() < np.exp(delta_area / T_accept):
                    points = new_points
                    current_min_area = new_min_area

        local_iterations = 1000
        step_size_initial = 0.03 * side_length
        for loc_it in range(local_iterations):
            step_size = step_size_initial * (1 - loc_it / local_iterations)
            idx = np.random.randint(0, 11)
            new_points = points.copy()
            delta = np.random.uniform(-step_size, step_size, size=2)
            new_point = points[idx] + delta
            new_point = clamp_to_triangle(new_point, A, B, C)

            dists_to_others = np.linalg.norm(points - new_point, axis=1)
            dists_to_others[idx] = 1e10
            if np.min(dists_to_others) < 1e-8:
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