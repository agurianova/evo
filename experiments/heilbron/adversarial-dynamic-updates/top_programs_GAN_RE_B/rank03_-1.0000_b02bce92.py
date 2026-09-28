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

        # Cache for triangle areas to enable partial updates
        n_points = points.shape[0]
        triangle_cache = {}
        
        # Initialize cache with all triangle areas
        for i in range(n_points):
            for j in range(i+1, n_points):
                for k in range(j+1, n_points):
                    a, b, c = current[i], current[j], current[k]
                    area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                    triangle_cache[(i, j, k)] = area

        def get_smallest_triangle_area_cached(pts, modified_indices=None):
            if modified_indices is None:
                # Full recalculation (shouldn't happen often)
                return get_smallest_triangle_area(pts)
            
            # Update only triangles involving modified points
            min_area = float('inf')
            for i in range(n_points):
                for j in range(i+1, n_points):
                    for k in range(j+1, n_points):
                        # Only recalculate triangles that include at least one modified point
                        if i in modified_indices or j in modified_indices or k in modified_indices:
                            a, b, c = pts[i], pts[j], pts[k]
                            area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                            triangle_cache[(i, j, k)] = area
                        min_area = min(min_area, triangle_cache[(i, j, k)])
            return min_area

        def get_top_k_triangles(pts, round_idx, stagnation_count, k_base=3):
            # Adaptive k: based on stagnation count
            k = max(k_base, min(10, k_base + stagnation_count // 10))
            
            # Get all triangle areas from cache
            areas = list(triangle_cache.values())
            indices = list(triangle_cache.keys())
            
            sorted_indices = [idx for _, idx in sorted(zip(areas, indices))]
            return sorted_indices[:k]

        for round_idx in range(n_rounds):
            # Dynamic boundary tolerance that decreases as search progresses
            tolerance = max(0.001 * (1 - round_idx/n_rounds), 1e-10)
            
            # Adaptive step decay that accelerates as temperature drops
            step_decay = 0.95 + 0.03 * (T / T0)
            
            # Adaptive single-point perturbation probability
            single_point_prob = max(0.3, 0.7 - 0.4 * stagnation_count/50)
            
            # Temperature-proportional stagnation threshold
            stagnation_threshold = max(20, int(50 * T / T0))

            # Use adaptive k based on current round and stagnation
            top_triangles = get_top_k_triangles(current, round_idx, stagnation_count, k_base=3)
            chosen_triangle = top_triangles[np.random.randint(len(top_triangles))]

            if np.random.rand() < single_point_prob:
                idx = np.random.choice(chosen_triangle)
                candidate = current.copy()
                # Use barycentric coordinates for perturbation to stay inside triangle
                bary = cartesian_to_barycentric(candidate[idx])
                # Add perturbation in barycentric space (ensures stays inside)
                bary_perturb = bary + np.random.normal(0, step_size, size=3)
                # Dynamic tolerance that decreases over time
n                bary_perturb = np.clip(bary_perturb, tolerance, 1.0 - tolerance)
                bary_perturb = bary_perturb / np.sum(bary_perturb)
                candidate[idx] = barycentric_to_cartesian(bary_perturb)
                
                # Only need to update triangles involving this point
                modified_indices = [idx]
            else:
                candidate = current.copy()
                modified_indices = []
                for idx in chosen_triangle:
                    # Use barycentric coordinates for perturbation to stay inside triangle
                    bary = cartesian_to_barycentric(candidate[idx])
                    # Add perturbation in barycentric space (ensures stays inside)
                    bary_perturb = bary + np.random.normal(0, step_size, size=3)
                    # Dynamic tolerance that decreases over time
                    bary_perturb = np.clip(bary_perturb, tolerance, 1.0 - tolerance)
                    bary_perturb = bary_perturb / np.sum(bary_perturb)
                    candidate[idx] = barycentric_to_cartesian(bary_perturb)
                    modified_indices.append(idx)

            candidate_score = get_smallest_triangle_area_cached(candidate, modified_indices)

            # Track best overall solution
            if candidate_score > best_overall_score:
                best_overall = candidate.copy()
                best_overall_score = candidate_score
                stagnation_count = 0
            
            # Reset stagnation count on ANY improvement (not just best)
            if candidate_score > current_score:
                current = candidate
                current_score = candidate_score
                stagnation_count = 0
            else:
                # Only increment if no improvement at all
                stagnation_count += 1

            # Stagnation handling - restart from best solution
            if stagnation_count >= stagnation_threshold:
                current = best_overall.copy()
                current_score = best_overall_score
                T = T0 * 0.5  # Reset to half initial temperature to maintain progress
                step_size = base_step
                stagnation_count = 0
            else:
                # Only attempt acceptance if not already accepted as current
                if candidate_score <= current_score:
                    delta = candidate_score - current_score
                    if np.random.rand() < np.exp(delta / T):
                        current = candidate
                        current_score = candidate_score

            # Update temperature and step size
            if round_idx < n_rounds - 1:
                T = T * T_decay
                step_size = step_size * step_decay

        return best_overall

    return improve