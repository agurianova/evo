from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def barycentric_project(point):
        """Project a point back into the triangle using barycentric coordinates."""
        v0 = B - A
        v1 = C - A
        v2 = point - A
        
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        if abs(denom) < 1e-10:
            return (A + B + C) / 3
            
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w
        
        # Clip to [0,1] and renormalize if outside
        if u < 0:
            u = 0
            sum_vw = v + w
            if sum_vw > 0:
                v, w = v/sum_vw, w/sum_vw
            else:
                v, w = 0.5, 0.5
        if v < 0:
            v = 0
            sum_uw = u + w
            if sum_uw > 0:
                u, w = u/sum_uw, w/sum_uw
            else:
                u, w = 0.5, 0.5
        if w < 0:
            w = 0
            sum_uv = u + v
            if sum_uv > 0:
                u, v = u/sum_uv, v/sum_uv
            else:
                u, v = 0.5, 0.5
        
        # Ensure sum is 1 (numerical stability)
        total = u + v + w
        if total > 0:
            u, v, w = u/total, v/total, w/total
        else:
            u, v, w = 1/3, 1/3, 1/3
        
        return u * A + v * B + w * C

    def get_adaptive_triangle_indices(pts, min_area=None, threshold_factor=1.1):
        """Get indices of all triangles with area below threshold_factor * min_area."""
        n = pts.shape[0]
        areas = []
        indices = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k_idx in range(j+1, n):
                    a, b, c = pts[i], pts[j], pts[k_idx]
                    area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                    areas.append(area)
                    indices.append((i, j, k_idx))
        
        if not areas:
            return [(0, 1, 2)]
            
        # Calculate min_area if not provided
        if min_area is None:
            min_area = min(areas)
        
        # Select all triangles below threshold
        threshold = min_area * threshold_factor
        adaptive_indices = [idx for area, idx in zip(areas, indices) if area <= threshold]
        
        # Always return at least one triangle
