import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate multiple perturbed initial configurations based on literature patterns
    best_points = None
    best_min_area = -1
    
    for restart in range(5):
        # Literature-derived row structure with randomized perturbations to break collinearity
        row_counts = [1, 2, 3, 4, 1]
        v_levels = [0.90, 0.70, 0.50, 0.30, 0.00]  # Base levels from known distributions
        points = []
        
        for i in range(len(row_counts)):
            num_points = row_counts[i]
            v = v_levels[i] + random.uniform(-0.01, 0.01)  # Break row alignment
            for j in range(num_points):
                # Add horizontal offset to prevent straight-line degeneracy
                u_val = (1 - v) * (j + 0.5 + random.uniform(-0.1, 0.1)) / num_points
                P = (1 - u_val - v) * A + u_val * B + v * C
                points.append(P)

        points = np.array(points)
        
        # Simulated Annealing with corrected parameters
        current_points = points.copy()
        current_min_area = get_smallest_triangle_area(current_points)
        n_points = len(current_points)

        T = 0.1  # Increased from 0.01 for larger initial steps
        cooling_rate = 0.999  # Slower cooling for thorough exploration
        max_iter_sa = 100000

        for _ in range(max_iter_sa):
            T *= cooling_rate
            if T < 1e-5:
                break
            
            i = random.randint(0, n_points-1)
            step = T * 0.1  # Proportional step sizing
            angle = random.uniform(0, 2 * math.pi)
            dx = step * math.cos(angle)
            dy = step * math.sin(angle)
            
            candidate = current_points.copy()
            candidate[i] = current_points[i] + np.array([dx, dy])
            
            if not is_inside_triangle(candidate[i], A, B, C):
                continue
                
            new_min_area = get_smallest_triangle_area(candidate)
            delta = new_min_area - current_min_area

            if delta > 0 or random.random() < np.exp(delta / T):
                current_points = candidate
                current_min_area = new_min_area

        # Enhanced Hill-Climbing with adaptive steps
        points = current_points
        current_min_area = get_smallest_triangle_area(points)
        max_iter_hc = 5000
        step_size = 0.01
        min_improvement = 1e-10
        stagnation_count = 0
        directions = [(math.cos(math.radians(a)), math.sin(math.radians(a))) 
                     for a in range(0, 360, 22)]  # 16 directions

        for _ in range(max_iter_hc):
            best_improvement = 0.0
            best_point_index = None
            best_direction = None

            for i in range(n_points):
                for (dx, dy) in directions:
                    candidate = points.copy()
                    candidate[i] = points[i] + np.array([step_size * dx, step_size * dy])
                    if not is_inside_triangle(candidate[i], A, B, C):
                        continue
                    new_min_area = get_smallest_triangle_area(candidate)
                    improvement = new_min_area - current_min_area
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_point_index = i
                        best_direction = (dx, dy)

            if best_improvement < min_improvement:
                stagnation_count += 1
                if stagnation_count > 10:
                    step_size *= 0.9  # Reduce step on stagnation
                    stagnation_count = 0
                    if step_size < 1e-5:
                        break
                continue
            
            stagnation_count = 0
            points[best_point_index] += np.array([step_size * best_direction[0], step_size * best_direction[1]])
            current_min_area += best_improvement

        # Track best configuration across restarts
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_points = points.copy()

    return best_points