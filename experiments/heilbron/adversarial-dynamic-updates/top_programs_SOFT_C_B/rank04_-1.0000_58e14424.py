from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

EPS = 1e-5

# Barycentric coordinate helpers
def cartesian_to_barycentric(point, A, B, C):
    v0 = B - A
    v1 = C - A
    v2 = point - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    return np.array([u, v, w])

def barycentric_to_cartesian(bary, A, B, C):
    u, v, w = bary
    return u * A + v * B + w * C

def smooth_barycentric_projection(bary):
    # Smoother projection that maintains proportional distances to boundaries
    u, v, w = bary
    
    # Handle negative coordinates by proportional redistribution
    negatives = np.array([max(0, -u), max(0, -v), max(0, -w)])
    total_negative = np.sum(negatives)
    
    if total_negative > 0:
        positives = np.array([max(0, u), max(0, v), max(0, w)])
        total_positive = np.sum(positives)
        
        if total_positive > 0:
            # Distribute negative mass proportionally to positive coordinates
            redistribution = positives / total_positive * total_negative
            u = max(0, u) + redistribution[0]
            v = max(0, v) + redistribution[1]
            w = max(0, w) + redistribution[2]
        else:
            # Fallback to uniform distribution if all negative
            u, v, w = 1/3, 1/3, 1/3
    
    # Ensure sum is 1
    total = u + v + w
    return np.array([u, v, w]) / total

def estimate_gradient(points, idx, A, B, C, base_score=None):
    """Estimate gradient of minimum triangle area w.r.t. point position using finite differences."""
    if base_score is None:
        base_score = get_smallest_triangle_area(points)
    
    # Try small perturbations in x and y directions
    dx = np.array([EPS, 0])
    dy = np.array([0, EPS])
    
    # Create perturbed points
    points_dx_pos = points.copy()
    points_dx_pos[idx] += dx
    score_dx_pos = get_smallest_triangle_area(points_dx_pos)
    
    points_dx_neg = points.copy()
    points_dx_neg[idx] -= dx
    score_dx_neg = get_smallest_triangle_area(points_dx_neg)
    
    points_dy_pos = points.copy()
    points_dy_pos[idx] += dy
    score_dy_pos = get_smallest_triangle_area(points_dy_pos)
    
    points_dy_neg = points.copy()
    points_dy_neg[idx] -= dy
    score_dy_neg = get_smallest_triangle_area(points_dy_neg)
    
    # Calculate central differences
    grad_x = (score_dx_pos - score_dx_neg) / (2 * EPS)
    grad_y = (score_dy_pos - score_dy_neg) / (2 * EPS)
    
    return np.array([grad_x, grad_y])

