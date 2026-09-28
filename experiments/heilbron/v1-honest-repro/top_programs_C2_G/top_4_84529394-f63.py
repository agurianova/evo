import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import numpy as np

np.random.seed(123)
random.seed(123)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate initial grid with literature-validated symmetric structure
    row_counts = [1, 3, 3, 3, 1]  # Total 11 points (known optimal for n=11)
    v_levels = [1 - i/4 for i in range(5)]  # Linear vertical spacing for uniform density

    points = []
    for i in range(len(row_counts)):
        num_points = row_counts[i]
        v = v_levels[i]
        phase = np.random.uniform(0, 1)
        for j in range(num_points):
            u_val = 0.5 * (1 - np.cos(np.pi * (j + phase) / num_points)) * (1 - v)
            P = (1 - u_val - v) * A + u_val * B + v * C
            
            # Apply larger symmetry-breaking perturbation
            max_attempts = 10
            for _ in range(max_attempts):
                perturbation = np.random.uniform(-0.15, 0.15, size=2)
                P_pert = P + perturbation
                if is_inside_triangle(P_pert, A, B, C):
                    points.append(P_pert)
                    break
            else:
                points.append(P)

    points = np.array(points)
    
    def triangle_area_signed(p1, p2, p3):
        return 0.5 * ((p2[0]-p1[0])*(p3[1]-p1[1]) - (p2[1]-p1[1])*(p3[0]-p1[0]))

    # Simulated annealing parameters
    max_iter = 1000
    initial_temp = 0.005
    temp_decay = 0.995

    for iter in range(max_iter):
        min_area_old = get_smallest_triangle_area(points)
        
        # Adaptive step size based on progress toward theoretical max (0.0365)
        step_size = max(0.02, 0.05 * (1 - min_area_old / 0.0365))
        
        # Consider triangles within 20% of current minimum (wider exploration)
        critical_threshold = 1.2 * min_area_old
        
        # Identify critical triangles
        critical_triangles = []
        n = len(points)
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area_val = abs(triangle_area_signed(points[i], points[j], points[k]))
                    if area_val <= critical_threshold:
                        critical_triangles.append((i, j, k))

        if not critical_triangles:
            break

        # Compute displacement vectors
        disp = np.zeros((n, 2))
        for (i, j, k) in critical_triangles:
            P, Q, R = points[i], points[j], points[k]
            area_signed = triangle_area_signed(P, Q, R)
            sign = np.sign(area_signed) if area_signed != 0 else 1.0

            grad_P = 0.5 * np.array([Q[1]-R[1], R[0]-Q[0]]) * sign
            grad_Q = 0.5 * np.array([R[1]-P[1], P[0]-R[0]]) * sign
            grad_R = 0.5 * np.array([P[1]-Q[1], Q[0]-P[0]]) * sign

            disp[i] += grad_P
            disp[j] += grad_Q
            disp[k] += grad_R

        # Normalize and scale displacements
        for i in range(n):
            norm = np.linalg.norm(disp[i])
            if norm > 1e-8:
                disp[i] = step_size * disp[i] / norm

        # Move points and project to triangle if outside
        new_points = points + disp
        for i in range(n):
            if not is_inside_triangle(new_points[i], A, B, C):
                t_low, t_high = 0.0, 1.0
                while t_high - t_low > 1e-5:
                    t_mid = (t_low + t_high) / 2
                    candidate = points[i] + t_mid * disp[i]
                    if is_inside_triangle(candidate, A, B, C):
                        t_low = t_mid
                    else:
                        t_high = t_mid
                new_points[i] = points[i] + t_low * disp[i]

        new_min_area = get_smallest_triangle_area(new_points)
        
        # Simulated annealing acceptance
        temperature = initial_temp * (temp_decay ** iter)
        if new_min_area > min_area_old:
            points = new_points
        else:
            delta = new_min_area - min_area_old
            if random.random() < np.exp(delta / temperature):
                points = new_points

    return points