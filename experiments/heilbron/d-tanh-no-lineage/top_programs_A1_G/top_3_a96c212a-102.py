# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
import numpy as np
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Precompute triangle dimensions
    base = B[0] - A[0]
    height = C[1]

    def generate_initial_grid():
        # Parameterized row count for 11 points: 4 rows provides better distribution
        n_rows = 4
        # Balanced distributions for 4 rows with 11 points
        distributions = [
            [2, 3, 3, 3],
            [3, 2, 3, 3],
            [3, 3, 2, 3],
            [3, 3, 3, 2],
            [2, 2, 3, 4],
            [2, 2, 4, 3],
            [2, 4, 2, 3],
            [4, 2, 2, 3]
        ]
        points_per_row = random.choice(distributions)
        points = []
        for i in range(n_rows):
            y = (i + 0.5) * (height / n_rows)
            width = base * (1 - y / height)
            x0 = (base - width) / 2
            spacing = width / (points_per_row[i] - 1) if points_per_row[i] > 1 else 0
            
            for j in range(points_per_row[i]):
                x = x0 + j * spacing
                # Apply larger perturbation with validity checks
                for _ in range(10):
                    dx = random.uniform(-0.02, 0.02)  # Increased from ±0.01 to ±0.02
                    dy = random.uniform(-0.02, 0.02)
                    candidate = np.array([x + dx, y + dy])
                    
                    # Check inside triangle and distinctness
                    if not is_inside_triangle([candidate], A, B, C):
                        continue
                    distinct = True
                    for p in points:
                        if np.linalg.norm(candidate - p) < 0.001:
                            distinct = False
                            break
                    if distinct:
                        points.append(candidate)
                        break
                else:
                    points.append(np.array([x, y]))  # Fallback to unperturbed
        return np.array(points)

    best_config = None
    best_min_area = -1

    for seed in range(10):
        np.random.seed(seed)
        random.seed(seed)
        
        # Generate and validate initial grid
        points = generate_initial_grid()
        if not is_inside_triangle(points, A, B, C):
            continue
        
        # Initial min area
        current_min_area = get_smallest_triangle_area(points)
        
        # Adaptive initial temperature based on point count and target
        T0_initial = 0.015  # Slightly higher base temperature
        current_T0 = T0_initial
        step_size0 = 0.1
        num_iterations = 5000
        
        # Track best in this seed
        best_config_this_seed = points.copy()
        best_min_area_this_seed = current_min_area
        last_improvement_iter = 0
        improvement_streak = 0
        max_stagnation = 1000

        for iter in range(num_iterations):
            # Recompute min area and critical points via brute force
            min_area_val = float('inf')
            freq = [0] * 11  # Frequency of points in minimal triangles
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        a, b, c = points[i], points[j], points[k]
                        area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        if area < min_area_val - 1e-9:
                            min_area_val = area
                            freq = [0] * 11
                            freq[i] = 1
                            freq[j] = 1
                            freq[k] = 1
                        elif abs(area - min_area_val) <= 1e-9:
                            freq[i] += 1
                            freq[j] += 1
                            freq[k] += 1
            current_min_area = min_area_val

            # Adaptive restart condition with dynamic threshold
            stagnation = iter - last_improvement_iter
            if stagnation > max_stagnation:
                points = best_config_this_seed.copy()
                current_min_area = best_min_area_this_seed
                # Adaptive temperature boost based on stagnation
                temp_boost = 1.0 + (stagnation - max_stagnation) / 2000.0
                current_T0 = min(0.5, current_T0 * temp_boost)  # Cap temperature
                last_improvement_iter = iter
                improvement_streak = 0

            # Compute temperature with adaptive cooling
            T = current_T0 / (1 + math.log(1 + iter))

            # Select point to perturb with frequency weighting
            critical_set = {i for i in range(11) if freq[i] > 0}
            if critical_set and random.random() < 0.8:
                critical_points = list(critical_set)
                critical_freqs = [freq[i] for i in critical_points]
                total_freq = sum(critical_freqs)
                if total_freq > 0:
                    probs = [f / total_freq for f in critical_freqs]
                    idx = np.random.choice(critical_points, p=probs)
                else:
                    idx = random.choice(critical_points)
            else:
                idx = random.randint(0, 10)

            old_point = points[idx].copy()
            frac = iter / num_iterations
            
            # Power-law step size decay (1.5 exponent) for better exploration/exploitation balance
            step_size = step_size0 * ((1 - frac) ** 1.5)

            # Generate and validate candidate
            delta = np.random.uniform(-step_size, step_size, size=2)
            candidate = old_point + delta
            
            if not is_inside_triangle([candidate], A, B, C):
                continue
            
            distinct = True
            for i in range(11):
                if i == idx:
                    continue
                if np.linalg.norm(candidate - points[i]) < 0.001:
                    distinct = False
                    break
            if not distinct:
                continue

            # Evaluate candidate
            points[idx] = candidate
            new_min_area = get_smallest_triangle_area(points)
            if new_min_area <= 0:
                points[idx] = old_point
                continue

            # Simulated annealing acceptance
            delta_area = new_min_area - current_min_area
            if delta_area >= 0:
                current_min_area = new_min_area
                # Track best configuration in this seed
                if new_min_area > best_min_area_this_seed:
                    best_min_area_this_seed = new_min_area
                    best_config_this_seed = points.copy()
                    last_improvement_iter = iter
                    improvement_streak += 1
                    # Reduce temperature if consistently improving
                    if improvement_streak > 200:
                        current_T0 = max(0.005, current_T0 * 0.95)
                        improvement_streak = 0
            else:
                if T > 1e-9 and random.random() < math.exp(delta_area / T):
                    current_min_area = new_min_area
                else:
                    points[idx] = old_point

        # Track best configuration across seeds
        final_area = get_smallest_triangle_area(points)
        if final_area > best_min_area:
            best_min_area = final_area
            best_config = points.copy()

    return best_config

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def _d_entrypoint():
    A, B, C = get_unit_triangle()
    triangle_height = C[1]  # Precompute triangle height for scaling

    # Empirical calibration based on observed performance
    EMPIRICAL_MAX = 0.030  # Slightly above current best (0.02837) for realistic optimism
    ABS_MIN_STEP = 0.001 * triangle_height  # Absolute minimum step size

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
        
        # Create diverse parameter sets for chains
        chain_params = []
        for i in range(base_chains):
            # Vary exploration parameters across chains
            move_ratio_base = 0.5 + 0.2 * (i % 3)  # Cycle through 0.5, 0.7, 0.9
            move_ratio_factor = 0.3 + 0.1 * (i % 2)  # Cycle through 0.3, 0.4
            temp_factor = 0.8 + 0.2 * (i % 2)  # Cycle through 0.8, 1.0
            chain_params.append((move_ratio_base, move_ratio_factor, temp_factor))
        
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
                    
                    # Handle nearly collinear points for gradient direction robustness
                    if abs(f) < 1e-10:
                        f = 1e-10  # Perturb slightly to break tie
                    sign_f = 1.0 if f >= 0 else -1.0

                    grad_i = np.array([y2 - y3, x3 - x2]) * sign_f
                    grad_j = np.array([y3 - y1, x1 - x3]) * sign_f
                    grad_k = np.array([y1 - y2, x2 - x1]) * sign_f

                    # COMBINED gradient normalization for coordinated movement
                    combined_grad = np.concatenate([grad_i, grad_j, grad_k])
                    combined_norm = np.linalg.norm(combined_grad) + 1e-10
                    
                    # Calculate base step size with absolute minimum bound
                    base_step_size = max(ABS_MIN_STEP, 0.01 * triangle_height, 0.3 * current_score)
                    
                    # Dampened step size with sqrt(improvement_rate)
                    improvement_rate = (best_chain_score - initial_score) / (iter_idx + 1)
                    step_size = base_step_size * (1 + 0.5 * np.sqrt(max(0, improvement_rate)))
                    
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
        
        # Create diverse parameter sets for additional chains
        for i in range(additional_chains):
            move_ratio_base = 0.5 + 0.2 * ((base_chains + i) % 3)
            move_ratio_factor = 0.3 + 0.1 * ((base_chains + i) % 2)
            temp_factor = 0.8 + 0.2 * ((base_chains + i) % 2)
            
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
                    
                    # Handle nearly collinear points
                    if abs(f) < 1e-10:
                        f = 1e-10
                    sign_f = 1.0 if f >= 0 else -1.0

                    grad_i = np.array([y2 - y3, x3 - x2]) * sign_f
                    grad_j = np.array([y3 - y1, x1 - x3]) * sign_f
                    grad_k = np.array([y1 - y2, x2 - x1]) * sign_f

                    # COMBINED gradient normalization
                    combined_grad = np.concatenate([grad_i, grad_j, grad_k])
                    combined_norm = np.linalg.norm(combined_grad) + 1e-10
                    
                    # Base step size with absolute minimum bound
                    base_step_size = max(ABS_MIN_STEP, 0.01 * triangle_height, 0.3 * current_score)
                    
                    # Adaptive step size with dampened improvement rate
                    improvement_rate = (best_chain_score - initial_score) / (iter_idx + 1)
                    step_size = base_step_size * (1 + 0.5 * np.sqrt(max(0, improvement_rate)))
                    
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
                base_step_size = max(ABS_MIN_STEP, 0.01 * triangle_height, 0.1 * current_score)
                step_size = base_step_size * (decay_rate ** refinement_iter)
                
                triplet, _ = find_minimal_triplet(current)
                i, j, k = triplet
                
                x1, y1 = current[i]
                x2, y2 = current[j]
                x3, y3 = current[k]
                f = (x2 - x1)*(y3 - y1) - (x3 - x1)*(y2 - y1)
                
                # Handle nearly collinear points
                if abs(f) < 1e-10:
                    f = 1e-10
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