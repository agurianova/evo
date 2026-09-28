from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    
    def improve(points: np.ndarray) -> np.ndarray:
        # Adaptive initialization based on input configuration
        initial_min_area = get_smallest_triangle_area(points)
        T0 = 0.1 * np.sqrt(initial_min_area)  # Adaptive initial temperature
        temp_decay = 0.999  # Slower decay for sustained exploration
        step0 = 0.1 * np.sqrt(initial_min_area)  # Adaptive step size
        step_decay = 0.999  # Slower step decay
        max_iter = 500
        early_stop = 100

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        no_improve = 0

        for iteration in range(max_iter):
            step = step0 * (step_decay ** iteration)
            
            # Find all critical triangles (within 10% of current min_area)
            n = current.shape[0]
            min_area = float('inf')
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        p_i, p_j, p_k = current[i], current[j], current[k]
                        area = 0.5 * abs(
                            (p_j[0]-p_i[0])*(p_k[1]-p_i[1]) - 
                            (p_k[0]-p_i[0])*(p_j[1]-p_i[1])
                        )
                        triangles.append((i, j, k, area))
                        if area < min_area:
                            min_area = area

            # Handle near-zero min_area
            if min_area < 1e-10:
                min_area = 1e-10
            
            threshold = 1.1 * min_area
            critical_triangles = [(i, j, k) for (i, j, k, area) in triangles if area <= threshold]

            # Compute displacement directions for all points
            displacement_dir = np.zeros_like(current)
            for (i, j, k) in critical_triangles:
                p0, p1, p2 = current[i], current[j], current[k]
                d0 = np.linalg.norm(p1 - p2)
                d1 = np.linalg.norm(p0 - p2)
                d2 = np.linalg.norm(p0 - p1)
                longest_idx = np.argmax([d0, d1, d2])

                if longest_idx == 0:
                    apex_idx, base1_idx, base2_idx = i, j, k
                    base1, base2 = p1, p2
                elif longest_idx == 1:
                    apex_idx, base1_idx, base2_idx = j, i, k
                    base1, base2 = p0, p2
                else:
                    apex_idx, base1_idx, base2_idx = k, i, j
                    base1, base2 = p0, p1

                base_vec = base2 - base1
                base_length = np.linalg.norm(base_vec)
                if base_length < 1e-10:
                    continue
                
                # Determine movement strategy
                if np.random.rand() < 0.3:  # 30% chance for base movement
                    base_direction = base_vec / base_length
                    displacement_dir[base1_idx] += -base_direction
                    displacement_dir[base2_idx] += base_direction
                else:  # 70% chance for apex movement
                    normal = np.array([-base_vec[1], base_vec[0]]) / base_length
                    apex_to_base = current[apex_idx] - base1
                    d = np.dot(normal, apex_to_base)
                    displacement_dir[apex_idx] += normal * np.sign(d)

            # Normalize displacement directions per point
            for idx in range(n):
                norm = np.linalg.norm(displacement_dir[idx])
                if norm > 0:
                    displacement_dir[idx] /= norm

            # Find valid step size via halving
            step_temp = step
            valid_candidate = None
            while step_temp > 1e-5:
                candidate = current + step_temp * displacement_dir
                if is_inside_triangle(candidate, A, B, C):
                    valid_candidate = candidate
                    break
                step_temp *= 0.5

            if valid_candidate is None:
                no_improve += 1
                continue

            candidate = valid_candidate
            candidate_score = get_smallest_triangle_area(candidate)

            # Simulated annealing acceptance
            if candidate_score > current_score:
                current, current_score = candidate, candidate_score
            else:
                T = T0 * (temp_decay ** iteration)
                delta = candidate_score - current_score
                if np.random.rand() < np.exp(delta / T):
                    current, current_score = candidate, candidate_score

            # Update best solution and early stopping
            if candidate_score > best_score:
                best, best_score = candidate, candidate_score
                no_improve = 0
            else:
                no_improve += 1

            if no_improve >= early_stop:
                break

        return best

    return improve