import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Helper function for boundary projection
    def project_to_triangle(P, A, B, C):
        v0 = B - A
        v1 = C - A
        v2 = P - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        if abs(denom) < 1e-10:
            return P
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        if v < 0:
            v = 0
        if w < 0:
            w = 0
        if v + w > 1:
            scale = 1.0 / (v + w)
            v *= scale
            w *= scale
        return A + v * (B - A) + w * (C - A)

    # Generate balanced grid (3,3,2,2,1 points per row)
    rows = 5
    counts = [3, 3, 2, 2, 1]
    total_height = 1.3161  # Height of unit-area equilateral triangle
    points = []
    for row in range(rows):
        num_points = counts[row]
        v_coord = (row + 0.5) / rows
        scale = v_coord * total_height  # Row height for perturbation scaling
        for i in range(num_points):
            u_coord = (i + 0.5) / num_points * (1 - v_coord)
            P = (1 - u_coord - v_coord) * A + u_coord * B + v_coord * C
            # Scale perturbation by local row height
            perturbation = np.random.uniform(-0.01, 0.01, size=2) * scale
            P = P + perturbation
            points.append(P)
    points = np.array(points)
    
    # Simulated annealing parameters
    n_iterations = 5000
    initial_temp = 0.1
    decay = 0.995
    base_step = 0.1
    T = initial_temp
    current_min_area = get_smallest_triangle_area(points)

    for _ in range(n_iterations):
        # Find the single smallest triangle
        min_area = float('inf')
        min_triangle = None
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    a, b, c = points[i], points[j], points[k]
                    s_val = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                    area_val = 0.5 * abs(s_val)
                    if area_val < min_area:
                        min_area = area_val
                        min_triangle = (i, j, k)

        if min_triangle is None:
            break
        
        i, j, k = min_triangle
        a, b, c = points[i], points[j], points[k]
        s_val = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        factor = 1.0 if s_val >= 0 else -1.0
        
        # Compute normalized gradients for area maximization
        grad_a = factor * np.array([b[1]-c[1], c[0]-b[0]])
        grad_b = factor * np.array([c[1]-a[1], a[0]-c[0]])
        grad_c = factor * np.array([a[1]-b[1], b[0]-a[0]])
        
        if np.linalg.norm(grad_a) > 1e-8:
            grad_a = grad_a / np.linalg.norm(grad_a)
        if np.linalg.norm(grad_b) > 1e-8:
            grad_b = grad_b / np.linalg.norm(grad_b)
        if np.linalg.norm(grad_c) > 1e-8:
            grad_c = grad_c / np.linalg.norm(grad_c)

        # Temperature-scaled step
        step = base_step * (T / initial_temp)
        candidate = points.copy()
        candidate[i] = a + step * grad_a
        candidate[j] = b + step * grad_b
        candidate[k] = c + step * grad_c

        # Project candidate points to triangle boundary if outside
        for idx in [i, j, k]:
            candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

        # Evaluate candidate
        new_min_area = get_smallest_triangle_area(candidate)
        delta = new_min_area - current_min_area
        
        # Metropolis acceptance
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            points = candidate
            current_min_area = new_min_area

        # Cool down
        T *= decay

    return points