import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

def entrypoint() -> np.ndarray:
    base_seed = 42
    best_points = None
    best_min_area = -1.0

    def run_hill_climbing(points, A, B, C):
        step_size = 0.1
        step_anneal = 0.99
        max_iter = 1000
        n = 11

        for _ in range(max_iter):
            current_min = get_smallest_triangle_area(points)
            
            # Identify top 5 smallest triangles
            triangle_list = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = points[i]
                        x2, y2 = points[j]
                        x3, y3 = points[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        triangle_list.append((area, i, j, k))
            
            triangle_list.sort(key=lambda x: x[0])
            top5 = triangle_list[:5]
            critical_points = set()
            for area, i, j, k in top5:
                critical_points.add(i)
                critical_points.add(j)
                critical_points.add(k)
            critical_points = list(critical_points)

            improved = False
            for idx in critical_points:
                best_candidate = None
                best_min = current_min
                for _ in range(100):
                    angle = random.uniform(0, 2 * math.pi)
                    dx = step_size * math.cos(angle)
                    dy = step_size * math.sin(angle)
                    candidate = points.copy()
                    candidate[idx] = points[idx] + [dx, dy]

                    if not is_inside_triangle(candidate[idx], A, B, C):
                        candidate[idx] = points[idx] - [dx, dy]
                        if not is_inside_triangle(candidate[idx], A, B, C):
                            continue

                    new_min = get_smallest_triangle_area(candidate)
                    if new_min > best_min:
                        best_min = new_min
                        best_candidate = candidate

                if best_candidate is not None and best_min > current_min:
                    points = best_candidate
                    current_min = best_min
                    improved = True

            if not improved:
                step_size *= step_anneal
                if step_size < 1e-5:
                    break

            
        return points

    for trial in range(5):
        np.random.seed(base_seed + trial)
        random.seed(base_seed + trial)

        tri = get_unit_triangle()
        A, B, C = tri
        h = C[1]
        s = B[0]

        rows = [
            (1, 0.95),
            (2, 0.7),
            (3, 0.45),
            (3, 0.2),
            (2, 0.05)
        ]
        points = []
        for k, r in rows:
            y = r * h
            width = s * (1 - r)
            if k == 1:
                points.append([s / 2, y])
            else:
                for i in range(k):
                    x = (s - width) / 2 + i * (width / (k - 1))
                    points.append([x, y])
        points = np.array(points)

        # Apply larger perturbation
        perturb_vectors = np.random.uniform(-0.02, 0.02, (11, 2))
        for i in range(11):
            candidate_pt = points[i] + perturb_vectors[i]
            if is_inside_triangle(candidate_pt, A, B, C):
                points[i] = candidate_pt
            else:
                candidate_pt2 = points[i] - perturb_vectors[i] * 0.5
                if is_inside_triangle(candidate_pt2, A, B, C):
                    points[i] = candidate_pt2

        points = run_hill_climbing(points, A, B, C)

        min_area = get_smallest_triangle_area(points)
        if min_area > best_min_area:
            best_min_area = min_area
            best_points = points.copy()

    return best_points