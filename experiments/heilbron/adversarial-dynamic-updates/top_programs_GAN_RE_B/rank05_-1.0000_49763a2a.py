from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    # Barycentric coordinate utilities
    def to_barycentric(point):
        v0 = C - A
        v1 = B - A
        v2 = point - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        v = (d11 * d20 - d01 * d21) / (denom + 1e-10)
        w = (d00 * d21 - d01 * d20) / (denom + 1e-10)
        u = 1.0 - v - w
        return np.array([u, v, w])

    def to_cartesian(bary):
        u, v, w = bary
        return u * A + v * B + w * C

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_overall = current.copy()
        best_overall_score = current_score

        n_rounds = 500  # Increased from 200
        initial_min_area = current_score
        T0 = 0.1 * initial_min_area  # Adaptive temperature
        T_decay = 0.995
        base_step = 0.05
        step_decay = 0.997  # Slower decay

        T = T0
        step_size = base_step
        stagnation_count = 0

        # Convert initial points to barycentric for internal processing
        bary_points = np.array([to_barycentric(p) for p in current])

        def get_top_k_triangles(pts, k):
            n = pts.shape[0]
            areas = []
            indices = []
            for i in range(n):
                for j in range(i+1, n):
                    for k_idx in range(j+1, n):
                        a, b, c = pts[i], pts[j], pts[k_idx]
                        area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                        areas.append(area)
                        indices.append((i, j, k_idx))
            
            sorted_indices = [idx for _, idx in sorted(zip(areas, indices))]
            return sorted_indices[:k]

        for round_idx in range(n_rounds):
            # Adaptive k: starts at 3, increases to max 10 as search progresses
            k_val = min(10, 3 + round_idx // 50)
            top_triangles = get_top_k_triangles(current, k_val)
            chosen_triangle = top_triangles[np.random.randint(len(top_triangles))]

            # Adaptive probability for moving all three points
            all_points_prob = 0.3 + 0.4 * min(1.0, stagnation_count / 50)
            
            # Convert to barycentric for safe perturbation
            candidate_bary = bary_points.copy()
            
            if np.random.rand() < all_points_prob:
                # Move all three points of the triangle
n                for idx in chosen_triangle:
                    # Scale step by distance to nearest boundary (min barycentric coordinate)
                    min_bary = min(candidate_bary[idx])
                    adaptive_step = step_size * (0.2 + 0.8 * min_bary)
                    
                    # Generate random direction in barycentric space (preserving sum=1)
                    direction = np.random.normal(0, adaptive_step, size=3)
                    direction = direction - np.mean(direction)  # Ensure sum remains 0
                    candidate_bary[idx] += direction
                    
                    # Ensure barycentric coordinates stay valid
                    candidate_bary[idx] = np.clip(candidate_bary[idx], 0.001, 0.999)
                    candidate_bary[idx] /= np.sum(candidate_bary[idx])
            else:
                # Move a single point
                idx = np.random.choice(chosen_triangle)
                min_bary = min(candidate_bary[idx])
                adaptive_step = step_size * (0.2 + 0.8 * min_bary)
                
                direction = np.random.normal(0, adaptive_step, size=3)
                direction = direction - np.mean(direction)
                candidate_bary[idx] += direction
                
                # Ensure barycentric coordinates stay valid
                candidate_bary[idx] = np.clip(candidate_bary[idx], 0.001, 0.999)
                candidate_bary[idx] /= np.sum(candidate_bary[idx])

            # Convert back to Cartesian for evaluation
            candidate = np.array([to_cartesian(b) for b in candidate_bary])
            
            # Verify all points are inside (should be guaranteed by barycentric, but double-check)
            if not is_inside_triangle(candidate, A, B, C):
                # Fallback: use original points if somehow outside
                candidate = current.copy()

            candidate_score = get_smallest_triangle_area(candidate)

            # Only accept improvements (pure improvement task)
            if candidate_score > current_score:
                current = candidate
                bary_points = np.array([to_barycentric(p) for p in current])
                current_score = candidate_score
                stagnation_count = 0
                
                if candidate_score > best_overall_score:
                    best_overall = candidate.copy()
                    best_overall_score = candidate_score
            else:
                stagnation_count += 1

            # Update temperature and step size
            T = T * T_decay
            step_size = step_size * step_decay

        return best_overall

    return improve