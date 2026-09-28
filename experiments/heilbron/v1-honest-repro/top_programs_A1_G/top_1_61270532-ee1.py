import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint():
    tri = get_unit_triangle()
    A, B, C = tri

    def project(p):
        if is_inside_triangle(p, A, B, C):
            return p
        edges = [(A, B), (B, C), (C, A)]
        best_proj = None
        best_dist = float('inf')
        for (X, Y) in edges:
            v = Y - X
            w = p - X
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 < 1e-10:
                proj = X
            else:
                b = c1 / c2
                if b < 0:
                    proj = X
                elif b > 1:
                    proj = Y
                else:
                    proj = X + b * v
            dist = np.linalg.norm(p - proj)
            if dist < best_dist:
                best_dist = dist
                best_proj = proj
        return best_proj

    points = []
    for _ in range(11):
        u = random.random()
        v = random.random() * (1 - u)
        w = 1 - u - v
        p = u * A + v * B + w * C
        points.append(p)
    points = np.array(points)

    current_min = get_smallest_triangle_area(points)
    T = 0.001
    step_size_sa = 0.1
    for _ in range(10000):
        i = random.randint(0, 10)
        old_point = points[i].copy()
        move = np.random.uniform(-step_size_sa, step_size_sa, 2)
        new_point = old_point + move
        new_point = project(new_point)
        points[i] = new_point
        new_min = get_smallest_triangle_area(points)
        if new_min > current_min:
            current_min = new_min
        else:
            delta = new_min - current_min
            if random.random() < np.exp(delta / T):
                current_min = new_min
            else:
                points[i] = old_point
        T *= 0.9995

    step_size_gd = 0.01
    for _ in range(1000):
        current_min = get_smallest_triangle_area(points)
        grads = np.zeros((11, 2))
        n = 11
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    a, b, c = points[i], points[j], points[k]
                    f = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                    area_val = 0.5 * abs(f)
                    if area_val <= current_min + 1e-10:
                        sign_f = 1.0 if f >= 0 else -1.0
                        grad_i = 0.5 * sign_f * np.array([b[1] - c[1], c[0] - b[0]])
                        grad_j = 0.5 * sign_f * np.array([c[1] - a[1], -(c[0] - a[0])])
                        grad_k = 0.5 * sign_f * np.array([-(b[1] - a[1]), b[0] - a[0]])
                        grads[i] += grad_i
                        grads[j] += grad_j
                        grads[k] += grad_k

        old_points = points.copy()
        for i in range(11):
            grad_norm = np.linalg.norm(grads[i])
            if grad_norm > 1e-8:
                direction = grads[i] / grad_norm
                points[i] = old_points[i] + step_size_gd * direction
                points[i] = project(points[i])
        step_size_gd *= 0.99

    return points