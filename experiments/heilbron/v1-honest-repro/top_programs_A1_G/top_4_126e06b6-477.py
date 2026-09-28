# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def _g_entrypoint():
    base_seed = 42
    best_points = None
    best_min_area = -1.0

    for run in range(20):  # Increased from 5 to 20 trials
        np.random.seed(base_seed + run)
        random.seed(base_seed + run)

        tri = get_unit_triangle()
        A, B, C = tri

        points = []
        for _ in range(11):
            u = random.random()
            v = random.random() * (1 - u)
            w = 1 - u - v
            p = u * A + v * B + w * C
            points.append(p)
        points = np.array(points)

        # Simulated Annealing with boundary rejection
        T = 0.001  # Reverted from 0.01 to 0.001 based on historical evidence
        step_size_sa = 0.1
        current_min = get_smallest_triangle_area(points)
        for _ in range(10000):
            i = random.randint(0, 10)
            old_point = points[i].copy()
            move = np.random.uniform(-step_size_sa, step_size_sa, 2)
            new_point = old_point + move
            
            # Reject out-of-bounds moves instead of projecting
            if is_inside_triangle(new_point, A, B, C):
                points[i] = new_point
                new_min = get_smallest_triangle_area(points)
                if new_min > current_min:
                    current_min = new_min
                else:
                    delta = new_min - current_min
                    if random.random() < np.exp(delta / T):
                        current_min = new_min
                    else:
                        points[i] = old_point
            # Else: skip invalid move (points[i] remains old_point)
            T *= 0.9995

        # Gradient Descent with multiple improvements
        step_size_gd = 0.001  # Reduced from 0.01
        current_min = get_smallest_triangle_area(points)
        no_improve_count_conv = 0  # For convergence
        no_improve_count_pert = 0  # For perturbation restarts
        
        for _ in range(1000):
            current_min_prev = current_min
            grads = np.zeros((11, 2))
            n = 11
            
            # Relative tolerance for critical triangles
            tol = 1e-5 * current_min_prev
            critical_count = 0
            
            # Compute normalized gradients for critical triangles
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = points[i], points[j], points[k]
                        f = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                        area_val = 0.5 * abs(f)
                        if area_val <= current_min_prev + tol and area_val > 0:
                            sign_f = 1.0 if f >= 0 else -1.0
                            grad_i = 0.5 * sign_f * np.array([b[1] - c[1], c[0] - b[0]])
                            grad_j = 0.5 * sign_f * np.array([c[1] - a[1], -(c[0] - a[0])])
                            grad_k = 0.5 * sign_f * np.array([-(b[1] - a[1]), b[0] - a[0]])
                            
                            # Normalize the 6D gradient vector for this triangle
                            g = np.hstack((grad_i, grad_j, grad_k))
                            g_norm = np.linalg.norm(g)
                            if g_norm > 1e-10:
                                g_normalized = g / g_norm
                                grad_i_norm = g_normalized[0:2]
                                grad_j_norm = g_normalized[2:4]
                                grad_k_norm = g_normalized[4:6]
                                grads[i] += grad_i_norm
                                grads[j] += grad_j_norm
                                grads[k] += grad_k_norm
                                critical_count += 1

            # Normalize by number of critical triangles
            if critical_count > 0:
                grads /= critical_count

            # Update points with boundary rejection
            old_points = points.copy()
            for i in range(11):
                grad_norm = np.linalg.norm(grads[i])
                if grad_norm > 1e-8:
                    direction = grads[i] / grad_norm
                    points[i] = old_points[i] + step_size_gd * direction
                    # Reject out-of-bounds moves
                    if not is_inside_triangle(points[i], A, B, C):
                        points[i] = old_points[i]

            current_min = get_smallest_triangle_area(points)
            improvement = current_min - current_min_prev

            # Update counters for convergence and perturbation
            if improvement > 1e-8:
                no_improve_count_conv = 0
                no_improve_count_pert = 0
            else:
                no_improve_count_conv += 1
                no_improve_count_pert += 1

            # Early stopping for convergence
            if no_improve_count_conv >= 50:
                break

            # Perturbation restart for shallow traps
            if no_improve_count_pert >= 100:
                i = random.randint(0, 10)
                old_point = points[i].copy()
                move = np.random.uniform(-0.01, 0.01, 2)
                new_point = old_point + move
                if is_inside_triangle(new_point, A, B, C):
                    points[i] = new_point
                    min_after_pert = get_smallest_triangle_area(points)
                    if min_after_pert > current_min:
                        current_min = min_after_pert
                        no_improve_count_conv = 0
                        no_improve_count_pert = 0
                    else:
                        no_improve_count_pert = 0
                else:
                    no_improve_count_pert = 0

            step_size_gd *= 0.99  # Faster decay from 0.999

        min_area = get_smallest_triangle_area(points)
        if min_area > best_min_area:
            best_min_area = min_area
            best_points = points.copy()

    return best_points

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib

