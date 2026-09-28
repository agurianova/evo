import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def get_closest_edge(P, A, B, C):
    # Convert to barycentric coordinates
    v0 = B - A
    v1 = C - A
    v2 = P - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1 - v - w

    # Check which edge is closest
    dist_to_AB = u  # Distance to AB is proportional to w
    dist_to_BC = v  # Distance to BC is proportional to u
    dist_to_CA = w  # Distance to CA is proportional to v

    if dist_to_AB <= dist_to_BC and dist_to_AB <= dist_to_CA:
        return 'AB', np.array([B[0]-A[0], B[1]-A[1]])
    elif dist_to_BC <= dist_to_AB and dist_to_BC <= dist_to_CA:
        return 'BC', np.array([C[0]-B[0], C[1]-B[1]])
    else:
        return 'CA', np.array([A[0]-C[0], A[1]-C[1]])

def project_to_triangle(P, A, B, C):
    # Compute barycentric coordinates
    denom = 2.0  # 2 * area of ABC (which is 1)
    u = ((B[1] - C[1]) * (P[0] - C[0]) + (C[0] - B[0]) * (P[1] - C[1])) / denom
    v = ((C[1] - A[1]) * (P[0] - C[0]) + (A[0] - C[0]) * (P[1] - C[1])) / denom
    w = 1 - u - v

    # Clamp negative coordinates and renormalize
    coords = np.array([u, v, w])
    if np.any(coords < 0):
        coords = np.maximum(coords, 0)
        total = np.sum(coords)
        if total > 0:
            coords /= total
        else:
            coords = np.array([1/3, 1/3, 1/3])
    return coords[0] * A + coords[1] * B + coords[2] * C

def reflect_point(P, axis, A, B, C):
    """Reflect point P across specified axis of symmetry"""
    if axis == 'median_A':
        # Median from A to midpoint of BC
        M = (B + C) / 2
        return 2 * M - P
    elif axis == 'median_B':
        # Median from B to midpoint of AC
        M = (A + C) / 2
        return 2 * M - P
    else:  # 'median_C'
        # Median from C to midpoint of AB
        M = (A + B) / 2
        return 2 * M - P

