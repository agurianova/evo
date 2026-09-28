from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def project_onto_simplex(point):
    """
    Projects a point onto the 2-simplex (u,v,w >= 0, u+v+w=1)
    using the algorithm from 'Projection Onto A Simplex' by Yunmei Chen and Xiaojing Ye.
    """
    # Since w = 1 - u - v, we only need to project (u,v) onto u>=0, v>=0, u+v<=1
    u, v = point
    
    # First, project onto u>=0, v>=0
    u = max(0.0, u)
    v = max(0.0, v)
    
    # Then project onto u+v<=1
    if u + v > 1.0:
        # Move toward the line u+v=1
        t = (u + v - 1.0) / 2.0
        u -= t
        v -= t
        
        # Ensure non-negativity after projection
        if u < 0:
            v += u
            u = 0
        if v < 0:
            u += v
            v = 0
            
    w = 1.0 - u - v
    return np.array([u, v, w])

def cartesian_to_barycentric_jacobian(A, B, C):
    """
    Compute Jacobian matrix for Cartesian to barycentric conversion.
    Returns a 2x2 matrix that maps Cartesian coordinate changes to barycentric changes.
    """
    # The Jacobian relates d(x,y) to d(u,v) with w = 1 - u - v
    J = np.array([
        [B[0] - A[0], C[0] - A[0]],
        [B[1] - A[1], C[1] - A[1]]
    ])
    return np.linalg.inv(J)  # Maps Cartesian changes to barycentric changes

def calculate_area_gradient(p1, p2, p3):
    """
    Calculate the gradient of the triangle area with respect to each vertex.
    Returns three vectors indicating how to move each point to increase area.
    """
    # For triangle with points A,B,C, the gradient of area w.r.t. A is 0.5*(C-B) rotated 90 degrees
    grad_p1 = 0.5 * np.array([p3[1] - p2[1], p2[0] - p3[0]])
    grad_p2 = 0.5 * np.array([p1[1] - p3[1], p3[0] - p1[0]])
    grad_p3 = 0.5 * np.array([p2[1] - p1[1], p1[0] - p2[0]])
    
    # Normalize gradients
    norm1 = np.linalg.norm(grad_p1)
    norm2 = np.linalg.norm(grad_p2)
    norm3 = np.linalg.norm(grad_p3)
    
    if norm1 > 1e-10:
        grad_p1 /= norm1
    if norm2 > 1e-10:
        grad_p2 /= norm2
    if norm3 > 1e-10:
        grad_p3 /= norm3

    return grad_p1, grad_p2, grad_p3

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Precompute Jacobian for coordinate conversion
    jac = cartesian_to_barycentric_jacobian(A, B, C)

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Convert all points to barycentric for constrained movement
        bary_points = np.array([np.array([1 - p[0] - p[1], p[0], p[1]]) 
                               for p in [cartesian_to_barycentric(p, A, B, C) for p in points]])
        
        initial_step = 0.05
        step_size = initial_step
        stagnation_count = 0
        major_stagnation = 0
        max_iterations = 200
        tol = 1e-9
        n = 11
        
        # Adaptive exploration parameters
        exploration_phase = False
        exploration_counter = 0
        exploration_threshold = 25
        improvement_history = []
        history_window = 10
        
        for iteration in range(max_iterations):
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
            
            if not min_triplets:
                break
            
            # Update improvement history
            improvement_history.append(best_score)
            if len(improvement_history) > history_window:
                improvement_history.pop(0)
            
            # Determine if we're in exploration or exploitation phase
            if len(improvement_history) == history_window:
                improvement_rate = (improvement_history[-1] - improvement_history[0]) / history_window
n                if improvement_rate < 1e-6:  # Very slow improvement
                    exploration_phase = True
                    exploration_counter += 1
                else:
                    exploration_phase = False
                    exploration_counter = 0
            
            # Apply exploration strategy if needed
            if exploration_phase and exploration_counter > exploration_threshold:
                # Apply larger random perturbations to multiple points
                num_perturbed = max(1, n // 3)
                indices = np.random.choice(n, size=num_perturbed, replace=False)
                
                candidate_bary = bary_points.copy()
                for idx in indices:
                    # Larger random move in barycentric space
                    bary_move = np.random.uniform(-0.1, 0.1, size=3)
                    candidate_bary[idx] += bary_move
                    candidate_bary[idx] = project_onto_simplex(candidate_bary[idx][:2])
                
                # Convert back to Cartesian
                candidate = np.array([barycentric_to_cartesian(b, A, B, C) for b in candidate_bary])

                # Verify containment
                if is_inside_triangle(candidate, A, B, C):
                    score = get_smallest_triangle_area(candidate)
                    if score > best_score:
                        best = candidate
                        bary_points = np.array([cartesian_to_barycentric(p, A, B, C) for p in best])
                        best_score = score
                        stagnation_count = 0
                        major_stagnation = 0
                        exploration_phase = False
                        exploration_counter = 0

                # Reset exploration counter
                exploration_counter = 0
                continue

            # Select a minimal triangle to work on
            triplet_idx = np.random.randint(len(min_triplets))
            i, j, k = min_triplets[triplet_idx]
            
            # Calculate area gradients for all three points
            grad_i, grad_j, grad_k = calculate_area_gradient(best[i], best[j], best[k])

            # Convert gradients to barycentric space using Jacobian
            bary_grad_i = jac @ grad_i
            bary_grad_j = jac @ grad_j
            bary_grad_k = jac @ grad_k

            # Create candidate by moving all three points
            candidate_bary = bary_points.copy()
            
            # Apply constrained perturbation to all three points
            candidate_bary[i][:2] += bary_grad_i * step_size
            candidate_bary[j][:2] += bary_grad_j * step_size
            candidate_bary[k][:2] += bary_grad_k * step_size

            # Project back to simplex
            candidate_bary[i] = project_onto_simplex(candidate_bary[i][:2])
            candidate_bary[j] = project_onto_simplex(candidate_bary[j][:2])
            candidate_bary[k] = project_onto_simplex(candidate_bary[k][:2])

            # Convert back to Cartesian
            candidate = np.array([barycentric_to_cartesian(b, A, B, C) for b in candidate_bary])

            # Verify containment (should be guaranteed by barycentric, but double-check)
            if not is_inside_triangle(candidate, A, B, C):
                stagnation_count += 1
                major_stagnation += 1
            else:
                score = get_smallest_triangle_area(candidate)
                if score > best_score:
                    best = candidate
                    bary_points = np.array([cartesian_to_barycentric(p, A, B, C) for p in best])
                    best_score = score
                    stagnation_count = 0
                    major_stagnation = 0
                    
                    # Gradual step size increase when improving
                    step_size = min(step_size * 1.05, initial_step * 1.5)
                else:
                    stagnation_count += 1
                    major_stagnation += 1
                    
                    # Gradual step size decay when not improving
                    step_size *= 0.98

            # Stagnation handling
            if stagnation_count >= 10:
                step_size = initial_step * 0.25  # Larger reset for better recovery
                stagnation_count = 0

            # Major stagnation - restart with larger perturbation
            if major_stagnation >= 35:
                step_size = initial_step * 0.7  # Larger step for escaping deep local optima
                stagnation_count = 0
                major_stagnation = 0

        return best

    return improve