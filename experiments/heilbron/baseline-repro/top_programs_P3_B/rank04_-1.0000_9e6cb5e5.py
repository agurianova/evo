from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Precompute denominator for barycentric conversion (2 * area(ABC))
    denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
    base_length = np.linalg.norm(B - A)  # Compute triangle base length for step size scaling

    def improve(points: np.ndarray) -> np.ndarray:
        n = len(points)
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score

        # Initialize top-3 solution pool
        pool = []  # List of (score, points) tuples

        # Simulated annealing parameters
        initial_temp = 0.01
        temp = initial_temp
        cooling_rate = 0.995
        max_iter = 1000
        patience = 20
        no_improve_count = 0
        restart_count = 0
        step_size_base = 0.1 * base_length  # Scaled base step size

        # For dynamic temperature calibration
        early_deltas = []

        for iter in range(max_iter):
            # Identify critical points with ADAPTIVE THRESHOLD (based on current solution quality)
            weights = np.zeros(n)
            # Adaptive threshold: widens when far from optimum, tightens near optimum
            threshold = current_score * (1 + 0.5 * (1 - current_score / 0.0365))
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        p1, p2, p3 = current[i], current[j], current[k]
                        area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1]))
                        if area < threshold:
                            deficit = threshold - area
                            weights[i] += deficit
                            weights[j] += deficit
                            weights[k] += deficit

            total_weight = np.sum(weights)
            if total_weight == 0:
                idx = np.random.randint(0, n)
            else:
                probs = weights / total_weight
                idx = np.random.choice(n, p=probs)

            # Compute adaptive step size - CHANGED STAGNATION FACTOR FROM 0.5 TO 1.5
            current_step = step_size_base * (1 - iter/max_iter) * (1 + 1.5 * (no_improve_count/patience))
            current_step = max(1e-5, current_step)

            # Perturb selected point and project boundary-aware
            orig = current[idx].copy()
            d = np.random.normal(0, current_step, 2)
            
            # Boundary-aware projection via directional binary search
            t_low, t_high = 0.0, 1.0
            for _ in range(10):
                t_mid = (t_low + t_high) / 2
                p_mid = orig + t_mid * d
                if is_inside_triangle(p_mid, A, B, C):
                    t_low = t_mid
                else:
                    t_high = t_mid
            
            candidate = current.copy()
            candidate[idx] = orig + t_low * d

            # Evaluate candidate
            new_score = get_smallest_triangle_area(candidate)
            
            # Update top-3 solution pool
            if len(pool) < 3:
                pool.append((new_score, candidate.copy()))
                pool.sort(key=lambda x: x[0], reverse=True)
            else:
                if new_score > pool[-1][0]:
                    pool[-1] = (new_score, candidate.copy())
                    pool.sort(key=lambda x: x[0], reverse=True)

            # Update best solution
            if new_score > best_score:
                best = candidate.copy()
                best_score = new_score

            # Simulated annealing acceptance
            delta = new_score - current_score
            if iter < 50:
                # Use ABSOLUTE DELTAS for robust temperature calibration
                early_deltas.append(abs(delta))

            if delta > 0 or np.random.rand() < np.exp(delta / temp):
                current = candidate
                current_score = new_score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Cool temperature
            temp *= cooling_rate

            # Dynamic temperature reset at iteration 50
            if iter == 49 and len(early_deltas) > 0:
                std_dev = np.std(early_deltas)
                if std_dev < 1e-12:
                    std_dev = 0.001
                initial_temp = 10 * std_dev
                temp = initial_temp

            # Restart mechanism on stagnation - ADDED PERTURBATION AND PROJECTION
            if no_improve_count >= patience:
                if pool:
                    idx_pool = np.random.randint(0, len(pool))
                    current = pool[idx_pool][1].copy()
                    # Apply small Gaussian perturbation to all points
                    current += np.random.normal(0, 0.01 * base_length, current.shape)
                    # Project each point back to the triangle
                    for i in range(len(current)):
                        p = current[i]
                        if not is_inside_triangle(p, A, B, C):
                            centroid = (A + B + C) / 3.0
                            d_vec = centroid - p
                            t_low_inner, t_high_inner = 0.0, 1.0
                            for _ in range(10):
                                t_mid_inner = (t_low_inner + t_high_inner) / 2
                                p_mid_inner = p + t_mid_inner * d_vec
n                                if is_inside_triangle(p_mid_inner, A, B, C):
                                    t_low_inner = t_mid_inner
                                else:
                                    t_high_inner = t_mid_inner
                            current[i] = p + t_low_inner * d_vec
                    current_score = get_smallest_triangle_area(current)
                else:
                    current = best.copy()
                    current_score = best_score
                no_improve_count = 0
                restart_count += 1

        return best

    return improve