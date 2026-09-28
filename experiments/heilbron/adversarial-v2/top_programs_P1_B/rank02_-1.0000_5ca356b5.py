import numpy as np
from itertools import combinations
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle

np.random.seed(42)

def project_point_to_triangle(p, A, B, C):
    """Project point p onto the triangle defined by A, B, C"""
    v0 = B - A
    v1 = C - A
    v2 = p - A
    
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-10:
        return A
    
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    
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
        
    return A + v * v0 + w * v1

def entrypoint():
    A_tri, B_tri, C_tri = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        best = points.copy()
        best_score = get_smallest_triangle_area(points)
        current_score = best_score

        initial_step_size = 0.01
        step_size = initial_step_size
        temperature = 0.05
        no_improve_count = 0
        
        for iteration in range(1000):
            # Find all triangles and their areas
            triangles = []
            for i, j, k in combinations(range(11), 3):
                ax, ay = current[i]
                bx, by = current[j]
                cx, cy = current[k]
                s_val = 0.5 * ((bx - ax) * (cy - ay) - (cx - ax) * (by - ay))
                abs_area = abs(s_val)
                triangles.append((abs_area, i, j, k, s_val))

            # Sort by area
            triangles.sort(key=lambda x: x[0])
            
            # Adaptive selection of critical triangles
            min_area = triangles[0][0]
            if min_area > 0:
                # Dynamic threshold percentage based on current solution quality
                # As min_area improves (gets larger), tighten the threshold
                threshold_pct = 0.15
                if best_score > 0.02:
                    threshold_pct = 0.08  # Tighter threshold for better solutions
                elif best_score > 0.015:
                    threshold_pct = 0.12
                
                threshold = min_area * (1 + threshold_pct)
                top_triangles = [t for t in triangles if t[0] <= threshold]
                # Ensure we have at least 3 triangles to work with
                if len(top_triangles) < 3:
                    top_triangles = triangles[:3]
            else:
                top_triangles = triangles[:3]

            # Initialize gradient accumulators for all points
            gradients = np.zeros_like(current)
            
            # Count point involvement in critical triangles
            involvement = np.zeros(11)
            for _, i, j, k, _ in top_triangles:
                involvement[i] += 1
                involvement[j] += 1
                involvement[k] += 1
            
            # Process each top triangle
            for abs_area, i, j, k, s_val in top_triangles:
                # Weight based on how small this triangle is
                weight = 1.0 / (abs_area + 1e-10)
                
                A = current[i]
                B = current[j]
                C = current[k]

                sign_S = 1.0 if s_val >= 0 else -1.0

                # Compute side lengths for adaptive step sizing
                len_BC = np.linalg.norm(B - C)
                len_AC = np.linalg.norm(A - C)
                len_AB = np.linalg.norm(A - B)

                # Compute gradients with adaptive scaling
                grad_A = sign_S * np.array([B[1] - C[1], C[0] - B[0]])
                grad_B = sign_S * np.array([C[1] - A[1], A[0] - C[0]])
                grad_C = sign_S * np.array([A[1] - B[1], B[0] - A[0]])

                # Normalize gradients and scale by side lengths for consistent area impact
                for grad, side_len in [(grad_A, len_BC), (grad_B, len_AC), (grad_C, len_AB)]:
                    norm = np.linalg.norm(grad)
                    if norm > 0:
                        grad[:] = grad / norm * side_len

                # Accumulate weighted gradients
                gradients[i] += weight * grad_A
                gradients[j] += weight * grad_B
                gradients[k] += weight * grad_C

            # Scale gradients by involvement (points in more small triangles move more)
            max_involvement = np.max(involvement) if np.max(involvement) > 0 else 1
n            for i in range(11):
                if involvement[i] > 0:
                    # Use sqrt scaling for diminishing returns effect
                    scale_factor = np.sqrt(involvement[i] / max_involvement)
                    gradients[i] *= scale_factor

            # Create candidate by moving all points with non-zero gradients
            candidate = current.copy()
            
            # Adaptive step sizing based on solution quality and progress
            if best_score < 0.01:
                step_factor = 1.5  # Exploration phase - larger steps
            elif best_score < 0.02:
                step_factor = 1.0  # Transition phase
            else:
                step_factor = 0.7   # Refinement phase - smaller steps
            
            # Adjust for recent progress
            if no_improve_count < 20:
                progress_factor = 1.1  # Making progress, maintain momentum
            else:
                progress_factor = 0.8  # Stuck, reduce step size

            adaptive_step = step_size * step_factor * progress_factor
n            for i in range(11):
                if np.linalg.norm(gradients[i]) > 0:
                    candidate[i] += adaptive_step * gradients[i]

            # Project any points outside the triangle back onto the boundary
            for i in range(11):
                if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                    candidate[i] = project_point_to_triangle(candidate[i], A_tri, B_tri, C_tri)

            new_score = get_smallest_triangle_area(candidate)

            # Update best solution if improvement found
            if new_score > best_score:
                best = candidate.copy()
                best_score = new_score
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0
            elif new_score > current_score:
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0
            else:
                delta = new_score - current_score
                if delta < 0:
                    prob = np.exp(delta / temperature)
                    if np.random.random() < prob:
                        current = candidate.copy()
                        current_score = new_score
                        no_improve_count = 0
                    else:
                        no_improve_count += 1
                else:
                    no_improve_count += 1

            # Periodic global perturbation to escape deep local minima
            # Adaptive interval - harder problems get more frequent perturbations
            base_interval = 200
            if best_score > 0:
                perturbation_factor = 0.03 / max(best_score, 0.005)
                global_perturbation_interval = int(base_interval * perturbation_factor)
                global_perturbation_interval = max(50, min(300, global_perturbation_interval))
            else:
                global_perturbation_interval = 200

            if no_improve_count >= global_perturbation_interval:
                # Perturb points proportionally to their involvement in small triangles
                perturbation = np.random.uniform(-0.02, 0.02, size=current.shape)
                # Scale perturbation by involvement
                for i in range(11):
                    if involvement[i] > 0:
                        scale_factor = 0.5 + 0.5 * (involvement[i] / max_involvement)
                        perturbation[i] *= scale_factor
                
                candidate = current + perturbation
                
                # Project back to triangle
                for i in range(11):
                    if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                        candidate[i] = project_point_to_triangle(candidate[i], A_tri, B_tri, C_tri)
                
                new_score = get_smallest_triangle_area(candidate)
                
                if new_score > best_score:
                    best = candidate.copy()
                    best_score = new_score
                    
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0

            # Adaptive step size reduction
            if no_improve_count >= 50:
                step_size *= 0.95
                no_improve_count = 0

            # Adaptive temperature decay
            if iteration > 200:
                temperature *= 0.995  # Faster decay for exploitation
            else:
                temperature *= 0.999  # Slower decay for initial exploration

        return best

    return improve