# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def _g_entrypoint():
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

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def _d_entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_triangle(p, A, B, C):
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

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        n = points.shape[0]

        T0 = 0.1 * best_score
        T = T0
        step_size0 = 0.05
        cooling_factor = 0.9995
        max_iter = 10000
        plateau_length = 1000
        no_improve_count = 0

        rng = np.random.RandomState(42)

        for _ in range(max_iter):
            current_min = get_smallest_triangle_area(best)
            min_triangles = []
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = best[i], best[j], best[k]
                        area_val = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                        if area_val <= current_min + 1e-10:
                            min_triangles.append((i, j, k))

            critical_points = set()
            for tri in min_triangles:
                critical_points.update(tri)
            critical_points = list(critical_points)

            num_perturb = rng.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
            if not critical_points:
                chosen_indices = rng.choice(n, size=num_perturb, replace=False)
            else:
                num_to_choose = min(num_perturb, len(critical_points))
                chosen_indices = rng.choice(critical_points, size=num_to_choose, replace=False)
                if num_to_choose < num_perturb:
                    remaining = list(set(range(n)) - set(critical_points))
                    if remaining:
                        additional = rng.choice(remaining, size=num_perturb - num_to_choose, replace=False)
                        chosen_indices = np.concatenate([chosen_indices, additional])

            candidate = best.copy()
            step_size = step_size0 * (T / T0)

            for idx in chosen_indices:
                perturbation = rng.uniform(-step_size, step_size, size=2)
                candidate[idx] += perturbation

            for i in range(n):
                if not is_inside_triangle(candidate[i], A, B, C):
                    candidate[i] = project_to_triangle(candidate[i], A, B, C)

            score = get_smallest_triangle_area(candidate)

            if score > best_score:
                best = candidate
                best_score = score
                no_improve_count = 0
            else:
                delta = score - best_score
                if rng.random() < np.exp(delta / T):
                    best = candidate
                    best_score = score
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            T *= cooling_factor

            if no_improve_count >= plateau_length:
                break

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)