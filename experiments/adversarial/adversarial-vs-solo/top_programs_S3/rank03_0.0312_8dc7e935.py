import numpy as np
import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    side_length = np.linalg.norm(B - A)

    best_points = None
    best_min_area = -1

    n_restarts = 20
    # Increased bias for [4,3,3,1] structure (3/8 probability)
    candidate_row_structures = [
        [3, 3, 3, 2],
        [4, 3, 2, 2],
        [5, 3, 2, 1],
        [4, 4, 2, 1],
        [3, 3, 2, 2, 1],
        [4, 3, 3, 1],
        [4, 3, 3, 1],
        [4, 3, 3, 1]
    ]

    for restart in range(n_restarts):
        points_per_row = random.choice(candidate_row_structures)
        rows = len(points_per_row)
        offsets = np.random.uniform(0.2, 0.8, size=rows)

        points = []
        for i in range(rows):
            num_pts = points_per_row[i]
            v = (i + 0.5) / rows
            for j in range(num_pts):
                u = (j + offsets[i]) / num_pts * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                points.append(P)
        points = np.array(points, dtype=np.float32)

        # Reduced perturbation magnitude to preserve row structure
        points += np.random.uniform(-0.01, 0.01, size=points.shape)

        # Ensure all points are inside the triangle after perturbation
        for i in range(len(points)):
            if not is_inside_triangle(np.array([points[i]]), A, B, C):
                centroid = (A + B + C) / 3
                while not is_inside_triangle(np.array([points[i]]), A, B, C):
                    points[i] = 0.99 * points[i] + 0.01 * centroid

        current_min_area = get_smallest_triangle_area(points)
        T0 = (0.01 * side_length) ** 2  # Initial temperature
        warm_up_iters = 1000
        n_iterations = 10000

        for it in range(n_iterations):
            # Time-dependent move selection probabilities
            if it < 0.3 * n_iterations:
                probs = [0.5, 0.3, 0.2]
            elif it < 0.7 * n_iterations:
                probs = [0.7, 0.2, 0.1]
            else:
                probs = [0.9, 0.1, 0.0]

            k = np.random.choice([1, 2, 3], p=probs)
            indices = np.random.choice(11, size=k, replace=False)
            new_points = points.copy()
            valid_move = True

            # Generate and validate new positions with Voronoi-based step sizing
            for idx in indices:
                # Compute min distance to other points (Voronoi-based)
                dists = np.linalg.norm(points - points[idx], axis=1)
                dists = dists[dists > 1e-8]  # Exclude self
                min_dist = np.min(dists) if len(dists) > 0 else 0.01 * side_length
                
                # Robust step sizing: min distance scaled with floor
                step_length = max(0.001 * side_length, 0.5 * min_dist)
                delta = np.random.uniform(-step_length, step_length, size=2)
                new_point = points[idx] + delta
                
                if not is_inside_triangle(np.array([new_point]), A, B, C):
                    valid_move = False
                    break
                new_points[idx] = new_point

            if not valid_move:
                continue

            new_min_area = get_smallest_triangle_area(new_points)
            if new_min_area < 1e-8:
                continue

            # Set adaptive temperature with warm-up period and exponential decay
            if it < warm_up_iters:
                T_accept = T0
            else:
                # Exponential decay: T = T0 * exp(-5*(it-warm_up_iters)/(n_iterations-warm_up_iters))
                decay_factor = 5.0
                T_accept = T0 * np.exp(-decay_factor * (it - warm_up_iters) / (n_iterations - warm_up_iters))

            # Acceptance criteria
            if new_min_area > current_min_area:
                points = new_points
                current_min_area = new_min_area
                accepted = True
            else:
                delta_area = new_min_area - current_min_area
                if np.random.random() < np.exp(delta_area / T_accept):
                    points = new_points
                    current_min_area = new_min_area
                    accepted = True
                else:
                    accepted = False

        # Local search polish with decaying step size
        local_iterations = 1000
        step_size_initial = 0.01 * side_length
        for loc_it in range(local_iterations):
            step_size = step_size_initial * (1 - loc_it / local_iterations)
            idx = np.random.randint(0, 11)
            new_points = points.copy()
            delta = np.random.uniform(-step_size, step_size, size=2)
            new_point = points[idx] + delta
            
            if not is_inside_triangle(np.array([new_point]), A, B, C):
                continue
                
            new_points[idx] = new_point
            new_min_area = get_smallest_triangle_area(new_points)
            
            if new_min_area >= current_min_area - 1e-10:
                points = new_points
                current_min_area = new_min_area

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_points = points.copy()

    return best_points