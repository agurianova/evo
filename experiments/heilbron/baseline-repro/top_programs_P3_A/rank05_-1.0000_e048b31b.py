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

def heuristic_initialization(n_points=11):
    """Generate high-quality initial configuration based on Heilbronn literature patterns."""
    tri = get_unit_triangle()
    A, B, C = tri
    
    points = []
    
    # 3 vertex-near points (asymmetric clustering)
    vertex_offsets = [0.08, 0.12, 0.15]
    for i in range(3):
        u, v, w = vertex_offsets[i], vertex_offsets[i], vertex_offsets[i]
        if i == 0:  # Near A
            v = 0.18
            w = 0.12
            u = 1 - v - w
        elif i == 1:  # Near B
            u = 0.14
            w = 0.16
            v = 1 - u - w
        else:  # Near C
            u = 0.16
            v = 0.12
            w = 1 - u - v
        points.append(u * A + v * B + w * C)

    # 4 edge points using golden ratio (0.382, 0.618)
    golden_ratio = (np.sqrt(5) - 1) / 2
    edge_positions = [golden_ratio, 1 - golden_ratio]
    
    # AB edge (C coordinate small)
    for t in edge_positions:
        w = 0.1
        u = t * (1 - w)
        v = (1 - t) * (1 - w)
        points.append(u * A + v * B + w * C)

    # BC edge (A coordinate small)
    for t in edge_positions:
        u = 0.1
        v = t * (1 - u)
        w = (1 - t) * (1 - u)
        points.append(u * A + v * B + w * C)

    # 4 interior points forming symmetric quadrilateral
    # Based on known high-quality Heilbronn configurations
    interior_patterns = [
        (0.25, 0.25, 0.5),
        (0.25, 0.5, 0.25),
        (0.5, 0.25, 0.25),
        (0.33, 0.33, 0.34)
    ]
    
    for u, v, w in interior_patterns:
        points.append(u * A + v * B + w * C)

    return np.array(points)

