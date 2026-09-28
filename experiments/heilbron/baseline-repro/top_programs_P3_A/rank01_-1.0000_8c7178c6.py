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
    return coords[0] * A + coords[1] * B + coords[2] * C

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Literature-based region probabilities for n=11 with adaptive quality factor
    base_probs = [0.23, 0.37, 0.40]  # Known effective distribution for Heilbronn n=11
    
    # Adaptive quality factor that shifts toward vertex regions as min_area improves
    # Starts at 0.9 (slightly reduced vertex probability) and increases to 1.1 near optimum
    quality_factor = 0.9
    
    # Initialize with conservative region allocation
    region_probs = np.array(base_probs)
    region_probs = region_probs / sum(region_probs)
    
    counts = np.random.multinomial(11, region_probs)
    
    points = []
    # Vertex regions (3 vertices)
    for i in range(counts[0]):
        region = i % 3
        u, v, w = 0.1, 0.1, 0.1
        if region == 0:  # Near A
            v = random.uniform(0.05, 0.2)
            w = random.uniform(0.05, 0.2)
            u = 1 - v - w
        elif region == 1:  # Near B
            u = random.uniform(0.05, 0.2)
            w = random.uniform(0.05, 0.2)
            v = 1 - u - w
        else:  # Near C
            u = random.uniform(0.05, 0.2)
            v = random.uniform(0.05, 0.2)
            w = 1 - u - v
        
        # Ensure valid barycentric coordinates
        if u < 0 or v < 0 or w < 0:
            max_coord = max(u, v, w)
            u, v, w = u/max_coord, v/max_coord, w/max_coord
        
        points.append(u * A + v * B + w * C)

    # Edge regions (3 edges)
    for i in range(counts[1]):
        region = i % 3
        if region == 0:  # Near AB (w small)
            w = random.uniform(0.05, 0.2)
            t = random.uniform(0.15, 0.85)
            u = t * (1 - w)
            v = (1 - t) * (1 - w)
        elif region == 1:  # Near BC (u small)
            u = random.uniform(0.05, 0.2)
            t = random.uniform(0.15, 0.85)
            v = t * (1 - u)
            w = (1 - t) * (1 - u)
        else:  # Near CA (v small)
            v = random.uniform(0.05, 0.2)
            t = random.uniform(0.15, 0.85)
            u = t * (1 - v)
            w = (1 - t) * (1 - v)
        
        points.append(u * A + v * B + w * C)

    # Interior region
    for _ in range(counts[2]):
        while True:
            u = random.uniform(0.1, 0.7)
            v = random.uniform(0.1, 0.7)
            w = 1 - u - v
            if w >= 0.1 and w <= 0.7:
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
    alpha = 0.05  # Increased from 0.01 for faster adaptation
    momentum_base = 0.1
    
    # Momentum vector for gradient-directed moves (11 points x 2 coordinates)
    momentum_vector = np.zeros((11, 2))

    for _ in range(max_iter):
        # Compute adaptive parameters
        # Shift region probabilities toward vertices as we approach optimum
        if best_area > 0.025:
            quality_factor = 0.9 + 0.2 * (best_area - 0.025) / (0.0365 - 0.025)
            region_probs = np.array([
                base_probs[0] * quality_factor,
                base_probs[1] * (1.1 - 0.05 * (quality_factor - 0.9)),
                base_probs[2] * (1.1 - 0.05 * (quality_factor - 0.9))
            ])
            region_probs = region_probs / sum(region_probs)

        # Narrowed multi-point perturbation to focus on critical constraints
        target_count = max(3, min(6, int(4 * (1 - improvement_rate))))
        
        # Adaptive max no-improve threshold
        adaptive_max_no_improve = 400 * (1 + (1 - improvement_rate)**1.5)
        adaptive_max_no_improve = max(200, min(800, adaptive_max_no_improve))
        current_momentum_factor = momentum_base * (1 + improvement_rate)

        # Power-law step size progression (maintains exploration longer)
        current_step_size = step_size_base * (T / initial_T) ** 0.3

        # Adaptive gradient cap that intensifies focus on smallest triangles
        gradient_cap = 50.0 * (0.0365 / max(current_area, 0.01))
        gradient_cap = min(75.0, max(50.0, gradient_cap))

        # Adaptive perturbation ratio
        multi_point_ratio = 0.6 - 0.3 * improvement_rate
        multi_point_ratio = max(0.4, min(0.8, multi_point_ratio))

        if random.random() < (1 - multi_point_ratio):
            # Single point perturbation
            idx = random.randint(0, 10)
            angle = random.uniform(0, 2 * np.pi)
            r = random.uniform(0, current_step_size)
            dx = r * np.cos(angle)
            dy = r * np.sin(angle)
            new_point = current_config[idx] + np.array([dx, dy])
            new_point = project_to_triangle(new_point, A, B, C)
            
            # Simplified boundary recovery: push toward centroid with strength proportional to boundary proximity
            denom = 2.0
            u_bc = ((B[1]-C[1])*(new_point[0]-C[0]) + (C[0]-B[0])*(new_point[1]-C[1])) / denom
            v_bc = ((C[1]-A[1])*(new_point[0]-C[0]) + (A[0]-C[0])*(new_point[1]-C[1])) / denom
            w_bc = 1 - u_bc - v_bc
            boundary_dist = min(u_bc, v_bc, w_bc)
            tol = 1e-5
            if boundary_dist < tol:
                # Push toward centroid with strength proportional to boundary proximity
                centroid = (A + B + C) / 3
                direction = centroid - new_point
                direction = direction / np.linalg.norm(direction)
                strength = 0.2 * (1 - boundary_dist)
                new_point = new_point + strength * current_step_size * direction
                new_point = project_to_triangle(new_point, A, B, C)

            new_config = current_config.copy()
            new_config[idx] = new_point
            new_area = get_smallest_triangle_area(new_config)

        else:
            # Multi-point perturbation targeting the most critical constraints
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
            
            # Get top-k smallest triangles (narrowed focus on critical constraints)
            sorted_indices = np.argsort(areas)
            top_k_indices = [indices[idx] for idx in sorted_indices[:target_count]]

            # Accumulate gradients for all points in top-k triangles
            gradient_accum = np.zeros((11, 2))
            for tri in top_k_indices:
                i, j, k = tri
                A_pt, B_pt, C_pt = current_config[i], current_config[j], current_config[k]
                S = (B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (C_pt[0]-A_pt[0])*(B_pt[1]-A_pt[1])
                weight = min(gradient_cap, 1.0 / (abs(S) + 1e-10))
                sign = 1 if S >= 0 else -1
                dir_i = sign * weight * np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]])
                dir_j = sign * weight * np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[0]])
                dir_k = sign * weight * np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]])
                gradient_accum[i] += dir_i
                gradient_accum[j] += dir_j
                gradient_accum[k] += dir_k

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
                new_point = current_config[idx] + total_disp
                new_point = project_to_triangle(new_point, A, B, C)
                
                # Simplified boundary recovery
                denom = 2.0
                u_bc = ((B[1]-C[1])*(new_point[0]-C[0]) + (C[0]-B[0])*(new_point[1]-C[1])) / denom
                v_bc = ((C[1]-A[1])*(new_point[0]-C[0]) + (A[0]-C[0])*(new_point[1]-C[1])) / denom
                w_bc = 1 - u_bc - v_bc
                boundary_dist = min(u_bc, v_bc, w_bc)
                tol = 1e-5
                if boundary_dist < tol:
                    centroid = (A + B + C) / 3
                    direction = centroid - new_point
                    direction = direction / np.linalg.norm(direction)
                    strength = 0.2 * (1 - boundary_dist)
                    new_point = new_point + strength * current_step_size * direction
                    new_point = project_to_triangle(new_point, A, B, C)
                
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
            acceptance_prob = np.exp(delta / T)
            if random.random() < acceptance_prob:
                current_config = new_config
                current_area = new_area
                
                # ENHANCED MOMENTUM: Update for all accepted moves, not just improvements
                if 'unique_points' in locals():
                    for idx, base_disp in zip(unique_points, base_displacements):
                        # Weight by acceptance probability and improvement magnitude
                        weight = 0.1 * acceptance_prob * (1 + abs(delta))
                        momentum_vector[idx] = (1 - weight) * momentum_vector[idx] + weight * base_disp
            no_improve_count += 1
            improvement_rate = (1 - alpha) * improvement_rate + alpha * 0.0

        # Aggressive reheating for local optima escape when resistance is low
        reheating_multiplier = 0.95 if improvement_rate < 0.5 else 0.75
        if no_improve_count >= adaptive_max_no_improve:
            current_config = best_config.copy()
            current_area = best_area
            T = initial_T * min(1.0, reheating_multiplier * (no_improve_count / adaptive_max_no_improve))
            no_improve_count = 0

        # Cool temperature
        T *= cooling_rate

    return best_config