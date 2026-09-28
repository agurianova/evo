from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    """Return an improve(points) -> improved_points callable."""
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Set seed per input for independent randomness
        seed_val = hash(points.tobytes()) % (2**32)
        np.random.seed(seed_val)

        total_rounds = 500
        initial_step = 0.1
        final_step = 0.001
        final_temp = 1e-7

        # Auto-tune initial temperature via trial perturbations
        current_temp = points.copy()
        current_score_temp = get_smallest_triangle_area(current_temp)
        neg_deltas = []
        for _ in range(50):
            candidate = current_temp.copy()
            idx = np.random.randint(0, 11)
            candidate[idx] += np.random.normal(0, initial_step, size=2)
            if not is_inside_triangle(candidate, A, B, C):
                continue
            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - current_score_temp
            if delta < 0:
                neg_deltas.append(delta)

        if neg_deltas:
            avg_neg_delta = np.mean(neg_deltas)
            initial_temp = -avg_neg_delta / np.log(0.8)
        else:
            initial_temp = 0.001  # Fallback for rare no-negative-delta case

        # Helper to identify critical points with frequency weighting
        def get_minimal_triangles(pts):
            n = pts.shape[0]
            min_area_val = get_smallest_triangle_area(pts)
            tol = 1e-12
            critical_indices = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = pts[i]
                        x2, y2 = pts[j]
                        x3, y3 = pts[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if abs(area - min_area_val) < tol:
                            critical_indices.extend([i, j, k])
            return critical_indices if critical_indices else list(range(11))

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        stagnation_count = 0
        restart_next = None  # Temperature override for next iteration

        for t in range(total_rounds):
            # Adaptive parameters
            progress = t / total_rounds
            step_size = initial_step * (final_step / initial_step) ** progress

            # Handle restart temperature override
            if restart_next is not None:
                temp = restart_next
                restart_next = None
            else:
                temp = initial_temp * (final_temp / initial_temp) ** progress

            # Focus perturbations on critical points (weighted by frequency)
            critical_points = get_minimal_triangles(current)
            idx = np.random.choice(critical_points)

            # Generate candidate
            candidate = current.copy()
            candidate[idx] += np.random.normal(0, step_size, size=2)

            # Validate containment
            if not is_inside_triangle(candidate, A, B, C):
                continue

            candidate_score = get_smallest_triangle_area(candidate)

            # Update best if improvement found
            improved_best = False
            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                improved_best = True

            # Simulated annealing acceptance
            if candidate_score > current_score:
                current, current_score = candidate, candidate_score
            else:
                delta = candidate_score - current_score
                if np.random.rand() < np.exp(delta / temp):
                    current, current_score = candidate, candidate_score

            # Update stagnation counter
            if improved_best:
                stagnation_count = 0
            else:
                stagnation_count += 1

            # Trigger restart on stagnation
            if stagnation_count >= 50:
                restart_next = initial_temp
                current = best.copy()
                current_score = best_score
                stagnation_count = 0

        return best

    return improve