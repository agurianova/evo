import numpy as np
from itertools import combinations
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle

np.random.seed(42)

def entrypoint():
    A_tri, B_tri, C_tri = get_unit_triangle()
    
    # Precompute triangle edges for boundary distance calculations
    AB = B_tri - A_tri
    AC = C_tri - A_tri
    BC = C_tri - B_tri
    
    # Helper function to compute distance to triangle boundaries
    def boundary_distances(p):
        """Compute distances from point p to each edge of the triangle."""
        # Distance to AB edge
        v = p - A_tri
        proj = np.dot(v, AB) / np.dot(AB, AB)
        proj = np.clip(proj, 0, 1)
        closest_AB = A_tri + proj * AB
        dist_AB = np.linalg.norm(p - closest_AB)
        
        # Distance to AC edge
        v = p - A_tri
        proj = np.dot(v, AC) / np.dot(AC, AC)
        proj = np.clip(proj, 0, 1)
        closest_AC = A_tri + proj * AC
        dist_AC = np.linalg.norm(p - closest_AC)
        
        # Distance to BC edge
        v = p - B_tri
        proj = np.dot(v, BC) / np.dot(BC, BC)
        proj = np.clip(proj, 0, 1)
        closest_BC = B_tri + proj * BC
        dist_BC = np.linalg.norm(p - closest_BC)
        
        return dist_AB, dist_AC, dist_BC

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
        best_score = get_smallest_triangle_area(points)
        current_score = best_score

        # Adaptive step size controller based on move success rate
        step_size = 0.03  # Starting with larger step for exploration phase
        step_size_min = 0.001
        step_size_max = 0.1
        success_count = 0
        total_count = 0
        
        # Temperature parameters for simulated annealing
        temperature = 0.05  # Higher initial temperature for exploration
        temperature_decay = 0.995
        min_temperature = 1e-5
        temperature_restart_threshold = 50  # Iterations with no improvement before restart
        
        # For cycle detection
        history = []
        history_size = 50
        cycle_detected = False
        
        # Multi-stage optimization parameters
        exploration_phase = True
        exploration_phase_end = 400  # First 40% of iterations as exploration
        refinement_factor = 0.3  # For refinement phase
        
        no_improve_count = 0
        global_perturbation_count = 0
        max_global_perturbations = 3
        
        # For adaptive step size based on success rate
        success_window = 50
        success_threshold_high = 0.6  # Increase step if success rate > 60%
        success_threshold_low = 0.2   # Decrease step if success rate < 20%

        for iteration in range(1000):
            # Update adaptive parameters based on current best_score
            if best_score > 1e-5:  # Avoid division by zero
                # Dynamic success rate thresholds
                success_threshold_high = 0.7 * (best_score / 0.0365)
                success_threshold_low = 0.15 * (best_score / 0.0365)
                
                # Adaptive global perturbation limits
                max_global_perturbations = min(7, int(10 * (0.0365 - best_score)))
                
                # Adaptive triangle selection count
                adaptive_triangle_count = min(12, max(3, int(1 / best_score * 0.01)))
            
            # Cycle detection
            config_hash = (np.round(current, 4).tobytes(), round(best_score, 6))
            if config_hash in history:
                cycle_detected = True
            history.append(config_hash)
            if len(history) > history_size:
                history.pop(0)
            
            # Determine current phase (exploration vs refinement)
            if exploration_phase and iteration >= exploration_phase_end:
                exploration_phase = False
                # Switch to refinement parameters
                step_size = max(step_size * refinement_factor, step_size_min)
                temperature = max(temperature * refinement_factor, min_temperature)
                
            # Find smallest triangles
            triangle_data = []
            for i, j, k in combinations(range(11), 3):
                ax, ay = current[i]
                bx, by = current[j]
                cx, cy = current[k]
                s_val = 0.5 * ((bx - ax) * (cy - ay) - (cx - ax) * (by - ay))
                abs_area = abs(s_val)
                triangle_data.append((abs_area, i, j, k, s_val))
            
            # Sort by area and take top N (adaptive count based on distribution)
            triangle_data.sort(key=lambda x: x[0])
            # Adaptive selection: take all triangles within top 25% of smallest areas
            if len(triangle_data) > 0:
                threshold = triangle_data[min(5, len(triangle_data)-1)][0] * 1.25
                top_triangles = [t for t in triangle_data if t[0] <= threshold]
                
                # Use adaptive triangle count instead of hardcoding 8
                top_triangles = top_triangles[:min(adaptive_triangle_count, len(top_triangles))]
            else:
                top_triangles = triangle_data[:3]
            
            # If no triangles found, continue (shouldn't happen with 11 points)
            if not top_triangles:
                continue
                
            # Compute gradients for all top triangles
            total_grad = np.zeros_like(current)
            
            for abs_area, i, j, k, s_val in top_triangles:
                # Skip if area is zero (shouldn't happen with non-degenerate)
                if abs_area < 1e-10:
                    continue
                    
                # Use stronger weighting (1.2 exponent) to emphasize smallest triangles more
                weight = min(1.0 / (abs_area ** 1.2), 100.0)
                
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

            # Add boundary repulsion to gradients
            for i in range(11):
                dists = boundary_distances(current[i])
                min_dist = min(max(min(dists), 0.01), 0.5)  # Clamp to reasonable range
                
                # Compute repulsion direction (away from closest edge)
                repulsion = np.zeros(2)
                if dists[0] == min_dist:  # Closest to AB
                    normal = np.array([-AB[1], AB[0]])
                    normal = normal / np.linalg.norm(normal)
                    if np.dot(normal, current[i] - A_tri) < 0:
                        normal = -normal
                    repulsion += normal
                if dists[1] == min_dist:  # Closest to AC
                    normal = np.array([-AC[1], AC[0]])
                    normal = normal / np.linalg.norm(normal)
                    if np.dot(normal, current[i] - A_tri) < 0:
                        normal = -normal
                    repulsion += normal
                if dists[2] == min_dist:  # Closest to BC
                    normal = np.array([-BC[1], BC[0]])
                    normal = normal / np.linalg.norm(normal)
                    if np.dot(normal, current[i] - B_tri) < 0:
                        normal = -normal
                    repulsion += normal
                
                # Scale repulsion by inverse squared distance (stronger near boundary)
                # Make coefficient adaptive based on current solution quality
                repulsion_coefficient = 0.1
                if best_score > 1e-5:
                    repulsion_coefficient = 0.1 * (0.0365 / best_score) ** 0.5
                
                # Add minimum distance threshold for repulsion
                min_repulsion_dist = 0.05
