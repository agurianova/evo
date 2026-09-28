from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.stats import qmc

np.random.seed(42)

# Theoretical maximum for n=11 in unit area triangle is approximately 0.0319
# Use 95% of this as our practical maximum
THEORETICAL_MAX = 0.0319

HISTORY_SIZE = 50

# Global history variables for tracking successful movements across improve() calls
_movement_history = np.zeros((HISTORY_SIZE, 6))  # 6 dimensions for 3 points (x,y) each
_history_weights = np.zeros(HISTORY_SIZE)  # Weight for each historical movement
_history_count = 0
_history_index = 0

def update_movement_history(triplet_indices, movement_vectors, weight=1.0):
    """Update the movement history with successful triplet movements, weighted by improvement"""
    global _history_count, _history_index
    
    # Flatten the movement vectors for the three points
    flat_movement = np.concatenate([movement_vectors[i] for i in range(3)])
    
    # Store in circular buffer with weight
    _movement_history[_history_index] = flat_movement
    _history_weights[_history_index] = weight
    _history_index = (_history_index + 1) % HISTORY_SIZE
    if _history_count < HISTORY_SIZE:
        _history_count += 1

def get_historical_bias(triplet_indices):
    """Get a bias vector based on historical successful movements, weighted by improvement"""
    if _history_count == 0:
        return np.zeros(6)  # No history yet
    
    # Weighted average of historical movements
    total_weight = np.sum(_history_weights[:_history_count])
    if total_weight < 1e-10:
        return np.zeros(6)
    
    weighted_sum = np.zeros(6)
    for i in range(_history_count):
        weighted_sum += _history_weights[i] * _movement_history[i]
    
    return weighted_sum / total_weight

def entrypoint():
    A, B, C = get_unit_triangle()
    triangle_height = C[1]  # Precompute triangle height for scaling

    # Dynamic EMPIRICAL_MAX based on theoretical limits
    EMPIRICAL_MAX = 0.95 * THEORETICAL_MAX

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
        # Scale base chains with difficulty factor
        difficulty_factor = min(5.0, EMPIRICAL_MAX / max(initial_min_area, 1e-10))
        base_chains = max(5, min(15, int(5 * difficulty_factor)))
        
        # Scale patience based on problem difficulty with empirical calibration
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
            
            # DYNAMIC JITTER SCALING: Scale factor based on problem difficulty
            jitter_factor = 0.3 + 0.7 * (1 - initial_min_area / EMPIRICAL_MAX)
            jitter_amount = jitter_factor * initial_min_area
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
                    
                    # ADAPTIVE COLLNEARITY THRESHOLD: Scale with current min_area
                    collinearity_threshold = 1e-5 * max(0.001, current_score)
                    if len(S) > 1 and S[-1] < collinearity_threshold * S[0]:
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

                    # Blend with historical successful movements
                    historical_bias = get_historical_bias((i, j, k))
                    historical_bias_i = historical_bias[0:2]
                    historical_bias_j = historical_bias[2:4]
                    historical_bias_k = historical_bias[4:6]
                    
                    # DYNAMIC GRADIENT BLENDING: Blend factor based on problem difficulty
                    blend_factor = 0.1 + 0.6 * (1 - current_score / EMPIRICAL_MAX)
                    grad_i = (1 - blend_factor) * grad_i + blend_factor * historical_bias_i
                    grad_j = (1 - blend_factor) * grad_j + blend_factor * historical_bias_j
                    grad_k = (1 - blend_factor) * grad_k + blend_factor * historical_bias_k

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
                        
                        # WEIGHTED HISTORY UPDATES: Update from all chains with weight based on improvement
                        improvement_ratio = (best_chain_score - initial_score) / max(initial_score, 1e-10)
                        if improvement_ratio > 0.01:  # Only update if >1% improvement
                            movement_vectors = [grad_i, grad_j, grad_k]
                            update_movement_history((i, j, k), movement_vectors, weight=improvement_ratio)
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

        # EXPONENTIAL EXPLORATION SCALING: Quadratic relationship for additional chains
        actual_progress = best_score_overall - initial_min_area
        progress_ratio = min(1.0, actual_progress / early_progress_threshold) if early_progress_threshold > 0 else 0
        additional_chains = max(0, min(5, int(5 * (1 - progress_ratio)**2)))
        
        # Create diverse parameter sets for additional chains using Sobol sequence
        if additional_chains > 0:
            params = sampler.random(n=additional_chains)
            move_ratio_bases = 0.5 + 0.4 * params[:, 0]
            move_ratio_factors = 0.3 + 0.2 * params[:, 1]
            temp_factors = 0.8 + 0.2 * params[:, 2]
            chain_params = list(zip(move_ratio_bases, move_ratio_factors, temp_factors))
            
            for i in range(additional_chains):
                move_ratio_base, move_ratio_factor, temp_factor = chain_params[i]
                
                # DYNAMIC JITTER SCALING: Scale factor based on problem difficulty
                jitter_factor = 0.3 + 0.7 * (1 - initial_min_area / EMPIRICAL_MAX)
                jitter_amount = jitter_factor * initial_min_area
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
                        
                        # ADAPTIVE COLLNEARITY THRESHOLD: Scale with current min_area
                        collinearity_threshold = 1e-5 * max(0.001, current_score)
                        if len(S) > 1 and S[-1] < collinearity_threshold * S[0]:
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

                        # Blend with historical successful movements
                        historical_bias = get_historical_bias((i, j, k))
                        historical_bias_i = historical_bias[0:2]
                        historical_bias_j = historical_bias[2:4]
                        historical_bias_k = historical_bias[4:6]
                        
                        # DYNAMIC GRADIENT BLENDING: Blend factor based on problem difficulty
                        blend_factor = 0.1 + 0.6 * (1 - current_score / EMPIRICAL_MAX)
                        grad_i = (1 - blend_factor) * grad_i + blend_factor * historical_bias_i
                        grad_j = (1 - blend_factor) * grad_j + blend_factor * historical_bias_j
                        grad_k = (1 - blend_factor) * grad_k + blend_factor * historical_bias_k

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
                            
                            # WEIGHTED HISTORY UPDATES: Update from all chains with weight based on improvement
                            improvement_ratio = (best_chain_score - initial_score) / max(initial_score, 1e-10)
                            if improvement_ratio > 0.01:
                                movement_vectors = [grad_i, grad_j, grad_k]
                                update_movement_history((i, j, k), movement_vectors, weight=improvement_ratio)
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
                
                # ADAPTIVE COLLNEARITY THRESHOLD: Scale with current min_area
                collinearity_threshold = 1e-5 * max(0.001, current_score)
                if len(S) > 1 and S[-1] < collinearity_threshold * S[0]:
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

                # Blend with historical successful movements
                historical_bias = get_historical_bias((i, j, k))
                historical_bias_i = historical_bias[0:2]
                historical_bias_j = historical_bias[2:4]
                historical_bias_k = historical_bias[4:6]
                
                # DYNAMIC GRADIENT BLENDING: Blend factor based on problem difficulty
                blend_factor = 0.1 + 0.6 * (1 - current_score / EMPIRICAL_MAX)
                grad_i = (1 - blend_factor) * grad_i + blend_factor * historical_bias_i
                grad_j = (1 - blend_factor) * grad_j + blend_factor * historical_bias_j
                grad_k = (1 - blend_factor) * grad_k + blend_factor * historical_bias_k

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