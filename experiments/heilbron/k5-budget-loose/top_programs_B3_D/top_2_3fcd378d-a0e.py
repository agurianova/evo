from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        def is_inside(p):
            return is_inside_triangle(p.reshape(1, 2), A, B, C)

        def project_to_edge(P, A, B):
            AB = B - A
            AP = P - A
            t = np.dot(AP, AB) / (np.dot(AB, AB) + 1e-8)
            t = max(0.0, min(1.0, t))
            return A + t * AB

        def project_point(P):
            if is_inside(P):
                return P
            proj_ab = project_to_edge(P, A, B)
            proj_bc = project_to_edge(P, B, C)
            proj_ca = project_to_edge(P, C, A)
            d_ab = np.linalg.norm(P - proj_ab)
            d_bc = np.linalg.norm(P - proj_bc)
            d_ca = np.linalg.norm(P - proj_ca)
            if d_ab <= d_bc and d_ab <= d_ca:
                projected = proj_ab
            elif d_bc <= d_ab and d_bc <= d_ca:
                projected = proj_bc
            else:
                projected = proj_ca

            # Add small inward step with 30% probability to escape boundary traps
            if np.random.rand() < 0.3:
                centroid = (A + B + C) / 3
                inward_dir = centroid - projected
                inward_norm = np.linalg.norm(inward_dir)
                if inward_norm > 1e-8:
                    inward_dir = inward_dir / inward_norm
                    test_point = projected + 0.005 * inward_dir
                    if is_inside(test_point):
                        return test_point

            return projected

        def get_min_triangle_indices(pts):
            n = pts.shape[0]
            min_area = float('inf')
            best_tri = (0, 1, 2)
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = pts[i], pts[j], pts[k]
                        expr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                        area = 0.5 * abs(expr)
                        if area < min_area - 1e-10:
                            min_area = area
                            best_tri = (i, j, k)
            return min_area, best_tri

        # Run multiple independent annealing chains
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)

        for restart in range(3):
            # Start with perturbed version of input points
            current = points.copy() + np.random.normal(0, 0.01, (11, 2))
            # Project any out-of-bounds points
            for i in range(11):
                if not is_inside(current[i]):
                    current[i] = project_point(current[i])

            best = current.copy()
            best_score = get_smallest_triangle_area(best)
            current_score = best_score

            T0 = 0.005
            max_iter = 500
            initial_step = 0.05
            bias_factor = 0.8  # Increased from 0.7 to leverage more gradient information

            for iter in range(max_iter):
                T = T0 * (1 - iter / max_iter)

                min_area, (i0, i1, i2) = get_min_triangle_indices(current)
                a, b, c = current[i0], current[i1], current[i2]
                
                expr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                sign = 1 if expr >= 0 else -1

                dir0 = np.array([b[1] - c[1], c[0] - b[0]]) * sign
                dir1 = np.array([c[1] - a[1], a[0] - c[0]]) * sign
                dir2 = np.array([a[1] - b[1], b[0] - a[0]]) * sign

                for d in [dir0, dir1, dir2]:
                    norm = np.linalg.norm(d)
                    if norm > 1e-8:
                        d /= norm
                    else:
                        d[:] = 0

                step_size = initial_step * (T / T0)

                candidate = current.copy()
                for idx, direction in zip([i0, i1, i2], [dir0, dir1, dir2]):
                    if np.linalg.norm(direction) > 1e-8:
                        grad_pert = direction * (step_size * bias_factor)
                    else:
                        grad_pert = np.zeros(2)
                    # Ensure minimum randomness (0.001) even at low temperatures
                    rand_pert = np.random.normal(0, max(step_size * (1 - bias_factor), 0.001), 2)
                    candidate[idx] += grad_pert + rand_pert

                for i in range(11):
                    if not is_inside(candidate[i]):
                        candidate[i] = project_point(candidate[i])

                new_score = get_smallest_triangle_area(candidate)

                delta = new_score - current_score
                if delta > 0 or (T > 1e-8 and np.random.rand() < np.exp(delta / T)):
                    current = candidate
                    current_score = new_score
                    if new_score > best_score:
                        best = candidate
                        best_score = new_score

            if best_score > best_score_overall:
                best_overall = best.copy()
                best_score_overall = best_score

        return best_overall

    return improve