from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import hashlib


def entrypoint():
    A, B, C = get_unit_triangle()
    # Compute denom for barycentric conversion: (A-C) x (B-C)
    denom = (A[0]-C[0])*(B[1]-C[1]) - (A[1]-C[1])*(B[0]-C[0])

    def cartesian_to_barycentric(p):
        u = ((B[1]-C[1])*(p[0]-C[0]) - (B[0]-C[0])*(p[1]-C[1])) / denom
        v = ((A[0]-C[0])*(p[1]-C[1]) - (A[1]-C[1])*(p[0]-C[0])) / denom
        w = 1.0 - u - v
        return u, v, w

    def improve(points):
        # Set reproducible but input-specific random seed
        points_bytes = points.tobytes()
        hash_val = hashlib.sha256(points_bytes).hexdigest()
        seed = int(hash_val, 16) % (2**32)
        np.random.seed(seed)

        best = points.copy()
        
        # Helper: compute min area and triplet for any config
        def compute_min_area_and_triplet(config):
            n = config.shape[0]
            min_area = float('inf')
            min_triplet = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = 0.5 * abs(
                            (config[j,0]-config[i,0])*(config[k,1]-config[i,1]) - 
                            (config[j,1]-config[i,1])*(config[k,0]-config[i,0])
                        )
                        if area < min_area:
                            min_area = area
                            min_triplet = (i, j, k)
            return min_area, min_triplet

        # Helper: compute min area among triangles involving specific index
        def min_area_involving(config, idx):
            n = config.shape[0]
            min_area = float('inf')
            min_triplet = None
            for i in range(n):
                if i == idx: continue
                for j in range(i+1, n):
                    if j == idx: continue
                    area = 0.5 * abs(
                        (config[j,0]-config[i,0])*(config[idx,1]-config[i,1]) - 
                        (config[j,1]-config[i,1])*(config[idx,0]-config[i,0])
                    )
                    if area < min_area:
                        min_area = area
                        min_triplet = (i, j, idx)
            return min_area, min_triplet

        # Initialize with full scan
        best_score, min_triplet = compute_min_area_and_triplet(best)

        # Parameters for simulated annealing
        temp = 0.01
        cooling_rate = 0.99
        min_temp = 1e-5
        max_iterations = 500  # Increased due to optimization
        restart_patience = 20
        current_step_std = 0.01
        max_step_std = 0.1

        no_improve_count = 0
        iteration = 0

        while iteration < max_iterations and temp > min_temp:
            iteration += 1

            # Randomly select one vertex from current smallest triangle
            idx = np.random.choice(min_triplet)
            candidate = best.copy()

            # Convert point to barycentric coordinates
            p = candidate[idx]
            u, v, w = cartesian_to_barycentric(p)

            # Perturb in barycentric space
            noise = np.random.normal(0, current_step_std, 3)
            u_new = u + noise[0]
            v_new = v + noise[1]
            w_new = w + noise[2]
            
            # Clamp to non-negative and renormalize
            u_new = max(0.0, u_new)
            v_new = max(0.0, v_new)
            w_new = max(0.0, w_new)
            total = u_new + v_new + w_new
            if total < 1e-10:
                u_new, v_new, w_new = 1.0/3, 1.0/3, 1.0/3
            else:
                u_new /= total
                v_new /= total
                w_new /= total

            # Convert back to Cartesian
            p_new = u_new * A + v_new * B + w_new * C
            candidate[idx] = p_new

            # Compute candidate's min area and triplet efficiently
            if idx in min_triplet:
                candidate_score, candidate_triplet = compute_min_area_and_triplet(candidate)
            else:
                min_area_new, new_triplet = min_area_involving(candidate, idx)
                if min_area_new < best_score:
                    candidate_score = min_area_new
                    candidate_triplet = new_triplet
                else:
                    candidate_score = best_score
                    candidate_triplet = min_triplet

            # Simulated annealing acceptance
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
                min_triplet = candidate_triplet
                no_improve_count = 0
            else:
                delta = candidate_score - best_score
                if np.random.rand() < np.exp(delta / temp):
                    best = candidate
                    best_score = candidate_score
                    min_triplet = candidate_triplet
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            # Cool down
            temp *= cooling_rate

            # Check for restart
            if no_improve_count >= restart_patience:
                current_step_std = min(current_step_std * 1.5, max_step_std)
                no_improve_count = 0

        return best

    return improve