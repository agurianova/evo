import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri

    def generate_random_row_pattern():
        r = random.choice([4, 5])
        parts = [1] * r
        rem = 11 - r
        for _ in range(rem):
            idx = random.randint(0, r - 1)
            parts[idx] += 1
        return parts

    def generate_barycentric_lattice():
        rows = generate_random_row_pattern()
        r = len(rows)
        bary_points = []
        for i, k in enumerate(rows):
            gamma = 1 - (i + 0.5) / r
            total_ab = 1 - gamma
            for j in range(k):
                alpha = total_ab * (j + 0.5) / k
                beta = total_ab - alpha
                bary_points.append((alpha, beta, gamma))
        return bary_points

    def perturb_barycentric(bary_points, eps=0.05):
        cartesian_points = []
        for (alpha, beta, gamma) in bary_points:
            alpha_p = alpha + random.uniform(-eps, eps)
            beta_p = beta + random.uniform(-eps, eps)
            
            if alpha_p < 0:
                alpha_p = 0
            if beta_p < 0:
                beta_p = 0
            if alpha_p + beta_p > 1:
                scale = 1.0 / (alpha_p + beta_p)
                alpha_p *= scale
                beta_p *= scale
            gamma_p = 1 - alpha_p - beta_p
            
            P = alpha_p * A + beta_p * B + gamma_p * C
            cartesian_points.append(P)
        return np.array(cartesian_points)

    def optimize(config, max_iter):
        current_points = config.copy()
        current_min = get_smallest_triangle_area(current_points)

        for iter in range(max_iter):
            step_size = 0.1 * (0.99 ** iter)
            best_improvement = 0
            best_candidate = None

            # Single-point moves in 8 directions
            for point_idx in range(11):
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1), 
                               (1, 1), (-1, 1), (1, -1), (-1, -1)]:
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

            # Two-point coordinated moves if single-point fails
            if best_improvement == 0:
                for _ in range(5):
                    i, j = random.sample(range(11), 2)
                    dx, dy = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1), 
                                           (1, 1), (-1, 1), (1, -1), (-1, -1)])
                    step = np.array([dx, dy]) * step_size
                    candidate_config = current_points.copy()
                    candidate_config[i] += step
                    candidate_config[j] -= step
                    
                    if (is_inside_triangle(candidate_config[i], A, B, C) and 
                        is_inside_triangle(candidate_config[j], A, B, C)):
                        candidate_min = get_smallest_triangle_area(candidate_config)
                        if candidate_min > current_min:
                            improvement = candidate_min - current_min
                            if improvement > best_improvement:
                                best_improvement = improvement
                                best_candidate = ('double', i, j, step, candidate_min)

            # Apply best improvement
            if best_improvement > 0:
                if best_candidate[0] == 'single':
                    _, point_idx, candidate_point, current_min = best_candidate
                    current_points[point_idx] = candidate_point
                else:
                    _, i, j, step, current_min = best_candidate
                    current_points[i] += step
                    current_points[j] -= step

        return current_points

    best_config = None
    best_min = -1
    for restart in range(20):
        bary_points = generate_barycentric_lattice()
        config = perturb_barycentric(bary_points)
        
        # Validate configuration
        if not is_inside_triangle(config, A, B, C):
            continue
        
        config = optimize(config, max_iter=500)
        min_area_val = get_smallest_triangle_area(config)
        if min_area_val > best_min:
            best_min = min_area_val
            best_config = config

    return best_config