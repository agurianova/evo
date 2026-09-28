from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def identify_smallest_triangles(points, k=3):
        """Identify the k smallest triangles and return their vertex indices."""
        n = len(points)
        min_areas = []
        min_indices = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    # Calculate triangle area using cross product
                    v1 = points[j] - points[i]
                    v2 = points[k] - points[i]
                    area = 0.5 * abs(np.cross(v1, v2))
                    
                    if len(min_areas) < k or area < max(min_areas):
                        if len(min_areas) == k:
                            idx = min_areas.index(max(min_areas))
                            min_areas[idx] = area
                            min_indices[idx] = (i, j, k)
                        else:
                            min_areas.append(area)
                            min_indices.append((i, j, k))
        
        return min_indices, min_areas

    def estimate_gradient(points, idx, current_score, A, B, C, epsilon=1e-5):
        """Estimate gradient of minimum triangle area w.r.t. a specific point using central differences."""
        original_point = points[idx].copy()
        
        # Try perturbing in +x direction
        points_p_x = points.copy()
        points_p_x[idx] = original_point + np.array([epsilon, 0])
        if not is_inside_triangle(points_p_x[idx].reshape(1, 2), A, B, C):
            points_p_x[idx] = original_point  # Revert if outside
        score_p_x = get_smallest_triangle_area(points_p_x)
        
        # Try perturbing in -x direction
        points_m_x = points.copy()
        points_m_x[idx] = original_point - np.array([epsilon, 0])
        if not is_inside_triangle(points_m_x[idx].reshape(1, 2), A, B, C):
            points_m_x[idx] = original_point  # Revert if outside
        score_m_x = get_smallest_triangle_area(points_m_x)
        
        # Try perturbing in +y direction
        points_p_y = points.copy()
        points_p_y[idx] = original_point + np.array([0, epsilon])
        if not is_inside_triangle(points_p_y[idx].reshape(1, 2), A, B, C):
            points_p_y[idx] = original_point  # Revert if outside
        score_p_y = get_smallest_triangle_area(points_p_y)
        
        # Try perturbing in -y direction
        points_m_y = points.copy()
        points_m_y[idx] = original_point - np.array([0, epsilon])
        if not is_inside_triangle(points_m_y[idx].reshape(1, 2), A, B, C):
            points_m_y[idx] = original_point  # Revert if outside
        score_m_y = get_smallest_triangle_area(points_m_y)
        
        # Central difference for better accuracy
        dx = (score_p_x - score_m_x) / (2 * epsilon)
        dy = (score_p_y - score_m_y) / (2 * epsilon)
        
        return np.array([dx, dy])

    def improve(points: np.ndarray) -> np.ndarray:
        # Create input-dependent RNG for adversarial robustness
        seed = abs(hash(points.tobytes())) % (2**32)
        rng = np.random.default_rng(seed)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        
        total_iterations = 500  # Increased from 200 to 500
        early_stop_patience = 30  # Increased from 20
        T0 = 0.01
        no_improve_count = 0

        # Identify critical points involved in smallest triangles
        smallest_triangles, _ = identify_smallest_triangles(points, k=5)
        critical_points = set()
        for tri in smallest_triangles:
            critical_points.update(tri)
        critical_points = list(critical_points)

        for i in range(total_iterations):
            # Adaptive step size decay: square root schedule (maintains larger steps longer)
            sigma = 0.05 * (1 - i / total_iterations) ** 0.5
            
            # Dynamic bias toward smallest triangles (decreases as optimization progresses)
            critical_bias = max(0.3, 0.7 * (1 - i/total_iterations))
            
            # Decide perturbation scope with bias toward critical points
            if len(critical_points) > 0 and rng.random() < critical_bias:
                # Focus on smallest triangles
                num_points = rng.choice([1, 2, 3], p=[0.5, 0.35, 0.15])
                indices = rng.choice(critical_points, size=min(num_points, len(critical_points)), replace=False)
            else:
                # Decide perturbation scope: 60% single point, 40% multi-point
                if rng.random() < 0.4:
                    num_points = rng.choice([2, 3, 4])
                    indices = rng.choice(11, size=num_points, replace=False)
                else:
                    indices = [rng.choice(11)]

            candidate = current.copy()
            gradient_applied = False
            
            # Gradient-aware perturbation with decaying influence
            gradient_influence = max(0.3, 0.7 * (1 - i/total_iterations))
            if rng.random() < gradient_influence:
                for idx in indices:
                    grad = estimate_gradient(candidate, idx, current_score, A, B, C)
                    grad_norm = np.linalg.norm(grad)
                    if grad_norm > 1e-5:
                        # Normalize gradient and scale by sigma
                        grad_direction = grad / grad_norm
