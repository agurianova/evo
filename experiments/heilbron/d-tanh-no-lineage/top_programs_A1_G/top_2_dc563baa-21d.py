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
    
    def min_boundary_distance(points):
        dists = []
        for P in points:
            # Distance to AB
            AB = B - A
            AP = P - A
            cross_ab = AB[0]*AP[1] - AB[1]*AP[0]
            area_ab = 0.5 * abs(cross_ab)
            base_ab = np.linalg.norm(AB)
            dist_ab = 2 * area_ab / base_ab

            # Distance to BC
            BC = C - B
            BP = P - B
            cross_bc = BC[0]*BP[1] - BC[1]*BP[0]
            area_bc = 0.5 * abs(cross_bc)
            base_bc = np.linalg.norm(BC)
            dist_bc = 2 * area_bc / base_bc

            # Distance to CA
            CA = A - C
            CP = P - C
            cross_ca = CA[0]*CP[1] - CA[1]*CP[0]
            area_ca = 0.5 * abs(cross_ca)
            base_ca = np.linalg.norm(CA)
            dist_ca = 2 * area_ca / base_ca

            min_dist = min(dist_ab, dist_bc, dist_ca)
            dists.append(min_dist)
        return min(dists)

    n_restarts = 50
    best_config = None
    best_min_area = -1

    for restart in range(n_restarts):
        # Symmetric row distributions for 11 points
        row_counts = random.choice([[1, 2, 3, 5], [1, 3, 3, 4]])
        n_rows = len(row_counts)
        points = []
        
        # Generate symmetric grid configuration
        for i in range(n_rows):
            v_i = 1 - (i + 0.5) / n_rows  # Weight for C (top-heavy)
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
        
        # Apply Cartesian perturbations with validity checks
        max_attempts = 5
        perturbed_points = []
        for P in points:
            found = False
            for _ in range(max_attempts):
                r = 0.1 * math.sqrt(random.random())
                theta = 2 * math.pi * random.random()
                dx = r * math.cos(theta)
                dy = r * math.sin(theta)
                candidate = P + np.array([dx, dy])
                if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                    perturbed_points.append(candidate)
                    found = True
                    break
            if not found:
                perturbed_points.append(P)
        points = np.array(perturbed_points)
        
        # Simulated annealing optimization
        current_config = points.copy()
        current_min = get_smallest_triangle_area(current_config)
        current_boundary_dist = min_boundary_distance(current_config)
        current_value = current_min + 0.005 * current_boundary_dist
        
        n_points = len(current_config)
        max_iter = 3000
        initial_temp = 0.1
        cooling_rate = 0.95
        T = initial_temp

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
            candidate_boundary_dist = min_boundary_distance(candidate_config)
            candidate_value = new_min + 0.005 * candidate_boundary_dist
            
            delta = candidate_value - current_value
            if delta > 0 or random.random() < math.exp(delta / T):
                current_config = candidate_config
                current_min = new_min
                current_boundary_dist = candidate_boundary_dist
                current_value = candidate_value
                
            T *= cooling_rate

        if current_min > best_min_area:
            best_min_area = current_min
            best_config = current_config.copy()

    return best_config

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def _d_entrypoint():
    A, B, C = get_unit_triangle()
    triangle_height = C[1]  # Height of the unit area triangle

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
        adaptive_chains = base_chains
        # Replaced hardcoded 2% with adaptive threshold (min 0.005 or 5% of initial)
        early_progress_threshold = max(0.005, 0.05 * initial_min_area)
        
        best_overall = points.copy()
        best_score_overall = initial_min_area

        all_chains = []
        
        # Scale patience based on problem difficulty
        difficulty_factor = min(5.0, 0.0365 / max(initial_min_area, 1e-10))
        early_stop_patience = int(120 * difficulty_factor)  # Increased from 80
        
        # First run a subset of chains to determine if we need more
        for chain_idx in range(base_chains):
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
            
            # Set temperature based on problem scale, not current min_area
            T = 0.1 * triangle_height  # Replaced 0.5 * current_score
            early_improvement = False
            
            decay = 0.985
            no_improve_count = 0
            
            # Track progress for early decisions
            progress_indicator = 0

            for iter_idx in range(300):  # Using max iterations instead of per_chain_max_iter
                # Dynamic move ratio based on progress
                move_ratio = min(0.9, 0.6 + 0.3 * np.log(1 + no_improve_count / early_stop_patience))
                
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

                    # COORDINATED gradient normalization (fixes uncoordinated movement)
                    total_grad = np.linalg.norm(grad_i) + np.linalg.norm(grad_j) + np.linalg.norm(grad_k) + 1e-10
                    grad_i = grad_i / total_grad
                    grad_j = grad_j / total_grad
                    grad_k = grad_k / total_grad

                    # Calculate improvement rate for adaptive step size
                    improvement_rate = (best_chain_score - initial_score) / (iter_idx + 1)
                    # Added minimum step size based on triangle dimensions
                    base_step_size = max(0.01 * triangle_height, 0.3 * current_score)
                    step_size = base_step_size * (1 + 0.5 * np.sqrt(max(0, improvement_rate)))
                    candidate = current.copy()
                    candidate[i] += step_size * grad_i
                    candidate[j] += step_size * grad_j
                    candidate[k] += step_size * grad_k
                else:
                    i, j, k = np.random.choice(11, 3, replace=False)
                    # Added minimum step size for random moves
                    base_step_size = max(0.01 * triangle_height, 0.5 * current_score)
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

                # Adaptive temperature reset timing
                reset_iter = int(30 * (1 + 0.5 * difficulty_factor))
                if iter_idx == reset_iter and not early_improvement:
                    T = 0.1 * triangle_height  # Reset based on problem scale

                if no_improve_count >= early_stop_patience:
                    break

            all_chains.append((best_chain, best_chain_score))
            
            if best_chain_score > best_score_overall:
                best_overall = best_chain
                best_score_overall = best_chain_score

        # INVERTED chain count adaptation: run more chains when progress is slow
        actual_progress = best_score_overall - initial_min_area
        progress_ratio = actual_progress / max(early_progress_threshold, 1e-10)
        # Run more chains when progress is slow (inverse relationship)
        additional_chains = max(0, min(5, int(5 * (1 - min(progress_ratio, 0.99)))))
        
        for _ in range(additional_chains):
            jitter_amount = 0.5 * initial_min_area
            current = points.copy() + np.random.uniform(-jitter_amount, jitter_amount, size=points.shape)
            
            for i in range(len(current)):
                if not is_inside_triangle([current[i]], A, B, C):
                    current[i] = project_to_triangle(current[i], A, B, C)
            
            best_chain = current.copy()
            best_chain_score = get_smallest_triangle_area(best_chain)
            current_score = best_chain_score
            initial_score = current_score
            
            # Set temperature based on problem scale
            T = 0.1 * triangle_height
            decay = 0.985
            no_improve_count = 0

            for iter_idx in range(300):
                move_ratio = min(0.9, 0.6 + 0.3 * np.log(1 + no_improve_count / early_stop_patience))
                
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

                    # COORDINATED gradient normalization
                    total_grad = np.linalg.norm(grad_i) + np.linalg.norm(grad_j) + np.linalg.norm(grad_k) + 1e-10
                    grad_i = grad_i / total_grad
                    grad_j = grad_j / total_grad
                    grad_k = grad_k / total_grad

                    # Added minimum step size based on triangle dimensions
                    base_step_size = max(0.01 * triangle_height, 0.3 * current_score)
                    improvement_rate = (best_chain_score - initial_score) / (iter_idx + 1)
                    step_size = base_step_size * (1 + 0.5 * np.sqrt(max(0, improvement_rate)))
                    candidate = current.copy()
                    candidate[i] += step_size * grad_i
                    candidate[j] += step_size * grad_j
                    candidate[k] += step_size * grad_k
                else:
                    i, j, k = np.random.choice(11, 3, replace=False)
                    base_step_size = max(0.01 * triangle_height, 0.5 * current_score)
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

                # Adaptive temperature reset timing
                reset_iter = int(30 * (1 + 0.5 * difficulty_factor))
                if iter_idx == reset_iter and not early_improvement:
                    T = 0.1 * triangle_height

                if no_improve_count >= early_stop_patience:
                    break

            all_chains.append((best_chain, best_chain_score))
            
            if best_chain_score > best_score_overall:
                best_overall = best_chain
                best_score_overall = best_chain_score

        # Final refinement phase on top chains
        # Adaptive top_n based on problem difficulty
        top_n = max(2, min(5, int(3 * initial_min_area/0.0365)))
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
                # Added minimum step size for refinement
                base_step_size = max(0.01 * triangle_height, 0.1 * current_score)
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

                # COORDINATED gradient normalization in refinement phase too
                total_grad = np.linalg.norm(grad_i) + np.linalg.norm(grad_j) + np.linalg.norm(grad_k) + 1e-10
                grad_i = grad_i / total_grad
                grad_j = grad_j / total_grad
                grad_k = grad_k / total_grad

                candidate = current.copy()
                candidate[i] += step_size * grad_i
                candidate[j] += step_size * grad_j
                candidate[k] += step_size * grad_k

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