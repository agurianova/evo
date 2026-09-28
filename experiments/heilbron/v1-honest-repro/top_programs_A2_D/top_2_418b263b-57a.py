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
        max_consecutive_failures = 100
        max_steps = 1000

        consecutive_failures = 0
        step_count = 0

        while consecutive_failures < max_consecutive_failures and step_count < max_steps:
            factor = cooling_rate ** step_count
            step_count += 1

            min_area_val, min_triangles = compute_min_triangles(current)
            
            # Sort minimal triangles by largest side (descending) to prioritize smallest height
            base_lengths = []
            for tri in min_triangles:
                i0, i1, i2 = tri
                p0, p1, p2 = current[i0], current[i1], current[i2]
                d01 = np.linalg.norm(p0 - p1)
                d02 = np.linalg.norm(p0 - p2)
                d12 = np.linalg.norm(p1 - p2)
                base = max(d01, d02, d12)
                base_lengths.append(base)
            if base_lengths:
                sorted_indices = np.argsort(base_lengths)[::-1]
                min_triangles = [min_triangles[i] for i in sorted_indices]
            
            tri_idx = 0
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
            step_apex = 0.5 * min_side * factor
            candidate_apex = current.copy()
            candidate_apex[apex_i] = apex + step_apex * height_unit

            # Boundary fallback: if apex move fails, try moving base points inward
            candidate = None
            if is_inside_triangle(candidate_apex, A, B, C):
                candidate = candidate_apex
            else:
                centroid = (A + B + C) / 3.0
                # Try moving base_i inward
                dir_i = centroid - current[base_i]
                if np.linalg.norm(dir_i) > 1e-10:
                    dir_i = dir_i / np.linalg.norm(dir_i)
                    step_inward = 0.01 * min_side * factor
                    candidate_i = current.copy()
                    candidate_i[base_i] = current[base_i] + step_inward * dir_i
                    if is_inside_triangle(candidate_i, A, B, C):
                        candidate = candidate_i
                # If base_i move failed, try base_j
                if candidate is None:
                    dir_j = centroid - current[base_j]
                    if np.linalg.norm(dir_j) > 1e-10:
                        dir_j = dir_j / np.linalg.norm(dir_j)
                        candidate_j = current.copy()
                        candidate_j[base_j] = current[base_j] + step_inward * dir_j
                        if is_inside_triangle(candidate_j, A, B, C):
                            candidate = candidate_j

            if candidate is None:
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