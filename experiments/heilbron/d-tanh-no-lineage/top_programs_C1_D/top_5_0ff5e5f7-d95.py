from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def project_point(p):
        """Project point to nearest location on/inside triangle boundary."""
        if is_inside_triangle(np.array([p]), A, B, C):
            return p
        
        edges = [(A, B), (B, C), (C, A)]
        min_dist = np.inf
        best_proj = None
        
        for v1, v2 in edges:
            edge_vec = v2 - v1
            v = p - v1
            t = np.dot(v, edge_vec) / (np.dot(edge_vec, edge_vec) + 1e-10)
            t = np.clip(t, 0, 1)
            proj = v1 + t * edge_vec
            dist = np.linalg.norm(p - proj)
            if dist < min_dist:
                min_dist = dist
                best_proj = proj
        return best_proj

    def improve(points: np.ndarray) -> np.ndarray:
        # Initialize with input configuration
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        last_improve = 0
        
        T0 = 0.1
        base_step = 0.1
        max_iter = 200
        early_stop_patience = 50
        cooling_rate = 0.95

        for i in range(max_iter):
            # Check early stopping
            if i - last_improve > early_stop_patience:
                break

            # Update temperature
            T = T0 * (cooling_rate ** i)
            
            # Identify critical points (vertices of minimal-area triangles)
            min_area_val = get_smallest_triangle_area(current)
            critical_points = set()
            tol = 1e-6
            for i1 in range(11):
                for i2 in range(i1+1, 11):
                    for i3 in range(i2+1, 11):
                        x1, y1 = current[i1]
                        x2, y2 = current[i2]
                        x3, y3 = current[i3]
                        area = 0.5 * abs((x2 - x1)*(y3 - y1) - (x3 - x1)*(y2 - y1))
                        if abs(area - min_area_val) < tol:
                            critical_points.update([i1, i2, i3])
            
            # Setup biased point selection
            weights = np.ones(11)
            if critical_points:
                weights[list(critical_points)] = 10.0
            weights /= weights.sum()
            
            # Generate candidate: perturb 2-3 points
            k = np.random.choice([2, 3])
            idxs = np.random.choice(11, size=k, replace=False, p=weights)
            candidate = current.copy()
            step_size = base_step * np.sqrt(T / T0)
            
            for idx in idxs:
                candidate[idx] += np.random.normal(0, step_size, 2)
                # Project to boundary if needed
                candidate[idx] = project_point(candidate[idx])

            # Evaluate candidate
            candidate_score = get_smallest_triangle_area(candidate)
            
            # Update best solution if improvement found
            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                last_improve = i

            # Metropolis acceptance for current state
            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / (T + 1e-10)):
                current = candidate
                current_score = candidate_score

        # Local search refinement: optimize each point sequentially via 5x5 grid
        local_step = 0.01
        grid_size = 5
        config = best.copy()
        current_score = best_score
        for idx in range(11):
            original = config[idx].copy()
            best_candidate = config.copy()
            best_candidate_score = current_score
            for dx in np.linspace(-local_step, local_step, grid_size):
                for dy in np.linspace(-local_step, local_step, grid_size):
                    candidate = config.copy()
                    candidate[idx] = original + np.array([dx, dy])
                    candidate[idx] = project_point(candidate[idx])
                    candidate_score = get_smallest_triangle_area(candidate)
                    if candidate_score > best_candidate_score:
                        best_candidate = candidate
                        best_candidate_score = candidate_score
            if best_candidate_score > current_score:
                config = best_candidate
                current_score = best_candidate_score
        
        if current_score > best_score:
            best = config
            best_score = current_score

        return best

    return improve