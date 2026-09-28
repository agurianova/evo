from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def project_point_to_segment(p, a, b):
        ab = b - a
        ap = p - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
        t = max(0.0, min(1.0, t))
        return a + t * ab

    def project_to_triangle(p):
        if is_inside_triangle(p.reshape(1, 2), A, B, C):
            return p
        edges = [(A, B), (B, C), (C, A)]
        best_point = None
        best_dist = float('inf')
        for edge in edges:
            proj = project_point_to_segment(p, edge[0], edge[1])
            dist = np.linalg.norm(p - proj)
            if dist < best_dist:
                best_dist = dist
                best_point = proj
        return best_point

    def improve(points):
        def compute_triangle_area(a, b, c):
            return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))

        def find_smallest_triangle(pts):
            n = pts.shape[0]
            min_area = float('inf')
            min_indices = (0, 1, 2)
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        area = compute_triangle_area(pts[i], pts[j], pts[k])
                        if area < min_area:
                            min_area = area
                            min_indices = (i, j, k)
            return min_area, min_indices[0], min_indices[1], min_indices[2]

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        T = 0.1
        decay = 0.99

        for _ in range(500):
            _, i, j, k = find_smallest_triangle(current)
            A_pt = current[i]
            B_pt = current[j]
            C_pt = current[k]

            f = (B_pt[0] - A_pt[0]) * (C_pt[1] - A_pt[1]) - (C_pt[0] - A_pt[0]) * (B_pt[1] - A_pt[1])
            signed_area = 0.5 * f
            sign = 1 if signed_area > 0 else -1

            dir_i = np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]]) * sign
            dir_j = np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[0]]) * sign
            dir_k = np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]]) * sign

            norm_i = np.linalg.norm(dir_i)
            norm_j = np.linalg.norm(dir_j)
            norm_k = np.linalg.norm(dir_k)
            dir_i = dir_i / norm_i if norm_i > 1e-10 else np.zeros(2)
            dir_j = dir_j / norm_j if norm_j > 1e-10 else np.zeros(2)
            dir_k = dir_k / norm_k if norm_k > 1e-10 else np.zeros(2)

            step = T * 0.1
            candidate = current.copy()
            candidate[i] = A_pt + step * dir_i
            candidate[j] = B_pt + step * dir_j
            candidate[k] = C_pt + step * dir_k

            for idx in [i, j, k]:
                if not is_inside_triangle(candidate[idx:idx+1], A, B, C):
                    candidate[idx] = project_to_triangle(candidate[idx])

            new_score = get_smallest_triangle_area(candidate)
            delta = new_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current = candidate
                current_score = new_score

            T *= decay

        return current

    return improve