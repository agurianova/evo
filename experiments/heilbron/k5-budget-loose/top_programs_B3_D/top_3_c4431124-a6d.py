from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points):
        np.random.seed(42)
        current = points.copy()
        best = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_score = current_score

        # Initial parameters
        initial_temp = 0.005
        initial_step = 0.05
        temperature = initial_temp
        step_size = initial_step
        cooling_rate = 0.995
        max_iter = 500
        TOL = 1e-10
        
        # Stagnation handling
        stagnation_counter = 0
        stagnation_threshold = 50
        improvement_history = []
        k_smallest = 3  # Consider top k smallest triangles

        for it in range(max_iter):
            n = len(current)
            
            # Find top k smallest triangles
            smallest_triangles = []  # (area, i, j, k)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a = current[i]
                        b = current[j]
                        c = current[k]
                        area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                        
                        # Keep top k smallest triangles
                        if len(smallest_triangles) < k_smallest or area_val < smallest_triangles[-1][0]:
                            smallest_triangles.append((area_val, i, j, k))
                            smallest_triangles.sort(key=lambda x: x[0])
                            if len(smallest_triangles) > k_smallest:
                                smallest_triangles.pop()

            if not smallest_triangles:
                break

            # Initialize gradient accumulator for each point
            grad_accum = np.zeros_like(current)
            
            # Process each of the top k smallest triangles
            for area_val, i, j, k in smallest_triangles:
                a_pt = current[i]
                b_pt = current[j]
                c_pt = current[k]

                cross = (b_pt[0]-a_pt[0])*(c_pt[1]-a_pt[1]) - (c_pt[0]-a_pt[0])*(b_pt[1]-a_pt[1])
                sgn = np.sign(cross)

                grad_a = np.array([b_pt[1]-c_pt[1], c_pt[0]-b_pt[0]])
                grad_b = np.array([c_pt[1]-a_pt[1], a_pt[0]-c_pt[0]])
                grad_c = np.array([a_pt[1]-b_pt[1], b_pt[0]-a_pt[0]])

                dir_a = sgn * grad_a
                dir_b = sgn * grad_b
                dir_c = sgn * grad_c

                # Normalize if non-zero
                if np.linalg.norm(dir_a) > 1e-8:
                    dir_a = dir_a / np.linalg.norm(dir_a)
                else:
                    dir_a = np.zeros(2)
                if np.linalg.norm(dir_b) > 1e-8:
                    dir_b = dir_b / np.linalg.norm(dir_b)
                else:
                    dir_b = np.zeros(2)
                if np.linalg.norm(dir_c) > 1e-8:
                    dir_c = dir_c / np.linalg.norm(dir_c)
                else:
                    dir_c = np.zeros(2)

                # Accumulate gradients (weighted by triangle importance)
                weight = 1.0 / (area_val + 1e-10)  # Inverse area weighting
                grad_accum[i] += weight * dir_a
                grad_accum[j] += weight * dir_b
                grad_accum[k] += weight * dir_c

            # Normalize accumulated gradients
            for i in range(n):
                if np.linalg.norm(grad_accum[i]) > 1e-8:
                    grad_accum[i] = grad_accum[i] / np.linalg.norm(grad_accum[i])

            # Create candidate by moving all points according to accumulated gradients
            candidate = current.copy()
            for i in range(n):
                candidate[i] += step_size * grad_accum[i]

            # Project points back into triangle if needed
            for i in range(n):
                if not is_inside_triangle(candidate[i], A, B, C):
                    orig_pt = current[i]
                    v = candidate[i] - orig_pt
                    low, high = 0.0, 1.0
                    for _ in range(5):
                        mid = (low + high) / 2
                        test_pt = orig_pt + mid * v
                        if is_inside_triangle(test_pt, A, B, C):
                            low = mid
                        else:
                            high = mid
                    candidate[i] = orig_pt + low * v

            new_score = get_smallest_triangle_area(candidate)
            if new_score < TOL:
                # Adaptive cooling: only cool when we have a valid candidate
                temperature *= cooling_rate
                continue

            delta = new_score - current_score
            accepted = False
            
            # Metropolis acceptance
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current = candidate
                current_score = new_score
                accepted = True
                
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
                    improvement = new_score - best_score
                    improvement_history.append(improvement)
                    if len(improvement_history) > 10:
                        improvement_history.pop(0)
                    stagnation_counter = 0
                
            # Adaptive step size based on improvement history
            if accepted:
                # Increase step size if we've had consistent improvements
                if len(improvement_history) == 10 and np.mean(improvement_history) > 1e-6:
                    step_size = min(step_size * 1.05, 0.2)
            else:
                stagnation_counter += 1
                # Decrease step size if stagnating
                if stagnation_counter > 10:
                    step_size = max(step_size * 0.95, 0.01)

            # Stagnation recovery
            if stagnation_counter > stagnation_threshold:
                # Reset to best configuration
                current = best.copy()
                current_score = best_score
                
                # Reset parameters
                temperature = initial_temp
                step_size = initial_step
                
                # Add strategic perturbation to escape local minimum
                for i in range(n):
                    current[i] += np.random.normal(0, 0.05, size=2)
                    # Project back if needed
                    if not is_inside_triangle(current[i], A, B, C):
                        orig_pt = best[i]
                        v = current[i] - orig_pt
                        low, high = 0.0, 1.0
                        for _ in range(5):
                            mid = (low + high) / 2
                            test_pt = orig_pt + mid * v
                            if is_inside_triangle(test_pt, A, B, C):
                                low = mid
                            else:
                                high = mid
                        current[i] = orig_pt + low * v
                
                current_score = get_smallest_triangle_area(current)
                stagnation_counter = 0

            # Always cool temperature (but only when we had a valid candidate)
            temperature *= cooling_rate

        return best

    return improve