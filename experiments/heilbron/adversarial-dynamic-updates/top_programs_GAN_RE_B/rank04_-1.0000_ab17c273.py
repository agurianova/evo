from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    # Barycentric coordinate system helpers
    def cartesian_to_barycentric(p):
        v0 = B - A
        v1 = C - A
        v2 = p - A
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

    def barycentric_to_cartesian(bary):
        u, v, w = bary
        return u * A + v * B + w * C

    def compute_triangle_areas(points):
        n = points.shape[0]
        areas = {}
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                    areas[(i, j, k)] = area
        return areas

    def update_triangle_areas(points, areas, modified_indices):
        n = points.shape[0]
        # Only update triangles involving modified points
        for i in modified_indices:
            for j in range(n):
                if j == i:
                    continue
                for k in range(j+1, n):
                    if k == i:
                        continue
                    idx_tuple = tuple(sorted([i, j, k]))
                    a, b, c = points[idx_tuple[0]], points[idx_tuple[1]], points[idx_tuple[2]]
                    area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                    areas[idx_tuple] = area
        return areas

    def get_top_k_triangles(areas, k):
        # Sort triangles by area and return top k smallest
        sorted_triangles = sorted(areas.items(), key=lambda x: x[1])
        return [t[0] for t in sorted_triangles[:k]]

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_overall = current.copy()
        best_overall_score = current_score

        n_rounds = 500
        T0 = 0.01
        T_decay = 0.995
        base_step = 0.05

        T = T0
        step_size = base_step
        stagnation_count = 0

        # Precompute all triangle areas for incremental updates
        triangle_areas = compute_triangle_areas(current)

        for round_idx in range(n_rounds):
            # Adaptive k based on stagnation (not round index)
            k = max(3, min(10, 3 + stagnation_count // 15))
            top_triangles = get_top_k_triangles(triangle_areas, k)
            
            # Adaptive single-point perturbation probability
            single_point_prob = max(0.3, 0.7 - stagnation_count * 0.01)
            
            if np.random.rand() < single_point_prob:
                # Single point perturbation
                chosen_triangle = top_triangles[np.random.randint(len(top_triangles))]
                idx = np.random.choice(chosen_triangle)
                candidate = current.copy()
                
                # Dynamic boundary tolerance that decays to 0
                boundary_tolerance = max(0.001 * (1 - round_idx/n_rounds), 1e-5)
                
                # Use barycentric coordinates for perturbation
                bary = cartesian_to_barycentric(candidate[idx])
                bary_perturb = bary + np.random.normal(0, step_size, size=3)
                # Clip with dynamic tolerance
n                bary_perturb = np.clip(bary_perturb, boundary_tolerance, 1-boundary_tolerance)
                bary_perturb = bary_perturb / np.sum(bary_perturb)
                candidate[idx] = barycentric_to_cartesian(bary_perturb)
                
                # Update only affected triangles
                modified_indices = [idx]
            else:
                # Three-point perturbation
                chosen_triangle = top_triangles[np.random.randint(len(top_triangles))]
                candidate = current.copy()
                modified_indices = []
                
                # Dynamic boundary tolerance
                boundary_tolerance = max(0.001 * (1 - round_idx/n_rounds), 1e-5)
                
                for idx in chosen_triangle:
                    bary = cartesian_to_barycentric(candidate[idx])
                    bary_perturb = bary + np.random.normal(0, step_size, size=3)
                    bary_perturb = np.clip(bary_perturb, boundary_tolerance, 1-boundary_tolerance)
                    bary_perturb = bary_perturb / np.sum(bary_perturb)
                    candidate[idx] = barycentric_to_cartesian(bary_perturb)
                    modified_indices.append(idx)

            # Update triangle areas incrementally
            candidate_areas = triangle_areas.copy()
            candidate_areas = update_triangle_areas(candidate, candidate_areas, modified_indices)
            candidate_score = min(candidate_areas.values())

            # Track best overall solution
            if candidate_score > best_overall_score:
                best_overall = candidate.copy()
                best_overall_score = candidate_score
                stagnation_count = 0
            
            # Reset stagnation count on ANY improvement
            if candidate_score > current_score:
                current = candidate
                current_score = candidate_score
                triangle_areas = candidate_areas
                stagnation_count = 0
            else:
                stagnation_count += 1

            # Adaptive stagnation threshold based on temperature
            adaptive_threshold = max(20, int(50 * T / T0))
            
            # Stagnation handling - restart from best solution with partial temperature reset
            if stagnation_count >= adaptive_threshold:
                current = best_overall.copy()
                current_score = best_overall_score
                triangle_areas = compute_triangle_areas(current)
                T = T0 * 0.5  # Reset to half initial temperature
                step_size = base_step * (T / T0)  # Synchronize step size with temperature
                stagnation_count = 0
            else:
                # Only attempt acceptance if not already accepted as current
                if candidate_score <= current_score:
                    delta = candidate_score - current_score
                    if np.random.rand() < np.exp(delta / T):
                        current = candidate
                        current_score = candidate_score
                        triangle_areas = candidate_areas

            # Update temperature and step size with tighter synchronization
            if round_idx < n_rounds - 1:
                T = T * T_decay
                step_size = base_step * (T / T0)

        return best_overall

    return improve