from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

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

        initial_temp = 0.1
        cooling_rate = 0.95
        max_consecutive_failures = 500
        max_steps = 5000

        consecutive_failures = 0
        step_count = 0

        while consecutive_failures < max_consecutive_failures and step_count < max_steps:
            factor = cooling_rate ** step_count
            step_count += 1

            min_area_val, min_triangles = compute_min_triangles(current)
            
            # Sort minimal triangles by height (smallest height first)
            min_triangles_with_height = []
            for tri in min_triangles:
                i0, i1, i2 = tri
                p0, p1, p2 = current[i0], current[i1], current[i2]
                d01 = np.linalg.norm(p0 - p1)
                d02 = np.linalg.norm(p0 - p2)
                d12 = np.linalg.norm(p1 - p2)
                base_length = max(d01, d02, d12)
                height = 2 * min_area_val / base_length
                min_triangles_with_height.append((height, tri))
            min_triangles_with_height.sort(key=lambda x: x[0])
            min_triangles_sorted = [tri for (_, tri) in min_triangles_with_height]
            i0, i1, i2 = min_triangles_sorted[0]

            # Recompute sides to identify base (longest side) and apex
            d01 = np.linalg.norm(current[i0] - current[i1])
            d02 = np.linalg.norm(current[i0] - current[i2])
            d12 = np.linalg.norm(current[i1] - current[i2])
            sides = [(d01, i0, i1), (d02, i0, i2), (d12, i1, i2)]
            sides.sort(key=lambda x: x[0], reverse=True)
            base_length, base_i, base_j = sides[0]
            apex_i = [i for i in [i0, i1, i2] if i != base_i and i != base_j][0]

            # With 20% probability, do base-apart move (multi-point perturbation)
            if np.random.rand() < 0.2:
                vec = current[base_j] - current[base_i]
                base_norm = np.linalg.norm(vec)
                if base_norm < 1e-10:
                    consecutive_failures += 1
                    continue
                unit = vec / base_norm
                step_size = 0.5 * base_length * factor
                candidate = current.copy()
                candidate[base_i] = current[base_i] - step_size * unit
                candidate[base_j] = current[base_j] + step_size * unit

                if not is_inside_triangle(candidate, A, B, C):
                    consecutive_failures += 1
                    continue
                
                new_score = get_smallest_triangle_area(candidate)
            else:
                # Standard apex move
                p_base_i = current[base_i]
                p_base_j = current[base_j]
                p_apex = current[apex_i]

                base_vec = p_base_j - p_base_i
                base_norm = np.linalg.norm(base_vec)
                if base_norm < 1e-10:
                    consecutive_failures += 1
                    continue
                base_unit = base_vec / base_norm
                vec_apex_to_base_i = p_apex - p_base_i
                proj = np.dot(vec_apex_to_base_i, base_unit)
                foot = p_base_i + proj * base_unit
                height_vec = p_apex - foot
                height = np.linalg.norm(height_vec)
                if height < 1e-10:
                    consecutive_failures += 1
                    continue
                height_unit = height_vec / height

                step_size = 0.5 * base_length * factor
                candidate_apex = p_apex + step_size * height_unit
                candidate = current.copy()
                candidate[apex_i] = candidate_apex

                if is_inside_triangle(candidate, A, B, C):
                    new_score = get_smallest_triangle_area(candidate)
                else:
                    # Fallback: perturb base point inward toward centroid
                    base_points = [base_i, base_j]
                    idx_base = np.random.choice(base_points)
                    base_point = current[idx_base]
                    centroid = (A + B + C) / 3.0
                    direction = centroid - base_point
                    if np.linalg.norm(direction) < 1e-10:
                        consecutive_failures += 1
                        continue
                    direction = direction / np.linalg.norm(direction)
                    step_base = 0.05 * step_size
                    candidate = current.copy()
                    candidate[idx_base] = base_point + step_base * direction

                    if not is_inside_triangle(candidate, A, B, C):
                        consecutive_failures += 1
                        continue
                    new_score = get_smallest_triangle_area(candidate)

            # Simulated annealing acceptance
            current_temp = initial_temp * (cooling_rate ** step_count)
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

        return best

    return improve