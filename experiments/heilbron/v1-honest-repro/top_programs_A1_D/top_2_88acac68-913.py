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
        closest_edge = None
        
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
                closest_edge = (X, Y)
        
        # Add small inward bias
        if closest_edge is not None:
            edge_vec = closest_edge[1] - closest_edge[0]
            normal = np.array([-edge_vec[1], edge_vec[0]])
            normal = normal / np.linalg.norm(normal)
            # Ensure normal points inward
            mid_point = (closest_edge[0] + closest_edge[1]) / 2
            centroid = (A + B + C) / 3
            if np.dot(normal, centroid - mid_point) < 0:
                normal = -normal
            # Add small inward component
            best_proj += 0.01 * best_dist * normal
            
        return best_proj

    def compute_area_gradient(a, b, c):
        """Compute gradient to increase area of triangle (a,b,c)"""
        f = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        sign_f = 1.0 if f >= 0 else -1.0
        
        # Gradient for point a
        grad_a = 0.5 * sign_f * np.array([b[1] - c[1], c[0] - b[0]])
        # Gradient for point b
        grad_b = 0.5 * sign_f * np.array([c[1] - a[1], a[0] - c[0]])
        # Gradient for point c
        grad_c = 0.5 * sign_f * np.array([a[1] - b[1], b[0] - a[0]])
        
        return grad_a, grad_b, grad_c

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        n = points.shape[0]

        # Derive seed from input configuration hash for diverse exploration paths
        points_hash = hashlib.sha256(points.tobytes()).hexdigest()
        seed = int(points_hash[:8], 16) % (2**32 - 1)
        rng = np.random.RandomState(seed)

        # Adaptive cooling schedule parameters
        T0 = 0.5 * best_score
        T = T0
        # Initial step size proportional to current minimum area
        step_size0 = 0.1 * best_score
        cooling_factor = 0.9999
        max_iter = 10000
        plateau_length = 1000
        no_improve_count = 0

        for _ in range(max_iter):
            current_min = get_smallest_triangle_area(best)
            min_triangles = []
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = best[i], best[j], best[k]
                        area_val = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                        # Use relative tolerance for minimal triangle identification
                        if area_val <= current_min * (1 + 1e-3):
                            min_triangles.append((i, j, k))

            critical_points = set()
            for tri in min_triangles:
                critical_points.update(tri)
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
            step_size = step_size0 * (T / T0)

            # Gradient-based perturbation for critical points
            for idx in chosen_indices:
                is_critical = idx in critical_points
                if is_critical:
                    total_grad = np.zeros(2)
                    for tri in min_triangles:
                        if idx in tri:
                            i, j, k = tri
                            a, b, c = best[i], best[j], best[k]
                            grad_a, grad_b, grad_c = compute_area_gradient(a, b, c)
                            if idx == i:
                                total_grad += grad_a
                            elif idx == j:
                                total_grad += grad_b
                            else:  # idx == k
                                total_grad += grad_c
                    
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
                if rng.random() < np.exp(delta / T):
                    best = candidate
                    best_score = score
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            T *= cooling_factor

            if no_improve_count >= plateau_length:
                break

        return best

    return improve