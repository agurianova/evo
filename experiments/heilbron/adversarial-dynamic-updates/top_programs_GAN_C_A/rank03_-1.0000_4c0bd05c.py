import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Candidate row distributions (asymmetric patterns for n=11)
    distributions = [
        [5, 3, 2, 1],
        [4, 3, 3, 1],
        [4, 4, 2, 1],
        [3, 3, 3, 2],
        [6, 3, 2],       # Added new distribution
        [5, 4, 2]        # Added new distribution
    ]
    
    best_config = None
    best_score = -1
    
    # Helper to find indices of smallest triangles (top k)
    def compute_min_triangle_indices(points, k=3):
        n = points.shape[0]
        triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    triangles.append((area, i, j, k))
        
        triangles.sort(key=lambda x: x[0])
        return triangles[:k]

    # Helper for multi-bottleneck scoring
    def compute_score(triangles):
        # Weight top 3 smallest triangles (0.7, 0.2, 0.1)
        weights = [0.7, 0.2, 0.1]
        score = 0.0
        for i, (area, _, _, _) in enumerate(triangles):
            if i < len(weights):
                score += weights[i] * area
        return score

    # Generate hexagonal lattice configuration
    def generate_hexagonal_lattice():
        points = []
        rows = 4
        points_per_row = [3, 4, 3, 1]  # Hexagonal pattern for 11 points
        
        # Boundary buffer (1.5% of height)
        buffer = 0.015
        height = C[1] - A[1]
        
        for i, num_in_row in enumerate(points_per_row):
            # Add vertical buffer to keep points away from edges
            v = (i + 0.5) / (rows - 1 + 2*buffer) * (1 - 2*buffer) + buffer
            for j in range(num_in_row):
                # Horizontal offset for hexagonal pattern
                u_offset = 0.5 if i % 2 == 1 else 0
                u = ((j + 0.5 + u_offset) / num_in_row) * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                # Larger perturbation to break symmetry
                perturbation = np.random.uniform(-0.05 * (1 - v), 0.05 * (1 - v), size=2)
                points.append(P + perturbation)
        return np.array(points)

    # Try row-based distributions
    for row_dist in distributions:
        points = []
        rows = len(row_dist)
        
        # Generate initial grid with larger perturbation
        for i, num_in_row in enumerate(row_dist):
            v = (i + 0.5) / rows
            for j in range(num_in_row):
                u = (j + 0.5) / num_in_row * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                # Increased perturbation magnitude (0.01 → 0.05)
                perturbation = np.random.uniform(-0.05 * (1 - v), 0.05 * (1 - v), size=2)
                points.append(P + perturbation)

        current = np.array(points)
        min_triangles = compute_min_triangle_indices(current, k=3)
        current_score = compute_score(min_triangles)
        
        # Simulated annealing parameters (improved)
        initial_temp = 0.01  # Increased from 0.001
        temp_decay = 0.999   # Slower cooling
        initial_step = 0.02
        step_decay = 0.9995  # Slower step decay
        max_iter = 5000
        early_stop = 500
        
        temp = initial_temp
        step_size = initial_step
        no_improve = 0
        
        # Track best in this restart
        restart_best = current.copy()
        restart_best_triangles = min_triangles
n        restart_best_score = current_score
        
        for it in range(max_iter):
            # Identify bottleneck triangles (top 3)
            min_triangles = compute_min_triangle_indices(current, k=3)
            
            # 70% chance to perturb bottleneck points
            if np.random.rand() < 0.7:
                # Flatten indices from top triangles
                all_indices = set()
                for _, i, j, k in min_triangles:
                    all_indices.update([i, j, k])
                all_indices = list(all_indices)
                idx = np.random.choice(all_indices)
            else:
                idx = np.random.randint(0, 11)

            # Generate candidate move
            step = np.random.normal(0, step_size, size=2)
            candidate = current.copy()
            candidate[idx] += step

            # Validate containment
            if not is_inside_triangle(candidate[idx], A, B, C):
                continue

            # Evaluate candidate using multi-bottleneck score
            new_min_triangles = compute_min_triangle_indices(candidate, k=3)
            new_score = compute_score(new_min_triangles)

            # Simulated annealing acceptance
            if new_score > current_score:
                current = candidate
                current_score = new_score
                if new_score > restart_best_score:
                    restart_best = candidate.copy()
                    restart_best_triangles = new_min_triangles
                    restart_best_score = new_score
                no_improve = 0
            else:
                delta = current_score - new_score
                if np.random.rand() < np.exp(-delta / temp):
                    current = candidate
                    current_score = new_score
                    no_improve = 0
                else:
                    no_improve += 1

            # Adaptive cooling
            temp *= temp_decay
            step_size *= step_decay

            # Early stopping
            if no_improve >= early_stop:
                break

        # Update global best
        if restart_best_score > best_score:
            best_score = restart_best_score
            best_config = restart_best

    # Try hexagonal lattice initialization
    hex_config = generate_hexagonal_lattice()
    hex_triangles = compute_min_triangle_indices(hex_config, k=3)
    hex_score = compute_score(hex_triangles)
    
    if hex_score > best_score:
        best_score = hex_score
        best_config = hex_config

    # Final simulated annealing refinement
    current = best_config.copy()
    min_triangles = compute_min_triangle_indices(current, k=3)
    current_score = compute_score(min_triangles)
    
    # Final refinement parameters
    temp = 0.005
    step_size = 0.01
    no_improve = 0
    max_final_iter = 2000
    
    for it in range(max_final_iter):
        min_triangles = compute_min_triangle_indices(current, k=3)
        
        # Always perturb bottleneck points in final refinement
        all_indices = set()
        for _, i, j, k in min_triangles:
            all_indices.update([i, j, k])
        all_indices = list(all_indices)
        idx = np.random.choice(all_indices)

        step = np.random.normal(0, step_size, size=2)
        candidate = current.copy()
        candidate[idx] += step

        if not is_inside_triangle(candidate[idx], A, B, C):
            continue

        new_min_triangles = compute_min_triangle_indices(candidate, k=3)
        new_score = compute_score(new_min_triangles)

        if new_score > current_score:
            current = candidate
            current_score = new_score
            no_improve = 0
        else:
            delta = current_score - new_score
            if np.random.rand() < np.exp(-delta / temp):
                current = candidate
                current_score = new_score
                no_improve = 0
            else:
                no_improve += 1

        temp *= 0.998
        step_size *= 0.999

        if no_improve >= 300:
            break

    if current_score > best_score:
        best_config = current

    return best_config