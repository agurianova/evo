from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        T = 0.01
        step_size = 0.05
        max_iter = 200

        # Helper for single triangle area (used in bottleneck identification)
        def area_tri(a, b, c):
            return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))

        for _ in range(max_iter):
            # Identify smallest triangle (bottleneck)
            n = current.shape[0]
            min_area = float('inf')
            min_indices = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a = area_tri(current[i], current[j], current[k])
                        if a < min_area:
                            min_area = a
                            min_indices = (i, j, k)
            i, j, k = min_indices

            # Select point: 80% from bottleneck triangle, 20% random
            if np.random.rand() < 0.8:
                idx = np.random.choice([i, j, k])
            else:
                idx = np.random.randint(0, n)

            candidate = current.copy()
            # Compute perturbation
            if idx in (i, j, k):
                # Identify moving point and base points
                pts = [current[i], current[j], current[k]]
                idx_in_tri = [i, j, k].index(idx)
                A_pt = pts[idx_in_tri]
                B_pt, C_pt = pts[:idx_in_tri] + pts[idx_in_tri+1:]

                # Compute gradient direction for area increase
                v = C_pt - B_pt
                w = A_pt - B_pt
                cross = v[0]*w[1] - v[1]*w[0]
                sign = 1 if cross > 0 else -1
                direction = sign * np.array([-v[1], v[0]])
                norm_dir = direction / np.linalg.norm(direction)
                perturbation = step_size * norm_dir
            else:
                # Random direction for non-critical points
                direction = np.random.normal(0, 1, size=2)
                norm_dir = direction / np.linalg.norm(direction)
                perturbation = step_size * norm_dir

            candidate[idx] += perturbation

            # Check containment
            if is_inside_triangle(candidate, A, B, C):
                new_score = get_smallest_triangle_area(candidate)
                # Simulated annealing acceptance
                if new_score > current_score or np.random.rand() < np.exp((new_score - current_score) / T):
                    current = candidate
                    current_score = new_score

            # Adaptive cooling and step decay
            T *= 0.99
            step_size *= 0.995

        return current

    return improve