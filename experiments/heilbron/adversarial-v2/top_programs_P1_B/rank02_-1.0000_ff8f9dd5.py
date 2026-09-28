import numpy as np
from itertools import combinations
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle

np.random.seed(42)

def entrypoint():
    A_tri, B_tri, C_tri = get_unit_triangle()
    
    # Calculate triangle height for geometric scaling
    triangle_height = C_tri[1] - A_tri[1]
    
    # Helper function to project a point back into the triangle if outside
    def project_point(p):
        """Project point p back into the triangle using barycentric coordinates."""
        v0 = B_tri - A_tri
        v1 = C_tri - A_tri
        v2 = p - A_tri
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        if abs(denom) < 1e-10:
            return A_tri.copy()
            
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        
        # Clamp to triangle
        if v < 0:
            v = 0
            w = max(0, min(1, w))
        if w < 0:
            w = 0
            v = max(0, min(1, v))
        if v + w > 1:
            total = v + w
            v /= total
            w /= total
            
        return A_tri + v * (B_tri - A_tri) + w * (C_tri - A_tri)

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        best = points.copy()
        initial_score = get_smallest_triangle_area(points)
        best_score = initial_score
        current_score = best_score

        # Two-phase optimization parameters
        # Coarse phase: more exploration
        coarse_step_size = 0.025
        coarse_step_reduction = 0.9
        coarse_temperature = 0.02
        coarse_temp_decay = 0.99
        
        # Fine phase: more exploitation
        fine_step_size = 0.005
        fine_step_reduction = 0.95
        fine_temperature = 0.005
        fine_temp_decay = 0.999
        
        # Current phase parameters (start in coarse phase)
        step_size = coarse_step_size
        step_size_reduction = coarse_step_reduction
        temperature = coarse_temperature
        temperature_decay = coarse_temp_decay
        
        # Phase transition parameters
        phase = 'coarse'
        # Transition when we've reached 40% of theoretical maximum improvement
        phase_transition_threshold = 0.4 * initial_score
        # Make patience adaptive based on improvement rate
        phase_transition_patience = max(50, int(100 * (0.0365 / (initial_score + 1e-5))))
        no_improve_for_transition = 0

        no_improve_count = 0
        global_perturbation_count = 0
        max_global_perturbations = 4

        # Calculate adaptive triangle selection threshold using area distribution statistics
        def get_adaptive_triangle_threshold(triangle_data):
            if not triangle_data or len(triangle_data) < 3:
                return 0
            
            # Extract areas of the smallest triangles (top 20%)
            num_to_consider = max(3, len(triangle_data) // 5)
            smallest_areas = [t[0] for t in triangle_data[:num_to_consider]]
            
            # Calculate mean and standard deviation of these areas
            mean_area = np.mean(smallest_areas)
            std_area = np.std(smallest_areas)
            
            # Set threshold at mean + 0.5 std (focuses on truly critical triangles)
            threshold = mean_area + 0.5 * std_area
            
            # Ensure we select at least 3 triangles
            if threshold <= smallest_areas[-1]:
                return threshold
            else:
                # If threshold would select too few, use the area of the 3rd smallest triangle
                return triangle_data[min(2, len(triangle_data)-1)][0]

        # Track recent improvement rate for adaptive cooling
        improvement_history = []
        max_history = 50

        for iteration in range(1500):
            # Find all triangles and sort by area
            triangle_data = []
            for i, j, k in combinations(range(11), 3):
                ax, ay = current[i]
                bx, by = current[j]
                cx, cy = current[k]
                s_val = 0.5 * ((bx - ax) * (cy - ay) - (cx - ax) * (by - ay))
                abs_area = abs(s_val)
                triangle_data.append((abs_area, i, j, k, s_val))
            
            # Sort by area
            triangle_data.sort(key=lambda x: x[0])
            
            # Adaptive triangle selection using statistics of area distribution
            if triangle_data:
                threshold = get_adaptive_triangle_threshold(triangle_data)
                top_triangles = [t for t in triangle_data if t[0] <= threshold]
                # Ensure at least 3 triangles are selected
                if len(top_triangles) < 3:
                    top_triangles = triangle_data[:3]
            else:
                top_triangles = []
            
            # If no triangles found, continue (shouldn't happen with 11 points)
            if not top_triangles:
                continue
                
            # Compute gradients for all selected triangles
            total_grad = np.zeros_like(current)
            
            # Collect area values for adaptive weighting
            area_values = [t[0] for t in top_triangles]
            if area_values:
                # Set weight cap at 95th percentile of 1/area to prevent extreme values
                reciprocals = [1.0 / (a + 1e-10) for a in area_values]
                weight_cap = np.percentile(reciprocals, 95)
            else:
                weight_cap = 100.0
            
            for abs_area, i, j, k, s_val in top_triangles:
                # Skip if area is zero (shouldn't happen with non-degenerate)
                if abs_area < 1e-10:
                    continue
                    
                # Weight by inverse area with adaptive cap
                weight = min(1.0 / abs_area, weight_cap)
                
                A = current[i]
                B = current[j]
                C = current[k]
                
                sign_S = 1.0 if s_val >= 0 else -1.0
                
                # Compute gradients
                grad_A = sign_S * np.array([B[1] - C[1], C[0] - B[0]])
                grad_B = sign_S * np.array([C[1] - A[1], A[0] - C[0]])
                grad_C = sign_S * np.array([A[1] - B[1], B[0] - A[0]])
                
                # Normalize gradients
                for grad, idx in [(grad_A, i), (grad_B, j), (grad_C, k)]:
                    norm = np.linalg.norm(grad)
                    if norm > 1e-8:
                        grad = grad / norm
                    total_grad[idx] += weight * grad
            
            # Normalize total gradients by number of triangles affecting each point
            for i in range(11):
                count = sum(1 for _, tri_i, tri_j, tri_k, _ in top_triangles 
                           if i == tri_i or i == tri_j or i == tri_k)
                if count > 0:
                    total_grad[i] /= count

            # CRITICAL FIX: Prevent vanishing steps during early optimization
            # Use minimum effective score (0.015) to maintain reasonable step sizes
            min_effective_score = max(best_score, 0.015)
            adaptive_step = step_size * min_effective_score

            # Create candidate by moving all points
            candidate = current.copy()
            for i in range(11):
                if np.linalg.norm(total_grad[i]) > 1e-8:
                    candidate[i] += adaptive_step * total_grad[i]
            
            # Project any points outside the triangle back in
            for i in range(11):
                if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                    candidate[i] = project_point(candidate[i])
            
            # Check if candidate is valid (all points inside)
            if not is_inside_triangle(candidate, A_tri, B_tri, C_tri):
                no_improve_count += 1
                global_perturbation_count += 1
                continue
            
            new_score = get_smallest_triangle_area(candidate)
            improvement = new_score - best_score
            
            # Track improvement history for adaptive cooling
            improvement_history.append(improvement)
            if len(improvement_history) > max_history:
                improvement_history.pop(0)
            
            # Calculate recent improvement rate
            if len(improvement_history) > 10:
                recent_improvement = sum(improvement_history[-10:]) / 10
n                # Adaptive temperature decay - slow down cooling when improvements are frequent
                adaptive_temp_decay = temperature_decay - 0.005 * min(recent_improvement / (1e-5 + step_size), 0.5)
                adaptive_temp_decay = max(0.95, min(0.999, adaptive_temp_decay))
            else:
                adaptive_temp_decay = temperature_decay

            # Check for improvement
            if new_score > best_score:
                best = candidate.copy()
                best_score = new_score
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0
                global_perturbation_count = 0
                # Reset step_size when finding a new best solution
                step_size = coarse_step_size if phase == 'coarse' else fine_step_size
                
                # Check if we should transition to fine phase
                if phase == 'coarse' and best_score > phase_transition_threshold:
                    # Start monitoring for phase transition
                    no_improve_for_transition += 1
                    if no_improve_for_transition >= phase_transition_patience:
                        # Switch to fine phase
                        phase = 'fine'
                        step_size = fine_step_size
                        step_size_reduction = fine_step_reduction
                        temperature = fine_temperature
                        temperature_decay = fine_temp_decay
            elif new_score > current_score:
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0
                global_perturbation_count = 0
            else:
                delta = new_score - current_score
                if delta < 0:
                    prob = np.exp(delta / temperature)
                    if np.random.random() < prob:
                        current = candidate.copy()
                        current_score = new_score
                        no_improve_count = 0
                        global_perturbation_count = 0
                    else:
                        no_improve_count += 1
                        global_perturbation_count += 1
                else:
                    no_improve_count += 1
                    global_perturbation_count += 1
            
            # Adaptive step size reduction
            if no_improve_count >= 30:
                step_size *= step_size_reduction
                no_improve_count = 0
            
            # Targeted global perturbation when stuck
            if global_perturbation_count >= 60 and max_global_perturbations > 0:
                # Identify points involved in smallest triangles
                critical_points = set()
                for _, i, j, k, _ in triangle_data[:5]:  # Top 5 smallest triangles
                    critical_points.add(i)
                    critical_points.add(j)
                    critical_points.add(k)
                
                # Perturb only critical points with magnitude proportional to gradient and triangle geometry
                for idx in list(critical_points):
                    # Scale perturbation by gradient magnitude and triangle height
                    grad_norm = np.linalg.norm(total_grad[idx])
                    # Use triangle height for geometric scaling (0.15 * height * (1 + grad_norm))
                    base_radius = 0.15 * triangle_height * (1 + grad_norm)
                    angle = 2 * np.pi * np.random.random()
                    radius = base_radius * np.random.random()
                    dx = radius * np.cos(angle)
                    dy = radius * np.sin(angle)
                    candidate[idx] = current[idx] + np.array([dx, dy])
                
                # Project points back if outside
                for i in range(11):
                    if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                        candidate[i] = project_point(candidate[i])
                
                # Check if valid and evaluate
                if is_inside_triangle(candidate, A_tri, B_tri, C_tri):
                    current = candidate.copy()
                    current_score = get_smallest_triangle_area(current)
                    no_improve_count = 0
                    global_perturbation_count = 0
                    max_global_perturbations -= 1

            # Update temperature with adaptive decay
            temperature *= adaptive_temp_decay

            # Adaptive stopping criterion based on convergence
            if iteration > 100 and no_improve_count > 100 and best_score - initial_score < 0.0001:
                break

        return best

    return improve