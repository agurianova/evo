from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    # Helper function to compute area of a triangle given three points
    def triangle_area(a, b, c):
        return 0.5 * abs((a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1])))

    # Helper to get indices of the smallest triangle
    def get_smallest_triangle_indices(points):
        n = len(points)
        min_area = float('inf')
        best_indices = (0, 1, 2)
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = triangle_area(points[i], points[j], points[k])
                    if area < min_area:
                        min_area = area
                        best_indices = (i, j, k)
        return best_indices

    def improve(points: np.ndarray) -> np.ndarray:
        # Create reproducible random generator
        rng = np.random.default_rng(42)
        
        # Start with the input points
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        # Simulated annealing parameters
        max_iter = 1000
        temp = 0.02  # initial temperature
        cooling_rate = 0.99

        for _ in range(max_iter):
            # Get the smallest triangle to guide perturbation
            smallest_indices = get_smallest_triangle_indices(current)

            # Decide which point(s) to perturb
            p = rng.random()
            if p < 0.8:
                # Perturb one point from smallest triangle
                idx = smallest_indices[rng.integers(0, 3)]
                candidate = current.copy()
                candidate[idx] += rng.normal(0, temp, size=2)
            elif p < 0.9:
                # Perturb two points from smallest triangle
                idx1, idx2 = rng.choice(smallest_indices, 2, replace=False)
                candidate = current.copy()
                candidate[idx1] += rng.normal(0, temp, size=2)
                candidate[idx2] += rng.normal(0, temp, size=2)
            else:
                # Perturb a random point
                idx = rng.integers(0, 11)
                candidate = current.copy()
                candidate[idx] += rng.normal(0, temp, size=2)

            # Check if candidate is inside the triangle
            if not is_inside_triangle(candidate, A, B, C):
                temp *= cooling_rate
                continue

            # Evaluate candidate
            candidate_score = get_smallest_triangle_area(candidate)

            # Acceptance criterion: if better, always accept; if worse, accept with probability
            delta = candidate_score - current_score
            if delta > 0 or rng.random() < np.exp(delta / temp):
                current = candidate
                current_score = candidate_score

            # Update best if candidate is better than the best so far
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score

            # Cool down
            temp *= cooling_rate

        return best

    return improve