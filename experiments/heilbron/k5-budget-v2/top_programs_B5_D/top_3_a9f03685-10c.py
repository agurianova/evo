from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Seed RNG deterministically per input configuration
        seed = int(hash(points.tobytes()) % (2**32))
        rng = np.random.RandomState(seed)

        # Helper to find smallest triangle indices
        def get_smallest_triangle_indices(pts):
            n = pts.shape[0]
            min_area = float('inf')
            best_indices = (0, 1, 2)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = 0.5 * abs(
                            (pts[j,0] - pts[i,0]) * (pts[k,1] - pts[i,1]) -
                            (pts[k,0] - pts[i,0]) * (pts[j,1] - pts[i,1])
                        )
                        if area < min_area:
                            min_area = area
                            best_indices = (i, j, k)
            return best_indices, min_area

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        temperature = 0.001
        step_size = 0.05
        no_improve_count = 0

        for _ in range(500):
            if no_improve_count >= 100:
                break

            # Focus perturbation on bottleneck (smallest triangle)
            indices, _ = get_smallest_triangle_indices(current)
            if rng.rand() < 0.1:
                idxs = rng.choice(indices, size=2, replace=False)
            else:
                idxs = [rng.choice(indices)]

            candidate = current.copy()
            for idx in idxs:
                candidate[idx] += rng.normal(0, step_size, size=2)

            if not is_inside_triangle(candidate, A, B, C):
                continue

            score = get_smallest_triangle_area(candidate)

            # Track global best
            if score > best_score:
                best = candidate
                best_score = score
                no_improve_count = 0
                step_size = 0.05  # Reset step size on improvement
            else:
                no_improve_count += 1

            # Simulated annealing acceptance
            if score > current_score:
                current = candidate
                current_score = score
            else:
                delta = score - current_score
                if temperature > 1e-10 and rng.rand() < np.exp(delta / temperature):
                    current = candidate
                    current_score = score

            # Adaptive cooling and step decay
            temperature *= 0.95
            if no_improve_count % 10 == 0 and no_improve_count > 0:
                step_size = max(step_size * 0.9, 0.001)

        return best

    return improve