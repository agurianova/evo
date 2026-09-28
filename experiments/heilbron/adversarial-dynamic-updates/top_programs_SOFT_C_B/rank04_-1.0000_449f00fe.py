from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    side_length = np.linalg.norm(B - A)  # Precompute side length for barycentric scaling

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Precompute denominator for barycentric conversion (2 * area of ABC)
        denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
        
        # Helper functions for barycentric conversion
        def to_bary(p):
            u = ((B[1] - C[1]) * (p[0] - C[0]) + (C[0] - B[0]) * (p[1] - C[1])) / denom
            v = ((C[1] - A[1]) * (p[0] - C[0]) + (A[0] - C[0]) * (p[1] - C[1])) / denom
            return u, v
        
        def to_cart(u, v):
            w = 1 - u - v
            return u * A + v * B + w * C

        def boundary_penalty(p):
            """Cubic penalty function based on proximity to boundary (1.0 at center, approaches 0 near boundaries)"""
            u, v = to_bary(p)
            w = 1 - u - v
            min_dist = min(u, v, w)
            # Cubic function for smooth transition
            return 1.0 - (1.0 - min_dist)**3

        def soft_repulsion(p1, p2, min_dist=0.01):
            """Soft repulsion force between two points to maintain distinctness"""
            dist = np.linalg.norm(p2 - p1)
            if dist < min_dist:
                # Inverse-square repulsion with smooth transition
                strength = (min_dist - dist) / (min_dist * dist)
                direction = (p1 - p2) / dist if dist > 1e-10 else np.array([1.0, 0.0])
                return strength * direction
            return np.zeros(2)

        # Initialize step size based on current min area
        initial_step = 0.1 * np.sqrt(best_score) if best_score > 0 else 0.05
        step_size = initial_step
        stagnation_count = 0
        restart_failure_count = 0
        max_iterations = 500
        adaptive_stopping_threshold = 1e-5 * side_length
        min_step_size = 1e-8 * side_length
        tol = 1e-9
        n = 11
        
        # Adaptive temperature for exploration (starts high, cools over time)
        temperature = 1.0
        temperature_decay = 0.995
        
        # Track improvement rate for dynamic step adaptation
        improvement_window = 20
        improvement_history = [0] * improvement_window
        improvement_idx = 0
        last_significant_improvement = best_score
        
        # Track relative improvement for better stagnation detection
        relative_improvement_history = [0] * improvement_window
