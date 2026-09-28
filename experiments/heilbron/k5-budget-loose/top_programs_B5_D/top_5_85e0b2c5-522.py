from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points):
        np.random.seed(42)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        current = best.copy()
        current_score = best_score

        max_iterations = 500
        initial_temperature = 0.001
        cooling_rate = 0.99
        min_temperature = 1e-6
        step_size = 0.05
        T = initial_temperature

        def project_point(p):
            if is_inside_triangle(p, A, B, C):
                return p
            centroid = (A + B + C) / 3.0
            direction = centroid - p
            direction_norm = np.linalg.norm(direction)
            if direction_norm < 1e-6:
                return centroid
            low, high = 0.0, 1.0
            for _ in range(10):
                mid = (low + high) / 2
                candidate = p + mid * direction
                if is_inside_triangle(candidate, A, B, C):
                    high = mid
                else:
                    low = mid
            return p + high * direction

        def get_min_triangle_indices(pts):
            min_area = float('inf')
            min_indices = (0, 1, 2)
            n = pts.shape[0]
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        area = 0.5 * abs((pts[j, 0] - pts[i, 0]) * (pts[k, 1] - pts[i, 1]) - 
                                         (pts[k, 0] - pts[i, 0]) * (pts[j, 1] - pts[i, 1]))
                        if area < min_area:
                            min_area = area
                            min_indices = (i, j, k)
            return min_indices

        for _ in range(max_iterations):
            if T < min_temperature:
                break

            i, j, k = get_min_triangle_indices(current)
            candidate = current.copy()
            
            candidate[i] += np.random.normal(0, step_size, 2)
            candidate[j] += np.random.normal(0, step_size, 2)
            candidate[k] += np.random.normal(0, step_size, 2)

            candidate[i] = project_point(candidate[i])
            candidate[j] = project_point(candidate[j])
            candidate[k] = project_point(candidate[k])

            new_score = get_smallest_triangle_area(candidate)

            if new_score > current_score:
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
            else:
                delta = current_score - new_score
                if np.random.rand() < np.exp(-delta / T):
                    current = candidate
                    current_score = new_score

            T *= cooling_rate
            step_size *= cooling_rate

        return best

    return improve