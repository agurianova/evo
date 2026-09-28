# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Symmetric barycentric initialization with symmetry-breaking perturbation
    bary_coords = [
        (0.2, 0.2, 0.6),
        (0.2, 0.6, 0.2),
        (0.6, 0.2, 0.2),
        (0.1, 0.1, 0.8),
        (0.1, 0.8, 0.1),
        (0.8, 0.1, 0.1),
        (0.3, 0.3, 0.4),
        (0.3, 0.4, 0.3),
        (0.4, 0.3, 0.3),
        (0.4, 0.4, 0.2),
        (1/3, 1/3, 1/3)
    ]
    
    # Break symmetry via small perturbations
    for i in range(len(bary_coords)):
        u, v, w = bary_coords[i]
        du = np.random.uniform(-0.01, 0.01)
        dv = np.random.uniform(-0.01, 0.01)
        dw = np.random.uniform(-0.01, 0.01)
        u += du
        v += dv
        w += dw
        total = u + v + w
        u /= total
        v /= total
        w /= total
        bary_coords[i] = (u, v, w)

    points = np.array([
        u * A + v * B + w * C
        for u, v, w in bary_coords
    ])

    # Track global best configuration
    best_global = points.copy()
    best_global_min = get_smallest_triangle_area(points)

    # Optimization parameters
    step_size = 0.1
    max_iter = 500
    stagnation_counter = 0
    max_stagnation = 50

    for _ in range(max_iter):
        current_min = get_smallest_triangle_area(points)
        improved = False

        # 1. Weighted multi-triangle gradient moves (top-3)
        triangles = []  # (area2, i, j, k, f)
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    a, b, c = points[i], points[j], points[k]
                    f = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                    area2 = abs(f)
                    triangles.append((area2, i, j, k, f))
        triangles.sort(key=lambda x: x[0])
        top_triangles = triangles[:3]
        min_area2 = top_triangles[0][0]

        # Compute weighted gradients per point
        gradients = np.zeros((11, 2))
        for (area2, i, j, k, f) in top_triangles:
            if f < 0:
                j, k = k, j
                f = -f
            a, b, c = points[i], points[j], points[k]
            grad_a = np.array([b[1]-c[1], c[0]-b[0]])
            grad_b = np.array([c[1]-a[1], a[0]-c[0]])
            grad_c = np.array([a[1]-b[1], b[0]-a[0]])
            weight = 1.0 / (area2 - min_area2 + 1e-5)
            gradients[i] += weight * grad_a
            gradients[j] += weight * grad_b
            gradients[k] += weight * grad_c

        # Try moving points in top triangles
        candidate_points = set()
        for (_, i, j, k, _) in top_triangles:
            candidate_points.update([i, j, k])
            
        for idx in candidate_points:
            if np.linalg.norm(gradients[idx]) < 1e-8:
                continue
            candidate = points.copy()
            direction = gradients[idx] / np.linalg.norm(gradients[idx])
            new_point = candidate[idx] + step_size * direction

            # Boundary handling via line search
            if not is_inside_triangle(new_point, A, B, C):
                t = 1.0
                while t > 1e-5:
                    new_point = points[idx] + t * step_size * direction
                    if is_inside_triangle(new_point, A, B, C):
                        candidate[idx] = new_point
                        break
                    t *= 0.5
                else:
                    continue
            else:
                candidate[idx] = new_point

            new_min = get_smallest_triangle_area(candidate)
            if new_min > current_min:
                points = candidate
                improved = True
                if new_min > best_global_min:
                    best_global = points.copy()
                    best_global_min = new_min
                break

        if improved:
            stagnation_counter = 0
            continue

        # 2. Two-point random moves (fallback with increased coverage)
        pairs = set()
        while len(pairs) < 30:
            i, j = random.sample(range(11), 2)
            if i != j:
                pairs.add((min(i, j), max(i, j)))
        
        for i, j in pairs:
            best_candidate = None
            best_min = current_min
            for _ in range(50):
                angle1 = random.uniform(0, 2 * math.pi)
                angle2 = random.uniform(0, 2 * math.pi)
                candidate = points.copy()
                
                # Move point i
                dx1 = step_size * math.cos(angle1)
                dy1 = step_size * math.sin(angle1)
                candidate[i] = points[i] + [dx1, dy1]
                
                # Move point j
                dx2 = step_size * math.cos(angle2)
                dy2 = step_size * math.sin(angle2)
                candidate[j] = points[j] + [dx2, dy2]

                # Boundary handling via line search for both points
                valid = True
                for idx, pt in zip([i, j], [candidate[i], candidate[j]]):
                    if not is_inside_triangle(pt, A, B, C):
                        t = 1.0
                        while t > 1e-5:
                            new_pt = points[idx] + t * np.array([dx1, dy1] if idx == i else [dx2, dy2])
                            if is_inside_triangle(new_pt, A, B, C):
                                candidate[idx] = new_pt
                                break
                            t *= 0.5
                        else:
                            valid = False
                            break
                if not valid:
                    continue

                new_min = get_smallest_triangle_area(candidate)
                if new_min > best_min:
                    best_min = new_min
                    best_candidate = candidate

            if best_candidate is not None and best_min > current_min:
                points = best_candidate
                improved = True
                if best_min > best_global_min:
                    best_global = points.copy()
                    best_global_min = best_min
                break

        if improved:
            stagnation_counter = 0
            continue

        # 3. Stagnation handling
        step_size *= 0.99
        stagnation_counter += 1

        if step_size < 1e-5 or stagnation_counter >= max_stagnation:
            # Adaptive restart perturbation
            scale = 0.05 * (1 + stagnation_counter / max_stagnation)
            points = best_global.copy()
            for idx in range(11):
                dx = random.uniform(-scale * 1.5197, scale * 1.5197)
                dy = random.uniform(-scale * 1.3161, scale * 1.3161)
                new_point = points[idx] + [dx, dy]
                if is_inside_triangle(new_point, A, B, C):
                    points[idx] = new_point
                else:
                    new_point = points[idx] - [dx, dy]
                    if is_inside_triangle(new_point, A, B, C):
                        points[idx] = new_point
            step_size = 0.1
            stagnation_counter = 0

    return best_global

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def _d_entrypoint():
    A, B, C = get_unit_triangle()
    triangle_side = np.linalg.norm(B - A)  # Unit triangle side length ~1.52

    def compute_min_triangles(pts):
        n = pts.shape[0]
        min_area_val = float('inf')
        min_triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        pts[i,0]*(pts[j,1]-pts[k,1]) +
                        pts[j,0]*(pts[k,1]-pts[i,1]) +
                        pts[k,0]*(pts[i,1]-pts[j,1])
                    )
                    if area < min_area_val - 1e-10:
                        min_area_val = area
                        min_triangles = [(i, j, k)]
                    elif abs(area - min_area_val) < 1e-10:
                        min_triangles.append((i, j, k))
        return min_area_val, min_triangles

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        initial_temp = 0.5
        cooling_rate = 0.99
        max_consecutive_failures = 2000
        reheating_threshold = 1500
        reheating_factor = 0.7
        max_steps = 5000
        step_scale = 0.015  # 1% of unit triangle side length

        consecutive_failures = 0
        step_count = 0
        current_temp = initial_temp

        while consecutive_failures < max_consecutive_failures and step_count < max_steps:
            factor = cooling_rate ** step_count
            step_count += 1

            # 10% chance to perturb a random point not in minimal triangles
            if np.random.rand() < 0.1:
                all_indices = set(range(11))
                _, min_triangles = compute_min_triangles(current)
                min_indices = set()
                for tri in min_triangles:
                    min_indices.update(tri)
                candidate_indices = list(all_indices - min_indices)
                
                if candidate_indices:
                    idx = np.random.choice(candidate_indices)
                    candidate = current.copy()
                    # Apply Gaussian perturbation scaled by current progress
                    perturbation = np.random.normal(0, 0.005 * (1 + current_score), 2)
                    candidate[idx] += perturbation
                    
                    if is_inside_triangle(candidate, A, B, C):
                        new_score = get_smallest_triangle_area(candidate)
                        if new_score > current_score:
                            current = candidate
                            current_score = new_score
                            consecutive_failures = 0
                            if new_score > best_score:
                                best = candidate
                                best_score = new_score
                        else:
                            consecutive_failures += 1
                        continue

            min_area_val, min_triangles = compute_min_triangles(current)
            if not min_triangles:
                break
            
            tri_idx = np.random.randint(0, len(min_triangles))
            i0, i1, i2 = min_triangles[tri_idx]

            p0, p1, p2 = current[i0], current[i1], current[i2]
            d01 = np.linalg.norm(p0 - p1)
            d02 = np.linalg.norm(p0 - p2)
            d12 = np.linalg.norm(p1 - p2)
            sides = [(d01, (i0, i1), i2), (d02, (i0, i2), i1), (d12, (i1, i2), i0)]
            sides.sort(key=lambda x: x[0], reverse=True)
            base_length, (base_i, base_j), apex_i = sides[0]
            min_side = min(d01, d02, d12)

            base_vec = current[base_j] - current[base_i]
            base_norm = np.linalg.norm(base_vec)
            if base_norm < 1e-10:
                consecutive_failures += 1
                continue

            base_unit = base_vec / base_norm
            apex = current[apex_i]
            vec_apex_to_base_i = apex - current[base_i]
            proj = np.dot(vec_apex_to_base_i, base_unit)
            foot = current[base_i] + proj * base_unit
            height_vec = apex - foot
            height = np.linalg.norm(height_vec)
            if height < 1e-10:
                consecutive_failures += 1
                continue

            height_unit = height_vec / height
            
            # Use fixed scale relative to unit triangle instead of min_side
            step = step_scale * factor

            # Adapt move probability based on triangle aspect ratio
            aspect_ratio = height / base_length
            move_probability = 0.9 if aspect_ratio < 0.2 else 0.7
            
            if np.random.rand() < move_probability:
                candidate = current.copy()
                candidate[apex_i] = apex + step * height_unit

                if not is_inside_triangle(candidate, A, B, C):
                    consecutive_failures += 1
                    continue
            else:
                M = (current[base_i] + current[base_j]) / 2
                disp_i = current[base_i] - M
                disp_j = current[base_j] - M
                
                disp_i_norm = np.linalg.norm(disp_i)
                disp_j_norm = np.linalg.norm(disp_j)
                if disp_i_norm < 1e-10 or disp_j_norm < 1e-10:
                    consecutive_failures += 1
                    continue
                
                new_base_i = current[base_i] + step * (disp_i / disp_i_norm)
                new_base_j = current[base_j] + step * (disp_j / disp_j_norm)
                
                candidate = current.copy()
                candidate[base_i] = new_base_i
                candidate[base_j] = new_base_j

                if not (is_inside_triangle(new_base_i.reshape(1,2), A, B, C) and 
                        is_inside_triangle(new_base_j.reshape(1,2), A, B, C)):
                    consecutive_failures += 1
                    continue

            new_score = get_smallest_triangle_area(candidate)
            
            # Adaptive temperature based on current progress
            current_temp = initial_temp * factor * (1 + current_score)

            if new_score > current_score:
                current = candidate
                current_score = new_score
                consecutive_failures = 0
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
            else:
                delta = current_score - new_score
                if np.random.rand() < np.exp(-delta / current_temp):
                    current = candidate
                    current_score = new_score
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1

            # Reheating mechanism for escaping deep local minima
            if consecutive_failures >= reheating_threshold:
                current_temp = initial_temp * reheating_factor
                step_scale *= 1.2  # Slightly increase step size
                consecutive_failures = 0

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)