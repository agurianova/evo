# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random


def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri

    # Generate 50 random asymmetric patterns (compositions of 11 into 5 positive integers)
    np.random.seed(0)
    patterns = []
    for _ in range(50):
        positions = [0] + sorted(np.random.choice(range(1, 11), 4, replace=False)) + [11]
        parts = [positions[i+1] - positions[i] for i in range(5)]
        patterns.append(parts)

    def generate_base_lattice(rows):
        total_rows = len(rows)
        points = []
        for i, n in enumerate(rows):
            v = (i + 0.5) / total_rows
            for j in range(n):
                if n == 1:
                    u = (1 - v) / 2
                else:
                    u = (1 - v) * (j + 0.5) / n
                w = 1 - u - v
                base_bary = np.array([w, u, v])
                # Add barycentric noise and normalize (reduced from 0.05 to 0.02)
                noise = np.random.normal(0, 0.02, 3)
                new_bary = base_bary + noise
                new_bary = np.maximum(new_bary, 0)
                new_bary /= new_bary.sum()
                w_new, u_new, v_new = new_bary
                P = w_new * A + u_new * B + v_new * C
                points.append(P)
        return np.array(points)

    def optimize(config, max_iter):
        current_points = config.copy()
        current_min = get_smallest_triangle_area(current_points)
        step_size = 0.1
        improvement_history = []

        for iter in range(max_iter):
            best_improvement = 0
            best_candidate = None  # Will store (type, data)

            # Single-point moves: 8 random isotropic directions
            for point_idx in range(11):
                for _ in range(8):
                    angle = random.uniform(0, 2 * np.pi)
                    dx = np.cos(angle)
                    dy = np.sin(angle)
                    step = np.array([dx, dy]) * step_size
                    candidate_point = current_points[point_idx] + step
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

            # Two-point moves with independent random directions
            if best_improvement == 0:
                for _ in range(10):  # 10 random pairs
                    i, j = np.random.choice(11, 2, replace=False)
                    for _ in range(8):  # 8 random direction pairs
                        angle1 = random.uniform(0, 2 * np.pi)
                        angle2 = random.uniform(0, 2 * np.pi)
                        step1 = np.array([np.cos(angle1), np.sin(angle1)]) * step_size
                        step2 = np.array([np.cos(angle2), np.sin(angle2)]) * step_size
                        candidate_i = current_points[i] + step1
                        candidate_j = current_points[j] + step2
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

            # Three-point moves with constrained directions (new)
            if best_improvement == 0:
                for _ in range(5):  # 5 random triplets
                    i, j, k = np.random.choice(11, 3, replace=False)
                    for _ in range(4):  # 4 constrained direction sets
                        # Try coordinated moves: all points move in similar directions
                        base_angle = random.uniform(0, 2 * np.pi)
                        spread = 0.2  # Keep directions somewhat aligned
                        
                        angle1 = base_angle + random.uniform(-spread, spread)
                        angle2 = base_angle + random.uniform(-spread, spread)
                        angle3 = base_angle + random.uniform(-spread, spread)
                        
                        step1 = np.array([np.cos(angle1), np.sin(angle1)]) * step_size * 0.7
                        step2 = np.array([np.cos(angle2), np.sin(angle2)]) * step_size * 0.7
                        step3 = np.array([np.cos(angle3), np.sin(angle3)]) * step_size * 0.7
                        
                        candidate_i = current_points[i] + step1
                        candidate_j = current_points[j] + step2
                        candidate_k = current_points[k] + step3
                        
                        if (is_inside_triangle(candidate_i, A, B, C) and 
                            is_inside_triangle(candidate_j, A, B, C) and
                            is_inside_triangle(candidate_k, A, B, C)):
                            
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

            # Apply best improvement if found
            if best_improvement > 0:
                if best_candidate[0] == 'single':
                    _, idx, pt, current_min = best_candidate
                    current_points[idx] = pt
                elif best_candidate[0] == 'two':
                    _, i, j, pt_i, pt_j, current_min = best_candidate
                    current_points[i] = pt_i
                    current_points[j] = pt_j
                else:  # 'three'
                    _, i, j, k, pt_i, pt_j, pt_k, current_min = best_candidate
                    current_points[i] = pt_i
                    current_points[j] = pt_j
                    current_points[k] = pt_k
                improvement_history.append(best_improvement)
            else:
                improvement_history.append(0.0)

            # Maintain improvement history and adapt step size
            if len(improvement_history) > 10:
                improvement_history.pop(0)
            
            if len(improvement_history) == 10:
                avg_improve = sum(improvement_history) / 10.0
                if avg_improve < 1e-5:
                    step_size = max(step_size * 0.9, 0.001)

        # Local optima verification (new)
        is_local_optimum = False
        verification_attempts = 0
        while not is_local_optimum and verification_attempts < 10:
            improvement_found = False
            for _ in range(50):  # Try 50 random small perturbations
                perturbed_config = current_points.copy()
                for i in range(11):
                    if random.random() < 0.3:  # Perturb ~30% of points
                        perturbation = np.random.normal(0, 0.005, 2)
                        perturbed_point = perturbed_config[i] + perturbation
                        if is_inside_triangle(perturbed_point, A, B, C):
                            perturbed_config[i] = perturbed_point
                
                perturbed_min = get_smallest_triangle_area(perturbed_config)
                if perturbed_min > current_min:
                    # Found an improvement, continue optimizing from this point
                    current_points = perturbed_config
                    current_min = perturbed_min
                    improvement_found = True
                    break
            
            if not improvement_found:
                is_local_optimum = True
            verification_attempts += 1

        return current_points

    best_config = None
    best_min = -1
    # 20 restarts with per-restart seeding
    for restart in range(20):
        np.random.seed(42 + restart)
        random.seed(42 + restart)
        
        # Cycle through patterns
        rows = patterns[restart % len(patterns)]
        config = generate_base_lattice(rows)
        
        # Validate all points (should be inside due to barycentric noise)
        for i in range(11):
            assert is_inside_triangle(config[i], A, B, C), f"Point {i} outside after barycentric noise"

        config = optimize(config, max_iter=1000)  # Increased from 500 to 1000
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