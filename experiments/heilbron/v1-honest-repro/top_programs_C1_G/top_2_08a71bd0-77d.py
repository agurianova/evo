import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random

np.random.seed(42)
random.seed(42)

def project_to_triangle(P, A, B, C):
    def project_edge(P, A, B):
        AB = B - A
        AP = P - A
        t = np.dot(AP, AB) / (np.dot(AB, AB) + 1e-10)
        t = max(0.0, min(1.0, t))
        return A + t * AB

    proj_AB = project_edge(P, A, B)
    proj_BC = project_edge(P, B, C)
    proj_CA = project_edge(P, C, A)

    d_AB = np.linalg.norm(P - proj_AB)
    d_BC = np.linalg.norm(P - proj_BC)
    d_CA = np.linalg.norm(P - proj_CA)

    if d_AB <= d_BC and d_AB <= d_CA:
        return proj_AB
    elif d_BC <= d_AB and d_BC <= d_CA:
        return proj_BC
    else:
        return proj_CA

def signed_triangle_area(a, b, c):
    return 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))

def compute_gradient(points):
    n = len(points)
    min_area_val = get_smallest_triangle_area(points)
    gradient = np.zeros((n, 2))
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                s = signed_triangle_area(points[i], points[j], points[k])
                area = abs(s)
                if area <= min_area_val + 1e-8:
                    factor = 1.0 if s >= 0 else -1.0
                    dA = np.array([0.5*(points[j][1]-points[k][1]), 0.5*(points[k][0]-points[j][0])])
                    dB = np.array([0.5*(points[k][1]-points[i][1]), 0.5*(points[i][0]-points[k][0])])
                    dC = np.array([0.5*(points[i][1]-points[j][1]), 0.5*(points[j][0]-points[i][0])])
                    gradient[i] += factor * dA
                    gradient[j] += factor * dB
                    gradient[k] += factor * dC
    return gradient

def optimize_configuration(points, tri):
    A, B, C = tri
    points = np.array(points)
    step_size = 0.1
    max_iter = 100
    
    for iter in range(max_iter):
        grad = compute_gradient(points)
        grad_norm = np.linalg.norm(grad)
        if grad_norm < 1e-5:
            break
            
        step = step_size
        found = False
        for backtrack in range(20):
            new_points = points + step * grad
            for i in range(len(new_points)):
                if not is_inside_triangle(new_points[i], A, B, C):
                    new_points[i] = project_to_triangle(new_points[i], A, B, C)
            
            new_min_area = get_smallest_triangle_area(new_points)
            old_min_area = get_smallest_triangle_area(points)
            if new_min_area > old_min_area + 1e-10:
                points = new_points
                found = True
                break
            else:
                step *= 0.5
                
        if not found:
            break
            
    return points

def generate_hex_lattice(pattern, tri, perturbation_magnitude=0.02):
    A, B, C = tri
    points = []
    total_rows = len(pattern)
    
    for i, num_points in enumerate(pattern):
        v = (i + 0.5) / total_rows
        step = (1 - v) / num_points
        offset = step / 2 if i % 2 == 1 else 0
        
        for j in range(num_points):
            u = offset + j * step
            P = (1 - u - v) * A + u * B + v * C
            dy = perturbation_magnitude * (1 if j % 2 == 0 else -1)
            P[1] += dy
            points.append(P)
            
    return np.array(points)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri

    patterns = [
        [4, 3, 2, 1, 1],
        [5, 3, 2, 1],
        [3, 3, 3, 2]
    ]
    
    candidates = []
    for pattern in patterns:
        points = generate_hex_lattice(pattern, tri, perturbation_magnitude=0.02)
        candidates.append(points)

    optimized = []
    for points in candidates:
        opt_points = optimize_configuration(points, tri)
        optimized.append(opt_points)

    best_index = 0
    best_min_area = 0
    for i, points in enumerate(optimized):
        min_area = get_smallest_triangle_area(points)
        if min_area > best_min_area:
            best_min_area = min_area
            best_index = i

    return optimized[best_index]