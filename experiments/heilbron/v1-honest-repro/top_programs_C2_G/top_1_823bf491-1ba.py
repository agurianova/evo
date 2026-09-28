import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(123)

def entrypoint() -> np.ndarray:
    # Get triangle vertices and compute dimensions
    A, B, C = get_unit_triangle()
    L = B[0] - A[0]  # Base length (1.5197)
    H = C[1] - A[1]  # Height (1.3161)

    # Generate hexagonal lattice with 11 points (4,3,2,2 rows)
    s = L / 4.0  # Optimal spacing for 11 points
    rows = [(0, 4), (1, 3), (2, 2), (3, 2)]  # (row_index, num_points)
    points = []
    
    for row_idx, n_points in rows:
        y = row_idx * (np.sqrt(3) / 2) * s
        # Calculate horizontal boundaries at current height
        x_left = (L / (2 * H)) * y
        x_right = L - x_left
        width = x_right - x_left
        
        if n_points > 1:
            total_span = (n_points - 1) * s
            if total_span > width:
                total_span = width
            start_x = x_left + (width - total_span) / 2
        else:
            start_x = (x_left + x_right) / 2
            
        for j in range(n_points):
            x = start_x + j * s
            points.append([x, y])
    
    # Apply controlled symmetry-breaking initial perturbation
    perturbed_points = []
    for x, y in points:
        dx = np.random.uniform(-0.05, 0.05)
        dy = np.random.uniform(-0.05, 0.05)
        new_pt = [x + dx, y + dy]
        if is_inside_triangle(np.array([new_pt]), A, B, C):
            perturbed_points.append(new_pt)
        else:
            perturbed_points.append([x, y])
    
    # Initialize optimization state
    current = np.array(perturbed_points)
    current_score = get_smallest_triangle_area(current)
    best = current.copy()
    best_score = current_score
    
    # Adaptive parameters
    T = 0.1
    cooling_rate = 0.98
    step_size = 0.1
    max_iter = 2000
    last_improve_iter = 0
    n = len(current)

    for iter in range(max_iter):
        # Compute per-point minimum triangle area weights
        min_area_per_point = [float('inf')] * n
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        (current[j,0]-current[i,0])*(current[k,1]-current[i,1]) -
                        (current[k,0]-current[i,0])*(current[j,1]-current[i,1])
                    )
                    for idx in [i, j, k]:
                        if area < min_area_per_point[idx]:
                            min_area_per_point[idx] = area
        
        # Calculate perturbation weights (higher for bottleneck points)
        weights = np.array([1.0 / (a + 1e-5) for a in min_area_per_point])
        weights /= weights.sum()
        
        # Select point to perturb based on weights
        idx = np.random.choice(n, p=weights)
        
        # Generate perturbation
        angle = np.random.uniform(0, 2*np.pi)
        dx = step_size * np.cos(angle)
        dy = step_size * np.sin(angle)
        candidate = current.copy()
        candidate[idx] = [current[idx,0] + dx, current[idx,1] + dy]
        
        # Validate containment
        if not is_inside_triangle(candidate[idx:idx+1], A, B, C):
            step_size = max(0.01, step_size * 0.9)
            T *= cooling_rate
            continue
        
        # Evaluate candidate
        new_score = get_smallest_triangle_area(candidate)
        if new_score <= 0:
            step_size = max(0.01, step_size * 0.9)
            T *= cooling_rate
            continue

        # Simulated annealing acceptance
        delta = new_score - current_score
        accepted = (delta > 0) or (np.random.rand() < np.exp(delta / T))
        
        if accepted:
            current = candidate
            current_score = new_score
            improved_global = False
            
            if new_score > best_score:
                best = candidate
                best_score = new_score
                improved_global = True
                last_improve_iter = iter

            # Adaptive step size adjustment
            if improved_global:
                step_size = min(0.2, step_size * 1.1)
            else:
                # Maintain step size for non-global improvements
                pass
        else:
            step_size = max(0.01, step_size * 0.9)

        # Cooling and restart mechanism
        T *= cooling_rate
        if iter - last_improve_iter > 500:
            T = 0.1
            step_size = 0.1
            last_improve_iter = iter

    return best