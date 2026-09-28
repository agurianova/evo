from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Set seed based on input for deterministic per-configuration behavior
        rounded_points = np.round(points, 6)
        seed_tuple = tuple(map(tuple, rounded_points))
        seed = hash(seed_tuple) % (2**32)
        np.random.seed(seed)

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        max_iter = 200
        T = 0.001
        cooling_rate = 0.995
        tol = 1e-9

        for _ in range(max_iter):
            # Identify bottleneck triangles (those with area <= current_score + tol)
            bottleneck_triangles = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        x1, y1 = current[i]
                        x2, y2 = current[j]
                        x3, y3 = current[k]
                        area = 0.5 * abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
                        if area <= current_score + tol:
                            bottleneck_triangles.append((i, j, k))

            if not bottleneck_triangles:
                T *= cooling_rate
                continue

            # Randomly select one bottleneck triangle
            i, j, k = bottleneck_triangles[np.random.randint(0, len(bottleneck_triangles))]
            p_i, p_j, p_k = current[i], current[j], current[k]
            centroid = (p_i + p_j + p_k) / 3.0

            # Compute directions away from centroid
            v_i = p_i - centroid
            v_j = p_j - centroid
            v_k = p_k - centroid
            norm_i = np.linalg.norm(v_i)
            norm_j = np.linalg.norm(v_j)
            norm_k = np.linalg.norm(v_k)

            # Skip if degenerate
            if norm_i < 1e-5 or norm_j < 1e-5 or norm_k < 1e-5:
                T *= cooling_rate
                continue

            dir_i = v_i / norm_i
            dir_j = v_j / norm_j
            dir_k = v_k / norm_k

            # Adaptive step size
            step = 0.1 * np.sqrt(current_score)

            # Generate candidate by expanding the triangle
            candidate = current.copy()
            candidate[i] = p_i + step * dir_i
            candidate[j] = p_j + step * dir_j
            candidate[k] = p_k + step * dir_k

            # Check containment
            if not is_inside_triangle(candidate, A, B, C):
                T *= cooling_rate
                continue

            new_score = get_smallest_triangle_area(candidate)

            # Update best solution if improved
            if new_score > best_score:
                best = candidate.copy()
                best_score = new_score

            # Simulated annealing acceptance
            if new_score > current_score:
                current = candidate
                current_score = new_score
            else:
                delta = new_score - current_score
                if np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = new_score

            T *= cooling_rate

        return best

    return improve