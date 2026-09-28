import random
import numpy as np
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    width = B[0] - A[0]
    mid_x = (A[0] + B[0]) / 2
    height = C[1]

    def expand_to_full(reduced):
        left_points = reduced[:5]
        axis_point = reduced[5]
        right_points = np.array([[width - x, y] for x, y in left_points])
        full_points = np.vstack([left_points, right_points, [axis_point]])
        return full_points

    def check_distinctness(points, tol=1e-5):
        n = len(points)
        for i in range(n):
            for j in range(i+1, n):
                if np.linalg.norm(points[i] - points[j]) < tol:
                    return False
        return True

    def generate_initial_points(n_reduced=6, max_retry=1000):
        left_points = []
        for _ in range(5):
            retry = 0
            while retry < max_retry:
                u = random.betavariate(0.5, 0.5)
                v = random.betavariate(0.5, 0.5)
                if u + v > 1:
                    u, v = 1 - u, 1 - v
                w = 1 - u - v
                P = u * A + v * B + w * C
                if P[0] > mid_x:
                    P = np.array([width - P[0], P[1]])
                if P[0] >= mid_x - 1e-10:
                    retry += 1
                    continue
                if len(left_points) > 0:
                    dists = np.linalg.norm(np.array(left_points) - P, axis=1)
                    if np.min(dists) < 1e-5:
                        retry += 1
                        continue
                left_points.append(P)
                break
            else:
                left_points.append(P)

        retry = 0
        while retry < max_retry:
            y = random.betavariate(0.5, 0.5) * height
            P_axis = np.array([mid_x, y])
            if len(left_points) > 0:
                dists = np.linalg.norm(np.array(left_points) - P_axis, axis=1)
                if np.min(dists) < 1e-5:
                    retry += 1
                    continue
            break
        else:
            P_axis = np.array([mid_x, y])

        return np.array(left_points + [P_axis])

    def simulated_annealing(initial_reduced, max_iter, initial_temp, final_temp, initial_step):
        reduced = initial_reduced.copy()
        full_points = expand_to_full(reduced)
        current_min_area = get_smallest_triangle_area(full_points)
        temp = initial_temp

        for i in range(max_iter):
            current_step = initial_step * (temp / initial_temp)

            r = random.random()
            if r < 0.7:
                num_points = 1
            elif r < 0.9:
                num_points = 2
            else:
                num_points = 3

            indices = random.sample(range(6), num_points)
            new_reduced = reduced.copy()
            valid_move = True

            for idx in indices:
                dx = random.uniform(-current_step, current_step)
                dy = random.uniform(-current_step, current_step)
                if idx < 5:
                    new_x = reduced[idx, 0] + dx
                    new_y = reduced[idx, 1] + dy
                    new_point = np.array([new_x, new_y])
                    if not is_inside_triangle(new_point, A, B, C):
                        valid_move = False
                        break
                    if new_point[0] > mid_x:
                        new_point[0] = width - new_point[0]
                    if new_point[0] >= mid_x - 1e-10:
                        valid_move = False
                        break
                    new_reduced[idx] = new_point
                else:
                    new_y = reduced[idx, 1] + dy
                    if new_y < 0 or new_y > height:
                        valid_move = False
                        break
                    new_reduced[idx] = np.array([mid_x, new_y])

            if not valid_move:
                continue

            full_points = expand_to_full(new_reduced)
            if not is_inside_triangle(full_points, A, B, C) or not check_distinctness(full_points):
                continue

            new_min_area = get_smallest_triangle_area(full_points)
            delta = new_min_area - current_min_area
            if delta > 0 or random.random() < math.exp(delta / temp):
                reduced = new_reduced
                current_min_area = new_min_area

            temp = initial_temp * (final_temp / initial_temp) ** (i / max_iter)
            if temp < final_temp:
                temp = final_temp

        return reduced, current_min_area

    best_reduced = None
    best_min_area = -1
    for restart in range(5):
        random.seed(42 + restart)
        np.random.seed(42 + restart)
        initial_reduced = generate_initial_points(6)
        reduced, min_area = simulated_annealing(
            initial_reduced,
            max_iter=20000,
            initial_temp=0.01,
            final_temp=0.0001,
            initial_step=0.1
        )
        if min_area > best_min_area:
            best_min_area = min_area
            best_reduced = reduced

    return expand_to_full(best_reduced)