import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import numpy as np

np.random.seed(42)
random.seed(42)

def triangle_area(a, b, c):
    return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    points = []
    
    # Literature-optimal row structure for 11 points with linear vertical spacing
    row_counts = [2, 3, 4, 2]  # Sum=11, known effective distribution
    v_levels = [0.2, 0.4, 0.6, 0.8]  # Linear spacing for 4 rows

    for i in range(len(row_counts)):
        num_points = row_counts[i]
        v = v_levels[i]
        for j in range(num_points):
            # Reduced random phase to preserve symmetry
            random_phase = random.uniform(-0.1, 0.1)
            angle = np.pi * (j + 0.5 + random_phase) / num_points
            u_val = 0.5 * (1 - np.cos(angle)) * (1 - v)
            
            P = (1 - u_val - v) * A + u_val * B + v * C
            
            # Reduced perturbation range for precise placement
            max_attempts = 10
            for _ in range(max_attempts):
                perturbation = np.random.uniform(-0.01, 0.01, size=2)
                P_pert = P + perturbation
                if is_inside_triangle(P_pert, A, B, C):
                    points.append(P_pert)
                    break
            else:
                points.append(P)

    points = np.array(points)
    
    # Simulated annealing optimization with geometry-aligned moves
    initial_T = 0.05
    cooling_rate = 0.995
    max_iter = 1000
    min_temp = 1e-5
    base_step = 0.05
    T = initial_T
    n = len(points)
    min_dist_threshold = 1e-5

    for _ in range(max_iter):
        current_min_area = get_smallest_triangle_area(points)
        
        # Find smallest triangle
        min_area_val = float('inf')
        min_triangle_indices = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = triangle_area(points[i], points[j], points[k])
                    if area < min_area_val:
                        min_area_val = area
                        min_triangle_indices = (i, j, k)

        if min_triangle_indices is None:
            break
            
        i, j, k = min_triangle_indices
        idx = np.random.choice([i, j, k])

        # Compute geometry-aligned move direction
        if idx == i:
            a, b, c = points[i], points[j], points[k]
            edge = c - b
            base_pt = b
            v = a - base_pt
        elif idx == j:
            a, b, c = points[i], points[j], points[k]
            edge = c - a
            base_pt = a
            v = b - base_pt
        else:  # idx == k
            a, b, c = points[i], points[j], points[k]
            edge = b - a
            base_pt = a
            v = c - base_pt

        perp = np.array([-edge[1], edge[0]])
        dot_val = np.dot(perp, v)
        if dot_val < 0:
            perp = -perp
        norm_perp = np.linalg.norm(perp)
        if norm_perp < 1e-8:
            continue
        direction = perp / norm_perp

        step = base_step * (T / initial_T)
        candidate = points.copy()
        candidate[idx] = points[idx] + step * direction

        # Check constraints
        if not is_inside_triangle(candidate[idx], A, B, C):
            continue
        
        too_close = False
        for k in range(n):
            if k == idx: continue
            if np.linalg.norm(candidate[idx] - candidate[k]) < min_dist_threshold:
                too_close = True
                break
        if too_close:
            continue

        new_min_area = get_smallest_triangle_area(candidate)
        delta = new_min_area - current_min_area

        # Simulated annealing acceptance
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            points = candidate

        # Cooling
        T *= cooling_rate
        if T < min_temp:
            break

    return points