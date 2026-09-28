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
            if len(min_triangles) == 0:
                consecutive_failures += 1
                continue

            # Sort minimal triangles by flattest-first (longest side descending)
            min_triangles_sorted = []
            for tri in min_triangles:
                i, j, k = tri
                d0 = np.linalg.norm(current[i]-current[j])
                d1 = np.linalg.norm(current[i]-current[k])
                d2 = np.linalg.norm(current[j]-current[k])
                longest_side = max(d0, d1, d2)
                min_triangles_sorted.append((longest_side, tri))
            min_triangles_sorted.sort(key=lambda x: x[0], reverse=True)
            _, tri = min_triangles_sorted[0]
            i0, i1, i2 = tri

            # Compute triangle geometry
            p0, p1, p2 = current[i0], current[i1], current[i2]
            d01 = np.linalg.norm(p0-p1)
            d02 = np.linalg.norm(p0-p2)
            d12 = np.linalg.norm(p1-p2)
            min_side_val = min(d01, d02, d12)
            sides = [(d01, (i0,i1), i2), (d02, (i0,i2), i1), (d12, (i1,i2), i0)]
            sides.sort(key=lambda x: x[0], reverse=True)
            base_length, (base_i, base_j), apex_i = sides[0]

            base_vec = current[base_j] - current[base_i]
            base_norm = np.linalg.norm(base_vec)
            if base_norm < 1e-10:
                consecutive_failures += 1
                continue

            base_unit = base_vec / base_norm

            # 20% chance for dual-point base perturbation
            if np.random.rand() < 0.2:
                step_size = max(0.25 * min_side_val * factor, 0.0025)
                candidate = current.copy()
                candidate[base_i] = current[base_i] - step_size * base_unit
                candidate[base_j] = current[base_j] + step_size * base_unit

                # Verify both base points remain inside
                if not (is_inside_triangle(candidate[[base_i]], A, B, C) and 
                        is_inside_triangle(candidate[[base_j]], A, B, C)):
                    consecutive_failures += 1
                    continue

            else:
                # Single-point apex move
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
                step_size = max(0.5 * min_side_val * factor, 0.005)
                candidate = current.copy()
                candidate[apex_i] = apex + step_size * height_unit

                # Boundary fallback for apex move
                if not is_inside_triangle(candidate, A, B, C):
                    base_points = [base_i, base_j]
                    chosen_base = np.random.choice(base_points)
                    centroid = (A + B + C) / 3
                    direction = centroid - current[chosen_base]
                    direction_norm = np.linalg.norm(direction)
                    if direction_norm < 1e-5:
                        consecutive_failures += 1
                        continue
                    step_vec = 0.005 * direction / direction_norm
                    candidate = current.copy()
                    candidate[chosen_base] = current[chosen_base] + step_vec
                    if not is_inside_triangle(candidate, A, B, C):
                        consecutive_failures += 1
                        continue

            new_score = get_smallest_triangle_area(candidate)
            current_temp = initial_temp * factor

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