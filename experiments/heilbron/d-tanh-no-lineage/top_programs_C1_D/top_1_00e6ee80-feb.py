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

    def closest_on_segment(P, A, B):
        """Project point P onto segment AB."""
        AB = B - A
        if np.linalg.norm(AB) < 1e-10:
            return A
        t = np.dot(P - A, AB) / np.dot(AB, AB)
        t = max(0.0, min(1.0, t))
        return A + t * AB

    def project_to_boundary(P, A, B, C):
        """Project point P to the closest point on triangle boundary."""
        proj_AB = closest_on_segment(P, A, B)
        proj_BC = closest_on_segment(P, B, C)
        proj_CA = closest_on_segment(P, C, A)
        
        d_AB = np.linalg.norm(P - proj_AB)
        d_BC = np.linalg.norm(P - proj_BC)
        d_CA = np.linalg.norm(P - proj_CA)
        
        if d_AB <= d_BC and d_AB <= d_CA:
            return proj_AB
        elif d_BC <= d_AB and d_BC <= d_CA:
            return proj_BC
        else:
            return proj_CA

    def improve(points: np.ndarray) -> np.ndarray:
        # Create configuration-specific seed for exploration diversity
        config_hash = int(abs(hash(points.tobytes())) % 1e9)
        rng = np.random.default_rng(config_hash)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        initial_min_area = best_score
        
        # CORRECTED: Base step inversely proportional to problem difficulty
        base_scale = 0.01
        base_step = base_scale / np.sqrt(initial_min_area + 1e-10)
        
        # Track recent improvements to adapt parameters
        improvement_history = []
        max_history = 50
        
        # Simulated annealing parameters
        T0 = 0.15 * base_step
        cooling_rate = 0.985
        T = T0
        total_iterations = min(1200, max(400, int(400 * max(1, 0.01 / (initial_min_area + 1e-10)))))
        no_improve_count = 0
        reheat_threshold = 60

        for iteration in range(total_iterations):
            min_area_val = get_smallest_triangle_area(best)
            critical_triangles = []
            n = best.shape[0]
            
            # CORRECTED: Removed absolute tolerance floor
            tolerance = 0.05 * min_area_val
            
            # Identify critical triangles (smallest area triangles)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = 0.5 * abs((best[j,0]-best[i,0])*(best[k,1]-best[i,1]) - 
                                      (best[k,0]-best[i,0])*(best[j,1]-best[i,1]))
                        # Use exponential weighting based on proximity to minimum area
                        if area <= min_area_val * (1 + tolerance):
                            # Weight by closeness to minimum area (higher weight for closer triangles)
                            weight = (min_area_val / (area + 1e-12)) ** 2
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

            # PRESERVE ABSOLUTE GRADIENT MAGNITUDES for proper step scaling
            gradient_magnitudes = np.linalg.norm(point_gradients, axis=1)
            max_magnitude = np.max(gradient_magnitudes)
            if max_magnitude > 1e-8:
                # Scale gradients directly by their relative magnitudes
                for i in range(11):
                    if gradient_magnitudes[i] > 1e-8:
                        magnitude_scale = gradient_magnitudes[i] / max_magnitude
                        point_gradients[i] = point_gradients[i] * magnitude_scale

            # Select points to perturb with bias toward high-gradient points
            if np.max(gradient_magnitudes) > 1e-8:
                # Higher probability for points with stronger gradient signals
                weights = np.exp(gradient_magnitudes / (max_magnitude + 1e-8))
                weights /= weights.sum()
                # Dynamically adjust number of points to perturb based on improvement history
                if len(improvement_history) > 10 and np.mean(improvement_history[-10:]) < 1e-5:
                    num_perturb = min(3, max(1, int(np.sum(gradient_magnitudes > 1e-4))))
                else:
                    num_perturb = min(3, max(1, int(np.sum(gradient_magnitudes > 1e-4))))
                indices = rng.choice(11, size=num_perturb, replace=False, p=weights)
            else:
                # Fallback to random if gradients are negligible
                indices = rng.choice(11, size=1, replace=False)

            # Random restarts to escape local minima (adaptive probability)
            restart_prob = max(0.01, min(0.1, 0.05 * (no_improve_count / reheat_threshold)))
            if rng.random() < restart_prob:
                # CORRECTED: Scale restart perturbation with base_step
                restart_perturbation = rng.normal(0, 0.2 * base_step, size=points.shape)
                candidate = best.copy() + restart_perturbation
                
                # Project points back to triangle using precise boundary projection
                for i in range(11):
                    if not is_inside_triangle(candidate[i].reshape(1, 2), A, B, C):
                        candidate[i] = project_to_boundary(candidate[i], A, B, C)
                
                # Evaluate candidate
                score = get_smallest_triangle_area(candidate)
                if score > 1e-12:  # Valid configuration
                    best = candidate
                    best_score = score
                    T = T0  # Reset temperature
                    no_improve_count = 0
                continue

            candidate = best.copy()
            # Adaptive step size based on current min_area and improvement history
            step_size = base_step * (T / T0)
            
            # CORRECTED: INCREASE step size when stuck to escape local minima
            if len(improvement_history) > 20:
                recent_improvement = np.mean(improvement_history[-20:])
                if recent_improvement < 1e-6:
                    step_size *= 1.2  # Increase step when stuck
                elif recent_improvement > 1e-4:
                    step_size *= 1.05  # Slightly increase step when making good progress

            for idx in indices:
                # Apply gradient step
                candidate[idx] = best[idx] + step_size * point_gradients[idx]
                
                # Project to boundary if needed
                if not is_inside_triangle(candidate[idx].reshape(1, 2), A, B, C):
                    candidate[idx] = project_to_boundary(candidate[idx], A, B, C)

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

            # Simulated annealing acceptance
            delta = score - best_score
            if delta > 0 or (T > 1e-8 and rng.random() < np.exp(delta / T)):
                best = candidate
                best_score = score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Cooling and reheating mechanism
            T *= cooling_rate
            if no_improve_count >= reheat_threshold:
                # Reheat to escape local minimum, but recompute T0 based on current min_area
                current_T0 = 0.15 * base_step * (0.01 / (best_score + 1e-10)) ** 0.25
                T = current_T0 * (1.0 + 0.5 * no_improve_count / reheat_threshold)
                no_improve_count = 0

        return best

    return improve