def _d_entrypoint():
    A, B, C = get_unit_triangle()
    base_length = np.linalg.norm(B - A)

    def barycentric_coordinates(p, A, B, C):
        """Convert Cartesian to barycentric coordinates"""
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
            return np.array([1.0/3, 1.0/3, 1.0/3])  # Fallback to centroid
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w
        return np.array([u, v, w])

    def project_to_triangle_barycentric(p, A, B, C):
        """Project point to triangle using barycentric coordinates"""
        b = barycentric_coordinates(p, A, B, C)
        
        # Clip negative coordinates to zero
        b = np.maximum(b, 0)
        b /= np.sum(b)  # Renormalize to ensure sum to 1
        
        # Project back to Cartesian
        return b[0] * A + b[1] * B + b[2] * C

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
        # Base step size proportional to current min area
        step_size0 = 0.5 * best_score
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
            triangle_areas = []
            
            # Compute all triangle areas and identify minimal ones
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = best[i], best[j], best[k]
                        area_val = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                        # Use relative tolerance that tightens as current_min decreases
                        tolerance = 1.0 + 0.01 * (current_min / 0.0365)
                        if area_val <= current_min * tolerance:
                            min_triangles.append((i, j, k))
                            triangle_areas.append(area_val)

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
            
            # Calculate gap to theoretical optimum for adaptive step sizing
            gap_to_optimum = 0.0365 - current_min
            step_size = step_size0 * (gap_to_optimum / 0.0365) * (T / T0)

            # Gradient-based perturbation for critical points with inverse-area weighting
            for idx in chosen_indices:
                is_critical = idx in critical_points
                if is_critical:
                    total_grad = np.zeros(2)
                    for tri_idx, tri in enumerate(min_triangles):
                        if idx in tri:
                            i, j, k = tri
                            a, b, c = best[i], best[j], best[k]
                            area_val = triangle_areas[tri_idx]
                            
                            # Weight gradient by inverse area to prioritize smallest triangles
                            weight = 1.0 / max(area_val, 1e-10)
                            grad_a, grad_b, grad_c = compute_area_gradient(a, b, c)
                            grad_a *= weight
                            grad_b *= weight
                            grad_c *= weight
                            
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

            # Boundary handling using barycentric projection
            for i in range(n):
                if not is_inside_triangle(candidate[i], A, B, C):
                    candidate[i] = project_to_triangle_barycentric(candidate[i], A, B, C)

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

            # Update cooling factor based on improvement rate AND proximity to optimum
            if total_steps % 100 == 0 and total_steps > 0:
                improvement_rate = improvement_count / total_steps
                gap_to_optimum = 0.0365 - best_score
                
                # More exploratory when far from optimum
                if gap_to_optimum > 0.01:
                    if improvement_rate > 0.2:
                        cooling_factor = 0.999
                    else:
                        cooling_factor = 0.998
                # More exploitative when close to optimum
                else:
                    if improvement_rate > 0.1:
                        cooling_factor = 0.9995
                    else:
                        cooling_factor = 0.9985
                
                improvement_count = 0
                total_steps = 0

            T *= cooling_factor

            if no_improve_count >= plateau_length:
                break

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)