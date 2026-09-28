import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Symmetric barycentric initialization (11 points)
    bary_coords = [
        (0.2, 0.2, 0.6),
        (0.2, 0.6, 0.2),
        (0.6, 0.2, 0.2),
        (0.1, 0.1, 0.8),
        (0.1, 0.8, 0.1),
        (0.8, 0.1, 0.1),
        (0.3, 0.3, 0.4),
        (0.3, 0.4, 0.3),
        (0.4, 0.3, 0.3),
        (0.4, 0.4, 0.2),
        (1/3, 1/3, 1/3)
    ]
    points = np.array([
        u * A + v * B + w * C
        for u, v, w in bary_coords
    ])

    # Track global best configuration
    best_global = points.copy()
    best_global_min = get_smallest_triangle_area(points)

    # Optimization parameters
    step_size = 0.1
    max_iter = 500
    stagnation_counter = 0
    max_stagnation = 50

    for _ in range(max_iter):
        current_min = get_smallest_triangle_area(points)
        improved = False

        # 1. Gradient moves for smallest triangle (primary)
        min_area_val = float('inf')
        min_tri = None
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    a, b, c = points[i], points[j], points[k]
                    # Compute signed area * 2
                    f = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                    area2 = abs(f)
                    if area2 < min_area_val:
                        min_area_val = area2
                        min_tri = (i, j, k, f)

        i, j, k, f = min_tri
        a, b, c = points[i], points[j], points[k]
        
        # Ensure positive orientation for gradient calculation
        if f < 0:
            j, k = k, j
            b, c = c, b
            f = -f

        # Compute gradients for triangle area
        grad_a = np.array([b[1]-c[1], c[0]-b[0]])
        grad_b = np.array([c[1]-a[1], a[0]-c[0]])
        grad_c = np.array([a[1]-b[1], b[0]-a[0]])

        # Try moving each point of the smallest triangle
        for point_idx, grad in zip([i, j, k], [grad_a, grad_b, grad_c]):
            candidate = points.copy()
            new_point = candidate[point_idx] + step_size * grad
            
            # Barycentric line search for boundary compliance
            if not is_inside_triangle(new_point, A, B, C):
                t = 1.0
                while t > 1e-5:
                    new_point = points[point_idx] + t * step_size * grad
                    if is_inside_triangle(new_point, A, B, C):
                        candidate[point_idx] = new_point
                        break
                    t *= 0.5
                else:
                    continue
            else:
                candidate[point_idx] = new_point

            new_min = get_smallest_triangle_area(candidate)
            if new_min > current_min:
                points = candidate
                improved = True
                if new_min > best_global_min:
                    best_global = points.copy()
                    best_global_min = new_min
                break

        if improved:
            stagnation_counter = 0
            continue

        # 2. Two-point random moves (fallback with increased coverage)
        pairs = set()
        while len(pairs) < 30:
            i, j = random.sample(range(11), 2)
            if i != j:
                pairs.add((min(i, j), max(i, j)))
        
        for i, j in pairs:
            best_candidate = None
            best_min = current_min
            for _ in range(50):
                angle1 = random.uniform(0, 2 * math.pi)
                angle2 = random.uniform(0, 2 * math.pi)
                candidate = points.copy()
                
                # Move point i
                dx1 = step_size * math.cos(angle1)
                dy1 = step_size * math.sin(angle1)
                candidate[i] = points[i] + [dx1, dy1]
                
                # Move point j
                dx2 = step_size * math.cos(angle2)
                dy2 = step_size * math.sin(angle2)
                candidate[j] = points[j] + [dx2, dy2]

                # Boundary handling via line search for both points
                valid = True
                for idx, pt in zip([i, j], [candidate[i], candidate[j]]):
                    if not is_inside_triangle(pt, A, B, C):
                        t = 1.0
                        while t > 1e-5:
                            new_pt = points[idx] + t * np.array([dx1, dy1] if idx == i else [dx2, dy2])
                            if is_inside_triangle(new_pt, A, B, C):
                                candidate[idx] = new_pt
                                break
                            t *= 0.5
                        else:
                            valid = False
                            break
                if not valid:
                    continue

                new_min = get_smallest_triangle_area(candidate)
                if new_min > best_min:
                    best_min = new_min
                    best_candidate = candidate

            if best_candidate is not None and best_min > current_min:
                points = best_candidate
                improved = True
                if best_min > best_global_min:
                    best_global = points.copy()
                    best_global_min = best_min
                break

        if improved:
            stagnation_counter = 0
            continue

        # 3. Stagnation handling
        step_size *= 0.99
        stagnation_counter += 1

        if step_size < 1e-5 or stagnation_counter >= max_stagnation:
            # Restart from perturbed global best
            points = best_global.copy()
            for idx in range(11):
                dx = random.uniform(-0.05 * 1.5197, 0.05 * 1.5197)
                dy = random.uniform(-0.05 * 1.3161, 0.05 * 1.3161)
                new_point = points[idx] + [dx, dy]
                if is_inside_triangle(new_point, A, B, C):
                    points[idx] = new_point
                else:
                    new_point = points[idx] - [dx, dy]
                    if is_inside_triangle(new_point, A, B, C):
                        points[idx] = new_point
            step_size = 0.1
            stagnation_counter = 0

    return best_global