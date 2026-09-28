import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri

    # Generate 10 symmetric row patterns for 5 rows summing to 11
    patterns = []
    for a in range(1, 5):
        for b in range(1, (11 - 2*a) // 2 + 1):
            c = 11 - 2*a - 2*b
            if c > 0:
                patterns.append([a, b, c, b, a])

    def generate_base_lattice(rows):
        total_rows = len(rows)
        points = []
        for i, n in enumerate(rows):
            v = (i + 0.5) / total_rows
            for j in range(n):
                if n == 1:
                    u = (1 - v) / 2
                else:
                    u = (1 - v) * (j + 0.5) / n
                w = 1 - u - v
                base_bary = np.array([w, u, v])
                # Add barycentric noise and normalize
                noise = np.random.normal(0, 0.05, 3)
                new_bary = base_bary + noise
                new_bary = np.maximum(new_bary, 0)
                new_bary /= new_bary.sum()
                w_new, u_new, v_new = new_bary
                P = w_new * A + u_new * B + v_new * C
                points.append(P)
        return np.array(points)

    def optimize(config, max_iter):
        current_points = config.copy()
        current_min = get_smallest_triangle_area(current_points)
        step_size = 0.1
        no_improve_count = 0

        for iter in range(max_iter):
            best_improvement = 0
            best_candidate = None  # Will store (type, data)

            # Single-point moves: 8 directions
            for point_idx in range(11):
                for dx, dy in [(1,0), (-1,0), (0,1), (0,-1), (1,1), (1,-1), (-1,1), (-1,-1)]:
                    step = np.array([dx, dy]) * step_size
                    candidate_point = current_points[point_idx] + step
                    if not is_inside_triangle(candidate_point, A, B, C):
                        continue
                    candidate_config = current_points.copy()
                    candidate_config[point_idx] = candidate_point
                    candidate_min = get_smallest_triangle_area(candidate_config)
                    if candidate_min > current_min:
                        improvement = candidate_min - current_min
                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_candidate = ('single', point_idx, candidate_point, candidate_min)

            # Two-point moves if single-point failed
            if best_improvement == 0:
                for _ in range(10):  # 10 random pairs
                    i, j = np.random.choice(11, 2, replace=False)
                    for dx, dy in [(1,0), (-1,0), (0,1), (0,-1), (1,1), (1,-1), (-1,1), (-1,-1)]:
                        step = np.array([dx, dy]) * step_size
                        candidate_i = current_points[i] + step
                        candidate_j = current_points[j] - step
                        if not (is_inside_triangle(candidate_i, A, B, C) and 
                                is_inside_triangle(candidate_j, A, B, C)):
                            continue
                        candidate_config = current_points.copy()
                        candidate_config[i] = candidate_i
                        candidate_config[j] = candidate_j
                        candidate_min = get_smallest_triangle_area(candidate_config)
                        if candidate_min > current_min:
                            improvement = candidate_min - current_min
                            if improvement > best_improvement:
                                best_improvement = improvement
                                best_candidate = ('two', i, j, candidate_i, candidate_j, candidate_min)

            # Apply best improvement if found
            if best_improvement > 0:
                if best_candidate[0] == 'single':
                    _, idx, pt, current_min = best_candidate
                    current_points[idx] = pt
                else:
                    _, i, j, pt_i, pt_j, current_min = best_candidate
                    current_points[i] = pt_i
                    current_points[j] = pt_j
                no_improve_count = 0
            else:
                no_improve_count += 1
                # Adaptive step decay
                if no_improve_count >= 10:
                    step_size *= 0.9
                    no_improve_count = 0
                    if step_size < 0.001:
                        step_size = 0.001

        return current_points

    best_config = None
    best_min = -1
    # 20 restarts with per-restart seeding
    for restart in range(20):
        np.random.seed(42 + restart)
        random.seed(42 + restart)
        
        # Cycle through 10 patterns
        rows = patterns[restart % len(patterns)]
        config = generate_base_lattice(rows)
        
        # Validate all points (should be inside due to barycentric noise)
        for i in range(11):
            assert is_inside_triangle(config[i], A, B, C), f"Point {i} outside after barycentric noise"

        config = optimize(config, max_iter=500)
        min_area_val = get_smallest_triangle_area(config)
        if min_area_val > best_min:
            best_min = min_area_val
            best_config = config

    return best_config