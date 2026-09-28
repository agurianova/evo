import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def point_to_line_distance(point, line_start, line_end):
    """Calculate perpendicular distance from point to line segment."""
    line_vec = line_end - line_start
    point_vec = point - line_start
    line_len = np.linalg.norm(line_vec)
    if line_len == 0:
        return np.linalg.norm(point_vec)
    
    # Project point onto line
    t = np.dot(point_vec, line_vec) / (line_len * line_len)
    t = max(0, min(1, t))  # Clamp to segment
    projection = line_start + t * line_vec
    return np.linalg.norm(point - projection)

def get_closest_edge(point, A, B, C):
    """Determine which edge (AB, BC, or CA) the point is closest to."""
    # Calculate distances to each edge
    dist_AB = point_to_line_distance(point, A, B)
    dist_BC = point_to_line_distance(point, B, C)
    dist_CA = point_to_line_distance(point, C, A)
    
    # Return the edge with minimum distance
    if dist_AB <= dist_BC and dist_AB <= dist_CA:
        return A, B  # AB edge
    elif dist_BC <= dist_AB and dist_BC <= dist_CA:
        return B, C  # BC edge
    else:
        return C, A  # CA edge

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

def sample_high_quality_configuration(A, B, C):
    """
    Generate diverse initial configurations by sampling from multiple high-quality templates
    with random perturbations and quality filtering.
    """
    # Multiple high-quality templates from literature for n=11
    templates = [
        # Template 1: Symmetric configuration
        [(0.05, 0.05, 0.90), (0.05, 0.90, 0.05), (0.90, 0.05, 0.05),
         (0.20, 0.20, 0.60), (0.20, 0.60, 0.20), (0.60, 0.20, 0.20),
         (0.30, 0.30, 0.40), (0.30, 0.50, 0.20), (0.50, 0.30, 0.20),
         (0.40, 0.40, 0.20), (0.35, 0.35, 0.30)],
        
        # Template 2: More edge-focused configuration
        [(0.03, 0.03, 0.94), (0.03, 0.94, 0.03), (0.94, 0.03, 0.03),
         (0.15, 0.15, 0.70), (0.15, 0.70, 0.15), (0.70, 0.15, 0.15),
         (0.25, 0.25, 0.50), (0.25, 0.60, 0.15), (0.60, 0.25, 0.15),
         (0.35, 0.35, 0.30), (0.45, 0.45, 0.10)],
        
        # Template 3: More central-focused configuration
        [(0.07, 0.07, 0.86), (0.07, 0.86, 0.07), (0.86, 0.07, 0.07),
         (0.18, 0.18, 0.64), (0.18, 0.64, 0.18), (0.64, 0.18, 0.18),
         (0.28, 0.28, 0.44), (0.28, 0.55, 0.17), (0.55, 0.28, 0.17),
         (0.38, 0.38, 0.24), (0.32, 0.32, 0.36)],
        
        # Template 4: Asymmetric configuration
        [(0.04, 0.06, 0.90), (0.06, 0.88, 0.06), (0.89, 0.05, 0.06),
         (0.17, 0.22, 0.61), (0.23, 0.62, 0.15), (0.63, 0.19, 0.18),
         (0.32, 0.33, 0.35), (0.28, 0.53, 0.19), (0.54, 0.27, 0.19),
         (0.42, 0.41, 0.17), (0.36, 0.36, 0.28)]
    ]
    
    # Generate candidate configurations with random perturbations
    candidates = []
    for template in templates:
        for _ in range(3):  # Generate 3 perturbed versions per template
            bary_coords = []
            for u, v, w in template:
                # Add small random perturbations (max 5% of coordinate value)
                u_pert = max(0.0, min(1.0, u + random.uniform(-0.05, 0.05) * u))
                v_pert = max(0.0, min(1.0, v + random.uniform(-0.05, 0.05) * v))
                w_pert = 1.0 - u_pert - v_pert
                # Ensure w stays within bounds
                if w_pert < 0:
                    diff = -w_pert / 2
                    u_pert += diff
                    v_pert += diff
                    w_pert = 0
                elif w_pert > 1:
                    diff = (w_pert - 1) / 2
                    u_pert -= diff
                    v_pert -= diff
                    w_pert = 1
                bary_coords.append((u_pert, v_pert, w_pert))
            
            # Convert to Cartesian points
            points = np.array([u * A + v * B + w * C for u, v, w in bary_coords])
            min_area = get_smallest_triangle_area(points)
            candidates.append((points, min_area))
    
    # Sort by quality and select top 3
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]  # Return the best candidate

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Adaptive initialization using multiple templates with quality filtering
    initial_config = sample_high_quality_configuration(A, B, C)
    
    # Simulated annealing parameters
    max_iter = 50000
    initial_T = 0.1
    cooling_rate = 0.995
    step_size_base = 0.05

    current_config = initial_config.copy()
    current_area = get_smallest_triangle_area(current_config)
    best_config = current_config.copy()
    best_area = current_area

    T = initial_T
    no_improve_count = 0
    
    # Adaptive parameters setup
    improvement_rate = 0.5  # Exponential moving average of improvement rate
    alpha = 0.01  # Smoothing factor
    
    # Phase detection variables
    exploration_phase = True
    phase_change_threshold = 0.7  # Threshold for switching to exploitation phase
    
    # Momentum vector for gradient-directed moves (11 points x 2 coordinates)
    momentum_vector = np.zeros((11, 2))
    momentum_decay = 0.9
    base_momentum_factor = 0.1

    # Cache for triangle area calculations
    area_cache_valid = False
    min_area_val = 0.0
    second_min_area_val = 0.0

    for iter_count in range(max_iter):
        # Recalculate area gap periodically or when needed
        if not area_cache_valid or iter_count % 50 == 0 or no_improve_count > 300:
            all_areas = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        A_pt = current_config[i]
                        B_pt = current_config[j]
                        C_pt = current_config[k]
                        area_val = 0.5 * abs((B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (C_pt[0]-A_pt[0])*(B_pt[1]-A_pt[1]))
                        all_areas.append(area_val)
            
            sorted_areas = sorted(all_areas)
            min_area_val = sorted_areas[0]
            second_min_area_val = sorted_areas[1] if len(sorted_areas) > 1 else min_area_val
            area_cache_valid = True

            # Update exploration/exploitation phase based on gap ratio
            gap_ratio = min_area_val / (second_min_area_val + 1e-10)
            if gap_ratio > phase_change_threshold:
                exploration_phase = False
            else:
                exploration_phase = True

        # Compute adaptive parameters using linear relationships
        multi_point_ratio = 0.3 + 0.4 * (1 - improvement_rate)
        multi_point_ratio = max(0.3, min(0.7, multi_point_ratio))
        adaptive_max_no_improve = 400 + 400 * (1 - improvement_rate)
        adaptive_max_no_improve = max(200, min(800, adaptive_max_no_improve))
        
        # Compute momentum factor based on phase and convergence
        if exploration_phase:
            current_momentum_factor = base_momentum_factor * 0.5
        else:
            # In exploitation phase, use gap ratio to control momentum
            gap_ratio = min_area_val / (second_min_area_val + 1e-10)
            current_momentum_factor = base_momentum_factor * (0.2 + 0.8 * gap_ratio)

        # Power-law step size progression (better convergence properties)
        step_size_exponent = 0.5 + 0.5 * improvement_rate
        current_step_size = step_size_base * (T / initial_T)**step_size_exponent

        # Calculate gap ratio for adaptive targeting
        gap_ratio = min_area_val / (second_min_area_val + 1e-10)
        
        # Target more triangles when gap is small (many triangles close to minimum)
        # CRITICAL CHANGE: Added conditional logic for deep convergence
        if gap_ratio < 0.15:
            # In deep local optima, focus exclusively on the absolute smallest triangles
            target_count = 2
        else:
            target_count = max(3, min(15, int(10 * (1 - gap_ratio) + 3)))

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
            
            # Edge-specific boundary handling
            if np.array_equal(new_point, current_config[idx]):
                # On boundary - move parallel to the closest edge
                closest_A, closest_B = get_closest_edge(current_config[idx], A, B, C)
                edge_dir = closest_B - closest_A
                edge_dir = edge_dir / np.linalg.norm(edge_dir)
                new_point = current_config[idx] + 0.01 * current_step_size * edge_dir
                new_point = project_to_triangle(new_point, A, B, C)

            new_config = current_config.copy()
            new_config[idx] = new_point
            new_area = get_smallest_triangle_area(new_config)

        else:
            # Multi-point perturbation targeting variable number of smallest triangles
            areas = []
            indices = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        A_pt = current_config[i]
                        B_pt = current_config[j]
                        C_pt = current_config[k]
                        area_val = 0.5 * abs((B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (C_pt[0]-A_pt[0])*(B_pt[1]-A_pt[1]))
                        areas.append(area_val)
                        indices.append((i, j, k))
            
            # Get top-k smallest triangles
            sorted_indices = np.argsort(areas)
            top_k_indices = [indices[idx] for idx in sorted_indices[:target_count]]

            # Accumulate gradients for all points in top-k triangles with adaptive weighting
            gradient_accum = np.zeros((11, 2))
            
            # Adaptive gradient power based on improvement rate
            gradient_power = 0.5 + 0.5 * (1 - improvement_rate)
            
            for tri in top_k_indices:
                i, j, k = tri
                A_pt, B_pt, C_pt = current_config[i], current_config[j], current_config[k]
                S = (B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (C_pt[0]-A_pt[0])*(B_pt[1]-A_pt[1])
                area_val = 0.5 * abs(S)
                
                # Enhanced gradient weighting: exponential focus on smallest triangles
                weight = np.exp(-gradient_power * (area_val - min_area_val) / (1e-10 + min_area_val))
                
                sign = 1 if S >= 0 else -1
                dir_i = sign * np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]])
                dir_j = sign * np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[1]])
                dir_k = sign * np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]])
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
                new_point = current_config[idx] + total_disp
                new_point = project_to_triangle(new_point, A, B, C)
                
                # Edge-specific boundary handling
                if np.array_equal(new_point, current_config[idx]):
                    # On boundary - move parallel to the closest edge
                    closest_A, closest_B = get_closest_edge(current_config[idx], A, B, C)
                    edge_dir = closest_B - closest_A
                    edge_dir = edge_dir / np.linalg.norm(edge_dir)
                    new_point = current_config[idx] + 0.01 * current_step_size * edge_dir
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
                area_cache_valid = False
                
                # Update momentum vector for points in unique_points (if multi-point move)
                if 'unique_points' in locals():
                    for idx, base_disp in zip(unique_points, base_displacements):
                        momentum_vector[idx] = momentum_decay * momentum_vector[idx] + (1 - momentum_decay) * base_disp
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
            # Make reheating depend on the gap between smallest and second-smallest triangles
            gap_ratio = min_area_val / (second_min_area_val + 1e-10)
            reheating_factor = 0.2 + 0.8 * gap_ratio
            
            current_config = best_config.copy()
            current_area = best_area
            T = initial_T * reheating_factor
            no_improve_count = 0
            area_cache_valid = False

        # Cool temperature
        T *= cooling_rate

    return best_config