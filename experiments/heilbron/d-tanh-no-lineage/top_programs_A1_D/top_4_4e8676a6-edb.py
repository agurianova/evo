from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import math

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

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
        # Adaptive early progress threshold
        early_progress_threshold = max(0.005, 0.05 * initial_min_area)  # Adaptive threshold
        
        best_overall = points.copy()
        best_score_overall = initial_min_area

        all_chains = []
        
        # Scale patience based on problem difficulty
        difficulty_factor = min(5.0, 0.0365 / max(initial_min_area, 1e-10))
        early_stop_patience = int(80 * difficulty_factor)
        
        # Calculate adaptive reset iteration for temperature
        reset_iter = int(30 * (1 + 0.5 * difficulty_factor))
        
        # First run a subset of chains to determine if we need more
        for chain_idx in range(base_chains):
            # Adaptive jitter proportional to current min_area
            jitter_factor = 0.3 + 0.4 * (1 - initial_min_area/0.0365)
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
            
            # Increased initial temperature from 0.2 to 0.5 for better exploration
            T = 0.5 * current_score
            early_improvement = False
            
            decay = 0.985
            no_improve_count = 0
            
            # Track progress for early decisions
            progress_indicator = 0

            for iter_idx in range(300):  # Using max iterations instead of per_chain_max_iter
                # Smooth logarithmic move ratio adaptation
                move_ratio = min(0.9, 0.6 + 0.3 * math.log(1 + no_improve_count / early_stop_patience))
                
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

                    # Normalize each gradient independently to ensure equal relative importance
                    grad_i = grad_i / (np.linalg.norm(grad_i) + 1e-10)
                    grad_j = grad_j / (np.linalg.norm(grad_j) + 1e-10)
                    grad_k = grad_k / (np.linalg.norm(grad_k) + 1e-10)

                    # Calculate improvement rate for adaptive step size
                    improvement_rate = (best_chain_score - initial_score) / (iter_idx + 1)
                    # Dampened step size adaptation to prevent overshooting
                    step_size = 0.3 * current_score * (1 + 0.5 * math.sqrt(max(0, improvement_rate)))
                    candidate = current.copy()
                    candidate[i] += step_size * grad_i
                    candidate[j] += step_size * grad_j
                    candidate[k] += step_size * grad_k
                else:
                    i, j, k = np.random.choice(11, 3, replace=False)
                    # Adaptive step size for random moves
                    step_size = 0.5 * current_score
                    candidate = current.copy()
                    candidate[i] += np.random.normal(0, step_size, 2)
                    candidate[j] += np.random.normal(0, step_size, 2)
                    candidate[k] += np.random.normal(0, step_size, 2)

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

                if no_improve_count >= early_stop_patience:
                    break

                # Adaptive temperature reset timing
                if iter_idx == reset_iter and not early_improvement:
                    T = 0.5 * current_score

            all_chains.append((best_chain, best_chain_score))
            
            if best_chain_score > best_score_overall:
                best_overall = best_chain
                best_score_overall = best_chain_score

        # Adaptive chain count: scale additional chains proportionally to progress amount
        progress_ratio = (best_score_overall - initial_min_area) / max(initial_min_area, 1e-10)
        additional_chains = max(0, min(5, int(progress_ratio * 10)))
        for _ in range(additional_chains):
            # Adaptive jitter proportional to current min_area
            jitter_factor = 0.3 + 0.4 * (1 - initial_min_area/0.0365)
            jitter_amount = jitter_factor * initial_min_area
            current = points.copy() + np.random.uniform(-jitter_amount, jitter_amount, size=points.shape)
            
            for i in range(len(current)):
                if not is_inside_triangle([current[i]], A, B, C):
                    current[i] = project_to_triangle(current[i], A, B, C)
            
            best_chain = current.copy()
            best_chain_score = get_smallest_triangle_area(best_chain)
            current_score = best_chain_score
            initial_score = current_score
            
            # Increased initial temperature from 0.2 to 0.5
            T = 0.5 * current_score
            decay = 0.985
            no_improve_count = 0

            for iter_idx in range(300):
                # Smooth logarithmic move ratio adaptation
                move_ratio = min(0.9, 0.6 + 0.3 * math.log(1 + no_improve_count / early_stop_patience))
                
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

                    # Normalize each gradient independently to ensure equal relative importance
                    grad_i = grad_i / (np.linalg.norm(grad_i) + 1e-10)
                    grad_j = grad_j / (np.linalg.norm(grad_j) + 1e-10)
                    grad_k = grad_k / (np.linalg.norm(grad_k) + 1e-10)

                    # Dampened step size adaptation
                    improvement_rate = (best_chain_score - initial_score) / (iter_idx + 1)
                    step_size = 0.3 * current_score * (1 + 0.5 * math.sqrt(max(0, improvement_rate)))
                    candidate = current.copy()
                    candidate[i] += step_size * grad_i
                    candidate[j] += step_size * grad_j
                    candidate[k] += step_size * grad_k
                else:
                    i, j, k = np.random.choice(11, 3, replace=False)
                    step_size = 0.5 * current_score
                    candidate = current.copy()
                    candidate[i] += np.random.normal(0, step_size, 2)
                    candidate[j] += np.random.normal(0, step_size, 2)
                    candidate[k] += np.random.normal(0, step_size, 2)

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

                if no_improve_count >= early_stop_patience:
                    break

            all_chains.append((best_chain, best_chain_score))
            
            if best_chain_score > best_score_overall:
                best_overall = best_chain
                best_score_overall = best_chain_score

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
                step_size = 0.1 * current_score * (decay_rate ** refinement_iter)  # decaying from 0.1 to 0.01
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

                # Normalize each gradient independently to ensure equal relative importance
                grad_i = grad_i / (np.linalg.norm(grad_i) + 1e-10)
                grad_j = grad_j / (np.linalg.norm(grad_j) + 1e-10)
                grad_k = grad_k / (np.linalg.norm(grad_k) + 1e-10)

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