n                if best_score > 1e-5:
                    min_repulsion_dist = 0.05 * (0.0365 / best_score) ** 0.3
                
                if min_dist < min_repulsion_dist:
                    repulsion_strength = repulsion_coefficient * best_score / (min_dist * min_dist)
                    total_grad[i] += repulsion * repulsion_strength

            # Normalize total gradients by number of triangles affecting each point
            for i in range(11):
                count = sum(1 for _, tri_i, tri_j, tri_k, _ in top_triangles 
                           if i == tri_i or i == tri_j or i == tri_k)
                if count > 0:
                    total_grad[i] /= count
                
                # Normalize gradient direction
                norm = np.linalg.norm(total_grad[i])
                if norm > 1e-8:
                    total_grad[i] /= norm

            # Create candidate by moving all points
            candidate = current.copy()
            for i in range(11):
                if np.linalg.norm(total_grad[i]) > 1e-8:
                    candidate[i] += step_size * total_grad[i]
            
            # Project any points outside the triangle back in
            for i in range(11):
                if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                    candidate[i] = project_point(candidate[i])
            
            # Check if candidate is valid (all points inside)
            if not is_inside_triangle(candidate, A_tri, B_tri, C_tri):
                # Update success tracking
                total_count += 1
                no_improve_count += 1
                global_perturbation_count += 1
                continue
            
            new_score = get_smallest_triangle_area(candidate)
            
            # Track whether this move was accepted for success rate calculation
            move_accepted = False
            
            # Check for improvement
            if new_score > best_score:
                best = candidate.copy()
                best_score = new_score
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0
                global_perturbation_count = 0
                move_accepted = True
            elif new_score > current_score:
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0
                global_perturbation_count = 0
                move_accepted = True
            else:
                delta = new_score - current_score
                if delta < 0:
                    prob = np.exp(delta / temperature)
                    if np.random.random() < prob:
                        current = candidate.copy()
                        current_score = new_score
                        no_improve_count = 0
                        global_perturbation_count = 0
                        move_accepted = True
                    else:
                        no_improve_count += 1
                        global_perturbation_count += 1
                else:
                    no_improve_count += 1
                    global_perturbation_count += 1

            # Update success tracking
            if move_accepted:
                success_count += 1
            total_count += 1

            # Adaptive step size based on success rate
            if total_count >= success_window:
                success_rate = success_count / total_count
                if success_rate > success_threshold_high:
                    step_size = min(step_size * 1.05, step_size_max)
                elif success_rate < success_threshold_low:
                    step_size = max(step_size * 0.9, step_size_min)
                # Reset counters
                success_count = 0
                total_count = 0

            # Update temperature
            temperature = max(temperature * temperature_decay, min_temperature)

            # Temperature restart mechanism
            if no_improve_count >= temperature_restart_threshold:
                temperature = 0.1 * (0.0365 / max(best_score, 1e-5))
                no_improve_count = 0

            # Targeted global perturbation when stuck
            if (no_improve_count >= 100 or cycle_detected) and max_global_perturbations > 0:
                # Identify points involved in smallest triangles
                active_points = set()
                for _, i, j, k, _ in top_triangles[:5]:  # Top 5 smallest triangles
                    active_points.add(i)
                    active_points.add(j)
                    active_points.add(k)
                
                # Convert to list and sort by involvement in small triangles
                active_points = list(active_points)
                point_ranks = {p: 0 for p in active_points}
                for rank, (_, i, j, k, _) in enumerate(top_triangles[:5]):
                    decay_factor = 0.7 ** rank  # Power-law decay
                    for pt in [i, j, k]:
                        if pt in point_ranks:
                            point_ranks[pt] += decay_factor
                
                # Sort points by rank (highest rank first)
                sorted_points = sorted(active_points, key=lambda p: point_ranks[p], reverse=True)
                # Take top 3 points
                target_points = sorted_points[:3]

                # Make perturbation magnitude adaptive based on current solution quality
                perturbation_magnitude = 0.08
                if best_score > 1e-5:
                    perturbation_magnitude = 0.08 * (0.0365 / best_score) ** 0.7

                # Perturb target points with magnitude based on rank
                for idx, point_idx in enumerate(target_points):
                    rank = idx + 1
                    magnitude = perturbation_magnitude * (0.7 ** (rank-1))  # Power-law decay
                    
                    # Random direction
                    angle = 2 * np.pi * np.random.random()
                    dx = magnitude * np.cos(angle)
                    dy = magnitude * np.sin(angle)
                    
                    candidate[point_idx] = current[point_idx] + np.array([dx, dy])

                # Project points back if outside
                for i in target_points:
                    if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                        candidate[i] = project_point(candidate[i])
                
                # Check if valid and evaluate
                if is_inside_triangle(candidate, A_tri, B_tri, C_tri):
                    current = candidate.copy()
                    current_score = get_smallest_triangle_area(current)
                    no_improve_count = 0
                    global_perturbation_count = 0
                    max_global_perturbations -= 1
                    move_accepted = True
                    cycle_detected = False

            # Early stopping if no improvement for too long
            if no_improve_count >= 250:
                break

        return best

    return improve