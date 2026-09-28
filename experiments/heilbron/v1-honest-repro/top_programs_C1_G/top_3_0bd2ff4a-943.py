import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    L = np.linalg.norm(B - A)  # Characteristic length (~1.52)

    # Random initialization with uniform barycentric sampling
    points = []
    while len(points) < 11:
        u = random.random()
        v = random.random()
        if u + v > 1:
            continue
        P = (1 - u - v) * A + u * B + v * C
        # Check distinctness
        if all(np.linalg.norm(P - p) > 1e-5 for p in points):
            points.append(P)
    current = np.array(points)
    current_min_area = get_smallest_triangle_area(current)

    # Simulated annealing parameters
    T = 0.5  # Increased from 0.01 per insight
    T_min = 1e-8  # Lowered from 1e-6
    alpha = 0.995
    steps_per_temp = 50

    while T > T_min:
        for step in range(steps_per_temp):
            # Adaptive multi-point perturbation (1/2/3 points)
            r = random.random()
            k = 1 if r < 0.7 else (2 if r < 0.95 else 3)
            indices = random.sample(range(11), k)
            
            # Generate candidate with k-point move
            candidate = current.copy()
            valid_move = True
            new_positions = []
            
            for i in indices:
                angle = random.uniform(0, 2 * np.pi)
                step_size = T * random.uniform(0, 0.1 * L)  # Scaled by triangle dimensions
                dx = step_size * np.cos(angle)
                dy = step_size * np.sin(angle)
                new_point = candidate[i] + np.array([dx, dy])
                new_positions.append((i, new_point))

            # Update candidate and validate
            for i, pt in new_positions:
                candidate[i] = pt
            
            # Check containment for moved points
            for i, pt in new_positions:
                if not is_inside_triangle(pt, A, B, C):
                    valid_move = False
                    break
            
            # Check distinctness
            if valid_move:
                for i in range(11):
                    for j in range(i+1, 11):
                        if np.linalg.norm(candidate[i] - candidate[j]) < 1e-5:
                            valid_move = False
                            break
                    if not valid_move:
                        break

            if not valid_move:
                continue

            new_min_area = get_smallest_triangle_area(candidate)

            # Acceptance criterion
            if new_min_area > current_min_area:
                current = candidate
                current_min_area = new_min_area
            else:
                delta = new_min_area - current_min_area
                if random.random() < np.exp(delta / T):
                    current = candidate
                    current_min_area = new_min_area

        T *= alpha

    # Final local search to ensure local optimum
    step_small = 0.001 * L
    directions = [
        (step_small, 0), (-step_small, 0),
        (0, step_small), (0, -step_small),
        (step_small, step_small), (step_small, -step_small),
        (-step_small, step_small), (-step_small, -step_small)
    ]
    improved = True
    while improved:
        improved = False
        for i in range(11):
            best_candidate = current
            best_min_area = current_min_area
            for dx, dy in directions:
                new_point = current[i] + np.array([dx, dy])
                if not is_inside_triangle(new_point, A, B, C):
                    continue
                # Check distinctness
                distinct = True
                for j in range(11):
                    if j == i: continue
                    if np.linalg.norm(new_point - current[j]) < 1e-5:
                        distinct = False
                        break
                if not distinct:
                    continue
                
                candidate = current.copy()
                candidate[i] = new_point
                new_min_area = get_smallest_triangle_area(candidate)
                
                if new_min_area > best_min_area:
                    best_min_area = new_min_area
                    best_candidate = candidate

            if best_min_area > current_min_area:
                current = best_candidate
                current_min_area = best_min_area
                improved = True
                break  # Restart scan after any improvement

    return current