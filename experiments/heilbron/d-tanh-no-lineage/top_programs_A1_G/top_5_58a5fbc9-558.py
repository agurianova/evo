# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    n_restarts = 50
    best_config = None
    best_min_area = -1

    # Define expanded row distributions (all sum to 11)
    distributions = [
        [1, 2, 3, 5],
        [1, 3, 3, 4],
        [2, 3, 3, 3],
        [1, 1, 4, 5],
        [1, 2, 4, 4]
    ]
    # Track best min_area per distribution
    scores = {tuple(d): -1.0 for d in distributions}

    for restart in range(n_restarts):
        # Bandit-based distribution selection
        if restart < len(distributions):
            row_counts = distributions[restart]
        else:
            if random.random() < 0.8:  # 80% exploitation
                row_counts = max(distributions, key=lambda d: scores[tuple(d)])
            else:
                row_counts = random.choice(distributions)
        
        n_rows = len(row_counts)
        points = []
        
        # Generate symmetric grid configuration
        for i in range(n_rows):
            v_i = 1 - (i + 0.5) / n_rows
            k = row_counts[i]
            total_weight_AB = 1 - v_i
            step = total_weight_AB / k
            
            for j in range(k):
                offset = (j - (k-1)/2) * step
                weight_A = total_weight_AB/2 - offset
                weight_B = total_weight_AB/2 + offset
                P = weight_A * A + weight_B * B + v_i * C
                points.append(P)
        points = np.array(points)
        
        # Min_area-optimized perturbation
        max_attempts = 5
        perturbed_points = []
        for i, P in enumerate(points):
            candidates = []
            for _ in range(max_attempts):
                r = 0.1 * math.sqrt(random.random())
                theta = 2 * math.pi * random.random()
                dx = r * math.cos(theta)
                dy = r * math.sin(theta)
                candidate = P + np.array([dx, dy])
                
                if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                    # Create temporary config with candidate
                    temp_config = points.copy()
                    temp_config[i] = candidate
                    area_val = get_smallest_triangle_area(temp_config)
                    candidates.append((area_val, candidate))
            
            if candidates:
                # Select candidate with highest min_area
                best_candidate = max(candidates, key=lambda x: x[0])[1]
                perturbed_points.append(best_candidate)
            else:
                perturbed_points.append(P)
        points = np.array(perturbed_points)
        
        # Simulated annealing optimization
        current_config = points.copy()
        current_min = get_smallest_triangle_area(current_config)
        
        n_points = len(current_config)
        max_iter = 3000
        initial_temp = 0.1
        cooling_rate = 0.95
        T = initial_temp

        # Adaptive cooling state
        accepted_count = 0
        total_count = 0

        for iter in range(max_iter):
            step_size = 0.05 * (1 - iter / max_iter)
            
            idx = random.randint(0, n_points - 1)
            r = step_size * math.sqrt(random.random())
            theta = 2 * math.pi * random.random()
            dx = r * math.cos(theta)
            dy = r * math.sin(theta)
            candidate_point = current_config[idx] + np.array([dx, dy])
            
            if not is_inside_triangle(candidate_point.reshape(1, 2), A, B, C):
                continue
                
            candidate_config = current_config.copy()
            candidate_config[idx] = candidate_point
            new_min = get_smallest_triangle_area(candidate_config)
            
            # Pure min_area objective (no boundary penalty)
            delta = new_min - current_min
            if delta > 0 or random.random() < math.exp(delta / T):
                current_config = candidate_config
                current_min = new_min
                accepted_count += 1
            
            total_count += 1
            T *= cooling_rate

            # Adaptive cooling adjustment
            if total_count % 100 == 0:
                acceptance_rate = accepted_count / 100.0
                if acceptance_rate > 0.6:
                    cooling_rate = min(0.99, cooling_rate * 1.01)
                elif acceptance_rate < 0.1:
                    cooling_rate = max(0.8, cooling_rate * 0.99)
                accepted_count = 0

        # Update distribution score
        dist_key = tuple(row_counts)
        if current_min > scores[dist_key]:
            scores[dist_key] = current_min

        if current_min > best_min_area:
            best_min_area = current_min
            best_config = current_config.copy()

    return best_config

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.stats import qmc

np.random.seed(42)

