from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from collections import deque

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def find_minimal_triangles(points):
        n = len(points)
        min_area_val = float('inf')
        candidate_triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    x1, y1 = points[i]
                    x2, y2 = points[j]
                    x3, y3 = points[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area < min_area_val - 1e-9:
                        min_area_val = area
                        candidate_triangles = [(i, j, k)]
                    elif abs(area - min_area_val) <= 1e-9:
                        candidate_triangles.append((i, j, k))
        return min_area_val, candidate_triangles

    def improve(points: np.ndarray) -> np.ndarray:
        current_points = points.copy()
        current_score = get_smallest_triangle_area(current_points)
        
        # Hyperparameters
        max_iterations = 200
        max_no_improve = 50
        initial_temp = 0.001
        cooling_rate = 0.995
        step_size = 0.02
        acceptance_window = 50
        target_acceptance_rate = 0.4

        temperature = initial_temp
        consecutive_no_improve = 0
        acceptance_history = deque(maxlen=acceptance_window)

        for _ in range(max_iterations):
            if consecutive_no_improve >= max_no_improve:
                break

            # Identify bottleneck triangles
            _, candidate_triangles = find_minimal_triangles(current_points)
            if not candidate_triangles:
                continue
            
            # Select one minimal triangle randomly
            idx0, idx1, idx2 = candidate_triangles[np.random.randint(0, len(candidate_triangles))]

            # Generate candidate by perturbing all three points
            candidate = current_points.copy()
            for idx in [idx0, idx1, idx2]:
                candidate[idx] += np.random.normal(0, step_size, size=2)

            # Skip if outside triangle
            if not is_inside_triangle(candidate, A, B, C):
                continue

            new_score = get_smallest_triangle_area(candidate)
            delta = new_score - current_score

            # Simulated annealing acceptance
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current_points = candidate
                current_score = new_score
                consecutive_no_improve = 0
                accepted = True
            else:
                consecutive_no_improve += 1
                accepted = False

            acceptance_history.append(accepted)

            # Adaptive step size tuning
            if len(acceptance_history) >= 10:
                acceptance_rate = np.mean(acceptance_history)
                if acceptance_rate > target_acceptance_rate + 0.1:
                    step_size *= 1.1
                elif acceptance_rate < target_acceptance_rate - 0.1:
                    step_size *= 0.9
                step_size = max(0.001, min(step_size, 0.1))

            temperature *= cooling_rate

        return current_points

    return improve