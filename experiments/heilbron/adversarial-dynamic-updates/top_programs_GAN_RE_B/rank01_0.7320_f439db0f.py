from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        n_rounds = 200
        T0 = 0.01
        T_decay = 0.99
        base_step = 0.05
        step_decay = 0.995

        def get_min_triangle_indices(pts):
            n = pts.shape[0]
            min_area = float('inf')
            best_indices = (0, 1, 2)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = pts[i], pts[j], pts[k]
                        area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                        if area < min_area:
                            min_area = area
                            best_indices = (i, j, k)
            return best_indices

        for round_idx in range(n_rounds):
            T = T0 * (T_decay ** round_idx)
            current_step = base_step * (step_decay ** round_idx)
            
            indices = get_min_triangle_indices(best)
            
            if np.random.rand() < 0.7:
                idx = np.random.choice(indices)
                candidate = best.copy()
                perturbation = np.random.normal(0, current_step, size=2)
                candidate[idx] += perturbation
            else:
                candidate = best.copy()
                for idx in indices:
                    perturbation = np.random.normal(0, current_step, size=2)
                    candidate[idx] += perturbation
            
            if not is_inside_triangle(candidate, A, B, C):
                continue
            
            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - best_score
            
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                best = candidate
                best_score = candidate_score
        
        return best

    return improve