def entrypoint():
    A, B, C = get_unit_triangle()
    initial_step_size = 0.05

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        step_size = initial_step_size
        stagnation_count = 0
        max_iterations = 150
        tol = 1e-9
        success_streak = 0
        
        # Convert all points to barycentric coordinates for easier constraint handling
        bary_points = np.array([cartesian_to_barycentric(p, A, B, C) for p in points])
        
        for _ in range(max_iterations):
            # Find all minimal-area triangles
            min_area = float('inf')
            min_triplets = []
            n = 11
            
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
            
            # Collect all vertices from minimal triangles with frequency counts
            vertex_count = np.zeros(n, dtype=int)
            for triplet in min_triplets:
                for idx in triplet:
                    vertex_count[idx] += 1
            
            # Calculate gradients for all points
            gradients = {}
            for i in range(n):
                if vertex_count[i] > 0:
                    gradients[i] = estimate_gradient(best, i, A, B, C, best_score)
            
            # Select multiple vertices based on frequency (softmax weighting)
            if np.sum(vertex_count) > 0:
                # Use softmax to get selection probabilities
                temperature = 0.5
                exp_counts = np.exp(vertex_count / temperature)
                probs = exp_counts / np.sum(exp_counts)
                
                # Select 2-3 vertices based on frequency
                num_to_select = min(3, max(2, int(np.sum(vertex_count) / len(min_triplets))))
                selected_indices = np.random.choice(n, size=num_to_select, p=probs, replace=False)
            else:
                selected_indices = [np.random.randint(0, n)]
            
            # Create candidate by perturbing selected vertices
            candidate_points = best.copy()
            improved_this_iter = False
            
            for idx in selected_indices:
                # Convert to barycentric
                bary = bary_points[idx].copy()
                
                # Determine perturbation direction
                if idx in gradients:
                    grad = gradients[idx]
                    grad_norm = np.linalg.norm(grad)
                    
                    if grad_norm > 1e-5:
                        # Use gradient direction (normalized)
                        direction = grad / grad_norm
                        
                        # Scale step by gradient magnitude (stronger signal = larger step)
                        adaptive_step = step_size * min(2.0, max(0.5, grad_norm * 1000))
                        
                        # Apply in Cartesian space for directional accuracy
                        cartesian_perturb = direction * adaptive_step
                        candidate_points[idx] = best[idx] + cartesian_perturb
                    else:
                        # Fallback to random perturbation if gradient is weak
                        cartesian_perturb = np.random.normal(0, step_size, size=2)
                        candidate_points[idx] = best[idx] + cartesian_perturb
                else:
                    # Fallback to random perturbation
                    cartesian_perturb = np.random.normal(0, step_size, size=2)
                    candidate_points[idx] = best[idx] + cartesian_perturb

                # Convert back to barycentric for constraint handling
                bary = cartesian_to_barycentric(candidate_points[idx], A, B, C)
                bary = smooth_barycentric_projection(bary)
                candidate_points[idx] = barycentric_to_cartesian(bary, A, B, C)

            # Check containment
            if not is_inside_triangle(candidate_points, A, B, C):
                # Try smaller step if outside
                candidate_points = best.copy()
                for idx in selected_indices:
                    direction = gradients.get(idx, np.random.normal(0, 1, size=2))
                    direction = direction / (np.linalg.norm(direction) + 1e-8)
                    candidate_points[idx] = best[idx] + direction * (step_size * 0.5)
                    
                    # Re-project to ensure containment
                    bary = cartesian_to_barycentric(candidate_points[idx], A, B, C)
                    bary = smooth_barycentric_projection(bary)
                    candidate_points[idx] = barycentric_to_cartesian(bary, A, B, C)

                if not is_inside_triangle(candidate_points, A, B, C):
                    stagnation_count += 1
                    continue

            # Evaluate candidate
            score = get_smallest_triangle_area(candidate_points)
            if score > best_score:
                best = candidate_points
                best_score = score
                improved_this_iter = True
                
                # Update barycentric representation
                for idx in selected_indices:
                    bary_points[idx] = cartesian_to_barycentric(best[idx], A, B, C)
                
                # Update success streak
                success_streak += 1
                stagnation_count = 0
            else:
                stagnation_count += 1

            # Adaptive step management based on success streak
            step_decay = 0.98 - 0.08 * min(success_streak / 5, 1)
            step_size *= step_decay
            
            # Reset success streak if no improvement
            if not improved_this_iter:
                success_streak = max(0, success_streak - 1)

            # Stagnation handling - enhanced multi-point restart
            if stagnation_count >= 10:
                # Reset step size to fraction of initial
                step_size = initial_step_size * 0.1
                
            # Deep stagnation - multi-point restart with gradient guidance
            if stagnation_count >= 25:
                # Identify top 3 vertices most involved in minimal triangles
                if np.sum(vertex_count) > 0:
                    critical_indices = np.argsort(vertex_count)[-3:]
                else:
                    critical_indices = np.random.choice(n, size=3, replace=False)
                
                # Create restart candidate by perturbing multiple critical points
                candidate_points = best.copy()
                restart_step = initial_step_size * 2.0
                
                for idx in critical_indices:
                    if idx in gradients:
                        grad = gradients[idx]
                        grad_norm = np.linalg.norm(grad)
                        if grad_norm > 1e-5:
                            direction = grad / grad_norm
n                            # Apply larger step in gradient direction
                            candidate_points[idx] = best[idx] + direction * restart_step
                        else:
                            # Random direction if gradient is weak
                            angle = np.random.uniform(0, 2 * np.pi)
                            direction = np.array([np.cos(angle), np.sin(angle)])
                            candidate_points[idx] = best[idx] + direction * restart_step
                    else:
                        # Random perturbation
                        angle = np.random.uniform(0, 2 * np.pi)
                        candidate_points[idx] = best[idx] + np.array([np.cos(angle), np.sin(angle)]) * restart_step

                    # Project back to valid region
                    bary = cartesian_to_barycentric(candidate_points[idx], A, B, C)
                    bary = smooth_barycentric_projection(bary)
                    candidate_points[idx] = barycentric_to_cartesian(bary, A, B, C)

                # Evaluate restart candidate
                if is_inside_triangle(candidate_points, A, B, C):
                    score = get_smallest_triangle_area(candidate_points)
                    if score > best_score:
                        best = candidate_points
                        best_score = score
                        # Update barycentric representation
                        for idx in critical_indices:
                            bary_points[idx] = cartesian_to_barycentric(best[idx], A, B, C)

                # Reset stagnation and step size
                stagnation_count = 0
                step_size = initial_step_size

        return best

    return improve