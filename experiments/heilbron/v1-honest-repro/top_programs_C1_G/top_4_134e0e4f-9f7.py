import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def project_to_boundary(point, A, B, C, threshold=1e-3):
    """Project point to nearest boundary if within threshold distance"""
    def point_line_distance(p, a, b):
        # Distance from point p to line through a and b
        return np.abs(np.cross(b-a, a-p))/np.linalg.norm(b-a)
    
    dist_AB = point_line_distance(point, A, B)
    dist_BC = point_line_distance(point, B, C)
    dist_CA = point_line_distance(point, C, A)
    
    # If close to any boundary, project to it
    if dist_AB < threshold:
        # Project to AB
        ab = B - A
        t = np.dot(point - A, ab) / np.dot(ab, ab)
        t = max(0, min(1, t))
        return A + t * ab
    elif dist_BC < threshold:
        # Project to BC
        bc = C - B
        t = np.dot(point - B, bc) / np.dot(bc, bc)
        t = max(0, min(1, t))
        return B + t * bc
    elif dist_CA < threshold:
        # Project to CA
        ca = A - C
        t = np.dot(point - C, ca) / np.dot(ca, ca)
        t = max(0, min(1, t))
        return C + t * ca
    return point

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Calculate triangle properties
    side_length = np.linalg.norm(B - A)
    height = np.sqrt(3)/2 * side_length
    mid_x = (A[0] + B[0]) / 2
    mid_y = (A[1] + B[1]) / 2
    
    # Parameterized row configuration with controlled asymmetry
    base_rows = [1, 2, 3, 3, 2]
    if random.random() < 0.7:  # 70% chance of asymmetric configuration
        # Introduce controlled asymmetry by shifting points between rows
        asymmetry_factor = random.randint(0, 2)
        if asymmetry_factor == 1:  # Shift one point from row 3 to row 2
            base_rows = [1, 3, 2, 3, 2]
        elif asymmetry_factor == 2:  # Shift one point from row 4 to row 3
            base_rows = [1, 2, 4, 2, 2]
    # Else maintain symmetric configuration
    
    # Add tiny random perturbation to row counts to break symmetry
    rows = [max(1, r + random.randint(-1, 1)) for r in base_rows]
    # Ensure we have exactly 11 points
    while sum(rows) != 11:
        if sum(rows) > 11:
            idx = random.randint(0, 4)
            if rows[idx] > 1:
                rows[idx] -= 1
        else:
            idx = random.randint(0, 4)
            rows[idx] += 1

    total_rows = len(rows)
    points = []
    
    # Generate points with parameterized row configuration
    for i, m in enumerate(rows):
        v = 1 - (i + 0.5) / total_rows
        for j in range(m):
            u = (j + 0.5) / m * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            points.append(P)

    # Trim to exactly 11 points if needed
    current = np.array(points[:11])
    
    # Add tiny perturbation to avoid exact collinearity
    current += np.random.uniform(-1e-6, 1e-6, current.shape)
    current_min_area = get_smallest_triangle_area(current)

    # Enhanced simulated annealing parameters with higher exploration capacity
    T = 5.0  # Much higher initial temperature for broader exploration
    T_min = 1e-8
    alpha = 0.96  # Slower cooling rate for better exploration
    steps_per_temp = 100

    # Track success rate for adaptive move selection
    move_success = {1: 0.1, 2: 0.1, 3: 0.1}
    total_moves = {1: 1, 2: 1, 3: 1}
    stagnation_counter = 0
    max_stagnation = 50

    while T > T_min:
        improved_this_temp = False
        for step in range(steps_per_temp):
            # Find critical triangles (within 10% of minimum area)
            min_area = float('inf')
            n = len(current)
            
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = current[i], current[j], current[k]
                        area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        if area_val < min_area:
                            min_area = area_val

            # Collect triangles within 10% of minimum area
            critical_threshold = min_area * 1.1
            min_triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = current[i], current[j], current[k]
                        area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        if area_val <= critical_threshold:
                            min_triangles.append((i, j, k))

            # Temperature-based adaptive move weights
            temp_ratio = T / 5.0
            # Bias toward single-point moves early, multi-point later
            weights = [
                0.7 * (1 - temp_ratio) + 0.3 * temp_ratio,  # Single-point
                0.2 * (1 - temp_ratio) + 0.3 * temp_ratio,  # Two-point
                0.1 * (1 - temp_ratio) + 0.4 * temp_ratio   # Three-point
            ]
            k = random.choices([1, 2, 3], weights=weights)[0]
            
            # Adaptive step size with minimum constraint
            base_step = max(T * 0.1 * np.sqrt(min_area + 1e-10) * side_length, 
                            0.005 * side_length)  # Minimum step size constraint
            step_size = base_step / np.sqrt(k)
            
            # Select points to move - prioritize those in smallest triangles
            indices = set()
            if min_triangles:
                tri = min_triangles[random.randint(0, len(min_triangles)-1)]
                # Always include at least one point from a critical triangle
                indices.add(tri[random.randint(0, 2)])
                
            # Fill remaining points randomly if needed
            while len(indices) < k:
                idx = random.randint(0, 10)
                if idx not in indices:
                    indices.add(idx)
            
            indices = list(indices)
            new_points = []
            valid_move = True
            
            # Generate new positions for selected points
            for idx in indices:
                angle = random.uniform(0, 2 * np.pi)
                dx = step_size * np.cos(angle)
                dy = step_size * np.sin(angle)
                new_point = current[idx] + np.array([dx, dy])
                # Project to boundary if close
                new_point = project_to_boundary(new_point, A, B, C, threshold=1e-3)
                new_points.append(new_point)

            # Create candidate configuration
            candidate = current.copy()
            for idx, new_pt in zip(indices, new_points):
                candidate[idx] = new_pt

            # Check containment and distinctness
            if not is_inside_triangle(candidate, A, B, C):
                continue

            distinct = True
            for i in range(11):
                for j in range(i+1, 11):
                    if np.linalg.norm(candidate[i] - candidate[j]) < 1e-5:
                        distinct = False
                        break
                if not distinct:
                    break
            if not distinct:
                continue

            new_min_area = get_smallest_triangle_area(candidate)

            # Acceptance criterion
            if new_min_area > current_min_area:
                current = candidate
                current_min_area = new_min_area
                improved_this_temp = True
                # Record successful move
                move_success[k] += 1
            else:
                delta = new_min_area - current_min_area
                if random.random() < np.exp(delta / T):
                    current = candidate
                    current_min_area = new_min_area
                    improved_this_temp = True
                    # Record successful move
                    move_success[k] += 1
            
            # Record total move attempts
            total_moves[k] += 1

        # Update stagnation counter
        if improved_this_temp:
            stagnation_counter = 0
        else:
            stagnation_counter += 1
            
        # Apply symmetry-breaking perturbation after prolonged stagnation
        if stagnation_counter > max_stagnation * 0.8:
            symmetry_axis = mid_x
            for i in range(len(current)):
                if abs(current[i, 0] - symmetry_axis) < 1e-3:
                    # Point is on symmetry axis - perturb perpendicularly
                    current[i, 0] += 0.01 * side_length * (1 if random.random() > 0.5 else -1)
                elif current[i, 0] < symmetry_axis:
                    # Point is left of axis - perturb away from axis
                    current[i, 0] -= 0.005 * side_length
                else:
                    # Point is right of axis - perturb away from axis
                    current[i, 0] += 0.005 * side_length
            
            # Ensure points stay inside triangle
            for i in range(len(current)):
                if not is_inside_triangle(current[i], A, B, C):
                    # Project back if needed
                    current[i] = project_to_boundary(current[i], A, B, C)

        T *= alpha

    # Thorough local search targeting smallest triangles
    max_local_iters = 500
    for _ in range(max_local_iters):
        improved = False

        # Find critical triangles (within 10% of minimum area)
        min_area = float('inf')
        n = len(current)
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = current[i], current[j], current[k]
                    area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                    if area_val < min_area:
                        min_area = area_val

        critical_threshold = min_area * 1.1
        min_triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = current[i], current[j], current[k]
                    area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                    if area_val <= critical_threshold:
                        min_triangles.append((i, j, k))

        # Single-point local search focused on critical points
        critical_points = set()
        for tri in min_triangles:
            for idx in tri:
                critical_points.add(idx)

        for i in list(critical_points):
            for angle in np.linspace(0, 2*np.pi, 16, endpoint=False):
                # Adaptive step size with minimum constraint
                step = max(0.01 * np.sqrt(min_area + 1e-10) * side_length, 0.005 * side_length)
                dx = step * np.cos(angle)
                dy = step * np.sin(angle)
                new_point = current[i] + np.array([dx, dy])
                new_point = project_to_boundary(new_point, A, B, C, threshold=1e-3)
                
                if not is_inside_triangle(new_point, A, B, C):
                    continue

                distinct = True
                for j in range(11):
                    if j == i:
                        continue
                    if np.linalg.norm(new_point - current[j]) < 1e-5:
                        distinct = False
                        break
                if not distinct:
                    continue

                candidate = current.copy()
                candidate[i] = new_point
                new_min_area = get_smallest_triangle_area(candidate)
                
                if new_min_area > current_min_area:
                    current = candidate
                    current_min_area = new_min_area
                    improved = True
                    break  # Break angle loop
            if improved:
                break  # Break point loop

        if improved:
            continue

        # Two-point search on critical triangles
        if min_triangles:
            tri = min_triangles[random.randint(0, len(min_triangles)-1)]
            i, j, k = tri[0], tri[1], tri[2]
            # Randomly select two points from the critical triangle
            points_to_move = random.sample([i, j, k], 2)
            i, j = points_to_move[0], points_to_move[1]
            
            for attempt in range(50):
                angle_i = random.uniform(0, 2 * np.pi)
                angle_j = random.uniform(0, 2 * np.pi)
                # Adaptive step size with minimum constraint
                step = max(0.01 * np.sqrt(min_area + 1e-10) * side_length, 0.005 * side_length)
                
                dx_i = step * np.cos(angle_i)
                dy_i = step * np.sin(angle_i)
                dx_j = step * np.cos(angle_j)
                dy_j = step * np.sin(angle_j)
                
                new_i = current[i] + np.array([dx_i, dy_i])
                new_j = current[j] + np.array([dx_j, dy_j])
                new_i = project_to_boundary(new_i, A, B, C, threshold=1e-3)
                new_j = project_to_boundary(new_j, A, B, C, threshold=1e-3)
                
                if not (is_inside_triangle(new_i, A, B, C) and is_inside_triangle(new_j, A, B, C)):
                    continue

                distinct = True
                for k in range(11):
                    if k == i or k == j:
                        continue
                    if np.linalg.norm(new_i - current[k]) < 1e-5 or np.linalg.norm(new_j - current[k]) < 1e-5:
                        distinct = False
                        break
                if distinct and np.linalg.norm(new_i - new_j) < 1e-5:
                    distinct = False
                
                if not distinct:
                    continue

                candidate = current.copy()
                candidate[i] = new_i
                candidate[j] = new_j
                new_min_area = get_smallest_triangle_area(candidate)
                
                if new_min_area > current_min_area:
                    current = candidate
                    current_min_area = new_min_area
                    improved = True
                    break

        if improved:
            continue
        
        # Three-point search on critical triangles
        if min_triangles and random.random() < 0.6:  # Increased from 0.3 to 0.6
            tri = min_triangles[random.randint(0, len(min_triangles)-1)]
            i, j, k = tri[0], tri[1], tri[2]
            
            for attempt in range(30):
                angle_i = random.uniform(0, 2 * np.pi)
                angle_j = random.uniform(0, 2 * np.pi)
                angle_k = random.uniform(0, 2 * np.pi)
                # Adaptive step size with minimum constraint
                step = max(0.005 * np.sqrt(min_area + 1e-10) * side_length, 0.002 * side_length)
                
                dx_i = step * np.cos(angle_i)
                dy_i = step * np.sin(angle_i)
                dx_j = step * np.cos(angle_j)
                dy_j = step * np.sin(angle_j)
                dx_k = step * np.cos(angle_k)
                dy_k = step * np.sin(angle_k)
                
                new_i = current[i] + np.array([dx_i, dy_i])
                new_j = current[j] + np.array([dx_j, dy_j])
                new_k = current[k] + np.array([dx_k, dy_k])
                new_i = project_to_boundary(new_i, A, B, C, threshold=1e-3)
                new_j = project_to_boundary(new_j, A, B, C, threshold=1e-3)
                new_k = project_to_boundary(new_k, A, B, C, threshold=1e-3)
                
                if not (is_inside_triangle(new_i, A, B, C) and 
                        is_inside_triangle(new_j, A, B, C) and 
                        is_inside_triangle(new_k, A, B, C)):
                    continue

                distinct = True
                for idx, new_pt in enumerate([new_i, new_j, new_k]):
                    point_idx = [i, j, k][idx]
                    for l in range(11):
                        if l == point_idx:
                            continue
                        if np.linalg.norm(new_pt - current[l]) < 1e-5:
                            distinct = False
                            break
                    if not distinct:
                        break
                if distinct:
                    # Check pairwise distances among new points
                    if (np.linalg.norm(new_i - new_j) < 1e-5 or 
                        np.linalg.norm(new_i - new_k) < 1e-5 or 
                        np.linalg.norm(new_j - new_k) < 1e-5):
                        distinct = False
                
                if not distinct:
                    continue

                candidate = current.copy()
                candidate[i] = new_i
                candidate[j] = new_j
                candidate[k] = new_k
                new_min_area = get_smallest_triangle_area(candidate)
                
                if new_min_area > current_min_area:
                    current = candidate
                    current_min_area = new_min_area
                    improved = True
                    break

        if not improved:
            break

    return current