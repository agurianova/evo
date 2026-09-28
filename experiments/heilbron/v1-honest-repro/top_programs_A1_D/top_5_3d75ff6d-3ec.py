from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Initialize local random number generator for reproducibility
        rng = np.random.default_rng(42)
        
        # Helper to find vertices of smallest triangle
        def get_smallest_triangle_vertices(pts):
            n = pts.shape[0]
            min_area = float('inf')
            best_indices = (0, 1, 2)
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        x1, y1 = pts[i]
                        x2, y2 = pts[j]
                        x3, y3 = pts[k]
                        area = 0.5 * abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
                        if area < min_area:
                            min_area = area
                            best_indices = (i, j, k)
            return best_indices

        # Initialize search parameters
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        no_improve_count = 0
        consecutive_rejections = 0
        current_step = 0.05
        temp = 0.01
        cooling_rate = 0.95
        min_step = 0.001
        max_step = 0.2
        max_iterations = 500
        max_no_improve = 100

        # Simulated annealing loop
        for _ in range(max_iterations):
            # Termination conditions
            if no_improve_count >= max_no_improve or temp < 1e-5:
                break

            # Identify bottleneck triangle
            i, j, k = get_smallest_triangle_vertices(current)
            
            # Targeted perturbation: 1 or 2 vertices of smallest triangle
            if rng.random() < 0.5:
                idxs = [rng.choice([i, j, k])]
            else:
                idxs = rng.choice([i, j, k], 2, replace=False)

            candidate = current.copy()
            for idx in idxs:
                candidate[idx] += rng.normal(0, current_step, 2)

            # Validate containment
            if not is_inside_triangle(candidate, A, B, C):
                consecutive_rejections += 1
                continue

            candidate_score = get_smallest_triangle_area(candidate)

            # Update global best if improved
            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Acceptance criteria (simulated annealing)
            delta = current_score - candidate_score
            if delta <= 0:
                # Always accept improvements
                current = candidate
                current_score = candidate_score
                consecutive_rejections = 0
                # Refine search after improvement
                current_step = max(min_step, current_step * 0.9)
            else:
                # Accept worse solutions probabilistically
                if rng.random() < np.exp(-delta / temp):
                    current = candidate
                    current_score = candidate_score
                    consecutive_rejections = 0
                else:
                    consecutive_rejections += 1

            # Adaptive step size control
            if consecutive_rejections >= 10:
                current_step = min(max_step, current_step * 1.2)
                consecutive_rejections = 0

            # Cool temperature
            temp *= cooling_rate

        return best

    return improve