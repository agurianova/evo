# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def _g_entrypoint():
    base_seed = 42
    best_points = None
    best_min_area = -1.0

    for run in range(10):
        np.random.seed(base_seed + run)
        random.seed(base_seed + run)

        tri = get_unit_triangle()
        A, B, C = tri

        def project(p):
            if is_inside_triangle(p, A, B, C):
                return p
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

        points = []
        for _ in range(11):
            u = random.random()
            v = random.random() * (1 - u)
            w = 1 - u - v
            p = u * A + v * B + w * C
            points.append(p)
        points = np.array(points)

        current_min = get_smallest_triangle_area(points)
        T = 0.001
        step_size_sa = 0.2
        for _ in range(10000):
            i = random.randint(0, 10)
            old_point = points[i].copy()
            move = np.random.uniform(-step_size_sa, step_size_sa, 2)
            new_point = old_point + move
            new_point = project(new_point)
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
            T *= 0.9995

        step_size_gd = 0.01
        for _ in range(2000):
            current_min = get_smallest_triangle_area(points)
            grads = np.zeros((11, 2))
            n = 11
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = points[i], points[j], points[k]
                        f = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                        area_val = 0.5 * abs(f)
                        if area_val <= current_min + 1e-10:
                            sign_f = 1.0 if f >= 0 else -1.0
                            grad_i = 0.5 * sign_f * np.array([b[1] - c[1], c[0] - b[0]])
                            grad_j = 0.5 * sign_f * np.array([c[1] - a[1], -(c[0] - a[0])])
                            grad_k = 0.5 * sign_f * np.array([-(b[1] - a[1]), b[0] - a[0]])
                            grads[i] += grad_i
                            grads[j] += grad_j
                            grads[k] += grad_k

            old_points = points.copy()
            for i in range(11):
                grad_norm = np.linalg.norm(grads[i])
                if grad_norm > 1e-8:
                    direction = grads[i] / grad_norm
                    points[i] = old_points[i] + step_size_gd * direction
                    points[i] = project(points[i])
            step_size_gd *= 0.9995

        # Multi-point local search
        current_min = get_smallest_triangle_area(points)
        for _ in range(100):
            num_perturb = random.choice([2, 3])
            indices = random.sample(range(11), num_perturb)
            new_points = points.copy()
            for idx in indices:
                move = np.random.uniform(-0.05, 0.05, 2)
                new_point = new_points[idx] + move
                new_points[idx] = project(new_point)
            new_min = get_smallest_triangle_area(new_points)
            if new_min > current_min:
                points = new_points
                current_min = new_min

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

    def project_to_triangle(p, A, B, C, inward_bias=0.05):
        """Project point to triangle with small inward bias to avoid boundary clustering"""
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
        
        # Add small inward bias to prevent clustering on boundary
        if best_dist < 1e-5:  # Very close to boundary
            # Compute inward normal (simplified for equilateral triangle)
            edge_vec = Y - X
            normal = np.array([-edge_vec[1], edge_vec[0]])  # Perpendicular
            normal = normal / np.linalg.norm(normal) * inward_bias
            best_proj += normal
        
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

        # Derive seed from input configuration hash for diverse exploration
        points_hash = hashlib.md5(points.tobytes()).hexdigest()
        seed = int(points_hash, 16) % 1000000
        rng = np.random.RandomState(seed)

        # Adaptive cooling schedule parameters
        T0 = 0.5 * best_score
        T = T0
        # Step size proportional to current minimal area
        step_size0 = 0.1 * best_score
        cooling_factor = 0.9999
        max_iter = 10000
        plateau_length = 1000
        no_improve_count = 0

        # Track improvement history for adaptive cooling
        improvement_history = []
        improvement_window = 100

        for _ in range(max_iter):
            current_min = get_smallest_triangle_area(best)
            min_triangles = []
            
            # Use relative tolerance with absolute floor
            tolerance = max(1e-10, current_min * 0.01)
            
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = best[i], best[j], best[k]
                        area_val = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                        if area_val <= current_min + tolerance:
                            min_triangles.append((i, j, k))

            critical_points = set()
            for tri in min_triangles:
                critical_points.update(tri)
            critical_points = list(critical_points)

            # Adaptive perturbation strategy based on minimal triangle count
            if len(min_triangles) <= 3:  # Few minimal triangles
                num_perturb_probs = [0.1, 0.3, 0.6]  # Higher chance of perturbing 3 points
            else:
                num_perturb_probs = [0.3, 0.4, 0.3]  # Original distribution

            num_perturb = rng.choice([1, 2, 3], p=num_perturb_probs)

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
                improvement = score - best_score
                improvement_history.append(improvement)
                if len(improvement_history) > improvement_window:
                    improvement_history.pop(0)
                
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

            # Adaptive cooling based on improvement rate
            if len(improvement_history) > 10:
                avg_improvement = np.mean(improvement_history)
                if avg_improvement > 0.0001:
                    adaptive_cooling = 0.9995  # Slower cooling when progress is good
                else:
                    adaptive_cooling = 0.99995  # Faster cooling when progress is slow
            else:
                adaptive_cooling = cooling_factor
            
            T *= adaptive_cooling

            if no_improve_count >= plateau_length:
                break

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)