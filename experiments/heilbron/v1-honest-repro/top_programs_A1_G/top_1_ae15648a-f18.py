# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random


def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri

    # Generate symmetric patterns (sum to 11 with reflection symmetry)
    patterns = [
        [1, 3, 3, 3, 1],  # Classic Heilbronn pattern
        [2, 2, 3, 2, 2],  # Balanced symmetric pattern
        [1, 2, 5, 2, 1]   # Alternative symmetric pattern
    ]

    def generate_base_lattice(rows):
        total_rows = len(rows)
        points = []
        counterpart = np.zeros(11, dtype=int)
        total = 0
        for i, n in enumerate(rows):
            v = (i + 0.5) / total_rows
            start = total
            for j in range(n):
                # Symmetric barycentric coordinate generation
                s = (j - (n-1)/2.0) / n
                u = (1 - v) * (0.5 + s)
                w = (1 - v) * (0.5 - s)
                P = w * A + u * B + v * C
                points.append(P)
                idx = start + j
                counterpart[idx] = start + (n-1 - j)
            total += n
        return np.array(points), counterpart

    def optimize(config, counterpart, max_iter=1000):
        current_points = config.copy()
        current_min = get_smallest_triangle_area(current_points)
        step_size = 0.1
        improvement_history = []
        
        # Precompute symmetry axis properties
        M = (A + B) / 2
        V = C - M  # Axis direction vector

        # Identify symmetry elements
        axis_points = [i for i in range(11) if counterpart[i] == i]
        pairs = []
        for i in range(11):
            if i < counterpart[i]:
                pairs.append((i, counterpart[i]))

        for iter in range(max_iter):
            best_improvement = 0
            best_candidate = None

            # Single-point moves (axis points only)
            for point_idx in axis_points:
                for _ in range(16):
                    angle = random.uniform(0, 2 * np.pi)
                    d = np.array([np.cos(angle), np.sin(angle)]) * step_size
                    # Project to symmetry axis
                    proj = np.dot(d, V) / np.dot(V, V) * V
                    candidate_point = current_points[point_idx] + proj
                    if not is_inside_triangle(candidate_point, A, B, C):
                        continue
                    candidate_config = current_points.copy()
                    candidate_config[point_idx] = candidate_point
                    candidate_min = get_smallest_triangle_area(candidate_config)
                    if candidate_min > current_min:
                        improvement = candidate_min - current_min
                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_candidate = ('single', point_idx, candidate_point, candidate_min)

            # Two-point moves (symmetric pairs)
            if best_improvement == 0 and pairs:
                for i, j in pairs:
                    for _ in range(16):
                        angle = random.uniform(0, 2 * np.pi)
                        d = np.array([np.cos(angle), np.sin(angle)]) * step_size
                        candidate_i = current_points[i] + d
                        # Compute symmetric displacement for counterpart
                        d_sym = 2 * (np.dot(d, V) / np.dot(V, V)) * V - d
                        candidate_j = current_points[j] + d_sym
                        if not (is_inside_triangle(candidate_i, A, B, C) and 
                                is_inside_triangle(candidate_j, A, B, C)):
                            continue
                        candidate_config = current_points.copy()
                        candidate_config[i] = candidate_i
                        candidate_config[j] = candidate_j
                        candidate_min = get_smallest_triangle_area(candidate_config)
                        if candidate_min > current_min:
                            improvement = candidate_min - current_min
                            if improvement > best_improvement:
                                best_improvement = improvement
                                best_candidate = ('two', i, j, candidate_i, candidate_j, candidate_min)

            # Three-point coordinated moves
            if best_improvement == 0 and axis_points and pairs:
                for _ in range(5):
                    i = random.choice(axis_points)
                    j, k = random.choice(pairs)
                    
                    # Axis point displacement
                    angle1 = random.uniform(0, 2 * np.pi)
                    d1 = np.array([np.cos(angle1), np.sin(angle1)]) * step_size
                    proj1 = np.dot(d1, V) / np.dot(V, V) * V
                    candidate_i = current_points[i] + proj1
                    
                    # Symmetric pair displacement
                    angle2 = random.uniform(0, 2 * np.pi)
                    d2 = np.array([np.cos(angle2), np.sin(angle2)]) * step_size
                    d2_sym = 2 * (np.dot(d2, V) / np.dot(V, V)) * V - d2
                    candidate_j = current_points[j] + d2
                    candidate_k = current_points[k] + d2_sym
                    
                    if not (is_inside_triangle(candidate_i, A, B, C) and 
                            is_inside_triangle(candidate_j, A, B, C) and
                            is_inside_triangle(candidate_k, A, B, C)):
                        continue
                    
                    candidate_config = current_points.copy()
                    candidate_config[i] = candidate_i
                    candidate_config[j] = candidate_j
                    candidate_config[k] = candidate_k
                    candidate_min = get_smallest_triangle_area(candidate_config)
                    if candidate_min > current_min:
                        improvement = candidate_min - current_min
                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_candidate = ('three', i, j, k, candidate_i, candidate_j, candidate_k, candidate_min)

            # Apply best improvement
            if best_improvement > 0:
                if best_candidate[0] == 'single':
                    _, idx, pt, current_min = best_candidate
                    current_points[idx] = pt
                elif best_candidate[0] == 'two':
                    _, i, j, pt_i, pt_j, current_min = best_candidate
                    current_points[i] = pt_i
                    current_points[j] = pt_j
                else:
                    _, i, j, k, pt_i, pt_j, pt_k, current_min = best_candidate
                    current_points[i] = pt_i
                    current_points[j] = pt_j
                    current_points[k] = pt_k
                improvement_history.append(best_improvement)
            else:
                improvement_history.append(0.0)

            # Adaptive step size
            if len(improvement_history) > 10:
                improvement_history.pop(0)
            if len(improvement_history) == 10:
                avg_improve = sum(improvement_history) / 10.0
                if avg_improve < 1e-7:  # Tightened threshold
                    step_size = max(step_size * 0.9, 0.001)

        return current_points

    best_config = None
    best_min = -1
    # 20 restarts with symmetric patterns
    for restart in range(20):
        np.random.seed(42 + restart)
        random.seed(42 + restart)
        
        rows = patterns[restart % len(patterns)]
        config, counterpart = generate_base_lattice(rows)
        
        # Validate initial configuration
        for i in range(11):
            assert is_inside_triangle(config[i], A, B, C), f"Initial point {i} outside"

        config = optimize(config, counterpart, max_iter=1000)
        min_area_val = get_smallest_triangle_area(config)
        if min_area_val > best_min:
            best_min = min_area_val
            best_config = config

    return best_config

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