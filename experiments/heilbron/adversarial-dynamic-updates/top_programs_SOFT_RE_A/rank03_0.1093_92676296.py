import random

from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate initial grid with known robust row structure (4,3,3,1)
    rows = [4, 3, 3, 1]
    row_heights = [0.2, 0.4, 0.7, 0.9]  # v-coordinates in barycentric system
    
    points = []
    for i, num_points in enumerate(rows):
        v = row_heights[i]
        for j in range(num_points):
            u = (j + 0.5) / num_points * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            points.append(P)
    
    # Apply Gaussian perturbation to break residual symmetries
    points = np.array(points)
    perturbation = np.random.normal(0, 0.005, size=points.shape)
    points += perturbation
    
    # Simulated annealing to maximize min_area (20 steps)
    current_points = points.copy()
    current_score = get_smallest_triangle_area(current_points)
    
    for step in range(20):
        T = 0.01 * (0.95 ** step)
        candidate = current_points.copy()
        idx = np.random.randint(0, 11)
        move = np.random.normal(0, T, size=2)
        candidate[idx] += move
        
        # Skip if candidate moves outside triangle
        if not is_inside_triangle(candidate, A, B, C):
            continue
        
        new_score = get_smallest_triangle_area(candidate)
        delta = new_score - current_score
        
        # Metropolis acceptance for maximization
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            current_points = candidate
            current_score = new_score

    return current_points