n        relative_improvement_idx = 0

        for _ in range(max_iterations):
            # Find all minimal-area triangles and compute true minimum
            min_area = float('inf')
            all_areas = []
            
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = best[i]
                        x2, y2 = best[j]
                        x3, y3 = best[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        all_areas.append(area)
                        if area < min_area:
                            min_area = area
            
            # Collect minimal triangles with vertex frequency weighting
            min_triplets = []
            min_area_eps = min_area * (1 + 1e-5)  # Use relative tolerance for stability
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = best[i]
                        x2, y2 = best[j]
                        x3, y3 = best[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area <= min_area_eps:
                            min_triplets.append((i, j, k))
            
            # Count vertex frequencies in minimal triangles
            freq = [0] * n
            for triplet in min_triplets:
                i, j, k = triplet
                freq[i] += 1
                freq[j] += 1
                freq[k] += 1
            
            # Normalize frequencies for weighting
            max_freq = max(freq) if max(freq) > 0 else 1
            weights = [f / max_freq for f in freq]
            
            # Identify all points in minimal triangles
            min_points = set()
            for triplet in min_triplets:
                i, j, k = triplet
                min_points.update([i, j, k])
            min_points = list(min_points)
            
            # If no minimal triangles found (shouldn't happen), skip iteration
            if not min_points:
                continue
                
            # Compute gradients for minimal triangles with vertex-frequency weighting
            gradients = np.zeros((n, 2))
            for triplet in min_triplets:
                i, j, k = triplet
                p_i, p_j, p_k = best[i], best[j], best[k]
                
                # Calculate proper gradients for all three points
                # For triangle i,j,k:
                # - Gradient for i: perpendicular to (k-j)
                # - Gradient for j: perpendicular to (i-k)
                # - Gradient for k: perpendicular to (j-i)
                
                # Gradient for i (perpendicular to jk)
                jk = p_k - p_j
                grad_i = np.array([-jk[1], jk[0]])
                
                # Gradient for j (perpendicular to ki)
                ki = p_i - p_k
                grad_j = np.array([-ki[1], ki[0]])
                
                # Gradient for k (perpendicular to ij)
                ij = p_j - p_i
                grad_k = np.array([-ij[1], ij[0]])

                # Apply boundary penalties to gradients
                scale_i = boundary_penalty(p_i)
                scale_j = boundary_penalty(p_j)
                scale_k = boundary_penalty(p_k)
                
                grad_i = grad_i * scale_i
                grad_j = grad_j * scale_j
                grad_k = grad_k * scale_k

                # Normalize gradients
                norm_i = np.linalg.norm(grad_i)
                norm_j = np.linalg.norm(grad_j)
                norm_k = np.linalg.norm(grad_k)
                
                if norm_i > 0:
                    grad_i = grad_i / norm_i
                if norm_j > 0:
                    grad_j = grad_j / norm_j
                if norm_k > 0:
                    grad_k = grad_k / norm_k

                # Apply vertex-frequency-based weighting
                total_weight = weights[i] + weights[j] + weights[k]
                if total_weight > 0:
                    weight_factor = 3.0 / total_weight  # Normalize so average weight is 1
                    gradients[i] += weight_factor * weights[i] * grad_i
                    gradients[j] += weight_factor * weights[j] * grad_j
                    gradients[k] += weight_factor * weights[k] * grad_k

            # Add soft repulsion to maintain distinctness
            repulsion_scale = 0.05 * np.sqrt(min_area)  # Scale repulsion based on problem difficulty
            for i in range(n):
                for j in range(i+1, n):
                    repulsion = soft_repulsion(best[i], best[j], min_dist=0.015 * np.sqrt(min_area))
                    gradients[i] += repulsion_scale * repulsion
                    gradients[j] -= repulsion_scale * repulsion

            # Normalize gradients
            for i in range(n):
                grad_norm = np.linalg.norm(gradients[i])
                if grad_norm > 0:
                    gradients[i] /= grad_norm
            
            # Create candidate by perturbing all minimal points
            candidate = best.copy()
            step_size_bary = max(min_step_size, step_size) / side_length
            
            # Dynamic gradient strength based on stagnation
            grad_base_strength = 0.7
            grad_strength = grad_base_strength * (1.0 + min(stagnation_count / 20.0, 1.0))

            for idx in min_points:
                # Base perturbation: adaptive Gaussian noise (replaces Cauchy)
                scale = step_size_bary * temperature
                du_gaussian = np.random.normal(0, scale)
                dv_gaussian = np.random.normal(0, scale)
                
                # Add gradient direction if available
                grad = gradients[idx]
                du_grad = grad_strength * grad[0] * scale
                dv_grad = grad_strength * grad[1] * scale
                
                # Combine random and gradient-based movement
                du = du_gaussian + du_grad
                dv = dv_gaussian + dv_grad
                
                # Convert current point to barycentric
                u, v = to_bary(candidate[idx])
                
                # Apply perturbation in barycentric coordinates
                u_new, v_new = u + du, v + dv

                # Clamp to simplex [0,1] and adjust for u+v<=1
                u_new = max(0.0, min(1.0, u_new))
                v_new = max(0.0, min(1.0, v_new))
                if u_new + v_new > 1.0:
                    scale = 1.0 / (u_new + v_new)
                    u_new *= scale
                    v_new *= scale

                # Convert back to Cartesian
                new_point = to_cart(u_new, v_new)
                candidate[idx] = new_point
            
            # Check and evaluate candidate
            score = get_smallest_triangle_area(candidate)
            improved = score > best_score
            
            # Track relative improvement for better stagnation detection
            relative_improvement = (score - best_score) / (best_score + 1e-10) if improved else 0
            relative_improvement_history[relative_improvement_idx] = relative_improvement
            relative_improvement_idx = (relative_improvement_idx + 1) % improvement_window
            
            # Update improvement history
            improvement_history[improvement_idx] = 1 if improved else 0
            improvement_idx = (improvement_idx + 1) % improvement_window
            
            if improved:
                best = candidate
                best_score = score
                stagnation_count = 0
                restart_failure_count = 0  # Reset on any improvement
                
                # Dynamically update initial_step if significant improvement
                if best_score > last_significant_improvement * 1.05:
                    initial_step = 0.1 * np.sqrt(best_score)
                    last_significant_improvement = best_score
                    
                    # Reset temperature after significant improvement
                    temperature = 1.0
            else:
                stagnation_count += 1

            # Calculate recent improvement rate for dynamic step adaptation
            improvement_rate = sum(improvement_history) / improvement_window
            
            # Adaptive temperature cooling based on improvement
            if improved:
                temperature = min(1.0, temperature * 1.05)  # Slight increase after improvement
            else:
                temperature = max(0.1, temperature * temperature_decay)

            # Adjust step decay based on improvement rate
            # If improving frequently, decay slower; if stuck, decay faster
            step_decay = 0.95 + 0.05 * improvement_rate  # Ranges from 0.95 to 1.0
            step_size *= step_decay

            # Step size reset (tuned to fraction of current scale)
            if stagnation_count >= 10:
                step_size = 0.1 * initial_step
                stagnation_count = 0

            # Global restart after prolonged stagnation
            if stagnation_count >= 30:
                # Calculate average relative improvement
                avg_relative_improvement = sum(relative_improvement_history) / improvement_window
                
                # Only restart if improvement is truly minimal
                if avg_relative_improvement < 1e-4:
                    # Generate restart candidate with step based on current best_score
                    candidate_restart = best.copy()
                    restart_failure_count += 1
                    # Base restart step on current best_score for appropriate scale
                    restart_step = 0.1 * np.sqrt(best_score)
                    step_size_bary_restart = restart_step / side_length
                    
                    for i in range(n):
                        u, v = to_bary(best[i])
                        # Use adaptive Gaussian for restarts too
                        scale = step_size_bary_restart * temperature
                        du = np.random.normal(0, scale)
                        dv = np.random.normal(0, scale)
                        u_new, v_new = u + du, v + dv
                        u_new = max(0.0, min(1.0, u_new))
                        v_new = max(0.0, min(1.0, v_new))
                        if u_new + v_new > 1.0:
                            scale = 1.0 / (u_new + v_new)
                            u_new *= scale
                            v_new *= scale
                        candidate_restart[i] = to_cart(u_new, v_new)
                    
                    # Evaluate restart candidate
                    score_restart = get_smallest_triangle_area(candidate_restart)
                    if score_restart > best_score:
                        best = candidate_restart
                        best_score = score_restart
                        restart_failure_count = 0
                        
                        # Update initial_step if significant improvement
                        if best_score > last_significant_improvement * 1.05:
                            initial_step = 0.1 * np.sqrt(best_score)
                            last_significant_improvement = best_score
                            
                            # Reset temperature after significant improvement
                            temperature = 1.0
                    
                # Reset search parameters regardless of restart success
                step_size = initial_step
                stagnation_count = 0

            # Safe global perturbation phase for deep stagnation
            if stagnation_count >= 50:
                # Generate candidate by perturbing ALL points
                candidate_global = best.copy()
                global_step = 0.05 * np.sqrt(best_score)
                step_size_bary_global = global_step / side_length
                
                for i in range(n):
                    u, v = to_bary(best[i])
                    # Use adaptive Gaussian for global exploration
                    scale = step_size_bary_global * temperature
                    du = np.random.normal(0, scale)
                    dv = np.random.normal(0, scale)
                    u_new, v_new = u + du, v + dv
                    u_new = max(0.0, min(1.0, u_new))
                    v_new = max(0.0, min(1.0, v_new))
                    if u_new + v_new > 1.0:
                        scale = 1.0 / (u_new + v_new)
                        u_new *= scale
                        v_new *= scale
                    candidate_global[i] = to_cart(u_new, v_new)
                
                # Evaluate global candidate
                score_global = get_smallest_triangle_area(candidate_global)
                if score_global > best_score:
                    best = candidate_global
                    best_score = score_global
                    stagnation_count = 0
                    
                    # Update initial_step if significant improvement
                    if best_score > last_significant_improvement * 1.05:
                        initial_step = 0.1 * np.sqrt(best_score)
                        last_significant_improvement = best_score
                        
                        # Reset temperature after significant improvement
                        temperature = 1.0

            # Adaptive stopping
            if step_size < adaptive_stopping_threshold:
                break

        return best

    return improve