n                        candidate[idx] += grad_direction * sigma * 0.8
                        gradient_applied = True
                    else:
                        # Fallback to random perturbation
                        candidate[idx] += rng.normal(0, sigma, size=2)
            else:
                # Random perturbation
                for idx in indices:
                    candidate[idx] += rng.normal(0, sigma, size=2)

            # Project points back to triangle boundary if needed
            for idx in indices:
                if not is_inside_triangle(candidate[idx].reshape(1, 2), A, B, C):
                    # Simple projection to nearest boundary point
                    bary = np.array([
                        np.dot(candidate[idx] - B, C - B) / np.dot(C - B, C - B),
                        np.dot(candidate[idx] - A, C - A) / np.dot(C - A, C - A),
                        np.dot(candidate[idx] - A, B - A) / np.dot(B - A, B - A)
                    ])
                    # Find closest edge and project
                    min_bary = np.min(bary)
                    if min_bary < 0:
                        edge_idx = np.argmin(bary)
                        if edge_idx == 0:
                            # Project to BC edge
                            t = np.dot(candidate[idx] - B, C - B) / np.dot(C - B, C - B)
                            t = np.clip(t, 0, 1)
                            candidate[idx] = B + t * (C - B)
                        elif edge_idx == 1:
                            # Project to AC edge
                            t = np.dot(candidate[idx] - A, C - A) / np.dot(C - A, C - A)
                            t = np.clip(t, 0, 1)
                            candidate[idx] = A + t * (C - A)
                        else:
                            # Project to AB edge
                            t = np.dot(candidate[idx] - A, B - A) / np.dot(B - A, B - A)
                            t = np.clip(t, 0, 1)
                            candidate[idx] = A + t * (B - A)

            score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            T = T0 * (1 - i / total_iterations)
            if score > current_score:
                current = candidate
                current_score = score
                no_improve_count = 0
                if score > best_score:
                    best = candidate
                    best_score = score
                    # Update critical points after improvement
                    smallest_triangles, _ = identify_smallest_triangles(best, k=5)
                    critical_points = set()
                    for tri in smallest_triangles:
                        critical_points.update(tri)
                    critical_points = list(critical_points)
            else:
                delta = score - current_score
                if rng.random() < np.exp(delta / T):
                    current = candidate
                    current_score = score
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            # Restart mechanism for stagnation with adaptive perturbation magnitude
            if no_improve_count >= early_stop_patience:
                current = best.copy()
                current_score = best_score
                no_improve_count = 0
                
                # Adaptive restart perturbation magnitude
                restart_factor = 1 + no_improve_count / early_stop_patience
                restart_indices = rng.choice(11, size=rng.choice([2, 3, 4]), replace=False)
                for idx in restart_indices:
                    # Larger perturbation scaled by stagnation depth
                    current[idx] += rng.normal(0, restart_factor * 5 * sigma, size=2)
                
                # Project restart points back to triangle
                for idx in restart_indices:
                    if not is_inside_triangle(current[idx].reshape(1, 2), A, B, C):
                        bary = np.array([
                            np.dot(current[idx] - B, C - B) / np.dot(C - B, C - B),
                            np.dot(current[idx] - A, C - A) / np.dot(C - A, C - A),
                            np.dot(current[idx] - A, B - A) / np.dot(B - A, B - A)
                        ])
                        min_bary = np.min(bary)
                        if min_bary < 0:
                            edge_idx = np.argmin(bary)
                            if edge_idx == 0:
                                t = np.dot(current[idx] - B, C - B) / np.dot(C - B, C - B)
                                t = np.clip(t, 0, 1)
                                current[idx] = B + t * (C - B)
                            elif edge_idx == 1:
                                t = np.dot(current[idx] - A, C - A) / np.dot(C - A, C - A)
                                t = np.clip(t, 0, 1)
                                current[idx] = A + t * (C - A)
                            else:
                                t = np.dot(current[idx] - A, B - A) / np.dot(B - A, B - A)
                                t = np.clip(t, 0, 1)
                                current[idx] = A + t * (B - A)
                
                if is_inside_triangle(current, A, B, C):
                    current_score = get_smallest_triangle_area(current)
                    if current_score > best_score:
                        best = current.copy()
                        best_score = current_score
                        # Update critical points after restart improvement
                        smallest_triangles, _ = identify_smallest_triangles(best, k=5)
                        critical_points = set()
                        for tri in smallest_triangles:
                            critical_points.update(tri)
                        critical_points = list(critical_points)

        return best

    return improve