n        return adaptive_indices if adaptive_indices else [indices[np.argmin(areas)]]

    def calculate_area_gradient(points, triangle_indices):
        """Calculate gradient of triangle area with respect to each vertex position, weighted by inverse distances."""
        i, j, k = triangle_indices
        a, b, c = points[i], points[j], points[k]
        
        # Area = 0.5 * |(b-a) × (c-a)|
        # Partial derivatives:
        # dA/da = -0.5 * ((b_y - c_y), (c_x - b_x))
        # dA/db = -0.5 * ((c_y - a_y), (a_x - c_x))
        # dA/dc = -0.5 * ((a_y - b_y), (b_x - a_x))
        
        grad_a = np.array([-(b[1] - c[1]), b[0] - c[0]]) * 0.5
        grad_b = np.array([-(c[1] - a[1]), c[0] - a[0]]) * 0.5
        grad_c = np.array([-(a[1] - b[1]), a[0] - b[0]]) * 0.5
        
        # Calculate pairwise distances
        dist_ab = max(1e-10, np.linalg.norm(a - b))
        dist_ac = max(1e-10, np.linalg.norm(a - c))
        dist_bc = max(1e-10, np.linalg.norm(b - c))
        
        # Weight gradients by inverse distances (closer points have higher impact)
        weight_a = 1.0 / (dist_ab * dist_ac)
        weight_b = 1.0 / (dist_ab * dist_bc)
        weight_c = 1.0 / (dist_ac * dist_bc)
        
        grad_a = grad_a * weight_a
        grad_b = grad_b * weight_b
        grad_c = grad_c * weight_c

        # Normalize gradients
        norm_a = np.linalg.norm(grad_a)
        norm_b = np.linalg.norm(grad_b)
        norm_c = np.linalg.norm(grad_c)
        
        if norm_a > 1e-10:
            grad_a = grad_a / norm_a
        if norm_b > 1e-10:
            grad_b = grad_b / norm_b
        if norm_c > 1e-10:
            grad_c = grad_c / norm_c

        return grad_a, grad_b, grad_c

    def get_adaptive_parameters(initial_min_area, max_possible=0.0365):
        """Calculate annealing parameters based on initial configuration quality."""
        # Convert to percentile (0-1, where 0 is worst possible, 1 is best)
        quality_percentile = min(1.0, max(0.0, initial_min_area / max_possible))
        
        # For low-quality inputs (many small triangles), be more aggressive
        # For high-quality inputs (few small triangles), be more conservative
        base_step = 0.08 - 0.06 * quality_percentile
        T0 = 0.012 - 0.004 * quality_percentile
        T_decay_base = 0.997 + 0.001 * quality_percentile
        step_decay_base = 0.998 + 0.001 * quality_percentile
        min_ratio = 0.05 + 0.25 * quality_percentile
        
        return base_step, T0, T_decay_base, step_decay_base, min_ratio

    def run_annealing_chain(initial_points, base_step, T0, T_decay_base, step_decay_base, min_ratio):
        """Run a single annealing chain with specific parameters."""
        best = initial_points.copy()
        best_score = get_smallest_triangle_area(best)
        
        n_rounds = 350
        T_decay = T_decay_base
        step_decay = step_decay_base

        # Track improvement history for adaptive cooling
        improvement_history = []
        stagnation_counter = 0
        
        # Dynamic window size for adaptive cooling (larger early, smaller late)
        adaptive_window_size = 20

        for round_idx in range(n_rounds):
            # Adjust window size based on progress
            if improvement_history:
                if len(improvement_history) < 10:
                    adaptive_window_size = 20
                elif len(improvement_history) < 30:
                    adaptive_window_size = 15
                else:
                    adaptive_window_size = 5
            
            # Adjust cooling rate based on recent progress
            if improvement_history and len(improvement_history) >= adaptive_window_size:
                recent_improvements = improvement_history[-adaptive_window_size:]
                avg_improvement = np.mean(recent_improvements)
                if avg_improvement < 1e-6:
                    T_decay = max(0.996, T_decay * 1.001)
                    step_decay = min(0.9995, step_decay * 1.0005)
                    stagnation_counter += 1
                else:
                    T_decay = min(0.9985, T_decay * 0.9998)
                    step_decay = max(0.997, step_decay * 0.9997)
                    stagnation_counter = max(0, stagnation_counter - 1)
            
            # Scale stagnation threshold based on improvement rate
            stagnation_threshold = 10 + 20 * (1.0 - min(1.0, len(improvement_history)/50))
            
            # Reset if stuck for too long
            if stagnation_counter > stagnation_threshold:
                T_decay = T_decay_base
                step_decay = step_decay_base
                stagnation_counter = 0
                improvement_history = []

            T = T0 * (T_decay ** round_idx)
            current_step = base_step * (step_decay ** round_idx)
            
            # Dynamically adjust min_ratio based on progress
            if stagnation_counter > stagnation_threshold // 2:
                adaptive_min_ratio = min(0.3, min_ratio * 1.1)
            else:
                adaptive_min_ratio = max(0.01, min_ratio * 0.9)

            # Get adaptive triangle selection
            min_area = get_smallest_triangle_area(best)
            triangle_indices = get_adaptive_triangle_indices(best, min_area)
            
            if not triangle_indices:
                triangle_indices = [(0, 1, 2)]
            
            selected_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
            
            # Dynamic gradient/isotropic ratio: start exploratory, end refined
            gradient_ratio = 0.5 + 0.4 * (round_idx / n_rounds)
            # Further adjust based on recent progress
            if improvement_history and len(improvement_history) >= 5:
                recent_improvements = improvement_history[-5:]
                if all(imp < 1e-6 for imp in recent_improvements):
                    gradient_ratio = max(0.7, gradient_ratio)
                else:
                    gradient_ratio = min(0.9, gradient_ratio)

            if np.random.rand() < gradient_ratio:
                # Gradient-based perturbations (more targeted)
                grad_i, grad_j, grad_k = calculate_area_gradient(best, selected_triangle)
                
                # Dynamic perturbation count: more exploratory early, more focused late
                perturb_all = np.random.rand() < (0.3 + 0.6 * (round_idx / n_rounds))
                
                if not perturb_all:
                    idx = selected_triangle[np.random.randint(3)]
                    candidate = best.copy()
                    
                    if idx == selected_triangle[0]:
                        candidate[idx] += grad_i * current_step
                    elif idx == selected_triangle[1]:
                        candidate[idx] += grad_j * current_step
                    else:
                        candidate[idx] += grad_k * current_step
                    
                    # Project back if needed
                    candidate[idx] = barycentric_project(candidate[idx])
                else:
                    candidate = best.copy()
                    candidate[selected_triangle[0]] += grad_i * current_step
                    candidate[selected_triangle[1]] += grad_j * current_step
                    candidate[selected_triangle[2]] += grad_k * current_step
                    
                    # Project back if needed
                    for idx in selected_triangle:
                        candidate[idx] = barycentric_project(candidate[idx])
            else:
                # Isotropic perturbations (fallback)
                perturb_all = np.random.rand() < (0.3 + 0.6 * (round_idx / n_rounds))
                
                candidate = best.copy()
                if not perturb_all:
                    idx = selected_triangle[np.random.randint(3)]
                    r = current_step * np.sqrt(np.random.rand())
                    theta = 2 * np.pi * np.random.rand()
                    perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                    candidate[idx] += perturbation
                    
                    # Project back if needed
                    candidate[idx] = barycentric_project(candidate[idx])
                else:
                    for idx in selected_triangle:
                        r = current_step * np.sqrt(np.random.rand())
                        theta = 2 * np.pi * np.random.rand()
                        perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                        candidate[idx] += perturbation
                        
                        # Project back if needed
                        candidate[idx] = barycentric_project(candidate[idx])
            
            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - best_score
            
            # Track improvements for adaptive cooling
            if delta > 0:
                improvement_history.append(delta)
                if len(improvement_history) > 50:
                    improvement_history.pop(0)

            # Acceptance criterion
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                best = candidate
                best_score = candidate_score

        return best, best_score

    def improve(points: np.ndarray) -> np.ndarray:
        # Calculate initial min_area to determine difficulty
        initial_min_area = get_smallest_triangle_area(points)
        
        # Get adaptive parameters based on input difficulty
        base_step, T0, T_decay_base, step_decay_base, min_ratio = \
            get_adaptive_parameters(initial_min_area)
        
        # Run multiple annealing chains with different parameter variations
        chains = []
        
        # Chain 1: Primary adaptive chain
        chain1, score1 = run_annealing_chain(
            points.copy(),
            base_step=base_step,
            T0=T0,
            T_decay_base=T_decay_base,
            step_decay_base=step_decay_base,
            min_ratio=min_ratio
        )
        chains.append((chain1, score1))
        
        # Chain 2: Slightly more aggressive variant
        chain2, score2 = run_annealing_chain(
            points.copy(),
            base_step=min(0.08, base_step * 1.2),
            T0=min(0.012, T0 * 1.15),
            T_decay_base=max(0.996, T_decay_base * 0.995),
            step_decay_base=max(0.997, step_decay_base * 0.995),
            min_ratio=min(0.3, min_ratio * 1.1)
        )
        chains.append((chain2, score2))
        
        # Chain 3: Slightly more conservative variant
        chain3, score3 = run_annealing_chain(
            points.copy(),
            base_step=max(0.02, base_step * 0.8),
            T0=max(0.006, T0 * 0.85),
            T_decay_base=min(0.9985, T_decay_base * 1.005),
            step_decay_base=min(0.9995, step_decay_base * 1.005),
            min_ratio=max(0.01, min_ratio * 0.9)
        )
        chains.append((chain3, score3))
        
        # Select the best chain result
        best_chain = max(chains, key=lambda x: x[1])
        return best_chain[0]

    return improve