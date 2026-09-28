from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        # Initialize simulated annealing parameters
        temperature = 0.1 * current_score
        consecutive_failures = 0
        max_consecutive_failures = 100
        cooling_rate = 0.995

        while consecutive_failures < max_consecutive_failures:
            # Find smallest triangle by area
            n = current.shape[0]
            min_area_val = float('inf')
            min_triangle_indices = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        p1, p2, p3 = current[i], current[j], current[k]
                        area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1]))
                        if area < min_area_val:
                            min_area_val = area
                            min_triangle_indices = (i, j, k)

            i, j, k = min_triangle_indices
            
            # Find shortest side in smallest triangle
            d_ij = np.linalg.norm(current[j] - current[i])
            d_ik = np.linalg.norm(current[k] - current[i])
            d_jk = np.linalg.norm(current[k] - current[j])
            min_side = min(d_ij, d_ik, d_jk)
            if min_side == d_ij:
                a, b = i, j
            elif min_side == d_ik:
                a, b = i, k
            else:
                a, b = j, k

            # Compute movement direction and step
            direction = (current[b] - current[a]) / min_side
            step = 0.1 * min_side
            candidate = current.copy()
            candidate[a] = current[a] - step * direction
            candidate[b] = current[b] + step * direction

            # Validate candidate points stay within container
            if not (is_inside_triangle(candidate[a], A, B, C) and 
                    is_inside_triangle(candidate[b], A, B, C)):
                consecutive_failures += 1
                temperature *= cooling_rate
                continue

            # Evaluate candidate configuration
            new_score = get_smallest_triangle_area(candidate)
            
            # Skip degenerate configurations
            if new_score <= 1e-12:
                consecutive_failures += 1
                temperature *= cooling_rate
                continue

            # Update global best if improvement found
            if new_score > best_score:
                best = candidate.copy()
                best_score = new_score

            # Simulated annealing acceptance criterion
            if new_score >= current_score:
                current = candidate
                current_score = new_score
                consecutive_failures = 0
            else:
                delta = new_score - current_score
                acceptance_prob = np.exp(delta / temperature)
                if np.random.rand() < acceptance_prob:
                    current = candidate
                    current_score = new_score
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1

            # Cool temperature
            temperature *= cooling_rate

        return best

    return improve