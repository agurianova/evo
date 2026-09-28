from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
np.random.seed(123)

def entrypoint():
    A, B, C = get_unit_triangle()
    centroid = (A + B + C) / 3.0

    def improve(points: np.ndarray) -> np.ndarray:
        n = points.shape[0]
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_ever = current.copy()
        best_score_ever = current_score
        step_size = 0.05
        temp = 0.001
        consecutive_no_improve = 0
        max_iter = 500
        max_no_improve = 100

        def triangle_area(p, q, r):
            return 0.5 * abs(p[0]*(q[1]-r[1]) + q[0]*(r[1]-p[1]) + r[0]*(p[1]-q[1]))

        for _ in range(max_iter):
            min_area_val = float('inf')
            triangles = []
            for i1 in range(n):
                for i2 in range(i1+1, n):
                    for i3 in range(i2+1, n):
                        area_val = triangle_area(current[i1], current[i2], current[i3])
                        if area_val < min_area_val:
                            min_area_val = area_val
                        triangles.append((i1, i2, i3, area_val))
            
            critical_set = set()
            for (i1, i2, i3, area_val) in triangles:
                if abs(area_val - min_area_val) < 1e-9:
                    critical_set.update([i1, i2, i3])
            critical_list = list(critical_set)

            idx = np.random.choice(critical_list) if critical_list and np.random.rand() < 0.7 else np.random.randint(0, n)

            candidate = current.copy()
            candidate[idx] += np.random.normal(0, step_size, size=2)

            if not is_inside_triangle(candidate[idx:idx+1], A, B, C):
                p = candidate[idx]
                count = 0
                while not is_inside_triangle(p.reshape(1,2), A, B, C) and count < 10:
                    p = 0.5 * p + 0.5 * centroid
                    count += 1
                candidate[idx] = centroid if count == 10 else p

            min_dist = min(np.linalg.norm(candidate[idx] - candidate[j]) for j in range(n) if j != idx)
            if min_dist < 1e-5:
                dists = np.linalg.norm(candidate - candidate[idx], axis=1)
                dists[idx] = float('inf')
                j_closest = np.argmin(dists)
                direction = candidate[idx] - candidate[j_closest]
                direction = direction / np.linalg.norm(direction) if np.linalg.norm(direction) > 1e-10 else np.random.randn(2)
                candidate[idx] += direction * (1e-5 - min_dist)
                
                if not is_inside_triangle(candidate[idx:idx+1], A, B, C):
                    p = candidate[idx]
                    count = 0
                    while not is_inside_triangle(p.reshape(1,2), A, B, C) and count < 10:
                        p = 0.5 * p + 0.5 * centroid
                        count += 1
                    candidate[idx] = centroid if count == 10 else p

            new_score = get_smallest_triangle_area(candidate)

            if new_score > best_score_ever:
                best_ever, best_score_ever = candidate.copy(), new_score
                consecutive_no_improve, step_size = 0, max(0.001, step_size * 0.95)
            else:
                consecutive_no_improve += 1

            if consecutive_no_improve > 0 and consecutive_no_improve % 20 == 0:
                step_size = min(0.1, step_size * 1.2)

            if new_score > current_score or (np.random.rand() < np.exp((new_score - current_score) / temp)):
                current, current_score = candidate, new_score

            temp *= 0.995

            if consecutive_no_improve >= max_no_improve:
                break

        return best_ever

    return improve