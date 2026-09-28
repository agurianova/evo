import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()

    def get_smallest_triangle_indices(points):
        n = len(points)
        min_area = float('inf')
        best_indices = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    x1, y1 = points[i]
                    x2, y2 = points[j]
                    x3, y3 = points[k]
                    area = 0.5 * abs((x2 - x1)*(y3 - y1) - (x3 - x1)*(y2 - y1))
                    if area < min_area:
                        min_area = area
                        best_indices = (i, j, k)
        return best_indices, min_area

    def project_point(point, original, A, B, C, max_iter=5):
        if is_inside_triangle(point, A, B, C):
            return point
        low = 0.0
        high = 1.0
        for _ in range(max_iter):
            mid = (low + high) / 2
            candidate = original + mid * (point - original)
            if is_inside_triangle(candidate, A, B, C):
                low = mid
            else:
                high = mid
        return original + low * (point - original)

    def generate_perturbed_grid():
        num_rows = 4
        num_points_per_row = [4, 3, 2, 2]
        points = []
        for i in range(num_rows):
            v = i / num_rows
            n = num_points_per_row[i]
            for j in range(n):
                if n > 1:
                    u = j * ((1 - v) / (n - 1))
                else:
                    u = (1 - v) * 0.5
                du = random.uniform(-0.01, 0.01)
                dv = random.uniform(-0.01, 0.01)
                new_u = u + du
                new_v = v + dv
                if new_u < 0:
                    new_u = 0
                if new_v < 0:
                    new_v = 0
                if new_u + new_v > 1:
                    scale = 1.0 / (new_u + new_v)
                    new_u *= scale
                    new_v *= scale
                w = 1.0 - new_u - new_v
                P = new_u * A + new_v * B + w * C
                points.append(P)
        return np.array(points)

    def simulated_annealing(points):
        current_points = points.copy()
        current_min_area = get_smallest_triangle_area(current_points)
        best_points = current_points.copy()
        best_min_area = current_min_area

        initial_temp = 0.001
        cooling_rate = 0.995
        initial_step = 0.05
        max_iter = 10000

        temperature = initial_temp
        step_size = initial_step

        for iter in range(max_iter):
            if random.random() < 0.8:
                idx = random.randint(0, 10)
                original_point = current_points[idx]
                dx = step_size * random.gauss(0, 1)
                dy = step_size * random.gauss(0, 1)
                new_point = original_point + np.array([dx, dy])
                new_point = project_point(new_point, original_point, A, B, C)
                new_points = current_points.copy()
                new_points[idx] = new_point
            else:
                indices, _ = get_smallest_triangle_indices(current_points)
                i, j, k = indices
                new_points = current_points.copy()
                for idx in [i, j, k]:
                    original_point = current_points[idx]
                    dx = step_size * random.gauss(0, 1)
                    dy = step_size * random.gauss(0, 1)
                    new_point = original_point + np.array([dx, dy])
                    new_point = project_point(new_point, original_point, A, B, C)
                    new_points[idx] = new_point

            new_min_area = get_smallest_triangle_area(new_points)
            delta = new_min_area - current_min_area

            if delta > 0 or random.random() < math.exp(delta / temperature):
                current_points = new_points
                current_min_area = new_min_area
                if new_min_area > best_min_area:
                    best_points = new_points.copy()
                    best_min_area = new_min_area

            temperature *= cooling_rate
            step_size *= cooling_rate

            if temperature < 1e-8:
                break

        return best_points, best_min_area

    best_config = None
    best_min_area = -1

    for _ in range(50):
        points = generate_perturbed_grid()
        points, min_area = simulated_annealing(points)
        if min_area > best_min_area:
            best_config = points
            best_min_area = min_area

    return best_config