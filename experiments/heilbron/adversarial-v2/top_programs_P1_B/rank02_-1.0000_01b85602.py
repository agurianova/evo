import numpy as np
from itertools import combinations
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle

np.random.seed(42)

def entrypoint():
    A_tri, B_tri, C_tri = get_unit_triangle()
    
    # Helper function to compute distance to an edge
    def distance_to_edge(p, v1, v2):
        edge = v2 - v1
        edge_norm = np.linalg.norm(edge)
        if edge_norm < 1e-10:
            return np.linalg.norm(p - v1)
        edge_unit = edge / edge_norm
        w = p - v1
        proj = np.dot(w, edge_unit)
        if proj < 0:
            return np.linalg.norm(p - v1)
        elif proj > edge_norm:
            return np.linalg.norm(p - v2)
        else:
            perpendicular = w - proj * edge_unit
n            return np.linalg.norm(perpendicular)

    # Helper function to get outward normal of an edge
    def get_edge_normal(v1, v2):
        edge = v2 - v1
        normal = np.array([-edge[1], edge[0]])
        # Point outward from triangle
        centroid = (A_tri + B_tri + C_tri) / 3
        mid = (v1 + v2) / 2
        if np.dot(normal, centroid - mid) < 0:
            normal = -normal
        return normal / np.linalg.norm(normal)

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

        # Adjusted step size parameters per insight [step_size_tuning]
        step_size = 0.01  # Reduced from 0.05
        step_size_reduction = 0.95  # Slower reduction than 0.9
        step_size_patience = 50  # Longer patience than 10 steps
        
        # Adjusted temperature parameters per insight [temperature_tuning]
        temperature = 0.01  # Increased from 0.001
        temperature_decay = 0.999  # Slower decay than 0.995
        
        no_improve_count = 0
        global_perturbation_count = 0
        max_global_perturbations = 5  # Allow more global perturbations

        # Total iterations for multi-phase optimization
        total_iterations = 1000

        for iteration in range(total_iterations):
            # Determine current phase for coarse-to-fine optimization
            if iteration < total_iterations * 0.3:  # Phase 1: Exploration
                phase_factor = 2.0
                perturbation_magnitude = 0.1
            elif iteration < total_iterations * 0.7:  # Phase 2: Refinement
                phase_factor = 1.0
                perturbation_magnitude = 0.05
            else:  # Phase 3: Precision
                phase_factor = 0.5
                perturbation_magnitude = 0.02

            # Find all triangles and their areas
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
            
            # Adaptive triangle selection: take all within top 25% of smallest areas (max 8)
            if triangle_data:
                smallest_area = triangle_data[0][0]
                area_threshold = smallest_area * 1.25
                adaptive_triangles = [t for t in triangle_data if t[0] <= area_threshold]
                top_triangles = adaptive_triangles[:8]  # Cap at 8 triangles
            else:
                top_triangles = []
            
            # If no triangles found, continue (shouldn't happen with 11 points)
            if not top_triangles:
                continue
                
            # Compute gradients for all top triangles with capped weighting
            total_grad = np.zeros_like(current)
            max_weight = 100.0  # Cap to prevent instability near degenerate triangles
            
            for abs_area, i, j, k, s_val in top_triangles:
                # Skip if area is zero (shouldn't happen with non-degenerate)
                if abs_area < 1e-10:
                    continue
                    
                # Weight by inverse area with cap to prevent instability
                weight = min(1.0 / abs_area, max_weight)
                
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

            # Add boundary repulsion forces to prevent clustering near edges
            repulsion_strength = 0.01
            for i in range(11):
                p = current[i]
                # Distance to AB edge
                dist_AB = distance_to_edge(p, A_tri, B_tri)
                if dist_AB < 0.1:
                    normal_AB = get_edge_normal(A_tri, B_tri)
                    total_grad[i] += repulsion_strength / (dist_AB + 1e-8)**2 * normal_AB
                # Distance to BC edge
                dist_BC = distance_to_edge(p, B_tri, C_tri)
                if dist_BC < 0.1:
                    normal_BC = get_edge_normal(B_tri, C_tri)
                    total_grad[i] += repulsion_strength / (dist_BC + 1e-8)**2 * normal_BC
                # Distance to CA edge
                dist_CA = distance_to_edge(p, C_tri, A_tri)
                if dist_CA < 0.1:
                    normal_CA = get_edge_normal(C_tri, A_tri)
                    total_grad[i] += repulsion_strength / (dist_CA + 1e-8)**2 * normal_CA

            # Scale step size by current min_area and phase factor for adaptive gradient scaling
            adaptive_step = step_size * best_score * phase_factor
            
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
            
            # Check for improvement
            if new_score > best_score:
                best = candidate.copy()
                best_score = new_score
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0
                global_perturbation_count = 0
                # Reset step_size when finding a new best solution
                step_size = 0.01
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
            if no_improve_count >= step_size_patience:
                step_size *= step_size_reduction
                no_improve_count = 0
            
            # Global perturbation when stuck - now with targeted bottleneck points
            if global_perturbation_count >= 100 and max_global_perturbations > 0:
                # Identify bottleneck points (in top 5 smallest triangles)
                bottleneck_points = set()
                for _, i, j, k, _ in top_triangles[:5]:
                    bottleneck_points.update([i, j, k])
                bottleneck_points = list(bottleneck_points)

                # Perturb bottleneck points with magnitude decaying by triangle rank
                for idx in bottleneck_points[:3]:  # Perturb up to 3 bottleneck points
                    # Determine rank of triangles involving this point
                    triangle_ranks = [r for r, (_, i, j, k, _) in enumerate(top_triangles) 
                                      if idx in (i, j, k)]
                    if triangle_ranks:
                        rank = min(triangle_ranks)  # Use best (smallest) rank
                        magnitude = perturbation_magnitude * (0.7 ** rank)
                    else:
                        magnitude = perturbation_magnitude * 0.5
                    
                    # Random direction
                    angle = 2 * np.pi * np.random.random()
                    dx = magnitude * np.cos(angle)
                    dy = magnitude * np.sin(angle)
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
            
            # Update temperature
            temperature *= temperature_decay

        return best

    return improve