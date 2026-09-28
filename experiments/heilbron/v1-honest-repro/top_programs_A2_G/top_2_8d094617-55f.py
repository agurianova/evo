import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    def project_to_triangle(point, A, B, C):
        v0 = B - A
        v1 = C - A
        v2 = point - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        if abs(denom) < 1e-10:
            return A
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w

        if u < 0:
            u = 0
            if v + w > 0:
                v, w = v / (v + w), w / (v + w)
            else:
                v, w = 0.5, 0.5
        if v < 0:
            v = 0
            if u + w > 0:
                u, w = u / (u + w), w / (u + w)
            else:
                u, w = 0.5, 0.5
        if w < 0:
            w = 0
            if u + v > 0:
                u, v = u / (u + v), v / (u + v)
            else:
                u, v = 0.5, 0.5
        
        u = 1.0 - v - w
        return u * A + v * B + w * C

    def compute_area(a, b, c):
        return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    # Symmetric grid initialization
    base = B[0] - A[0]
    height = C[1]
    rows = [(0, 3), (1, 3), (2, 3), (3, 2)]
    points_list = []
    for row_idx, num in rows:
        y = row_idx * (height / 4.0)
        left_x = (base * y) / (2 * height)
        right_x = base - left_x
        width = right_x - left_x
        if num == 1:
            x = (left_x + right_x) / 2.0
            points_list.append([x, y])
        else:
            step = width / (num + 1)
            for j in range(1, num + 1):
                x = left_x + j * step
                points_list.append([x, y])

    points = np.array(points_list)
    valid = False
    for _ in range(100):
        perturbed = points.copy()
        for i in range(11):
            dx = random.uniform(-0.001, 0.001)
            dy = random.uniform(-0.001, 0.001)
            perturbed[i] = points[i] + [dx, dy]
            perturbed[i] = project_to_triangle(perturbed[i], A, B, C)
        min_area = get_smallest_triangle_area(perturbed)
        if min_area > 1e-8:
            points = perturbed
            valid = True
            break

    if not valid:
        points = []
        while len(points) < 11:
            s = random.random()
            t = random.random()
            if s + t > 1:
                s = 1 - s
                t = 1 - t
            point = A * (1 - s - t) + B * s + C * t
            point = np.array(point)
            distinct = True
            for p in points:
                if np.linalg.norm(p - point) < 1e-5:
                    distinct = False
                    break
            if distinct:
                points.append(point)
        points = np.array(points)

    # Hill climbing
    initial_step_size = 0.1
    step_size = initial_step_size
    max_iter = 1000
    no_improve_count = 0
    current_min = get_smallest_triangle_area(points)
    best_so_far = (points.copy(), current_min)

    for iteration in range(max_iter):
        current_min = get_smallest_triangle_area(points)
        improved = False

        # Gradient-based single-point moves
        n = 11
        min_area_val = float('inf')
        best_triangle = None
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    area = compute_area(points[i], points[j], points[k])
                    if area < min_area_val:
                        min_area_val = area
                        best_triangle = (i, j, k)

        candidates = []
        for idx in best_triangle:
            i, j, k = best_triangle
            a, b, c = points[i], points[j], points[k]
            if idx == i:
                p = a
                other1, other2 = b, c
            elif idx == j:
                p = b
                other1, other2 = a, c
            else:
                p = c
                other1, other2 = a, b

            v1 = other1 - p
            v2 = other2 - p
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            area_val = 0.5 * abs(cross)
            if area_val < 1e-10:
                continue

            if cross > 0:
                if idx == i:
                    grad = 0.5 * np.array([b[1] - c[1], c[0] - b[0]])
                elif idx == j:
                    grad = 0.5 * np.array([c[1] - a[1], a[0] - c[0]])
                else:
                    grad = 0.5 * np.array([a[1] - b[1], b[0] - a[0]])
            else:
                if idx == i:
                    grad = 0.5 * np.array([c[1] - b[1], b[0] - c[0]])
                elif idx == j:
                    grad = 0.5 * np.array([a[1] - c[1], c[0] - a[0]])
                else:
                    grad = 0.5 * np.array([b[1] - a[1], a[0] - b[0]])

            grad_norm = np.linalg.norm(grad)
            if grad_norm < 1e-10:
                continue
            grad = grad / grad_norm

            candidate_points = points.copy()
            candidate_points[idx] = points[idx] + step_size * grad
            candidate_points[idx] = project_to_triangle(candidate_points[idx], A, B, C)
            new_min = get_smallest_triangle_area(candidate_points)
            if new_min > min_area_val:
                candidates.append((new_min, candidate_points))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_candidate = candidates[0][1]
            new_min_val = candidates[0][0]
            if new_min_val > current_min:
                points = best_candidate
                current_min = new_min_val
                improved = True

        # Two-point moves (interleaved every 5 iterations or when stuck)
        if not improved or (iteration % 5 == 0):
            all_pairs = [(i, j) for i in range(11) for j in range(i + 1, 11)]
            random.shuffle(all_pairs)
            selected_pairs = all_pairs[:30]

            for i, j in selected_pairs:
                best_candidate = None
                best_min = current_min
                for _ in range(50):
                    angle1 = random.uniform(0, 2 * math.pi)
                    angle2 = random.uniform(0, 2 * math.pi)
                    candidate = points.copy()

                    dx1 = step_size * math.cos(angle1)
                    dy1 = step_size * math.sin(angle1)
                    candidate[i] = points[i] + [dx1, dy1]
                    candidate[i] = project_to_triangle(candidate[i], A, B, C)

                    dx2 = step_size * math.cos(angle2)
                    dy2 = step_size * math.sin(angle2)
                    candidate[j] = points[j] + [dx2, dy2]
                    candidate[j] = project_to_triangle(candidate[j], A, B, C)

                    new_min = get_smallest_triangle_area(candidate)
                    if new_min > best_min:
                        best_min = new_min
                        best_candidate = candidate

                if best_candidate is not None and best_min > current_min:
                    points = best_candidate
                    current_min = best_min
                    improved = True
                    break

        # Update best and check stagnation
        if current_min > best_so_far[1]:
            best_so_far = (points.copy(), current_min)
            no_improve_count = 0
        else:
            no_improve_count += 1

        # Stagnation restart
        if no_improve_count >= 50:
            points = best_so_far[0].copy()
            for i in range(11):
                points[i] += np.array([
                    random.uniform(-0.01, 0.01),
                    random.uniform(-0.01, 0.01)
                ])
                points[i] = project_to_triangle(points[i], A, B, C)
            current_min = get_smallest_triangle_area(points)
            no_improve_count = 0
            step_size = initial_step_size

        # Step size decay
        if not improved:
            step_size *= 0.99
            if step_size < 1e-5:
                step_size = 1e-5

    return points