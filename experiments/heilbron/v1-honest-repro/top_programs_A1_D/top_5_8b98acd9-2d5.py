from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_triangle(p, A, B, C):
        edges = [(A, B), (B, C), (C, A)]
        best_proj = None
        best_dist = float('inf')
        for (X, Y) in edges:
            v = Y - X
            w = p - X
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 < 1e-10:
                proj = X
            else:
                b = c1 / c2
                if b < 0:
                    proj = X
                elif b > 1:
                    proj = Y
                else:
                    proj = X + b * v
            dist = np.linalg.norm(p - proj)
            if dist < best_dist:
                best_dist = dist
                best_proj = proj
        return best_proj

    def line_search(points, idx, direction, current_min, A, B, C, max_step, num_steps=12):
        """Binary search for optimal step size along direction with early stopping."""
        low = 0.0
        high = max_step
        best_step = 0.0
        best_score = current_min
        improvement_threshold = 1e-8
        
        for _ in range(num_steps):
            mid = (low + high) / 2
            candidate = points.copy()
            candidate[idx] = points[idx] + direction * mid
            
            # Project back to triangle if needed
            if not is_inside_triangle(candidate[idx], A, B, C):
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
            
            score = get_smallest_triangle_area(candidate)
            
            if score > best_score:
                improvement = score - best_score
                best_step = mid
                best_score = score
                low = mid
                
                # Early stopping if improvement is small
                if improvement < improvement_threshold:
                    break
            else:
                high = mid
        
        return best_step

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        n = points.shape[0]

        # Adaptive initialization based on insights
        T0 = 0.5 * best_score  # Adaptive temperature initialization
        base_length = np.linalg.norm(B - A)
        step_size0 = 0.03 * base_length  # Increased step size for better exploration
        min_step_size = 0.001 * base_length
        max_iter = 10000
        plateau_length = 1000
        no_improve_count = 0

        rng = np.random.RandomState(42)

        # Polynomial decay parameter (alpha=2 gives faster initial cooling that slows later)
        alpha = 2.0

        for iter in range(max_iter):
            # Polynomial temperature decay: faster initial cooling that gradually slows
            T = T0 * (1 - iter/max_iter)**alpha
            
            current_min = get_smallest_triangle_area(best)
            min_triangles = []
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = best[i], best[j], best[k]
                        area_val = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                        if area_val <= current_min + 1e-10:
                            min_triangles.append((i, j, k))

            # Compute point weights based on triangle participation count
            point_weights = np.zeros(n)
            for tri in min_triangles:
                point_weights[list(tri)] += 1
            
            # Normalize weights for probability selection
            if np.sum(point_weights) > 0:
                point_probs = point_weights / np.sum(point_weights)
            else:
                point_probs = np.ones(n) / n

            # Decouple step size from temperature using square root relationship
            step_size = max(step_size0 * np.sqrt(T / T0), min_step_size)

            # 80% chance to use gradient-based moves when minimal triangles exist
            use_gradient = len(min_triangles) > 0 and rng.random() < 0.8
            
            candidate = best.copy()

            if use_gradient:
                # Accumulate gradients across ALL minimal triangles
                grads = np.zeros((n, 2))
                for (i, j, k) in min_triangles:
                    a, b, c = best[i], best[j], best[k]
                    f = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                    sign_f = 1.0 if f >= 0 else -1.0
                    grad_i = 0.5 * sign_f * np.array([b[1] - c[1], c[0] - b[0]])
                    grad_j = 0.5 * sign_f * np.array([c[1] - a[1], -(c[0] - a[0])])
                    grad_k = 0.5 * sign_f * np.array([-(b[1] - a[1]), b[0] - a[0]])
                    
                    grads[i] += grad_i
                    grads[j] += grad_j
                    grads[k] += grad_k

                # Normalize by number of triangles each point participates in
                # (avoid division by zero)
                for idx in range(n):
                    if point_weights[idx] > 0:
                        grads[idx] /= point_weights[idx]

                # Select points to move based on participation weights
                num_to_move = min(3, len(min_triangles))
                chosen_indices = rng.choice(n, size=num_to_move, p=point_probs, replace=False)

                for idx in chosen_indices:
                    grad_norm = np.linalg.norm(grads[idx])
                    if grad_norm > 1e-8:
                        direction = grads[idx] / grad_norm
                        # Use line search to find optimal step size
                        step = line_search(best, idx, direction, current_min, A, B, C, step_size)
                        candidate[idx] = best[idx] + direction * step
            else:
                # Random perturbations weighted by criticality
                num_perturb = 1 + (len(min_triangles) > 1) + (len(min_triangles) > 3)
                chosen_indices = rng.choice(n, size=num_perturb, p=point_probs, replace=False)

                for idx in chosen_indices:
                    perturbation = rng.uniform(-step_size, step_size, size=2)
                    candidate[idx] = best[idx] + perturbation

            # Project points back into the triangle
            for i in range(n):
                if not is_inside_triangle(candidate[i], A, B, C):
                    candidate[i] = project_to_triangle(candidate[i], A, B, C)

            score = get_smallest_triangle_area(candidate)

            if score > best_score:
                best = candidate
                best_score = score
                no_improve_count = 0
            else:
                delta = score - best_score
                if rng.random() < np.exp(delta / (T + 1e-10)):
                    best = candidate
                    best_score = score
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            if no_improve_count >= plateau_length:
                break

        return best

    return improve