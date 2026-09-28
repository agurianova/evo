from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    # Precompute triangle edge vectors for barycentric calculations
    AB = B - A
    AC = C - A
    BC = C - B
    
    # Helper to convert Cartesian to barycentric coordinates
    def cartesian_to_barycentric(p):
        # Solve for u, v where p = A + u*(B-A) + v*(C-A)
        mat = np.column_stack((AB, AC))
        b = p - A
        try:
            uv = np.linalg.solve(mat, b)
            u, v = uv[0], uv[1]
            w = 1 - u - v
n            return np.array([u, v, w])
        except np.linalg.LinAlgError:
            # Fallback for degenerate cases
            return np.array([0.333, 0.333, 0.333])

    # Helper to convert barycentric to Cartesian coordinates
    def barycentric_to_cartesian(bary):
        u, v, w = bary
        return A * w + B * u + C * v

    # Helper to project point to nearest boundary if outside
    def project_to_triangle(point):
        # Convert to barycentric coordinates
        bary = cartesian_to_barycentric(point)
        
        # Check if outside the triangle
        if np.all(bary >= 0):
            return point
            
        # Project to nearest edge or vertex
        # Edge AB: w=0
        bary_ab = np.array([bary[0], bary[1], 0])
        bary_ab = np.maximum(bary_ab, 0)
        bary_ab /= np.sum(bary_ab)
        
        # Edge AC: v=0
        bary_ac = np.array([bary[0], 0, bary[2]])
        bary_ac = np.maximum(bary_ac, 0)
        bary_ac /= np.sum(bary_ac)
        
        # Edge BC: u=0
        bary_bc = np.array([0, bary[1], bary[2]])
        bary_bc = np.maximum(bary_bc, 0)
        bary_bc /= np.sum(bary_bc)
        
        # Calculate distances to each edge projection
        point_ab = barycentric_to_cartesian(bary_ab)
        point_ac = barycentric_to_cartesian(bary_ac)
        point_bc = barycentric_to_cartesian(bary_bc)
        
        dist_ab = np.linalg.norm(point - point_ab)
        dist_ac = np.linalg.norm(point - point_ac)
        dist_bc = np.linalg.norm(point - point_bc)
        
        # Choose closest projection
        if dist_ab <= dist_ac and dist_ab <= dist_bc:
            return point_ab
        elif dist_ac <= dist_ab and dist_ac <= dist_bc:
            return point_ac
        else:
            return point_bc

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        
        # Simulated annealing parameters
        initial_temp = 0.001
        temp = initial_temp
        temp_decay = 0.995
        max_rounds = 200
        early_stop = 20
        no_improve = 0
        
        # Helper function to find smallest triangle
        def get_smallest_triangle_indices(points):
            n = points.shape[0]
            min_area = float('inf')
            best_indices = (0, 1, 2)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = points[i], points[j], points[k]
                        area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        if area < min_area:
                            min_area = area
                            best_indices = (i, j, k)
            return best_indices
        
        # Helper function to compute gradient for smallest triangle area
        def compute_gradient(points, idx1, idx2, idx3):
            p1, p2, p3 = points[idx1], points[idx2], points[idx3]
            
            v12 = p2 - p1
            v13 = p3 - p1
            
            # Gradient for p1: move perpendicular to v12 and v13
            grad_p1 = np.array([-v12[1] + v13[1], v12[0] - v13[0]])
            # Gradient for p2: move perpendicular to v12
            grad_p2 = np.array([-v12[1], v12[0]])
            # Gradient for p3: move perpendicular to v13
            grad_p3 = np.array([-v13[1], v13[0]])
            
            # Normalize gradients
            if np.linalg.norm(grad_p1) > 0:
                grad_p1 = grad_p1 / np.linalg.norm(grad_p1)
            if np.linalg.norm(grad_p2) > 0:
                grad_p2 = grad_p2 / np.linalg.norm(grad_p2)
            if np.linalg.norm(grad_p3) > 0:
                grad_p3 = grad_p3 / np.linalg.norm(grad_p3)
                
            return grad_p1, grad_p2, grad_p3
        
        for _round in range(max_rounds):
            # Identify the bottleneck (smallest triangle)
            i1, i2, i3 = get_smallest_triangle_indices(current)
            
            # 80% chance to perturb bottleneck points, 20% random
            if np.random.rand() < 0.8:
                idx = np.random.choice([i1, i2, i3])
            else:
                idx = np.random.randint(0, 11)
            
            # Compute gradient if perturbing bottleneck point
            # Adaptive step size with minimum threshold
            step_size = max(0.005, 0.02 * (temp / initial_temp))
            step = np.random.normal(0, step_size, size=2)
            
            if idx in [i1, i2, i3] and np.random.rand() < 0.7:
                grads = compute_gradient(current, i1, i2, i3)
                if idx == i1:
                    step = 0.25 * step + 0.75 * grads[0] * step_size
                elif idx == i2:
                    step = 0.25 * step + 0.75 * grads[1] * step_size
                else:
                    step = 0.25 * step + 0.75 * grads[2] * step_size
            
            candidate = current.copy()
            candidate[idx] += step
            
            # Project back inside triangle if needed
            candidate[idx] = project_to_triangle(candidate[idx])
            
            score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            delta = score - current_score
            if delta > 0 or (temp > 0 and np.random.rand() < np.exp(delta / temp)):
                current = candidate
                current_score = score
                if score > best_score:
                    best = candidate
                    best_score = score
                    # Reset early stopping counter only on new best
                    no_improve = 0
                else:
                    # Only increment if not a new global best
                    no_improve += 1
            else:
                # Only increment if not a new global best
                no_improve += 1
            
            # Cooling
            temp *= temp_decay
            
            # Early stopping
            if no_improve >= early_stop:
                break

        return best

    return improve