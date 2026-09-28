# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(123)

def _g_entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    S = B[0] - A[0]
    H = C[1]

    # Use known optimal row distribution [3,2,3,2,1] with geometry-adapted spacing
    rows = [3, 2, 3, 2, 1]
    
    # Compute horizontal spacing d with safety margin
    d = S / (2 + (S * np.sqrt(3)) / H) * 0.95
    h = (np.sqrt(3) / 2) * d  # Vertical spacing

    points = []
    for i, num_points in enumerate(rows):
        y = i * h
        available_width = S * (1 - y / H)
        total_span = (num_points - 1) * d
        slack = max(0, available_width - total_span)
        
        # Random offset within slack for asymmetry (resistance)
        row_offset = np.random.uniform(0, slack) if slack > 0 else 0.0
        start_x = (S - available_width) / 2 + row_offset
        
        for j in range(num_points):
            x = start_x + j * d
            points.append([x, y])
    
    points = np.array(points)

    # Stronger symmetry-breaking perturbation (5% of d)
    perturbation = np.random.uniform(-0.05 * d, 0.05 * d, size=(11, 2))
    points += perturbation

    # Enforce validity after perturbation
    centroid = (A + B + C) / 3
    for i in range(11):
        if not is_inside_triangle(points[i], A, B, C):
            direction = centroid - points[i]
            points[i] = points[i] + 0.1 * direction
            if not is_inside_triangle(points[i], A, B, C):
                points[i] = centroid

    # Basin hopping optimization
    best_points = points.copy()
    best_min_area = get_smallest_triangle_area(best_points)

    max_basin_hops = 100
    initial_step = 0.05
    step_decay = 0.99

    for hop in range(max_basin_hops):
        # Global perturbation with decaying step size
        step_size = initial_step * (step_decay ** hop)
        candidate = best_points + np.random.uniform(-step_size, step_size, size=(11, 2))

        # Enforce validity for candidate
        for i in range(11):
            if not is_inside_triangle(candidate[i], A, B, C):
                direction = centroid - candidate[i]
                for _ in range(10):
                    candidate[i] += 0.1 * direction
                    if is_inside_triangle(candidate[i], A, B, C):
                        break
                else:
                    candidate[i] = centroid

        # Local search via short simulated annealing
        current = candidate.copy()
        current_min_area = get_smallest_triangle_area(current)
        
        for local_iter in range(1000):
            step = 0.01 * (0.999 ** local_iter)
            T = 0.001 * (0.999 ** local_iter)
            
            idx = np.random.randint(0, 11)
            direction = np.random.uniform(-1, 1, 2)
            norm = np.linalg.norm(direction)
            direction = direction / norm if norm > 1e-5 else np.array([1.0, 0.0])
            
            new_point = current[idx] + step * direction
            if not is_inside_triangle(new_point, A, B, C):
                continue

            new_current = current.copy()
            new_current[idx] = new_point
            new_min_area = get_smallest_triangle_area(new_current)
            delta = new_min_area - current_min_area

            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current = new_current
                current_min_area = new_min_area

        # Update global best if improvement found
        if current_min_area > best_min_area:
            best_points = current
            best_min_area = current_min_area

    return best_points

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