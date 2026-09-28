from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    centroid = (A + B + C) / 3.0

    def get_smallest_triangle_indices(points):
        n = points.shape[0]
        min_area = float('inf')
        best_indices = (0, 1, 2)
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        (points[j,0] - points[i,0]) * (points[k,1] - points[i,1]) -
                        (points[k,0] - points[i,0]) * (points[j,1] - points[i,1])
                    )
                    if area < min_area:
                        min_area = area
                        best_indices = (i, j, k)
        return best_indices

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        max_iterations = 500
        early_stop_threshold = 100
        current_step = 0.05
        min_step = 0.001
        total_no_improve = 0
        
        for it in range(max_iterations):
            indices = get_smallest_triangle_indices(best)
            idx = np.random.choice(indices)
            
            candidate = best.copy()
            perturbation = np.random.normal(0, current_step, size=2)
            candidate[idx] += perturbation
            
            p = candidate[idx]
            while not is_inside_triangle(p.reshape(1, 2), A, B, C):
                p = (p + centroid) / 2.0
            candidate[idx] = p
            
            score = get_smallest_triangle_area(candidate)
            if score > best_score:
                best = candidate
                best_score = score
                total_no_improve = 0
                if current_step > min_step:
                    current_step *= 0.95
            else:
                total_no_improve += 1
                if total_no_improve >= early_stop_threshold:
                    break
                    
        return best

    return improve