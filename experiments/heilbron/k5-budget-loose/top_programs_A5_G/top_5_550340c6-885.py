import random
import math
import numpy as np

from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Known near-optimal configuration for n=11 in unit-side equilateral triangle (Brass-Moser-Pach)
    # Scaled to unit-area triangle using k=1.5197 (base length of our triangle)
    k = 1.5197
    unit_side_config = [
        [0.25, 0.144337567],
        [0.5, 0.288675135],
        [0.75, 0.144337567],
        [0.125, 0.216506351],
        [0.375, 0.216506351],
        [0.625, 0.216506351],
        [0.875, 0.216506351],
        [0.25, 0.433012702],
        [0.5, 0.433012702],
        [0.75, 0.433012702],
        [0.5, 0.577350269]
    ]
    initial_config = np.array(unit_side_config) * k
    
    min_dist = 1e-5
    n_restarts = 5
    best_overall_min_area = -1
    best_overall_points = None

    for restart in range(n_restarts):
        points = initial_config.copy()
        
        # Perturb initial configuration slightly
        for i in range(11):
            noise = np.random.uniform(-0.001, 0.001, 2)
            new_point = points[i] + noise
            if is_inside_triangle(new_point, A, B, C):
                too_close = False
                for j in range(11):
                    if i == j: continue
                    if np.linalg.norm(new_point - points[j]) < min_dist:
                        too_close = True
                        break
                if not too_close:
                    points[i] = new_point

        # Simulated Annealing setup
        T0 = 0.5
        alpha = 0.999
        max_iter = 50000
        current_min_area = get_smallest_triangle_area(points)
        best_min_area = current_min_area
        best_points = points.copy()

        for iteration in range(max_iter):
            T = T0 * (alpha ** iteration)

            # Compute average interpoint distance for adaptive step sizing
            total_dist = 0.0
            count = 0
            for i in range(11):
                for j in range(i+1, 11):
                    total_dist += np.linalg.norm(points[i] - points[j])
                    count += 1
            avg_dist = total_dist / count
            step_size = T * (avg_dist / 5.0)

            # 70% chance: single-point move, 30% chance: two-point move
            if random.random() < 0.7:
                # Single-point move
                idx = random.randint(0, 10)
                current_point = points[idx]
                angle = random.uniform(0, 2 * math.pi)
                dx = step_size * math.cos(angle)
                dy = step_size * math.sin(angle)
                new_point = current_point + np.array([dx, dy])

                if not is_inside_triangle(new_point, A, B, C):
                    continue
                
                too_close = False
                for i in range(11):
                    if i == idx: continue
                    if np.linalg.norm(new_point - points[i]) < min_dist:
                        too_close = True
                        break
                if too_close:
                    continue

                candidate_points = points.copy()
                candidate_points[idx] = new_point
                new_min_area = get_smallest_triangle_area(candidate_points)
                delta = new_min_area - current_min_area
                
                if delta > 0 or random.random() < math.exp(delta / T):
                    points = candidate_points
                    current_min_area = new_min_area
                    if new_min_area > best_min_area:
                        best_min_area = new_min_area
                        best_points = points.copy()

            else:
                # Two-point move: move two points oppositely along their connecting vector
                idx1, idx2 = random.sample(range(11), 2)
                p1, p2 = points[idx1], points[idx2]
                v = p2 - p1
                v_norm = np.linalg.norm(v)
                if v_norm < 1e-10:
                    continue
                v_unit = v / v_norm
                
                # Random direction: apart or together
                sign = 1 if random.random() < 0.5 else -1
                disp = sign * step_size * v_unit
                
                new_p1 = p1 + disp
                new_p2 = p2 - disp

                if not (is_inside_triangle(new_p1, A, B, C) and is_inside_triangle(new_p2, A, B, C)):
                    continue
                
                too_close = False
                for i in range(11):
                    if i == idx1 or i == idx2: continue
                    if np.linalg.norm(new_p1 - points[i]) < min_dist or np.linalg.norm(new_p2 - points[i]) < min_dist:
                        too_close = True
                        break
                if too_close:
                    continue

                candidate_points = points.copy()
                candidate_points[idx1] = new_p1
                candidate_points[idx2] = new_p2
                new_min_area = get_smallest_triangle_area(candidate_points)
                delta = new_min_area - current_min_area
                
                if delta > 0 or random.random() < math.exp(delta / T):
                    points = candidate_points
                    current_min_area = new_min_area
                    if new_min_area > best_min_area:
                        best_min_area = new_min_area
                        best_points = points.copy()

        # Single-point local search to ensure local optimality
        step_local = 1e-4
        improved = True
        while improved:
            improved = False
            for i in range(11):
                for dx in [-step_local, 0, step_local]:
                    for dy in [-step_local, 0, step_local]:
                        if dx == 0 and dy == 0:
                            continue
                        new_point = best_points[i] + np.array([dx, dy])
                        if not is_inside_triangle(new_point, A, B, C):
                            continue
                        
                        too_close = False
                        for j in range(11):
                            if j == i: continue
                            if np.linalg.norm(new_point - best_points[j]) < min_dist:
                                too_close = True
                                break
                        if too_close:
                            continue

                        candidate = best_points.copy()
                        candidate[i] = new_point
                        new_min_area = get_smallest_triangle_area(candidate)
                        if new_min_area > best_min_area:
                            best_points = candidate
                            best_min_area = new_min_area
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break

        # Track best configuration across restarts
        if best_min_area > best_overall_min_area:
            best_overall_min_area = best_min_area
            best_overall_points = best_points.copy()

    return best_overall_points