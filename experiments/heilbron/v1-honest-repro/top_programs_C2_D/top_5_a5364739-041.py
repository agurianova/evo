from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        step_size = 0.02
        max_iter = 100

        for _ in range(max_iter):
            n = best.shape[0]
            min_area_val = float('inf')
            tri_indices = None
            
            # Find smallest triangle by iterating all combinations
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        # Compute area of triangle (i,j,k)
                        area = 0.5 * abs(
                            (best[j,0] - best[i,0]) * (best[k,1] - best[i,1]) -
                            (best[k,0] - best[i,0]) * (best[j,1] - best[i,1])
                        )
                        if area < min_area_val:
                            min_area_val = area
                            tri_indices = (i, j, k)
            
            if tri_indices is None:
                break

            i, j, k = tri_indices
            p0, p1, p2 = best[i], best[j], best[k]
            centroid = (p0 + p1 + p2) / 3.0
            d0 = p0 - centroid
            d1 = p1 - centroid
            d2 = p2 - centroid

            # Skip if degenerate (shouldn't happen with min_area_val>0)
            norm0 = np.linalg.norm(d0)
            norm1 = np.linalg.norm(d1)
            norm2 = np.linalg.norm(d2)
            if norm0 < 1e-8 or norm1 < 1e-8 or norm2 < 1e-8:
                step_size = max(step_size * 0.9, 1e-5)
                continue

            # Normalize direction vectors
            d0 = d0 / norm0
            d1 = d1 / norm1
            d2 = d2 / norm2

            # Create candidate by moving points outward
            candidate = best.copy()
            candidate[i] = p0 + step_size * d0
            candidate[j] = p1 + step_size * d1
            candidate[k] = p2 + step_size * d2

            # Check distinctness (min pairwise distance > 1e-8)
            dists = np.linalg.norm(candidate[:, None, :] - candidate[None, :, :], axis=-1)
            np.fill_diagonal(dists, np.inf)
            if np.min(dists) < 1e-8:
                step_size = max(step_size * 0.9, 1e-5)
                continue

            # Check containment in unit triangle
            if not is_inside_triangle(candidate, A, B, C):
                step_size = max(step_size * 0.9, 1e-5)
                continue

            # Evaluate candidate
            candidate_score = get_smallest_triangle_area(candidate)
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
                step_size = min(step_size * 1.1, 0.1)  # Increase step size
            else:
                step_size = max(step_size * 0.9, 1e-5)  # Decrease step size

        return best

    return improve