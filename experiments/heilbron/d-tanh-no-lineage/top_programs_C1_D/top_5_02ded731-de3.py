from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def calculate_triangle_gradient(triangle, vertex_idx):
        """Calculate gradient of triangle area w.r.t. specified vertex."""
        p0, p1, p2 = triangle
        
        # Calculate signed area (positive for counterclockwise, negative for clockwise)
        signed_area = 0.5 * ((p1[0]-p0[0])*(p2[1]-p0[1]) - (p2[0]-p0[0])*(p1[1]-p0[1]))
        
        # Area = 0.5 * |(p1-p0) × (p2-p0)|
        # Gradient w.r.t. p0
        grad_p0 = np.array([-(p2[1] - p1[1]), p2[0] - p1[0]]) * 0.5
        # Gradient w.r.t. p1
        grad_p1 = np.array([p2[1] - p0[1], -(p2[0] - p0[0])]) * 0.5
        # Gradient w.r.t. p2
        grad_p2 = np.array([-(p1[1] - p0[1]), p1[0] - p0[0]]) * 0.5
        
        # Adjust gradient direction based on signed area to always increase absolute area
        sign = 1.0 if signed_area >= 0 else -1.0
        
        if vertex_idx == 0:
            return grad_p0 * sign
        elif vertex_idx == 1:
            return grad_p1 * sign
        else:
            return grad_p2 * sign

    def constrained_gradient_step(point, gradient, step_size, A, B, C, iteration, total_iterations, boundary_buffer_base=0.001):
        """Take a gradient step while ensuring point remains inside triangle with adaptive boundary repulsion."""
        if np.linalg.norm(gradient) < 1e-8:
            return point
        
        # Calculate dynamic boundary buffer - exponential decay instead of linear
        boundary_buffer = max(0.00005, boundary_buffer_base * 0.95 ** iteration)
        
        # First try full gradient step
        candidate = point + step_size * gradient
        
        # Check if candidate is too close to boundary
        def distance_to_boundary(p):
            # Calculate distance to each edge
            def edge_distance(p, a, b):
                ap = p - a
                ab = b - a
                t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-12)
                t = np.clip(t, 0, 1)
                projection = a + t * ab
                return np.linalg.norm(p - projection)
            
            d1 = edge_distance(p, A, B)
            d2 = edge_distance(p, B, C)
            d3 = edge_distance(p, C, A)
            return min(d1, d2, d3)
        
        # If point is already near boundary, reduce step toward boundary
        current_distance = distance_to_boundary(point)
        if current_distance < boundary_buffer:
            # Reduce step size proportionally to how close we are to boundary
            reduction_factor = current_distance / boundary_buffer
            step_size *= reduction_factor
            
        candidate = point + step_size * gradient
        
        # Project to boundary if outside
        if not is_inside_triangle(candidate.reshape(1, 2), A, B, C):
            t = 0.0
            step = step_size
            while step > 1e-6:
                candidate = point + (t + step) * gradient
                if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                    t += step
                else:
                    step *= 0.5
            
            candidate = point + t * gradient

        return candidate

    def improve(points: np.ndarray) -> np.ndarray:
        # Create configuration-specific seed for exploration diversity
        config_hash = int(abs(hash(points.tobytes())) % 1e9)
        rng = np.random.default_rng(config_hash)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        initial_min_area = best_score
        
        # Adaptive parameters based on input difficulty with tunable constants
        base_scale = 0.01
        # CHANGED: Replaced logarithmic scaling with power law for more aggressive exploration of hard problems
        base_step = base_scale * (0.01 / max(initial_min_area, 1e-8)) ** 0.4
        
        # Track recent improvements to adapt parameters
        improvement_history = []
        max_history = 50
        
        # Simulated annealing parameters
        T0 = 0.15 * base_step
        cooling_rate = 0.985
        T = T0
        # CHANGED: Dynamic threshold that scales with problem difficulty
        target_min_area = 0.0365 * 0.9  # 90% of theoretical maximum
        dynamic_threshold = 0.5 * target_min_area
        total_iterations = min(1200, max(400, int(400 * max(1, dynamic_threshold / (initial_min_area + 1e-10)))))
        no_improve_count = 0
        reheat_threshold = 60

        for iteration in range(total_iterations):
            min_area_val = get_smallest_triangle_area(best)
            critical_triangles = []
            n = best.shape[0]
            
            # CHANGED: Progressive tolerance that tightens as optimization proceeds
            tolerance = 0.05 * min_area_val * max(0.1, 1.0 - iteration/(2.0 * total_iterations))
            
            # Identify critical triangles (smallest area triangles)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = 0.5 * abs((best[j,0]-best[i,0])*(best[k,1]-best[i,1]) - 
                                      (best[k,0]-best[i,0])*(best[j,1]-best[i,1]))
                        # CHANGED: Dynamic weighting exponent that adapts to improvement rate
                        if len(improvement_history) > 5:
                            recent_improvement = np.mean(improvement_history[-5:])
                            decay_rate = 0.002 * (1 + 10 * recent_improvement / (min_area_val + 1e-12))
                        else:
                            decay_rate = 0.002
                        weight = (min_area_val / (area + 1e-12)) ** max(1.2, 3.0 - decay_rate * iteration)
                        if area <= min_area_val * (1 + tolerance):
                            critical_triangles.append((i, j, k, weight))

            # If no critical triangles found (shouldn't happen), skip
            if not critical_triangles:
                continue

            # Calculate gradient contributions for each point with weighting
            point_gradients = np.zeros_like(best)
            total_weight = 0.0
            
            for tri in critical_triangles:
                i, j, k, weight = tri
                triangle = [best[i], best[j], best[k]]
                
                # Get gradients for each vertex in this triangle
                grad_i = calculate_triangle_gradient(triangle, 0)
                grad_j = calculate_triangle_gradient(triangle, 1)
                grad_k = calculate_triangle_gradient(triangle, 2)
                
                # Accumulate weighted gradients
                point_gradients[i] += weight * grad_i
                point_gradients[j] += weight * grad_j
                point_gradients[k] += weight * grad_k
                total_weight += weight

            # Skip if no valid gradients
            if total_weight < 1e-8:
                continue

            # CHANGED: Use relative gradient threshold instead of fixed value
            max_grad = np.max(np.linalg.norm(point_gradients, axis=1))
            gradient_magnitudes = np.linalg.norm(point_gradients, axis=1)
            
            # Select points to perturb with bias toward high-gradient points
            if np.max(gradient_magnitudes) > 1e-8:
                # CHANGED: Exponentially decaying minimum bias
                min_bias = 0.05 * 0.95 ** (iteration / 10.0)
                weights = gradient_magnitudes / (max_grad + 1e-8) + min_bias
                weights /= weights.sum()
                # Dynamically adjust number of points to perturb based on improvement history
                if len(improvement_history) > 10 and np.mean(improvement_history[-10:]) < 1e-5:
                    num_perturb = min(5, max(1, int(np.sum(gradient_magnitudes > 1e-4))))
                else:
                    num_perturb = min(5, max(1, int(np.sum(gradient_magnitudes > 1e-4))))
                indices = rng.choice(11, size=num_perturb, replace=False, p=weights)
            else:
                # Fallback to random if gradients are negligible
                indices = rng.choice(11, size=1, replace=False)

            # Adaptive restarts based on stagnation
            restart_prob = 0.01 + 0.04 * min(1.0, (no_improve_count / 30.0) ** 2)
            if rng.random() < restart_prob and best_score > initial_min_area:
                # CHANGED: Problem-aware restart perturbation magnitude
                restart_magnitude = 0.01 * (0.01 / (best_score + 1e-10))
                restart_perturbation = rng.normal(0, restart_magnitude, size=points.shape)
                candidate = best.copy() + restart_perturbation
                
                # Project points back to triangle with boundary buffer
                for i in range(11):
                    candidate[i] = constrained_gradient_step(
                        best[i], 
                        restart_perturbation[i] / (np.linalg.norm(restart_perturbation[i]) + 1e-8), 
                        restart_magnitude,
                        A, B, C,
                        iteration,
                        total_iterations
                    )
                
                # Evaluate candidate
                score = get_smallest_triangle_area(candidate)
                if score > 1e-12 and score > best_score:  # Only accept if improvement
                    best = candidate
                    best_score = score
                    T = T0  # Reset temperature
                    no_improve_count = 0
                continue

            candidate = best.copy()
            # Adaptive step size based on current min_area and improvement history
            step_size = base_step * (T / T0)
            
            # DECREASE step size when stuck (was increase)
            if len(improvement_history) > 20:
                recent_improvement = np.mean(improvement_history[-20:])
                if recent_improvement < 1e-6:
                    step_size *= 0.8  # Decrease step when stuck
                elif recent_improvement > 1e-4:
                    step_size *= 1.1  # Slightly increase step when making good progress

            for idx in indices:
                # Apply gradient step with constraint handling and boundary repulsion
                candidate[idx] = constrained_gradient_step(
                    best[idx], 
                    point_gradients[idx], 
                    step_size,
                    A, B, C,
                    iteration,
                    total_iterations
                )

            # Validate candidate has no collinear points
            score = get_smallest_triangle_area(candidate)
            if score <= 1e-12:
                no_improve_count += 1
                T *= cooling_rate
                continue

            # Track improvement for adaptive parameter tuning
            improvement = score - best_score
            if improvement > 0:
                improvement_history.append(improvement)
                if len(improvement_history) > max_history:
                    improvement_history.pop(0)

            # Standard Metropolis acceptance criterion
            delta = score - best_score
            if delta > 0 or (T > 1e-8 and rng.random() < np.exp(delta/T)):
                best = candidate
                best_score = score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Cooling and reheating mechanism
            T *= cooling_rate
            if no_improve_count >= reheat_threshold:
                # CHANGED: Problem-aware reheating with dynamic exponent
                current_T0 = 0.15 * base_step * (0.01 / (best_score + 1e-10)) ** 0.25
                reheating_factor = 1.0 + 2.0 * (no_improve_count / reheat_threshold) ** (1.0 + 0.5 * (0.01 / (best_score + 1e-10)))
                T = current_T0 * reheating_factor
                no_improve_count = 0

        return best

    return improve