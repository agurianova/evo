import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def project_to_edge(P, A, B):
    AB = B - A
    AP = P - A
    ab2 = np.dot(AB, AB)
    if ab2 < 1e-10:
        return A
    t = np.dot(AP, AB) / ab2
    t = max(0.0, min(1.0, t))
    return A + t * AB

def project_to_triangle(P, A, B, C):
    proj_AB = project_to_edge(P, A, B)
    proj_BC = project_to_edge(P, B, C)
    proj_CA = project_to_edge(P, C, A)
    
    d_AB = np.linalg.norm(P - proj_AB)
    d_BC = np.linalg.norm(P - proj_BC)
    d_CA = np.linalg.norm(P - proj_CA)
    
    if d_AB <= d_BC and d_AB <= d_CA:
        return proj_AB
    elif d_BC <= d_AB and d_BC <= d_CA:
        return proj_BC
    else:
        return proj_CA

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    M_x = (A[0] + B[0]) / 2.0
    M = np.array([M_x, 0.0])
    
    def hill_climbing(initial_points, max_iter=50000, early_stop=1000):
        points = np.array(initial_points, copy=True)
        current_min_area = get_smallest_triangle_area(points)
        best_min_area = current_min_area
        best_points = points.copy()
        step_size = 0.1
        decay_rate = 0.995
        min_step = 1e-4
        no_improve_count = 0

        for i in range(max_iter):
            if random.random() < 0.8:
                base_idx = random.randint(0, 5)
                if base_idx < 5:
                    m = 2
                    scale = 1.0 / np.sqrt(m)
                    angle = random.uniform(0, 2*np.pi)
                    dx = step_size * scale * np.cos(angle)
                    dy = step_size * scale * np.sin(angle)
                    
                    new_left0 = points[base_idx] + np.array([dx, dy])
                    if not is_inside_triangle(new_left0, A, B, C):
                        new_left = project_to_triangle(new_left0, A, B, C)
                        new_right = np.array([2*M_x - new_left[0], new_left[1]])
                    else:
                        new_left = new_left0
                        new_right = np.array([2*M_x - new_left0[0], new_left0[1]])

                    old_left = points[base_idx].copy()
                    old_right = points[base_idx+5].copy()
                    
                    points[base_idx] = new_left
                    points[base_idx+5] = new_right
                    new_min_area = get_smallest_triangle_area(points)

                    if new_min_area > current_min_area:
                        current_min_area = new_min_area
                        if new_min_area > best_min_area:
                            best_min_area = new_min_area
                            best_points = points.copy()
                        no_improve_count = 0
                    else:
                        points[base_idx] = old_left
                        points[base_idx+5] = old_right
                        no_improve_count += 1
                else:
                    m = 1
                    scale = 1.0 / np.sqrt(m)
                    dy = step_size * scale * (1 if random.random() < 0.5 else -1)
                    new_axis0 = points[10] + np.array([0, dy])
                    if not is_inside_triangle(new_axis0, A, B, C):
                        new_axis = project_to_triangle(new_axis0, A, B, C)
                    else:
                        new_axis = new_axis0

                    old_axis = points[10].copy()
                    points[10] = new_axis
                    new_min_area = get_smallest_triangle_area(points)
                    
                    if new_min_area > current_min_area:
                        current_min_area = new_min_area
                        if new_min_area > best_min_area:
                            best_min_area = new_min_area
                            best_points = points.copy()
                        no_improve_count = 0
                    else:
                        points[10] = old_axis
                        no_improve_count += 1
            else:
                base_idx_left = random.randint(0, 4)
                scale = 1.0 / np.sqrt(3)
                angle = random.uniform(0, 2*np.pi)
                dx = step_size * scale * np.cos(angle)
                dy_left = step_size * scale * np.sin(angle)
                dy_axis = step_size * scale * (1 if random.random() < 0.5 else -1)

                new_left0 = points[base_idx_left] + np.array([dx, dy_left])
                if not is_inside_triangle(new_left0, A, B, C):
                    new_left = project_to_triangle(new_left0, A, B, C)
                    new_right = np.array([2*M_x - new_left[0], new_left[1]])
                else:
                    new_left = new_left0
                    new_right = np.array([2*M_x - new_left0[0], new_left0[1]])

                new_axis0 = points[10] + np.array([0, dy_axis])
                if not is_inside_triangle(new_axis0, A, B, C):
                    new_axis = project_to_triangle(new_axis0, A, B, C)
                else:
                    new_axis = new_axis0

                old_left = points[base_idx_left].copy()
                old_right = points[base_idx_left+5].copy()
                old_axis = points[10].copy()

                points[base_idx_left] = new_left
                points[base_idx_left+5] = new_right
                points[10] = new_axis
                new_min_area = get_smallest_triangle_area(points)

                if new_min_area > current_min_area:
                    current_min_area = new_min_area
                    if new_min_area > best_min_area:
                        best_min_area = new_min_area
                        best_points = points.copy()
                    no_improve_count = 0
                else:
                    points[base_idx_left] = old_left
                    points[base_idx_left+5] = old_right
                    points[10] = old_axis
                    no_improve_count += 1

            if i % 100 == 0:
                step_size *= decay_rate
                if step_size < min_step:
                    step_size = min_step

            if step_size < min_step and no_improve_count >= early_stop:
                break

        return best_points, best_min_area

    best_config = None
    best_area = -1
    num_starts = 50

    for _ in range(num_starts):
        points_left = []
        for i in range(5):
            while True:
                s = random.random()
                t = random.random() * (1 - s)
                P = (1 - s - t) * A + s * M + t * C
                if all(np.linalg.norm(P - q) > 1e-5 for q in points_left):
                    points_left.append(P)
                    break

        while True:
            u = random.random()
            P_axis = (1 - u) * M + u * C
            right_points = [np.array([2*M_x - p[0], p[1]]) for p in points_left]
            all_points_so_far = points_left + right_points
n            if all(np.linalg.norm(P_axis - q) > 1e-5 for q in all_points_so_far):
                break

        points = np.array(points_left + right_points + [P_axis])
        config, area = hill_climbing(points)
        if area > best_area:
            best_area = area
            best_config = config

    return best_config