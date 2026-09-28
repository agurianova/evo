import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    def min_boundary_distance(points):
        dists = []
        for P in points:
            # Distance to AB
            AB = B - A
            AP = P - A
            cross_ab = AB[0]*AP[1] - AB[1]*AP[0]
            area_ab = 0.5 * abs(cross_ab)
            base_ab = np.linalg.norm(AB)
            dist_ab = 2 * area_ab / base_ab

            # Distance to BC
            BC = C - B
            BP = P - B
            cross_bc = BC[0]*BP[1] - BC[1]*BP[0]
            area_bc = 0.5 * abs(cross_bc)
            base_bc = np.linalg.norm(BC)
            dist_bc = 2 * area_bc / base_bc

            # Distance to CA
            CA = A - C
            CP = P - C
            cross_ca = CA[0]*CP[1] - CA[1]*CP[0]
            area_ca = 0.5 * abs(cross_ca)
            base_ca = np.linalg.norm(CA)
            dist_ca = 2 * area_ca / base_ca

            min_dist = min(dist_ab, dist_bc, dist_ca)
            dists.append(min_dist)
        return min(dists)

    n_restarts = 50
    best_config = None
    best_min_area = -1

    for restart in range(n_restarts):
        # Symmetric row distributions for 11 points
        row_counts = random.choice([[1, 2, 3, 5], [1, 3, 3, 4]])
        n_rows = len(row_counts)
        points = []
        
        # Generate symmetric grid configuration
        for i in range(n_rows):
            v_i = 1 - (i + 0.5) / n_rows  # Weight for C (top-heavy)
            k = row_counts[i]
            total_weight_AB = 1 - v_i
            step = total_weight_AB / k
            
            for j in range(k):
                offset = (j - (k-1)/2) * step
                weight_A = total_weight_AB/2 - offset
                weight_B = total_weight_AB/2 + offset
                P = weight_A * A + weight_B * B + v_i * C
                points.append(P)
        points = np.array(points)
        
        # Apply Cartesian perturbations with validity checks
        max_attempts = 5
        perturbed_points = []
        for P in points:
            found = False
            for _ in range(max_attempts):
                r = 0.1 * math.sqrt(random.random())
                theta = 2 * math.pi * random.random()
                dx = r * math.cos(theta)
                dy = r * math.sin(theta)
                candidate = P + np.array([dx, dy])
                if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                    perturbed_points.append(candidate)
                    found = True
                    break
            if not found:
                perturbed_points.append(P)
        points = np.array(perturbed_points)
        
        # Simulated annealing optimization
        current_config = points.copy()
        current_min = get_smallest_triangle_area(current_config)
        current_boundary_dist = min_boundary_distance(current_config)
        current_value = current_min + 0.005 * current_boundary_dist
        
        n_points = len(current_config)
        max_iter = 3000
        initial_temp = 0.1
        cooling_rate = 0.95
        T = initial_temp

        for iter in range(max_iter):
            step_size = 0.05 * (1 - iter / max_iter)
            
            idx = random.randint(0, n_points - 1)
            r = step_size * math.sqrt(random.random())
            theta = 2 * math.pi * random.random()
            dx = r * math.cos(theta)
            dy = r * math.sin(theta)
            candidate_point = current_config[idx] + np.array([dx, dy])
            
            if not is_inside_triangle(candidate_point.reshape(1, 2), A, B, C):
                continue
                
            candidate_config = current_config.copy()
            candidate_config[idx] = candidate_point
            new_min = get_smallest_triangle_area(candidate_config)
            candidate_boundary_dist = min_boundary_distance(candidate_config)
            candidate_value = new_min + 0.005 * candidate_boundary_dist
            
            delta = candidate_value - current_value
            if delta > 0 or random.random() < math.exp(delta / T):
                current_config = candidate_config
                current_min = new_min
                current_boundary_dist = candidate_boundary_dist
                current_value = candidate_value
                
            T *= cooling_rate

        if current_min > best_min_area:
            best_min_area = current_min
            best_config = current_config.copy()

    return best_config