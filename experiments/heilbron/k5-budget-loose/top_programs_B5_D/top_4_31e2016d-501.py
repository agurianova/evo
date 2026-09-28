from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def get_smallest_triangle_indices(points):
        n = points.shape[0]
        min_area = float('inf')
        min_indices = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    x1, y1 = points[i]
                    x2, y2 = points[j]
                    x3, y3 = points[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        return min_indices

    def project_point(p, A, B, C):
        if is_inside_triangle(p, A, B, C):
            return p
        edges = [(A, B), (B, C), (C, A)]
        min_dist = float('inf')
        closest = None
        for (v1, v2) in edges:
            v = v2 - v1
            w = p - v1
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 < 1e-10:
                b = 0
            else:
                b = c1 / c2
            if b < 0:
                proj = v1
            elif b > 1:
                proj = v2
            else:
                proj = v1 + b * v
            dist = np.linalg.norm(p - proj)
            if dist < min_dist:
                min_dist = dist
                closest = proj
        return closest

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        max_iter = 200
        initial_temp = 0.001
        initial_step = 0.05
        step_decay = 0.99

        for i in range(max_iter):
            temp = initial_temp * (0.99 ** i)
            step = initial_step * (step_decay ** i)

            i1, i2, i3 = get_smallest_triangle_indices(current)
            indices = [i1, i2, i3]

            candidate = current.copy()
            for idx in indices:
                perturbation = np.random.normal(0, step, 2)
                candidate[idx] += perturbation

            for idx in indices:
                candidate[idx] = project_point(candidate[idx], A, B, C)

            candidate_score = get_smallest_triangle_area(candidate)

            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temp):
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score

        return best

    return improve