from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_overall = current.copy()
        best_score_overall = current_score
        
        # Hyperparameters
        max_iter = 500
        initial_temperature = 0.01
        cooling_rate = 0.995
        initial_step_size = 0.05
        step_decay = 0.995
        early_stop_patience = 50
        no_improve_count = 0
        
        temperature = initial_temperature
        step_size = initial_step_size

        for it in range(max_iter):
            # Find indices of smallest triangle in current configuration
            min_area_val = float('inf')
            min_tri = None
            n = current.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = 0.5 * abs(
                            (current[j,0] - current[i,0]) * (current[k,1] - current[i,1]) -
                            (current[k,0] - current[i,0]) * (current[j,1] - current[i,1])
                        )
                        if area < min_area_val:
                            min_area_val = area
                            min_tri = (i, j, k)

            # Perturb the three points of the smallest triangle
            candidate = current.copy()
            for idx in min_tri:
                candidate[idx] += np.random.normal(0, step_size, size=2)

            # Project perturbed points back to triangle using barycentric coordinates
            for idx in min_tri:
                P = candidate[idx]
                v0 = B - A
                v1 = C - A
                v2 = P - A
                d00 = np.dot(v0, v0)
                d01 = np.dot(v0, v1)
                d11 = np.dot(v1, v1)
                d20 = np.dot(v2, v0)
                d21 = np.dot(v2, v1)
                denom = d00 * d11 - d01 * d01
                
                if abs(denom) < 1e-12:
                    candidate[idx] = A
                else:
                    v = (d11 * d20 - d01 * d21) / denom
                    w = (d00 * d21 - d01 * d20) / denom
                    u = 1.0 - v - w
                    coords = np.array([u, v, w])
                    
                    if np.any(coords < 0):
                        coords = np.maximum(coords, 0)
                        total = np.sum(coords)
                        if total > 0:
                            coords /= total
                        else:
                            coords = np.array([1/3, 1/3, 1/3])
                    candidate[idx] = coords[0]*A + coords[1]*B + coords[2]*C

            # Evaluate candidate and skip if degenerate
            candidate_score = get_smallest_triangle_area(candidate)
            if candidate_score <= 1e-10:
                temperature *= cooling_rate
                step_size *= step_decay
                continue

            # Update best overall solution
            if candidate_score > best_score_overall:
                best_overall = candidate.copy()
                best_score_overall = candidate_score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Simulated annealing acceptance for current state
            delta = candidate_score - current_score
            if delta > 0:
                current = candidate
                current_score = candidate_score
            else:
                if np.random.rand() < np.exp(delta / temperature):
                    current = candidate
                    current_score = candidate_score

            # Update temperature and step size
            temperature *= cooling_rate
            step_size *= step_decay

            # Early stopping if no improvement in best solution
            if no_improve_count >= early_stop_patience:
                break

        return best_overall

    return improve