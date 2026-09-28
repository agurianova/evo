from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    total_rounds = 200
    initial_step = 0.05
    step_decay = 0.99
    initial_temp = 0.0005
    temp_decay = 0.99

    def improve(points: np.ndarray) -> np.ndarray:
        np.random.seed(42)
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        step_size = initial_step
        temperature = initial_temp

        def find_smallest_triplet(pts):
            n = pts.shape[0]
            min_area = float('inf')
            min_triplet = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = 0.5 * abs(
                            (pts[j,0]-pts[i,0])*(pts[k,1]-pts[i,1]) - 
                            (pts[k,0]-pts[i,0])*(pts[j,1]-pts[i,1])
                        )
                        if area < min_area:
                            min_area = area
                            min_triplet = (i, j, k)
            return min_triplet, min_area

        for _ in range(total_rounds):
            min_triplet, _ = find_smallest_triplet(best)
            indices_to_perturb = np.random.choice(min_triplet, size=2, replace=False)
            
            candidate = best.copy()
            for idx in indices_to_perturb:
                candidate[idx] += np.random.normal(0, step_size, size=2)

            if not is_inside_triangle(candidate, A, B, C):
                step_size *= step_decay
                temperature *= temp_decay
                continue

            score = get_smallest_triangle_area(candidate)
            
            if score > best_score:
                best = candidate
                best_score = score
            else:
                delta = score - best_score
                if np.random.rand() < np.exp(delta / temperature):
                    best = candidate
                    best_score = score

            step_size *= step_decay
            temperature *= temp_decay

        return best

    return improve