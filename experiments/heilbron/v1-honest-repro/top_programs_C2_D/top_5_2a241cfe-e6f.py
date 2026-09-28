from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        n = 11

        # Simulated annealing parameters
        initial_temp = 0.01
        temp = initial_temp
        cooling_rate = 0.99
        max_iter = 500
        no_improve_count = 0
        best_score_ever = current_score

        for it in range(max_iter):
            # Find smallest triangle (indices)
            min_area = float('inf')
            best_triangle = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        # Compute area for triangle (i,j,k)
                        area_val = 0.5 * abs(
                            (current[j,0] - current[i,0]) * (current[k,1] - current[i,1]) -
                            (current[j,1] - current[i,1]) * (current[k,0] - current[i,0])
                        )
                        if area_val < min_area:
                            min_area = area_val
                            best_triangle = (i, j, k)
            i0, i1, i2 = best_triangle

            # Randomly select one vertex of the smallest triangle to move
            idx = np.random.choice([i0, i1, i2])
            
            # Identify base points (the other two)
            if idx == i0:
                apex = current[i0]
                base1 = current[i1]
                base2 = current[i2]
            elif idx == i1:
                apex = current[i1]
                base1 = current[i0]
                base2 = current[i2]
            else:
                apex = current[i2]
                base1 = current[i0]
                base2 = current[i1]

            # Compute base vector and normal
            base_vec = base2 - base1
            base_norm = np.linalg.norm(base_vec)
            if base_norm < 1e-5:
                continue  # Skip degenerate base

            unit_base = base_vec / base_norm
            unit_normal = np.array([-unit_base[1], unit_base[0]])
            
            # Signed distance from apex to base line
            d = np.dot(apex - base1, unit_normal)
            if abs(d) < 1e-5:
                continue  # Nearly degenerate triangle

            # Direction to move apex to increase area (away from base)
            move_dir = np.sign(d) * unit_normal

            # Adaptive step size based on temperature
            step_size = 0.02 * (temp / initial_temp)
            candidate = current.copy()
            candidate[idx] = apex + step_size * move_dir

            # Check containment and adjust step if needed
            if not is_inside_triangle(candidate[idx:idx+1], A, B, C):
                step = step_size
                found = False
                for _ in range(5):
                    step /= 2.0
                    candidate[idx] = apex + step * move_dir
                    if is_inside_triangle(candidate[idx:idx+1], A, B, C):
                        found = True
                        break
                if not found:
                    continue

            # Evaluate candidate
            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - current_score

            # Acceptance criterion (simulated annealing)
            if delta >= 0 or np.random.rand() < np.exp(delta / temp):
                current = candidate
                current_score = candidate_score
                
                # Track best solution
                if current_score > best_score_ever:
                    best_score_ever = current_score
                    no_improve_count = 0
                else:
                    no_improve_count += 1
            else:
                no_improve_count += 1

            # Cool down and check early stopping
            temp *= cooling_rate
            if no_improve_count >= 100:
                break

        return current

    return improve