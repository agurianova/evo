from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        def find_smallest_triangle(pts):
            n = pts.shape[0]
            min_cross = float('inf')
            best_indices = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        cross_val = abs((pts[j,0]-pts[i,0])*(pts[k,1]-pts[i,1]) - 
                                       (pts[j,1]-pts[i,1])*(pts[k,0]-pts[i,0]))
                        if cross_val < min_cross:
                            min_cross = cross_val
                            best_indices = (i, j, k)
            return best_indices

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        T = 1.0
        T_min = 0.001
        alpha = 0.99
        max_iter = 200

        current = best.copy()
        current_score = best_score

        for _ in range(max_iter):
            i, j, k = find_smallest_triangle(current)
            idx = np.random.choice([i, j, k])
            
            step = 0.05 * T
            perturbation = np.random.normal(0, step, size=2)
            candidate = current.copy()
            candidate[idx] += perturbation

            if not is_inside_triangle(candidate, A, B, C):
                continue

            score = get_smallest_triangle_area(candidate)
            if score <= 1e-12:
                continue

            delta = score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current = candidate
                current_score = score
                if score > best_score:
                    best = candidate
                    best_score = score

            T = max(T_min, T * alpha)

        return best

    return improve