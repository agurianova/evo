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

    def line_search(points, idx, direction, current_min, A, B, C, max_step, num_steps=8):
        """Binary search for optimal step size along direction."""
        low = 0.0
        high = max_step
        best_step = 0.0
        best_score = current_min
        
        for _ in range(num_steps):
            mid = (low + high) / 2
            candidate = points.copy()
            candidate[idx] = points[idx] + direction * mid
            
            # Project back to triangle if needed
            if not is_inside_triangle(candidate[idx], A, B, C):
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
            
            score = get_smallest_triangle_area(candidate)
            
            if score > best_score:
                best_step = mid
                best_score = score
                low = mid
            else:
                high = mid
        
        return best_step

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        n = points.shape[0]

        # Adaptive initialization based on insights
        T0 = 0.5 * best_score  # Adaptive temperature initialization
        T = T0
        base_length = np.linalg.norm(B - A)
        step_size0 = 0.03 * base_length  # Increased step size for better exploration
        min_step_size = 0.001 * base_length
        max_iter = 10000
        plateau_length = 1000
        no_improve_count = 0

        rng = np.random.RandomState(42)

        for _ in range(max_iter):
            current_min = get_smallest_triangle_area(best)
            min_triangles = []
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = best[i], best[j], best[k]
                        area_val = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                        if area_val <= current_min + 1e-10:
                            min_triangles.append((i, j, k))

            critical_points = set()
            for tri in min_triangles:
                critical_points.update(tri)
            critical_points = list(critical_points)

            # Adaptive perturbation strategy
            num_perturb = 1
            if len(min_triangles) > 3:
                num_perturb = 3
            elif len(min_triangles) > 1:
                num_perturb = 2

            # 70% chance to use gradient-based moves when minimal triangles exist
            use_gradient = len(min_triangles) > 0 and rng.random() < 0.7
            
            candidate = best.copy()
            step_size = max(step_size0 * (T / T0), min_step_size)

            if use_gradient:
                # Select one random minimal triangle to avoid gradient conflicts
                tri_idx = rng.randint(0, len(min_triangles))
                i, j, k = min_triangles[tri_idx]
                
                # Compute gradient for just this triangle
                a, b, c = best[i], best[j], best[k]
                f = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                sign_f = 1.0 if f >= 0 else -1.0
                grad_i = 0.5 * sign_f * np.array([b[1] - c[1], c[0] - b[0]])
                grad_j = 0.5 * sign_f * np.array([c[1] - a[1], -(c[0] - a[0])])
                grad_k = 0.5 * sign_f * np.array([-(b[1] - a[1]), b[0] - a[0]])

                # Apply gradient to 1-3 random points from the triangle to maintain stability
                points_to_move = rng.choice([i, j, k], size=rng.randint(1, 4), replace=False)
                
                for idx in points_to_move:
                    if idx == i:
                        grad = grad_i
                    elif idx == j:
                        grad = grad_j
                    else:
                        grad = grad_k
                    
                    grad_norm = np.linalg.norm(grad)
                    if grad_norm > 1e-8:
                        direction = grad / grad_norm
                        # Use line search to find optimal step size
                        step = line_search(best, idx, direction, current_min, A, B, C, step_size)
                        candidate[idx] = best[idx] + direction * step
            else:
                # Random perturbations for selected points
                if not critical_points:
                    chosen_indices = rng.choice(n, size=num_perturb, replace=False)
                else:
                    num_to_choose = min(num_perturb, len(critical_points))
                    chosen_indices = rng.choice(critical_points, size=num_to_choose, replace=False)
                    if num_to_choose < num_perturb:
                        remaining = list(set(range(n)) - set(critical_points))
                        if remaining:
                            additional = rng.choice(remaining, size=num_perturb - num_to_choose, replace=False)
                            chosen_indices = np.concatenate([chosen_indices, additional])

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
                # Slow cooling when improving
                cooling_factor = 0.999
            else:
                delta = score - best_score
                if rng.random() < np.exp(delta / T):
                    best = candidate
                    best_score = score
                    no_improve_count = 0
                    # Slow cooling when accepting worse solution
                    cooling_factor = 0.999
                else:
                    no_improve_count += 1
                    # Much slower cooling when not improving (0.9995 instead of 0.995)
                    cooling_factor = 0.9995

            T *= cooling_factor

            if no_improve_count >= plateau_length:
                break

        return best

    return improve