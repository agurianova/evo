import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

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
        
        # Determine which edge the point is closest to
        edge = None
        if coords[0] == 0:
            edge = 'BC'  # u=0 means on BC edge
        elif coords[1] == 0:
            edge = 'AC'  # v=0 means on AC edge
        elif coords[2] == 0:
            edge = 'AB'  # w=0 means on AB edge
        return coords[0] * A + coords[1] * B + coords[2] * C, edge
    return coords[0] * A + coords[1] * B + coords[2] * C, None

def get_edge_direction(point, A, B, C, edge):
    if edge == 'AB':
        return B - A
    elif edge == 'BC':
        return C - B
    elif edge == 'AC':
        return C - A
    else:  # Interior point - use default direction
        return B - A

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Adaptive initialization with empirically optimized region distribution
    points = []
    
    # Optimized region distribution based on known high-quality configurations
    region_probs = [0.1, 0.4, 0.5]  # vertex, edge, interior - tuned to match successful configurations
    counts = np.random.multinomial(11, region_probs)
    
    # Vertex regions (3 vertices) with tighter bounds from empirical data
    for i in range(counts[0]):
        region = i % 3
        u, v, w = 0.1, 0.1, 0.1
        if region == 0:  # Near A
            v = random.uniform(0.02, 0.1)
            w = random.uniform(0.02, 0.1)
            u = 1 - v - w
        elif region == 1:  # Near B
            u = random.uniform(0.02, 0.1)
            w = random.uniform(0.02, 0.1)
            v = 1 - u - w
        else:  # Near C
            u = random.uniform(0.02, 0.1)
            v = random.uniform(0.02, 0.1)
            w = 1 - u - v
        
        # Ensure valid barycentric coordinates
        if u < 0 or v < 0 or w < 0:
            max_coord = max(u, v, w)
            u, v, w = u/max_coord, v/max_coord, w/max_coord
        
        points.append(u * A + v * B + w * C)

    # Edge regions (3 edges) with tighter bounds
    for i in range(counts[1]):
        region = i % 3
        if region == 0:  # Near AB (w small)
            w = random.uniform(0.02, 0.1)
            t = random.uniform(0.2, 0.8)
            u = t * (1 - w)
            v = (1 - t) * (1 - w)
        elif region == 1:  # Near BC (u small)
            u = random.uniform(0.02, 0.1)
            t = random.uniform(0.2, 0.8)
            v = t * (1 - u)
            w = (1 - t) * (1 - u)
        else:  # Near CA (v small)
            v = random.uniform(0.02, 0.1)
            t = random.uniform(0.2, 0.8)
            u = t * (1 - v)
            w = (1 - t) * (1 - v)
        
        points.append(u * A + v * B + w * C)

    # Interior region with tighter bounds
    for _ in range(counts[2]):
        while True:
            u = random.uniform(0.1, 0.6)
            v = random.uniform(0.1, 0.6)
            w = 1 - u - v
            if w >= 0.1 and w <= 0.6:
                break
        points.append(u * A + v * B + w * C)

    config = np.array(points)

    # Simulated annealing parameters
    max_iter = 50000
    initial_T = 0.1
    cooling_rate = 0.995
    step_size_base = 0.05

    current_config = config.copy()
    current_area = get_smallest_triangle_area(current_config)
    best_config = current_config.copy()
    best_area = current_area

    T = initial_T
    no_improve_count = 0
    
    # Adaptive parameters setup
    improvement_rate = 0.5  # Exponential moving average of improvement rate
    alpha = 0.01  # Smoothing factor
    momentum_base = 0.25  # Increased from 0.1 for stronger momentum
    
    # Momentum vector for gradient-directed moves (11 points x 2 coordinates)
    momentum_vector = np.zeros((11, 2))

    for _ in range(max_iter):
        # Compute adaptive parameters
        multi_point_ratio = 0.3 + 0.4 * (1 - improvement_rate)  # Simplified linear formula
        multi_point_ratio = max(0.3, min(0.7, multi_point_ratio))
        adaptive_max_no_improve = 200 + 600 * (1 - improvement_rate)  # Simplified linear formula
        adaptive_max_no_improve = max(200, min(800, adaptive_max_no_improve))
        
        # Stagnation-dependent momentum factor (decays as stagnation increases)
        stagnation_factor = 1.0 - min(0.5, no_improve_count / adaptive_max_no_improve)
        current_momentum_factor = momentum_base * stagnation_factor * (1 + improvement_rate)

        # Power-law step size progression (better exploration/exploitation balance)
        current_step_size = step_size_base * (T / initial_T) ** 0.5

        # Adaptive perturbation ratio
        if random.random() < (1 - multi_point_ratio):
            # Single point perturbation
            idx = random.randint(0, 10)
            angle = random.uniform(0, 2 * np.pi)
            r = random.uniform(0, current_step_size)
            dx = r * np.cos(angle)
            dy = r * np.sin(angle)
            new_point, edge = project_to_triangle(current_config[idx] + np.array([dx, dy]), A, B, C)
            
            # Gradient-aware boundary handling - now edge-specific with adaptive step size
            if np.array_equal(new_point, current_config[idx]):
                # On boundary - move parallel to the actual edge
                edge_dir = get_edge_direction(new_point, A, B, C, edge)
                edge_dir = edge_dir / np.linalg.norm(edge_dir)
                
                # Adaptive boundary step with variable size and small normal component
                boundary_step_size = current_step_size * random.uniform(0.05, 0.2)
                normal_component = 0.075 * boundary_step_size  # 7.5% normal component
                
                # Add small normal component toward interior
                normal_dir = np.array([-edge_dir[1], edge_dir[0]])
                if np.dot(normal_dir, C - A) < 0:  # Ensure pointing inward
                    normal_dir = -normal_dir
                
                new_point = current_config[idx] + boundary_step_size * edge_dir + normal_component * normal_dir
                new_point, _ = project_to_triangle(new_point, A, B, C)

            new_config = current_config.copy()
            new_config[idx] = new_point
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
            
            # Weight areas by inverse to prioritize smallest triangles with capping to prevent extreme weights
            weights = [min(20, 1.0 / max(area, 1e-5)) for area in areas]
            weighted_indices = [x for _, x in sorted(zip(weights, indices), reverse=True)]
            
            # Adaptive number of triangles to target based on temperature phase and current min_area
            # Minimum target_count increased to 5 for better resistance
            target_count = max(5, min(12, int(10 * (T / initial_T) ** 0.7 + 2 * (0.0365 - current_area) / 0.0365)))
            # Get top-k smallest triangles (weighted by inverse area)
            top_k_indices = weighted_indices[:target_count]

            # Accumulate gradients for all points in top-k triangles
            gradient_accum = np.zeros((11, 2))
            for tri in top_k_indices:
                i, j, k = tri
                A_pt, B_pt, C_pt = current_config[i], current_config[j], current_config[k]
                S = (B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (C_pt[0]-A_pt[0])*(B_pt[1]-A_pt[1])
                sign = 1 if S >= 0 else -1
                dir_i = sign * np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]])
                dir_j = sign * np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[1]])
                dir_k = sign * np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]])
                
                # Weight gradient by inverse area with capping
                area_val = abs(S) / 2.0  # Actual triangle area
                weight = min(20, 1.0 / max(area_val, 1e-5))
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
n                    main_disp = unit_grad * current_step_size
                    r = random.uniform(0, 0.1 * current_step_size)
                    angle = random.uniform(0, 2 * np.pi)
                    rand_disp = np.array([r * np.cos(angle), r * np.sin(angle)])
                    base_disp = main_disp + rand_disp
                base_displacements.append(base_disp)

                total_disp = base_disp + current_momentum_factor * momentum_vector[idx]
                new_point, edge = project_to_triangle(current_config[idx] + total_disp, A, B, C)
                
                # Gradient-aware boundary handling - now edge-specific with adaptive step size
                if np.array_equal(new_point, current_config[idx]):
                    # On boundary - move parallel to the actual edge
                    edge_dir = get_edge_direction(new_point, A, B, C, edge)
                    edge_dir = edge_dir / np.linalg.norm(edge_dir)
                    
                    # Adaptive boundary step with variable size and small normal component
                    boundary_step_size = current_step_size * random.uniform(0.05, 0.2)
                    normal_component = 0.075 * boundary_step_size  # 7.5% normal component
                    
                    # Add small normal component toward interior
                    normal_dir = np.array([-edge_dir[1], edge_dir[0]])
                    if np.dot(normal_dir, C - A) < 0:  # Ensure pointing inward
                        normal_dir = -normal_dir
                    
                    new_point = current_config[idx] + boundary_step_size * edge_dir + normal_component * normal_dir
                    new_point, _ = project_to_triangle(new_point, A, B, C)
                
                new_points.append(new_point)

            new_config = current_config.copy()
            for idx, new_pt in zip(unique_points, new_points):
                new_config[idx] = new_pt
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
            # Proportional reheating based on stagnation depth
            T = initial_T * (0.5 + 0.5 * no_improve_count / adaptive_max_no_improve)  # Increased base factor from 0.3 to 0.5
            no_improve_count = 0

        # Cool temperature
        T *= cooling_rate

    return best_config