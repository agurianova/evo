from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Configuration parameters
        initial_step = 0.05
        T0 = 0.001
        alpha = 0.995
        max_plateau = 100
        
        plateau_count = 0
        temperature = T0
        step_size = initial_step
        
        # Helper for bottleneck identification
        def area_of_triangle(p1, p2, p3):
            return 0.5 * abs((p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1])))

        while plateau_count < max_plateau:
            # Identify bottleneck triangle
            min_indices = None
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = area_of_triangle(best[i], best[j], best[k])
                        if area <= best_score + 1e-10:
                            min_indices = (i, j, k)
                            break
                    if min_indices is not None:
                        break
                if min_indices is not None:
                    break
            if min_indices is None:
                min_indices = (0, 1, 2)

            # Select points to perturb (1, 2, or 3 from bottleneck)
            r = np.random.rand()
            if r < 0.6:
                idxs = [np.random.choice(min_indices)]
            elif r < 0.9:
                idxs = np.random.choice(min_indices, size=2, replace=False).tolist()
            else:
                idxs = list(min_indices)

            candidate = best.copy()
            for idx in idxs:
                candidate[idx] += np.random.normal(0, step_size, size=2)

            # Check containment
            if not is_inside_triangle(candidate, A, B, C):
                plateau_count += 1
            else:
                # Evaluate candidate
                candidate_score = get_smallest_triangle_area(candidate)
                if np.isnan(candidate_score) or candidate_score < 1e-12:
                    plateau_count += 1
                else:
                    # Simulated annealing acceptance
                    if candidate_score > best_score:
                        best = candidate
                        best_score = candidate_score
                        plateau_count = 0
                    else:
                        if np.random.rand() < np.exp((candidate_score - best_score) / temperature):
                            best = candidate
                            best_score = candidate_score
                            plateau_count = 0
                        else:
                            plateau_count += 1

            # Update search parameters
            temperature *= alpha
            step_size = max(initial_step * (0.95 ** (plateau_count / 10.0)), 1e-5)

        return best

    return improve