from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        total_iters = 200
        initial_temp = 0.001
        initial_step = 0.05

        current = points.copy()
        best = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_score = current_score

        # Precompute all triangles and their areas once per configuration
        def get_top_k_smallest(config, k=5):
            n = config.shape[0]
            areas = []
            indices = []
            for i in range(n):
                for j in range(i + 1, n):
                    for l in range(j + 1, n):
                        p1, p2, p3 = config[i], config[j], config[l]
                        area_val = abs(p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1]))
                        areas.append(area_val)
                        indices.append((i, j, l))
            # Get indices of k smallest areas
            sorted_indices = np.argsort(areas)
            return [indices[i] for i in sorted_indices[:k]]

        for iter in range(total_iters):
            T = initial_temp * (1 - iter / total_iters)
            step_size = initial_step * (T / initial_temp) if initial_temp > 0 else initial_step

            # Focus on multiple bottleneck triangles
            top_triangles = get_top_k_smallest(current, k=5)
            
            # Count point occurrences in bottleneck triangles
            count = np.zeros(11, dtype=int)
            for tri in top_triangles:
                for idx in tri:
                    count[idx] += 1
            
            # Select most critical point (highest frequency)
            idx = np.random.choice(np.where(count == count.max())[0])

            candidate = current.copy()
            P = candidate[idx]

            # Convert to barycentric coordinates
            u = ((B[1] - C[1]) * (P[0] - C[0]) + (C[0] - B[0]) * (P[1] - C[1])) / 2.0
            v = ((C[1] - A[1]) * (P[0] - C[0]) + (A[0] - C[0]) * (P[1] - C[1])) / 2.0
            w = 1 - u - v

            # Perturb in barycentric space
            du = np.random.normal(0, step_size)
            dv = np.random.normal(0, step_size)
            dw = -du - dv

            u_new, v_new, w_new = u + du, v + dv, w + dw
            # Clip to non-negative and renormalize
            u_new, v_new, w_new = max(0, u_new), max(0, v_new), max(0, w_new)
            total = u_new + v_new + w_new
            if total > 0:
                u_new, v_new, w_new = u_new / total, v_new / total, w_new / total
                candidate_point = u_new * A + v_new * B + w_new * C
                candidate[idx] = candidate_point

            # Validate containment
            if not is_inside_triangle(candidate, A, B, C):
                continue

            candidate_score = get_smallest_triangle_area(candidate)

            # Update best solution
            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score

            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta > 0:
                current, current_score = candidate, candidate_score
            else:
                if np.random.rand() < np.exp(delta / T):
                    current, current_score = candidate, candidate_score

        return best

    return improve