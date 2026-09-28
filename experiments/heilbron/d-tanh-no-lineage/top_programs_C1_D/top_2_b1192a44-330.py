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

    def boundary_repulsion(point, A, B, C, min_distance=0.02):
        """Calculate repulsion vector to keep points away from triangle boundaries."""
        def distance_to_segment(P, A, B):
            AB = B - A
            AP = P - A
            if np.linalg.norm(AB) < 1e-10:
                return np.linalg.norm(AP), np.zeros(2)
            
            t = np.dot(AP, AB) / np.dot(AB, AB)
            t = max(0.0, min(1.0, t))
            projection = A + t * AB
            distance = np.linalg.norm(P - projection)
            
            if distance < 1e-10:
                # Perpendicular direction (choose one side)
                normal = np.array([-AB[1], AB[0]])
                normal = normal / np.linalg.norm(normal)
                return 0.0, normal
            
            direction = (P - projection) / distance
            return distance, direction

        d_AB, dir_AB = distance_to_segment(point, A, B)
        d_BC, dir_BC = distance_to_segment(point, B, C)
        d_CA, dir_CA = distance_to_segment(point, C, A)
        
        repulsion = np.zeros(2)
        
        # Apply repulsion if too close to boundary
        if d_AB < min_distance:
            strength = (min_distance - d_AB) / min_distance
            repulsion += strength * dir_AB
        
        if d_BC < min_distance:
            strength = (min_distance - d_BC) / min_distance
            repulsion += strength * dir_BC
        
        if d_CA < min_distance:
            strength = (min_distance - d_CA) / min_distance
            repulsion += strength * dir_CA
        
        return repulsion

    def constrained_gradient_step(point, gradient, step_size, A, B, C):
        """Take a gradient step while ensuring point remains inside triangle."""
        # First try full gradient step
        candidate = point + step_size * gradient
        
        if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
            return candidate
        
        # If outside, project along gradient direction to boundary
        t = 0.0
        step = step_size
        while step > 1e-6:
            candidate = point + (t + step) * gradient
            if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                t += step
            else:
                step *= 0.5
        
        return point + t * gradient

    def improve(points: np.ndarray) -> np.ndarray:
        # Create configuration-specific seed for exploration diversity
        config_hash = int(abs(hash(points.tobytes())) % 1e9)
        rng = np.random.default_rng(config_hash)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        initial_min_area = best_score
        
        # Adaptive parameters based on input difficulty
        # REVERSED RELATIONSHIP: smaller steps for harder problems (small min_area)
        base_scale = 0.01
        base_step = base_scale * np.sqrt(initial_min_area + 1e-10)
        
        # Track recent improvements to adapt parameters
        improvement_history = []
        max_history = 50
        
        # Simulated annealing parameters
        T0 = 0.15 * base_step
        cooling_rate = 0.99  # Slower cooling
        T = T0
        total_iterations = min(1200, max(400, int(400 * max(1, 0.01 / (initial_min_area + 1e-10)))))
        no_improve_count = 0
        reheat_threshold = 60

        for iteration in range(total_iterations):
            min_area_val = get_smallest_triangle_area(best)
            critical_triangles = []
            n = best.shape[0]
            
            # REVISED TOLERANCE: focus only on truly critical triangles
            tolerance = max(0.001, min(0.01, 0.05 * min_area_val))
            
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

            # ADDED: Boundary repulsion to prevent clustering at edges
            for i in range(11):
                repulsion = boundary_repulsion(best[i], A, B, C, min_distance=0.02)
                if np.linalg.norm(repulsion) > 1e-8:
                    point_gradients[i] += 0.3 * repulsion

            # Select points to perturb with bias toward high-gradient points
            gradient_magnitudes = np.linalg.norm(point_gradients, axis=1)
            max_magnitude = np.max(gradient_magnitudes)
            
            if np.max(gradient_magnitudes) > 1e-8:
                # Higher probability for points with stronger gradient signals
                weights = gradient_magnitudes + 0.01  # Reduced constant to prioritize critical points
                weights /= weights.sum()
                # Dynamically adjust number of points to perturb
                if len(improvement_history) > 10 and np.mean(improvement_history[-10:]) < 1e-5:
                    num_perturb = min(3, max(1, int(np.sum(gradient_magnitudes > 1e-4))))
                else:
                    num_perturb = min(3, max(1, int(np.sum(gradient_magnitudes > 1e-4))))
                indices = rng.choice(11, size=num_perturb, replace=False, p=weights)
            else:
                # Fallback to random if gradients are negligible
                indices = rng.choice(11, size=1, replace=False)

            # ADAPTIVE RESTARTS: probability increases with stagnation
            restart_prob = min(0.05, 0.005 + 0.0001 * no_improve_count)
            if rng.random() < restart_prob:
                # Apply small random perturbation to all points
                restart_perturbation = rng.normal(0, 0.005, size=points.shape)
                candidate = best.copy() + restart_perturbation
                
                # Project points back to triangle
                for i in range(11):
                    candidate[i] = constrained_gradient_step(
                        best[i], 
                        restart_perturbation[i] / (np.linalg.norm(restart_perturbation[i]) + 1e-8), 
                        0.005,
                        A, B, C
                    )
                
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
            
            # REVISED: DECREASE step size when stuck (was increase)
            if len(improvement_history) > 20:
                recent_improvement = np.mean(improvement_history[-20:])
                if recent_improvement < 1e-6:
                    step_size *= 0.8  # Decrease step when stuck
                elif recent_improvement > 1e-4:
                    step_size *= 1.0  # Neutral when making good progress

            for idx in indices:
                # Apply gradient step with constraint handling
                candidate[idx] = constrained_gradient_step(
                    best[idx], 
                    point_gradients[idx], 
                    step_size,
                    A, B, C
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
                # Reheat to escape local minimum
                current_T0 = 0.15 * base_step * (0.01 / (best_score + 1e-10)) ** 0.25
                T = current_T0 * (1.0 + 0.5 * no_improve_count / reheat_threshold)
                no_improve_count = 0

        return best

    return improve