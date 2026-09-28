from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()
    rng = np.random.RandomState(42)

    def project_point(p):
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

    def improve(points):
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        if best_score <= 0:
            best_score = 1e-5

        initial_temp = 0.1 * best_score
        temp = initial_temp
        base_step = 0.05
        cooling_rate = 0.995
        max_iter = 10000
        plateau_threshold = 1000
        plateau_count = 0
        n = 11

        for _ in range(max_iter):
            critical_points = set()
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = best[i], best[j], best[k]
                        area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        if area_val <= best_score + 1e-10:
                            critical_points.add(i)
                            critical_points.add(j)
                            critical_points.add(k)

            if not critical_points:
                critical_points = set(range(n))

            num_points = rng.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
            indices = rng.choice(list(critical_points), size=num_points, replace=False)

            candidate = current.copy()
            for idx in indices:
                step_size = base_step * (temp / initial_temp)
                perturbation = rng.uniform(-step_size, step_size, size=2)
                candidate[idx] += perturbation
                candidate[idx] = project_point(candidate[idx])

            candidate_score = get_smallest_triangle_area(candidate)

            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                plateau_count = 0
            else:
                plateau_count += 1

            delta = candidate_score - current_score
            if delta > 0 or (delta <= 0 and rng.rand() < np.exp(delta / temp)):
                current = candidate
                current_score = candidate_score

            temp *= cooling_rate

            if plateau_count >= plateau_threshold:
                break

        return best

    return improve