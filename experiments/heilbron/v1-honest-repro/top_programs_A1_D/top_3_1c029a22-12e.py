from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib

def entrypoint():
    A, B, C = get_unit_triangle()
    base_length = np.linalg.norm(B - A)

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
        
        # Apply inward bias only when extremely close to boundary
        if best_dist < 1e-8:
            inward_direction = np.zeros(2)
            for (X, Y) in edges:
                edge_normal = np.array([-(Y[1] - X[1]), Y[0] - X[0]])
                edge_normal = edge_normal / np.linalg.norm(edge_normal)
                inward_direction += edge_normal
            inward_direction = inward_direction / np.linalg.norm(inward_direction)
            best_proj += 0.05 * best_dist * inward_direction
            
        return best_proj

    def compute_area_gradient(a, b, c):
        """Compute gradient to increase area of triangle (a,b,c) with smooth transition"""
        f = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        # Use smooth tanh transition instead of discontinuous sign function
        sign_f = np.tanh(f * 10.0)
        
        # Gradient for point a
        grad_a = 0.5 * sign_f * np.array([b[1] - c[1], c[0] - b[0]])
        # Gradient for point b
        grad_b = 0.5 * sign_f * np.array([c[1] - a[1], a[0] - c[0]])
        # Gradient for point c
        grad_c = 0.5 * sign_f * np.array([a[1] - b[1], b[0] - a[0]])
        
        return grad_a, grad_b, grad_c

    def improve(points: np.ndarray) -> np.ndarray:
        # Derive seed from input config hash to avoid predictability
        config_hash = hash(tuple(map(tuple, points.copy())))
        seed = config_hash % (2**32)
        rng = np.random.RandomState(seed)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        n = points.shape[0]

        # Adaptive cooling schedule parameters
        T0 = 0.5 * best_score
        T = T0
        # Step size proportional to current min area (more adaptive than base length)
        step_size0 = 0.5 * best_score
        # Will be updated dynamically based on improvement rate
        cooling_factor = 0.9995  
        max_iter = max(5000, int(15000 * (0.0365 / max(best_score, 1e-6))))
        plateau_length = max(500, int(0.1 * max_iter))
        no_improve_count = 0
        improvement_count = 0
        total_steps = 0

        for _ in range(max_iter):
            total_steps += 1
            current_min = get_smallest_triangle_area(best)
            min_triangles = []
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = best[i], best[j], best[k]
                        area_val = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                        # Use relative tolerance instead of absolute
                        if area_val <= current_min * 1.01:
                            min_triangles.append((i, j, k, area_val))

            critical_points = set()
            for tri in min_triangles:
                critical_points.update(tri[:3])
            critical_points = list(critical_points)

            # Adaptive perturbation strategy based on minimal triangle count
            if len(min_triangles) <= 3:  # Few minimal triangles
                num_perturb = rng.choice([2, 3], p=[0.3, 0.7])
            else:
                num_perturb = rng.choice([1, 2, 3], p=[0.3, 0.4, 0.3])

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

            candidate = best.copy()
            
            # Calculate gap to theoretical optimum for adaptive step sizing
            gap_to_optimum = 0.0365 - current_min
            step_size = step_size0 * (gap_to_optimum / 0.0365) * (T / T0)

            # Gradient-based perturbation for critical points
            for idx in chosen_indices:
                is_critical = idx in critical_points
                if is_critical:
                    total_grad = np.zeros(2)
                    for tri in min_triangles:
                        i, j, k, area_val = tri
                        if idx in (i, j, k):
                            a, b, c = best[i], best[j], best[k]
                            grad_a, grad_b, grad_c = compute_area_gradient(a, b, c)
                            
                            # Weight gradient by inverse square of area to prioritize smallest triangles
                            weight = 1.0 / (area_val ** 2 + 1e-10)
                            
                            if idx == i:
                                total_grad += weight * grad_a
                            elif idx == j:
                                total_grad += weight * grad_b
                            else:  # idx == k
                                total_grad += weight * grad_c
                    
                    grad_norm = np.linalg.norm(total_grad)
                    if grad_norm > 1e-8:
                        direction = total_grad / grad_norm
                        candidate[idx] += step_size * direction
                    else:
                        # Fallback to random perturbation if gradient is zero
                        perturbation = rng.uniform(-step_size, step_size, size=2)
                        candidate[idx] += perturbation
                else:
                    perturbation = rng.uniform(-step_size, step_size, size=2)
                    candidate[idx] += perturbation

            # Periodic large jumps to escape deep local optima
            if total_steps % 500 == 0 and total_steps > 0:
                idx = rng.randint(0, n)
                direction = rng.uniform(-1, 1, size=2)
                direction = direction / (np.linalg.norm(direction) + 1e-8)
                candidate[idx] += 0.1 * base_length * direction

            for i in range(n):
                if not is_inside_triangle(candidate[i], A, B, C):
                    candidate[i] = project_to_triangle(candidate[i], A, B, C)

            score = get_smallest_triangle_area(candidate)

            if score > best_score:
                best = candidate
                best_score = score
                no_improve_count = 0
                improvement_count += 1
            else:
                delta = score - best_score
                if rng.random() < np.exp(delta / T):
                    best = candidate
                    best_score = score
                    no_improve_count = 0
                    improvement_count += 1
                else:
                    no_improve_count += 1

            # Update cooling factor based on recent improvement rate
            if total_steps % 100 == 0 and total_steps > 0:
                improvement_rate = improvement_count / total_steps
                if improvement_rate > 0.3:  # Frequent improvements
                    cooling_factor = 0.9995
                else:  # Rare improvements
                    cooling_factor = 0.9985
                improvement_count = 0
                total_steps = 0

            T *= cooling_factor

            if no_improve_count >= plateau_length:
                break

        return best

    return improve