def _d_entrypoint():
    A, B, C = get_unit_triangle()
    triangle_height = C[1]  # Precompute triangle height for scaling

    # Empirical calibration based on observed performance
    EMPIRICAL_MAX = 0.030  # Slightly above current best (0.02837) for realistic optimism

    def project_to_triangle(point, a, b, c):
        """Project a point outside the triangle to the nearest point on the boundary."""
        # Check if point is already inside
        if is_inside_triangle([point], a, b, c):
            return point
        
        # Convert to numpy arrays for vector operations
        a, b, c = np.array(a), np.array(b), np.array(c)
        point = np.array(point)
        
        # Edge AB
        ab = b - a
        ap = point - a
        t_ab = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
        t_ab = np.clip(t_ab, 0, 1)
        closest_ab = a + t_ab * ab
        
        # Edge BC
        bc = c - b
        bp = point - b
        t_bc = np.dot(bp, bc) / (np.dot(bc, bc) + 1e-10)
        t_bc = np.clip(t_bc, 0, 1)
        closest_bc = b + t_bc * bc
        
        # Edge CA
        ca = a - c
        cp = point - c
        t_ca = np.dot(cp, ca) / (np.dot(ca, ca) + 1e-10)
        t_ca = np.clip(t_ca, 0, 1)
        closest_ca = c + t_ca * ca
        
        # Find which is closest
        dist_ab = np.linalg.norm(point - closest_ab)
        dist_bc = np.linalg.norm(point - closest_bc)
        dist_ca = np.linalg.norm(point - closest_ca)
        
        if dist_ab <= dist_bc and dist_ab <= dist_ca:
            return closest_ab
        elif dist_bc <= dist_ab and dist_bc <= dist_ca:
            return closest_bc
        else:
            return closest_ca

    def find_minimal_triplet(pts):
        n = pts.shape[0]
        min_area = float('inf')
        best_triplet = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    x1, y1 = pts[i]
                    x2, y2 = pts[j]
                    x3, y3 = pts[k]
                    area = 0.5 * abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
                    if area < min_area:
                        min_area = area
                        best_triplet = (i, j, k)
        return best_triplet, min_area

    def improve(points: np.ndarray) -> np.ndarray:
        # Calculate initial min_area to scale exploration
        initial_min_area = get_smallest_triangle_area(points)
        
        # Adaptive parameters based on problem difficulty
        base_chains = 5
        
        # Scale patience based on problem difficulty with empirical calibration
        difficulty_factor = min(5.0, EMPIRICAL_MAX / max(initial_min_area, 1e-10))
        early_stop_patience = int(80 * difficulty_factor)
        
        # Logarithmic scaling for progress threshold to handle hard problems
        early_progress_threshold = max(0.001, 0.05 * np.log(1 + initial_min_area / 0.001))
        
        best_overall = points.copy()
        best_score_overall = initial_min_area

        all_chains = []
        
        # Create diverse parameter sets for chains using Sobol sequence
        sampler = qmc.Sobol(d=3, scramble=False)
        params = sampler.random(n=base_chains)
        # Scale parameters to desired ranges
        move_ratio_bases = 0.5 + 0.4 * params[:, 0]  # Range 0.5-0.9
        move_ratio_factors = 0.3 + 0.2 * params[:, 1]  # Range 0.3-0.5
        temp_factors = 0.8 + 0.2 * params[:, 2]  # Range 0.8-1.0
        chain_params = list(zip(move_ratio_bases, move_ratio_factors, temp_factors))
        
        # First run base chains with diverse parameters
        for chain_idx in range(base_chains):
            move_ratio_base, move_ratio_factor, temp_factor = chain_params[chain_idx]
            
            # Adaptive jitter proportional to current min_area
            jitter_amount = 0.5 * initial_min_area
            current = points.copy() + np.random.uniform(-jitter_amount, jitter_amount, size=points.shape)
            
            # Project any out-of-bounds points
            for i in range(len(current)):
                if not is_inside_triangle([current[i]], A, B, C):
                    current[i] = project_to_triangle(current[i], A, B, C)
            
            best_chain = current.copy()
            best_chain_score = get_smallest_triangle_area(best_chain)
            current_score = best_chain_score
            initial_score = current_score
            
            # Set temperature based on triangle dimensions instead of min_area
            T = 0.1 * triangle_height * temp_factor
            early_improvement = False
            
            decay = 0.985
            no_improve_count = 0
            
            # Track progress for early decisions
            progress_indicator = 0

            for iter_idx in range(300):
                # Faster increase when stuck - power function instead of log
                move_ratio = min(0.95, move_ratio_base + move_ratio_factor * (no_improve_count / early_stop_patience) ** 0.5)
                
                if np.random.rand() < move_ratio:
                    triplet, _ = find_minimal_triplet(current)
                    i, j, k = triplet
                    x1, y1 = current[i]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    f = (x2 - x1)*(y3 - y1) - (x3 - x1)*(y2 - y1)
                    
                    # SVD-based handling for nearly collinear points
                    points_triplet = np.array([current[i], current[j], current[k]])
                    centroid = np.mean(points_triplet, axis=0)
                    centered = points_triplet - centroid
                    U, S, Vt = np.linalg.svd(centered)
                    
                    # If smallest singular value is very small compared to largest, points are nearly collinear
                    if len(S) > 1 and S[-1] < 1e-5 * S[0]:
                        # Move points perpendicular to the line of best fit
                        direction = Vt[0]  # First principal component
                        perpendicular = np.array([-direction[1], direction[0]])
                        # Distribute the movement to push points apart
                        grad_i = perpendicular
                        grad_j = -2 * perpendicular
                        grad_k = perpendicular
                    else:
                        sign_f = 1.0 if f >= 0 else -1.0
                        grad_i = np.array([y2 - y3, x3 - x2]) * sign_f
                        grad_j = np.array([y3 - y1, x1 - x3]) * sign_f
                        grad_k = np.array([y1 - y2, x2 - x1]) * sign_f

                    # COMBINED gradient normalization for coordinated movement
                    combined_grad = np.concatenate([grad_i, grad_j, grad_k])
                    combined_norm = np.linalg.norm(combined_grad) + 1e-10
                    
                    # Calculate base step size with absolute minimum bound scaled by current min_area
                    ABS_MIN_STEP = 0.01 * current_score
                    base_step_size = max(ABS_MIN_STEP, 0.01 * triangle_height, 0.3 * current_score)
                    
                    # Enhanced step size adaptation with logarithmic scaling
                    improvement_rate = (best_chain_score - initial_score) / (iter_idx + 1)
                    step_size = base_step_size * (1 + 0.3 * np.log1p(max(0, improvement_rate * 100)))
                    
                    # Scale gradients by step size
                    grad_i = (grad_i / combined_norm) * step_size
                    grad_j = (grad_j / combined_norm) * step_size
                    grad_k = (grad_k / combined_norm) * step_size

                    candidate = current.copy()
                    candidate[i] += grad_i
                    candidate[j] += grad_j
                    candidate[k] += grad_k
                else:
                    i, j, k = np.random.choice(11, 3, replace=False)
                    # Use triangle dimensions for random moves too
                    ABS_MIN_STEP = 0.01 * current_score
                    base_step_size = max(ABS_MIN_STEP, 0.01 * triangle_height, 0.5 * current_score)
                    candidate = current.copy()
                    candidate[i] += np.random.normal(0, base_step_size, 2)
                    candidate[j] += np.random.normal(0, base_step_size, 2)
                    candidate[k] += np.random.normal(0, base_step_size, 2)

                # Project any out-of-bounds points to the triangle boundary
                for idx in range(len(candidate)):
                    if not is_inside_triangle([candidate[idx]], A, B, C):
                        candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

                candidate_score = get_smallest_triangle_area(candidate)
                delta = candidate_score - current_score

                # Track early progress for adaptive decisions
                if iter_idx < 100 and candidate_score - initial_score > early_progress_threshold:
                    early_improvement = True
                    progress_indicator = candidate_score - initial_score

                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = candidate_score
                    if candidate_score > best_chain_score:
                        best_chain = candidate
                        best_chain_score = candidate_score
                        no_improve_count = 0
                    else:
                        no_improve_count += 1
                else:
                    no_improve_count += 1

                T *= decay

                # Dynamic temperature reset based on actual progress
                if iter_idx > 20 and no_improve_count > early_stop_patience * 0.5:
                    T = 0.1 * triangle_height * temp_factor
                    no_improve_count = 0

                if no_improve_count >= early_stop_patience:
                    break

            all_chains.append((best_chain, best_chain_score))
            
            if best_chain_score > best_score_overall:
                best_overall = best_chain
                best_score_overall = best_chain_score

        # Invert the chain count relationship: run more chains when progress is slow
        actual_progress = best_score_overall - initial_min_area
        progress_ratio = min(1.0, actual_progress / early_progress_threshold) if early_progress_threshold > 0 else 0
        additional_chains = max(0, min(5, int(5 * (1 - progress_ratio))))
        
        # Create diverse parameter sets for additional chains using Sobol sequence
        if additional_chains > 0:
            params = sampler.random(n=additional_chains)
            move_ratio_bases = 0.5 + 0.4 * params[:, 0]
            move_ratio_factors = 0.3 + 0.2 * params[:, 1]
            temp_factors = 0.8 + 0.2 * params[:, 2]
            chain_params = list(zip(move_ratio_bases, move_ratio_factors, temp_factors))
            
            for i in range(additional_chains):
                move_ratio_base, move_ratio_factor, temp_factor = chain_params[i]
                
                jitter_amount = 0.5 * initial_min_area
                current = points.copy() + np.random.uniform(-jitter_amount, jitter_amount, size=points.shape)
                
                for i in range(len(current)):
                    if not is_inside_triangle([current[i]], A, B, C):
                        current[i] = project_to_triangle(current[i], A, B, C)
                
                best_chain = current.copy()
                best_chain_score = get_smallest_triangle_area(best_chain)
                current_score = best_chain_score
                initial_score = current_score
                
                # Set temperature based on triangle dimensions
                T = 0.1 * triangle_height * temp_factor
                decay = 0.985
                no_improve_count = 0

                for iter_idx in range(300):
                    # Faster increase when stuck - power function instead of log
                    move_ratio = min(0.95, move_ratio_base + move_ratio_factor * (no_improve_count / early_stop_patience) ** 0.5)
                    
                    if np.random.rand() < move_ratio:
                        triplet, _ = find_minimal_triplet(current)
                        i, j, k = triplet
                        x1, y1 = current[i]
                        x2, y2 = current[j]
                        x3, y3 = current[k]
                        f = (x2 - x1)*(y3 - y1) - (x3 - x1)*(y2 - y1)
                        
                        # SVD-based handling for nearly collinear points
                        points_triplet = np.array([current[i], current[j], current[k]])
                        centroid = np.mean(points_triplet, axis=0)
                        centered = points_triplet - centroid
                        U, S, Vt = np.linalg.svd(centered)
                        
                        if len(S) > 1 and S[-1] < 1e-5 * S[0]:
                            direction = Vt[0]
                            perpendicular = np.array([-direction[1], direction[0]])
                            grad_i = perpendicular
                            grad_j = -2 * perpendicular
                            grad_k = perpendicular
                        else:
                            sign_f = 1.0 if f >= 0 else -1.0
                            grad_i = np.array([y2 - y3, x3 - x2]) * sign_f
                            grad_j = np.array([y3 - y1, x1 - x3]) * sign_f
                            grad_k = np.array([y1 - y2, x2 - x1]) * sign_f

                        # COMBINED gradient normalization
                        combined_grad = np.concatenate([grad_i, grad_j, grad_k])
                        combined_norm = np.linalg.norm(combined_grad) + 1e-10
                        
                        # Base step size with minimum bound scaled by current min_area
                        ABS_MIN_STEP = 0.01 * current_score
                        base_step_size = max(ABS_MIN_STEP, 0.01 * triangle_height, 0.3 * current_score)
                        
                        # Adaptive step size with logarithmic scaling
                        improvement_rate = (best_chain_score - initial_score) / (iter_idx + 1)
                        step_size = base_step_size * (1 + 0.3 * np.log1p(max(0, improvement_rate * 100)))
                        
                        # Scale gradients by step size
                        grad_i = (grad_i / combined_norm) * step_size
                        grad_j = (grad_j / combined_norm) * step_size
                        grad_k = (grad_k / combined_norm) * step_size

                        candidate = current.copy()
                        candidate[i] += grad_i
                        candidate[j] += grad_j
                        candidate[k] += grad_k
                    else:
                        i, j, k = np.random.choice(11, 3, replace=False)
                        ABS_MIN_STEP = 0.01 * current_score
                        base_step_size = max(ABS_MIN_STEP, 0.01 * triangle_height, 0.5 * current_score)
                        candidate = current.copy()
                        candidate[i] += np.random.normal(0, base_step_size, 2)
                        candidate[j] += np.random.normal(0, base_step_size, 2)
                        candidate[k] += np.random.normal(0, base_step_size, 2)

                    for idx in range(len(candidate)):
                        if not is_inside_triangle([candidate[idx]], A, B, C):
                            candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

                    candidate_score = get_smallest_triangle_area(candidate)
                    delta = candidate_score - current_score

                    if delta > 0 or np.random.rand() < np.exp(delta / T):
                        current = candidate
                        current_score = candidate_score
                        if candidate_score > best_chain_score:
                            best_chain = candidate
                            best_chain_score = candidate_score
                            no_improve_count = 0
                        else:
                            no_improve_count += 1
                    else:
                        no_improve_count += 1

                    T *= decay

                    # Dynamic temperature reset based on actual progress
                    if iter_idx > 20 and no_improve_count > early_stop_patience * 0.5:
                        T = 0.1 * triangle_height * temp_factor
                        no_improve_count = 0

                    if no_improve_count >= early_stop_patience:
                        break

                all_chains.append((best_chain, best_chain_score))
                
                if best_chain_score > best_score_overall:
                    best_overall = best_chain
                    best_score_overall = best_chain_score

        # Final refinement phase on top chains
        # Adaptive top_n based on problem difficulty
        top_n = max(2, min(5, int(3 * initial_min_area/EMPIRICAL_MAX)))
        top_chains = sorted(all_chains, key=lambda x: x[1], reverse=True)[:top_n]
        for chain, score in top_chains:
            current = chain.copy()
            current_score = score
            initial_refinement_score = current_score
            
            # Pure gradient ascent with decaying step size
            for refinement_iter in range(50):
                # Adaptive decay rate based on improvement
                improvement_rate = (current_score - initial_refinement_score) / (refinement_iter + 1)
                decay_rate = max(0.7, 0.9 - 0.2 * improvement_rate)  # Between 0.7 and 0.9
                
                # Base step size with minimum bound for refinement
                ABS_MIN_STEP = 0.01 * current_score
                base_step_size = max(ABS_MIN_STEP, 0.01 * triangle_height, 0.1 * current_score)
                step_size = base_step_size * (decay_rate ** refinement_iter)
                
                triplet, _ = find_minimal_triplet(current)
                i, j, k = triplet
                
                x1, y1 = current[i]
                x2, y2 = current[j]
                x3, y3 = current[k]
                f = (x2 - x1)*(y3 - y1) - (x3 - x1)*(y2 - y1)
                
                # SVD-based handling for nearly collinear points
                points_triplet = np.array([current[i], current[j], current[k]])
                centroid = np.mean(points_triplet, axis=0)
                centered = points_triplet - centroid
                U, S, Vt = np.linalg.svd(centered)
                
                if len(S) > 1 and S[-1] < 1e-5 * S[0]:
                    direction = Vt[0]
                    perpendicular = np.array([-direction[1], direction[0]])
                    grad_i = perpendicular
                    grad_j = -2 * perpendicular
                    grad_k = perpendicular
                else:
                    sign_f = 1.0 if f >= 0 else -1.0
                    grad_i = np.array([y2 - y3, x3 - x2]) * sign_f
                    grad_j = np.array([y3 - y1, x1 - x3]) * sign_f
                    grad_k = np.array([y1 - y2, x2 - x1]) * sign_f

                # COMBINED gradient normalization in refinement phase too
                combined_grad = np.concatenate([grad_i, grad_j, grad_k])
                combined_norm = np.linalg.norm(combined_grad) + 1e-10
                
                # Scale gradients by step size
                grad_i = (grad_i / combined_norm) * step_size
                grad_j = (grad_j / combined_norm) * step_size
                grad_k = (grad_k / combined_norm) * step_size

                candidate = current.copy()
                candidate[i] += grad_i
                candidate[j] += grad_j
                candidate[k] += grad_k

                # Project any out-of-bounds points
                for idx in range(len(candidate)):
                    if not is_inside_triangle([candidate[idx]], A, B, C):
                        candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

                candidate_score = get_smallest_triangle_area(candidate)
                
                if candidate_score > current_score:
                    current = candidate
                    current_score = candidate_score
                    
                    if current_score > best_score_overall:
                        best_overall = current
                        best_score_overall = current_score

        return best_overall

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)