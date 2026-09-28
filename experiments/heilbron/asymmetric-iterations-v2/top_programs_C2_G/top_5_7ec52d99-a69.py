import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Compute triangle height for geometric scaling
    H = C[1]  # Since triangle is flat-bottomed with area=1.0
    
    # Initialize 11 points using balanced [4,4,3] grid (no fixed vertices)
    rows = 3
    points_per_row = [4, 4, 3]
    points = []
    for i in range(rows):
        v = (i + 1) / (rows + 1)  # Row positions: 0.25, 0.5, 0.75
        for j in range(points_per_row[i]):
            u = (j + 0.5) / points_per_row[i] * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            # Increased perturbation to prevent collinearity (±0.01 instead of ±0.001)
            P += np.random.uniform(-0.01, 0.01, size=2)
            points.append(P)
    
    current_points = np.array(points)
    current_min_area = get_smallest_triangle_area(current_points)

    # Geometrically scaled step sizes
    step_sizes = [0.02 * H, 0.01 * H, 0.005 * H]

    for step_size in step_sizes:
        no_improve_count = 0
        # Fixed 50 iterations per step size
        for _ in range(50):
            # Identify smallest triangle
            i, j, k = get_smallest_triangle_indices(current_points)
            best_candidate = None
            best_min_area = current_min_area
            
            # Adaptive trial count: 20 for base step, scales inversely with step_size
            base_step = 0.02 * H
            trials = int(20 * (base_step / step_size))

            for trial in range(trials):
                candidate = current_points.copy()
                # Randomly select TWO points from smallest triangle (mimicking opponent)
                idx1, idx2 = np.random.choice([i, j, k], 2, replace=False)
                
                # Perturb first point
                angle = np.random.uniform(0, 2*np.pi)
                dx = step_size * np.cos(angle)
                dy = step_size * np.sin(angle)
                candidate[idx1] += [dx, dy]
                if not is_inside_triangle(candidate[idx1], A, B, C):
                    candidate[idx1] -= [dx, dy]  # Revert if outside

                # Perturb second point
                angle = np.random.uniform(0, 2*np.pi)
                dx = step_size * np.cos(angle)
                dy = step_size * np.sin(angle)
                candidate[idx2] += [dx, dy]
                if not is_inside_triangle(candidate[idx2], A, B, C):
                    candidate[idx2] -= [dx, dy]  # Revert if outside

                new_min_area = get_smallest_triangle_area(candidate)
                if new_min_area > best_min_area:
                    best_min_area = new_min_area
                    best_candidate = candidate

            # Update if improvement found
            if best_candidate is not None:
                current_points = best_candidate
                current_min_area = best_min_area
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Restart mechanism after 10 consecutive non-improvements
            if no_improve_count >= 10:
                restart_candidate = current_points.copy()
                for idx in range(len(restart_candidate)):
                    angle = np.random.uniform(0, 2*np.pi)
                    r = np.random.uniform(0, step_size * 2)
                    dx = r * np.cos(angle)
                    dy = r * np.sin(angle)
                    new_point = restart_candidate[idx] + [dx, dy]
                    if is_inside_triangle(new_point, A, B, C):
                        restart_candidate[idx] = new_point
                
                # Accept restart even if min_area decreases (to escape local optimum)
                current_points = restart_candidate
                current_min_area = get_smallest_triangle_area(current_points)
                no_improve_count = 0

    return current_points

def get_smallest_triangle_indices(points):
    n = points.shape[0]
    min_area = float('inf')
    min_indices = (0, 1, 2)
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                 (points[k,0]-points[i,0])*(points[j,1]-points[i,1]))
                if area < min_area:
                    min_area = area
                    min_indices = (i, j, k)
    return min_indices