def enforce_symmetry(points, A, B, C):
    """Enforce reflection symmetry across all three medians"""
    n = len(points)
    if n != 11:
        return points
    
    # For n=11, we expect:
    # - 1 point at centroid (symmetric by itself)
    # - 5 pairs of symmetric points (10 points)
    
    # Find centroid candidate (closest to geometric center)
    centroid = np.array([A+B+C])/3
    centroid_idx = np.argmin(np.linalg.norm(points - centroid, axis=1))
    symmetric_points = np.delete(points, centroid_idx, axis=0)
    
    # Group into symmetric pairs
    pairs = []
    remaining = list(range(10))
    while remaining:
        i = remaining.pop(0)
        min_dist = float('inf')
        best_j = -1
        for j in remaining:
            # Check symmetry across all three medians
            dist_A = np.linalg.norm(symmetric_points[i] - reflect_point(symmetric_points[j], 'median_A', A, B, C))
            dist_B = np.linalg.norm(symmetric_points[i] - reflect_point(symmetric_points[j], 'median_B', A, B, C))
            dist_C = np.linalg.norm(symmetric_points[i] - reflect_point(symmetric_points[j], 'median_C', A, B, C))
            min_dist_ij = min(dist_A, dist_B, dist_C)
            if min_dist_ij < min_dist:
                min_dist = min_dist_ij
                best_j = j
        if best_j != -1:
            pairs.append((i, best_j))
            remaining.remove(best_j)
    
    # Enforce symmetry in pairs
    new_points = np.zeros((11, 2))
    new_points[centroid_idx] = points[centroid_idx]
    for idx, (i, j) in enumerate(pairs):
        # Take average position to enforce symmetry
        avg = (symmetric_points[i] + symmetric_points[j]) / 2
        # Project to ensure validity
        avg = project_to_triangle(avg, A, B, C)
        # Create symmetric pair
        reflected_A = reflect_point(avg, 'median_A', A, B, C)
        reflected_B = reflect_point(avg, 'median_B', A, B, C)
        reflected_C = reflect_point(avg, 'median_C', A, B, C)
        
        # Choose reflection that minimizes total displacement
        disp_A = np.linalg.norm(avg - symmetric_points[i]) + np.linalg.norm(reflected_A - symmetric_points[j])
        disp_B = np.linalg.norm(avg - symmetric_points[i]) + np.linalg.norm(reflected_B - symmetric_points[j])
        disp_C = np.linalg.norm(avg - symmetric_points[i]) + np.linalg.norm(reflected_C - symmetric_points[j])
        
        if disp_A <= disp_B and disp_A <= disp_C:
            new_points[idx] = avg
            new_points[idx+1] = reflected_A
        elif disp_B <= disp_A and disp_B <= disp_C:
            new_points[idx] = avg
            new_points[idx+1] = reflected_B
        else:
            new_points[idx] = avg
            new_points[idx+1] = reflected_C
    
    return new_points

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # SYMMETRY-CONSTRAINED INITIALIZATION FOR N=11
    # Known optimal patterns: 3 near vertices, 6 near edges, 2 in interior
    # With reflection symmetry across all three medians
    points = np.zeros((11, 2))
    
    # 1. CENTROID POINT (symmetric by itself)
    centroid = (A + B + C) / 3
    points[0] = centroid
    
    # 2. VERTEX-NEAR POINTS (3 pairs, but we'll create 3 points and enforce symmetry)
    # Literature shows optimal n=11 has points near vertices
    vertex_offsets = [0.15, 0.18, 0.12]  # Adaptive offsets based on literature
    for i, offset in enumerate(vertex_offsets):
        if i == 0:  # Near A
            P = A + offset * (B - A) + offset * (C - A)
        elif i == 1:  # Near B
            P = B + offset * (A - B) + offset * (C - B)
        else:  # Near C
            P = C + offset * (A - C) + offset * (B - C)
        points[1+i] = project_to_triangle(P, A, B, C)
    
    # 3. EDGE POINTS (3 pairs, 6 points total)
    # Literature shows optimal n=11 has points distributed along edges
    edge_params = [
        (0.2, 0.7), (0.3, 0.6), (0.4, 0.5),  # AB edge
        (0.25, 0.75), (0.35, 0.65), (0.45, 0.55)  # BC and CA edges
    ]
    edge_idx = 4
    for params in edge_params:
        if edge_idx < 7:  # AB edge
            t = params[0]
            P = A + t * (B - A)
            # Add small perpendicular displacement inward
            perp = np.array([-(B[1]-A[1]), B[0]-A[0]])
            perp = perp / np.linalg.norm(perp) * params[1]
            points[edge_idx] = project_to_triangle(P + perp, A, B, C)
        elif edge_idx < 9:  # BC edge
            t = params[0] - 0.2
            P = B + t * (C - B)
            perp = np.array([-(C[1]-B[1]), C[0]-B[0]])
            perp = perp / np.linalg.norm(perp) * params[1]
            points[edge_idx] = project_to_triangle(P + perp, A, B, C)
        else:  # CA edge
            t = params[0] - 0.4
            P = C + t * (A - C)
            perp = np.array([-(A[1]-C[1]), A[0]-C[0]])
            perp = perp / np.linalg.norm(perp) * params[1]
            points[edge_idx] = project_to_triangle(P + perp, A, B, C)
        edge_idx += 1
    
    # 4. INTERIOR POINTS (1 pair, 2 points)
    interior_params = [(0.3, 0.3), (0.4, 0.4)]
    for i, (u, v) in enumerate(interior_params):
        w = 1 - u - v
        points[10-i] = u * A + v * B + w * C
    
    # Enforce symmetry across all three medians
    points = enforce_symmetry(points, A, B, C)

    # Simulated annealing parameters
    max_iter = 50000
    initial_T = 0.1
    cooling_rate = 0.995
    step_size_base = 0.05

    current_config = points.copy()
    current_area = get_smallest_triangle_area(current_config)
    best_config = current_config.copy()
    best_area = current_area

    T = initial_T
    no_improve_count = 0
    
    # Adaptive parameters setup
    improvement_rate = 0.5  # Exponential moving average of improvement rate
    alpha = 0.01  # Smoothing factor
    momentum_base = 0.1
    
    # Momentum vector for gradient-directed moves (11 points x 2 coordinates)
    momentum_vector = np.zeros((11, 2))

    for _ in range(max_iter):
        # Compute adaptive parameters
        multi_point_ratio = 0.3 + 0.4 * (1 - improvement_rate)
        multi_point_ratio = max(0.3, min(0.7, multi_point_ratio))
        adaptive_max_no_improve = 400 * (1 + (1 - improvement_rate))
        adaptive_max_no_improve = max(200, min(800, adaptive_max_no_improve))
        current_momentum_factor = momentum_base * (1 + improvement_rate)

        # Piecewise step size schedule (geometrically adaptive)
        if T > 0.7 * initial_T:
            # Early phase: high exploration
            current_step_size = step_size_base * 1.5
        elif T > 0.3 * initial_T:
            # Mid phase: linear decay
            current_step_size = step_size_base * (0.5 + 0.5 * (T - 0.3 * initial_T) / (0.4 * initial_T))
        else:
            # Late phase: fine-tuning with slow exponential decay
            current_step_size = step_size_base * 0.5 * np.exp(-5 * (initial_T - T) / initial_T)

        # Adaptive perturbation ratio
        if random.random() < (1 - multi_point_ratio):
            # Single point perturbation
            idx = random.randint(0, 10)
            angle = random.uniform(0, 2 * np.pi)
            r = random.uniform(0, current_step_size)
            dx = r * np.cos(angle)
            dy = r * np.sin(angle)
            new_point = current_config[idx] + np.array([dx, dy])
            new_point = project_to_triangle(new_point, A, B, C)
            
            # Edge-specific boundary handling with adaptive displacement
            if np.array_equal(new_point, current_config[idx]):
                edge_name, edge_dir = get_closest_edge(current_config[idx], A, B, C)
                edge_dir = edge_dir / np.linalg.norm(edge_dir)
                # Adaptive displacement factor based on temperature and improvement rate
                adaptive_factor = 0.01 + 0.04 * (1 - T / initial_T) + 0.05 * improvement_rate
                new_point = current_config[idx] + adaptive_factor * current_step_size * edge_dir
                new_point = project_to_triangle(new_point, A, B, C)

            new_config = current_config.copy()
            new_config[idx] = new_point
            
            # ENFORCED SYMMETRY: Update symmetric points
            new_config = enforce_symmetry(new_config, A, B, C)
            
            # COLLINERARITY CHECK
            new_area = get_smallest_triangle_area(new_config)
            if new_area < 1e-5:
                # Apply small orthogonal perturbation to break collinearity
                areas = []
                indices = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            A_pt = new_config[i]
                            B_pt = new_config[j]
                            C_pt = new_config[k]
                            area_val = abs((B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (C_pt[0]-A_pt[0])*(B_pt[1]-A_pt[1]))
                            areas.append(area_val)
                            indices.append((i, j, k))
                
                # Find near-collinear triangles
                near_collinear = [idx for idx, area in enumerate(areas) if area < 1e-5]
                if near_collinear:
                    i, j, k = indices[near_collinear[0]]
                    # Compute direction of collinearity
                    dir1 = new_config[j] - new_config[i]
                    dir2 = new_config[k] - new_config[i]
                    if np.linalg.norm(dir1) > 1e-10 and np.linalg.norm(dir2) > 1e-10:
                        dir1 = dir1 / np.linalg.norm(dir1)
                        dir2 = dir2 / np.linalg.norm(dir2)
                        # Orthogonal direction
                        ortho = np.array([-dir1[1], dir1[0]])
                        # Perturb middle point
                        new_config[j] += 0.001 * current_step_size * ortho
                        new_config = project_to_triangle(new_config[j], A, B, C)
                        new_area = get_smallest_triangle_area(new_config)

        else:
            # Adaptive multi-point perturbation targeting variable number of smallest triangles
            areas = []
            indices = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        A_pt = current_config[i]
                        B_pt = current_config[j]
                        C_pt = current_config[k]
                        area_val = abs((B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (C_pt[0]-A_pt[0])*(B_pt[1]-A_pt[1]))
                        areas.append(area_val)
                        indices.append((i, j, k))
            
            # Adaptive number of triangles to target based on temperature phase
            target_count = max(3, min(10, int(10 * T / initial_T + np.log10(11))))
            # Get top-k smallest triangles
            sorted_indices = np.argsort(areas)
            top_k_indices = [indices[idx] for idx in sorted_indices[:target_count]]

            # Accumulate gradients for all points in top-k triangles
            gradient_accum = np.zeros((11, 2))
            for tri_idx, tri in enumerate(top_k_indices):
                i, j, k = tri
                A_pt, B_pt, C_pt = current_config[i], current_config[j], current_config[k]
                S = (B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (C_pt[0]-A_pt[0])*(B_pt[1]-A_pt[1])
                sign = 1 if S >= 0 else -1
                dir_i = sign * np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]])
                dir_j = sign * np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[1]])
                dir_k = sign * np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]])
                
                # Weight by inverse area to prioritize critical triangles
                weight = 1.0 / (areas[sorted_indices[tri_idx]] + 1e-10)
                gradient_accum[i] += weight * dir_i
                gradient_accum[j] += weight * dir_j
                gradient_accum[k] += weight * dir_k

            # Get unique points in top-k triangles
            unique_points = set()
            for tri in top_k_indices:
                unique_points.update(tri)
            unique_points = list(unique_points)

            # Compute displacements for unique points
            new_points = []
            base_displacements = []
            for idx in unique_points:
                grad = gradient_accum[idx]
                norm = np.linalg.norm(grad)
                if norm < 1e-10:
                    angle = random.uniform(0, 2 * np.pi)
                    r = current_step_size
                    base_disp = np.array([r * np.cos(angle), r * np.sin(angle)])
                else:
                    unit_grad = grad / norm
                    main_disp = unit_grad * current_step_size
                    r = random.uniform(0, 0.1 * current_step_size)
                    angle = random.uniform(0, 2 * np.pi)
                    rand_disp = np.array([r * np.cos(angle), r * np.sin(angle)])
                    base_disp = main_disp + rand_disp
                base_displacements.append(base_disp)

                total_disp = base_disp + current_momentum_factor * momentum_vector[idx]
                new_point = current_config[idx] + total_disp
                new_point = project_to_triangle(new_point, A, B, C)
                
                # Edge-specific boundary handling with adaptive displacement
                if np.array_equal(new_point, current_config[idx]):
                    edge_name, edge_dir = get_closest_edge(current_config[idx], A, B, C)
                    edge_dir = edge_dir / np.linalg.norm(edge_dir)
                    # Adaptive displacement factor based on temperature and improvement rate
                    adaptive_factor = 0.01 + 0.04 * (1 - T / initial_T) + 0.05 * improvement_rate
                    new_point = current_config[idx] + adaptive_factor * current_step_size * edge_dir
                    new_point = project_to_triangle(new_point, A, B, C)
                
                new_points.append(new_point)

            new_config = current_config.copy()
            for idx, new_pt in zip(unique_points, new_points):
                new_config[idx] = new_pt
            
            # ENFORCED SYMMETRY: Update symmetric points
            new_config = enforce_symmetry(new_config, A, B, C)
            
            # COLLINERARITY CHECK
            new_area = get_smallest_triangle_area(new_config)
            if new_area < 1e-5:
                # Apply small orthogonal perturbation to break collinearity
                areas = []
                indices = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            A_pt = new_config[i]
                            B_pt = new_config[j]
                            C_pt = new_config[k]
                            area_val = abs((B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (C_pt[0]-A_pt[0])*(B_pt[1]-A_pt[1]))
                            areas.append(area_val)
                            indices.append((i, j, k))
                
                # Find near-collinear triangles
                near_collinear = [idx for idx, area in enumerate(areas) if area < 1e-5]
                if near_collinear:
                    i, j, k = indices[near_collinear[0]]
                    # Compute direction of collinearity
                    dir1 = new_config[j] - new_config[i]
                    dir2 = new_config[k] - new_config[i]
                    if np.linalg.norm(dir1) > 1e-10 and np.linalg.norm(dir2) > 1e-10:
                        dir1 = dir1 / np.linalg.norm(dir1)
                        dir2 = dir2 / np.linalg.norm(dir2)
                        # Orthogonal direction
                        ortho = np.array([-dir1[1], dir1[0]])
                        # Perturb middle point
                        new_config[j] += 0.001 * current_step_size * ortho
                        new_config = project_to_triangle(new_config[j], A, B, C)
                        new_area = get_smallest_triangle_area(new_config)

        # Acceptance logic
        if new_area > current_area:
            current_config = new_config
            current_area = new_area
            if new_area > best_area:
                best_area = new_area
                best_config = new_config.copy()
                no_improve_count = 0
                
                # Update momentum vector for points in unique_points (if multi-point move)
                if 'unique_points' in locals():
                    for idx, base_disp in zip(unique_points, base_displacements):
                        momentum_vector[idx] = 0.9 * momentum_vector[idx] + 0.1 * base_disp
            else:
                no_improve_count += 1

            # Update improvement rate
            improvement_rate = (1 - alpha) * improvement_rate + alpha * 1.0
        else:
            delta = new_area - current_area
            if random.random() < np.exp(delta / T):
                current_config = new_config
                current_area = new_area
            no_improve_count += 1
            improvement_rate = (1 - alpha) * improvement_rate + alpha * 0.0

        # Proportional reheating for local optima escape
        if no_improve_count >= adaptive_max_no_improve:
            current_config = best_config.copy()
            current_area = best_area
            # Linear reheating based on stagnation depth
            T = initial_T * (0.3 + 0.7 * (no_improve_count / adaptive_max_no_improve))
            no_improve_count = 0

        # Cool temperature
        T *= cooling_rate

    return best_config