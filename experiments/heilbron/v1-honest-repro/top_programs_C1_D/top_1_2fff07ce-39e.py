from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Seed RNG per input for independent randomness
        seed = hash(points.tobytes()) % (2**32)
        np.random.seed(seed)

        # Local function to find minimal-area triangles
        def get_minimal_triangles(pts, tol=1e-5):
            n = pts.shape[0]
            min_area = float('inf')
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = pts[i], pts[j], pts[k]
                        area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        if area_val < min_area - tol:
                            min_area = area_val
                            triangles = [(i, j, k)]
                        elif abs(area_val - min_area) <= tol:
                            triangles.append((i, j, k))
            return triangles

        # Initialize with input configuration
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score

        # Configuration parameters
        max_rounds = 200
        initial_temp = 0.001
        cooling_rate = 0.99
        initial_step = 0.05
        final_step = 0.005

        for round_idx in range(max_rounds):
            # Calculate adaptive parameters
            temp = initial_temp * (cooling_rate ** round_idx)
            step_size = initial_step * (final_step / initial_step) ** (round_idx / max_rounds)

            # Generate candidate by perturbing critical point
            candidate = current.copy()
            min_triangles = get_minimal_triangles(current)
            if min_triangles:
                tri = min_triangles[np.random.randint(len(min_triangles))]
                idx = tri[np.random.randint(3)]
            else:
                idx = np.random.randint(0, 11)

            # Apply perturbation
            candidate[idx] += np.random.normal(0, step_size, size=2)

            # Validate containment
            if not is_inside_triangle(candidate, A, B, C):
                continue

            # Evaluate candidate
            score = get_smallest_triangle_area(candidate)

            # Update global best if improved
            if score > best_score:
                best = candidate.copy()
                best_score = score

            # Simulated annealing acceptance
            if score > current_score:
                current, current_score = candidate, score
            else:
                delta = score - current_score
                if np.random.rand() < np.exp(delta / temp):
                    current, current_score = candidate, score

        return best

    return improve