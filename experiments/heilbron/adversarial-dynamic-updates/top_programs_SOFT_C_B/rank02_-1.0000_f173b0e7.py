from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

# Barycentric coordinate helpers
def to_bary(p, A, B, C):
    v0 = B - A
    v1 = C - A
    v2 = p - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    return u, v, w

def to_cart(u, v, w, A, B, C):
    return u * A + v * B + w * C

def clamp_bary(u, v, w):
    # Project onto the simplex u+v+w=1, u,v,w>=0
    coords = np.array([u, v, w])
    # Handle negative values
    if np.any(coords < 0):
        coords = np.maximum(coords, 0)
        coords /= np.sum(coords)
    # Handle sum > 1
    if np.sum(coords) > 1.0:
        coords /= np.sum(coords)
    return coords[0], coords[1], coords[2]

def entrypoint():
    A, B, C = get_unit_triangle()
    side_length = np.linalg.norm(B - A)

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Search phase control
        use_geometric_phase = True
        geometric_phase_threshold = 0.0005
        
        # Adaptive parameters
        initial_step = 0.05
        step_size = initial_step
        stagnation_count = 0
        max_iterations = 150
        tol = 1e-9
        n = 11
        
        for _ in range(max_iterations):
            # Find all minimal-area triangles
            min_area = float('inf')
            min_triplets = []
            
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = best[i]
                        x2, y2 = best[j]
                        x3, y3 = best[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area < min_area - tol:
                            min_area = area
                            min_triplets = [(i, j, k)]
                        elif abs(area - min_area) < tol:
                            min_triplets.append((i, j, k))
            
            # Count vertex frequencies in minimal triangles
            freq = [0] * n
            for triplet in min_triplets:
                for idx in triplet:
                    freq[idx] += 1
            
            # Sort vertices by frequency (descending)
            candidate_indices = sorted(range(n), key=lambda i: -freq[i])
            
            # Try to improve using geometric gradients (Phase 1)
            improvement_found = False
            improvement_magnitude = 0.0
            
            if use_geometric_phase:
                for idx in candidate_indices:
                    if freq[idx] == 0:
                        break
                    
                    # For each minimal triangle containing this vertex
                    for triplet in min_triplets:
                        if idx not in triplet:
                            continue
                        
                        # Get the triangle vertices
                        i, j, k = triplet
                        p_i, p_j, p_k = best[i], best[j], best[k]
                        
                        # Calculate vectors along the edges
                        v_ij = p_j - p_i
                        v_ik = p_k - p_i
                        
                        # Calculate perpendicular vectors (rotated 90 degrees)
                        perp_ij = np.array([-v_ij[1], v_ij[0]])
                        perp_ik = np.array([-v_ik[1], v_ik[0]])
                        
                        # Normalize
                        norm_ij = np.linalg.norm(perp_ij)
                        norm_ik = np.linalg.norm(perp_ik)
                        if norm_ij > 1e-10:
                            perp_ij /= norm_ij
                        if norm_ik > 1e-10:
                            perp_ik /= norm_ik
                        
                        # Calculate gradient for area increase
                        if idx == i:
                            grad = 0.5 * (perp_ij + perp_ik)
                        elif idx == j:
                            grad = 0.5 * (-perp_ij + (p_k - p_j))
                            grad = np.array([-grad[1], grad[0]])  # Perpendicular
                            if np.linalg.norm(grad) > 1e-10:
                                grad /= np.linalg.norm(grad)
                        else:  # idx == k
                            grad = 0.5 * (-perp_ik + (p_j - p_k))
                            grad = np.array([-grad[1], grad[0]])  # Perpendicular
                            if np.linalg.norm(grad) > 1e-10:
                                grad /= np.linalg.norm(grad)
                        
                        # Scale by step size
                        if np.linalg.norm(grad) > 1e-10:
                            move = grad * step_size
                            
                            # Convert to barycentric for safe movement
                            u, v, w = to_bary(best[idx], A, B, C)
                            # Project move vector to barycentric coordinates
                            du, dv, dw = move[0]/side_length, move[1]/side_length, -move[0]/side_length - move[1]/side_length
                            u_new, v_new, w_new = clamp_bary(u + du, v + dv, w + dw)
                            
                            # Convert back to Cartesian
                            new_point = to_cart(u_new, v_new, w_new, A, B, C)
                            
                            candidate = best.copy()
                            candidate[idx] = new_point
                            
                            # Check validity
                            if not is_inside_triangle(candidate, A, B, C):
                                continue
                            
                            score = get_smallest_triangle_area(candidate)
                            if score > best_score:
                                improvement_found = True
                                improvement_magnitude = score - best_score
                                best = candidate
                                best_score = score
                                # Exit inner loop once improvement found
                                break
                    if improvement_found:
                        break

            # If geometric phase isn't working well, switch to barycentric perturbations (Phase 2)
            if not improvement_found and use_geometric_phase:
                if improvement_magnitude < geometric_phase_threshold:
                    use_geometric_phase = False

            # Barycentric perturbation phase
            if not improvement_found and not use_geometric_phase:
                for idx in candidate_indices:
                    if freq[idx] == 0:
                        break
                    
                    # Convert to barycentric
                    u, v, w = to_bary(best[idx], A, B, C)
                    
                    # Adaptive perturbation magnitude based on frequency
                    freq_factor = 1.0 + 0.5 * (freq[idx] / len(min_triplets))
                    perturb_mag = step_size * freq_factor
n                    # Random direction in barycentric space (preserving u+v+w=1)
                    du = np.random.normal(0, perturb_mag)
                    dv = np.random.normal(0, perturb_mag)
                    dw = -du - dv  # Maintain sum constraint
                    
                    u_new, v_new, w_new = clamp_bary(u + du, v + dv, w + dw)
                    
                    # Convert back to Cartesian
                    new_point = to_cart(u_new, v_new, w_new, A, B, C)
                    
                    candidate = best.copy()
                    candidate[idx] = new_point
                    
                    # Check validity
                    if not is_inside_triangle(candidate, A, B, C):
                        continue
                    
                    score = get_smallest_triangle_area(candidate)
                    if score > best_score:
                        improvement_found = True
                        best = candidate
                        best_score = score
                        break

            # Update search state
            if improvement_found:
                stagnation_count = 0
                # Adaptive step decay based on improvement
                step_size = min(step_size * 1.05, initial_step * 2.0)  # Allow growth for good moves
            else:
                stagnation_count += 1
                step_size *= 0.95

            # Reset step size if stuck for too long
            if stagnation_count >= 10:
                step_size = initial_step * (0.25 + 0.75 * (1.0 - best_score / 0.0365))
                stagnation_count = 0

        return best

    return improve