def verify_local_optimum(config, A, B, C, epsilon=1e-5, step=0.001):
    """Verify configuration is at a true local optimum by checking all 1-point perturbations."""
    current_area = get_smallest_triangle_area(config)
    n_points = len(config)
    
    for i in range(n_points):
        for dx, dy in [(step, 0), (-step, 0), (0, step), (0, -step), 
                       (step/np.sqrt(2), step/np.sqrt(2)), 
                       (-step/np.sqrt(2), step/np.sqrt(2))]:
            new_point = config[i] + np.array([dx, dy])
            new_point = project_to_triangle(new_point, A, B, C)
            
            # Skip if point didn't move (boundary constraint)
            if np.array_equal(new_point, config[i]):
                continue

            new_config = config.copy()
            new_config[i] = new_point
            new_area = get_smallest_triangle_area(new_config)
            
            if new_area > current_area + epsilon:
                return False, new_config
    
    return True, config

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate high-quality initial configuration using literature-based patterns
    config = heuristic_initialization(11)
    current_area = get_smallest_triangle_area(config)
    
    # Simulated annealing parameters
    max_iter = 60000
    initial_T = 0.15
    cooling_rate = 0.995
    step_size_base = 0.06

    current_config = config.copy()
    current_area = get_smallest_triangle_area(current_config)
    best_config = current_config.copy()
    best_area = current_area

    T = initial_T
    no_improve_count = 0
    
    # Adaptive parameters setup
    improvement_rate = 0.5  # Exponential moving average of improvement rate
    alpha = 0.01  # Smoothing factor
    momentum_base = 0.15
    
    # Momentum vector for gradient-directed moves (11 points x 2 coordinates)
    momentum_vector = np.zeros((11, 2))

    for iter_count in range(max_iter):
        # Compute adaptive parameters
        multi_point_ratio = 0.2 + 0.5 * (1 - improvement_rate)
        multi_point_ratio = max(0.2, min(0.6, multi_point_ratio))
        adaptive_max_no_improve = 300 + 500 * (1 - improvement_rate)
        adaptive_max_no_improve = max(150, min(800, adaptive_max_no_improve))
        current_momentum_factor = momentum_base * (1 + 1.5 * improvement_rate)

        # Steeper step size progression for better fine-tuning
        current_step_size = step_size_base * (T / initial_T) ** 0.6

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
            
            # Enhanced boundary handling with increased displacement factor
            if np.array_equal(new_point, current_config[idx]):
                closest_A, closest_B = get_closest_edge(current_config[idx], A, B, C)
                edge_dir = closest_B - closest_A
                edge_dir = edge_dir / np.linalg.norm(edge_dir)
                # Increased from 0.01 to 0.05 with random direction component
                rand_angle = random.uniform(0, 2 * np.pi)
                rand_dir = np.array([np.cos(rand_angle), np.sin(rand_angle)])
                combined_dir = 0.7 * edge_dir + 0.3 * rand_dir
                combined_dir = combined_dir / np.linalg.norm(combined_dir)
                new_point = current_config[idx] + 0.05 * current_step_size * combined_dir
                new_point = project_to_triangle(new_point, A, B, C)

            new_config = current_config.copy()
            new_config[idx] = new_point
            new_area = get_smallest_triangle_area(new_config)

        else:
            # Adaptive multi-point perturbation with refined targeting
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
            
            # Reduced target count for focused optimization
            target_count = max(2, min(6, int(4 * T / initial_T + 1)))
            sorted_indices = np.argsort(areas)
            top_k_indices = [indices[idx] for idx in sorted_indices[:target_count]]

            # Enhanced gradient weighting to emphasize smallest triangles
            target_area = 0.0365
            gradient_power = 0.2 + 0.8 * (1 - min(current_area, target_area) / target_area)

            gradient_accum = np.zeros((11, 2))
            for tri in top_k_indices:
                i, j, k = tri
                A_pt, B_pt, C_pt = current_config[i], current_config[j], current_config[k]
                S = (B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (C_pt[0]-A_pt[0])*(B_pt[1]-A_pt[1])
                area_val = 0.5 * abs(S)
                weight = 1.0 / ((area_val + 1e-10) ** gradient_power)
                
                sign = 1 if S >= 0 else -1
                dir_i = sign * np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]])
                dir_j = sign * np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[1]])
                dir_k = sign * np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]])
                gradient_accum[i] += weight * dir_i
                gradient_accum[j] += weight * dir_j
                gradient_accum[k] += weight * dir_k

            unique_points = set()
            for tri in top_k_indices:
                unique_points.update(tri)
            unique_points = list(unique_points)

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
                    r = random.uniform(0, 0.15 * current_step_size)
                    angle = random.uniform(0, 2 * np.pi)
                    rand_disp = np.array([r * np.cos(angle), r * np.sin(angle)])
                    base_disp = main_disp + rand_disp
                base_displacements.append(base_disp)

                total_disp = base_disp + current_momentum_factor * momentum_vector[idx]
                new_point = current_config[idx] + total_disp
                new_point = project_to_triangle(new_point, A, B, C)
                
                # Enhanced boundary handling
                if np.array_equal(new_point, current_config[idx]):
                    closest_A, closest_B = get_closest_edge(current_config[idx], A, B, C)
                    edge_dir = closest_B - closest_A
                    edge_dir = edge_dir / np.linalg.norm(edge_dir)
                    rand_angle = random.uniform(0, 2 * np.pi)
                    rand_dir = np.array([np.cos(rand_angle), np.sin(rand_angle)])
                    combined_dir = 0.7 * edge_dir + 0.3 * rand_dir
                    combined_dir = combined_dir / np.linalg.norm(combined_dir)
                    new_point = current_config[idx] + 0.05 * current_step_size * combined_dir
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
                
                if 'unique_points' in locals():
                    for idx, base_disp in zip(unique_points, base_displacements):
                        momentum_vector[idx] = 0.9 * momentum_vector[idx] + 0.1 * base_disp
            else:
                no_improve_count += 1

            improvement_rate = (1 - alpha) * improvement_rate + alpha * 1.0
        else:
            delta = new_area - current_area
            if random.random() < np.exp(delta / T):
                current_config = new_config
                current_area = new_area
            no_improve_count += 1
            improvement_rate = (1 - alpha) * improvement_rate + alpha * 0.0

        # Aggressive reheating strategy
        if no_improve_count >= adaptive_max_no_improve:
            current_config = best_config.copy()
            current_area = best_area
            # More aggressive reheating proportional to stagnation depth
            T = initial_T * (0.5 + 0.5 * (1 - improvement_rate))
            no_improve_count = 0

        # Cool temperature
        T *= cooling_rate

    # Post-optimization verification to ensure local optimum
    is_optimum, verified_config = verify_local_optimum(best_config, A, B, C)
    if is_optimum:
        return verified_config
    else:
        # If not optimum, do limited additional optimization
        current_config = verified_config
        current_area = get_smallest_triangle_area(current_config)
        T = initial_T * 0.3
        
        for _ in range(5000):
            # Only single-point perturbations for refinement
n            idx = random.randint(0, 10)
            angle = random.uniform(0, 2 * np.pi)
            r = random.uniform(0, 0.01)
            dx = r * np.cos(angle)
            dy = r * np.sin(angle)
            new_point = current_config[idx] + np.array([dx, dy])
            new_point = project_to_triangle(new_point, A, B, C)
            
            if np.array_equal(new_point, current_config[idx]):
                closest_A, closest_B = get_closest_edge(current_config[idx], A, B, C)
                edge_dir = closest_B - closest_A
                edge_dir = edge_dir / np.linalg.norm(edge_dir)
                new_point = current_config[idx] + 0.05 * 0.01 * edge_dir
                new_point = project_to_triangle(new_point, A, B, C)

            new_config = current_config.copy()
            new_config[idx] = new_point
            new_area = get_smallest_triangle_area(new_config)

            if new_area > current_area:
                current_config = new_config
                current_area = new_area
                
                if new_area > best_area:
                    best_area = new_area
                    best_config = new_config.copy()

            T *= cooling_rate

        # Final verification
        is_optimum, final_config = verify_local_optimum(best_config, A, B, C)
        return final_config