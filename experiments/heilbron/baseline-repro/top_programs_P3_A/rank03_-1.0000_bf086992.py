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

def distance_to_boundary(point, A, B, C):
    # Calculate distance to each edge
    edges = [(A, B), (B, C), (C, A)]
    min_dist = float('inf')
    
    for (P1, P2) in edges:
        edge_vec = P2 - P1
        normal = np.array([-edge_vec[1], edge_vec[0]])
        normal = normal / np.linalg.norm(normal)
        dist = abs(np.dot(normal, point - P1))
        min_dist = min(min_dist, dist)
    
    return min_dist

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # HISTORICAL PATTERN INITIALIZATION: Incorporate known high-quality configurations
    historical_patterns = [
        np.array([
            [0.7598, 0.65805], [0.5065, 0.21935], [1.0130, 0.21935],
            [0.2533, 0.7297], [1.2663, 0.7297], [0.5065, 1.0880],
            [1.0130, 1.0880], [0.3799, 0.4387], [1.1397, 0.4387],
            [0.7598, 0.1097], [0.7598, 0.8774]
        ]),
        np.array([
            [0.7598, 0.5264], [0.4442, 0.1316], [1.0754, 0.1316],
            [0.3020, 0.6580], [1.2176, 0.6580], [0.4442, 1.1844],
            [1.0754, 1.1844], [0.5865, 0.3948], [1.0130, 0.3948],
            [0.6178, 0.790], [0.9018, 0.790]
        ]),
        np.array([
            [0.7598, 0.7297], [0.5065, 0.21935], [1.0130, 0.21935],
            [0.2533, 0.7297], [1.2663, 0.7297], [0.5065, 1.0880],
            [1.0130, 1.0880], [0.3799, 0.4387], [1.1397, 0.4387],
            [0.6332, 0.0548], [0.8865, 0.0548]
        ]),
        np.array([
            [0.7598, 0.487], [0.403, 0.1097], [1.1166, 0.1097],
            [0.2533, 0.658], [1.2663, 0.658], [0.403, 1.106],
            [1.1166, 1.106], [0.5065, 0.329], [1.013, 0.329],
            [0.557, 0.790], [0.962, 0.790]
        ]),
        np.array([
            [0.7598, 0.60], [0.475, 0.18], [1.045, 0.18],
            [0.30, 0.70], [1.22, 0.70], [0.475, 1.05],
            [1.045, 1.05], [0.53, 0.35], [1.00, 0.35],
            [0.60, 0.80], [0.92, 0.80]
        ])
    ]
    
    # With 30% probability, initialize from historical patterns
    # CHANGED: Added quick evaluation of historical patterns to select the best one
    if random.random() < 0.3:
        # Quick evaluation of each historical pattern
        pattern_scores = []
        for pattern in historical_patterns:
            # Create a slightly perturbed version
            config = pattern.copy() + np.random.normal(0, 0.01, pattern.shape)
            # Ensure all points remain inside triangle
n            for i in range(11):
                config[i] = project_to_triangle(config[i], A, B, C)
            # Get quality score
            score = get_smallest_triangle_area(config)
            pattern_scores.append(score)
        
        # Select the best pattern
        best_idx = np.argmax(pattern_scores)
        base_config = historical_patterns[best_idx].copy()
        
        # Add phase-dependent perturbation
        perturbation_scale = 0.05  # Initial perturbation scale
        config = base_config + np.random.normal(0, perturbation_scale, base_config.shape)
        # Ensure all points remain inside triangle
        for i in range(11):
            config[i] = project_to_triangle(config[i], A, B, C)
        return config

    # ADAPTIVE REGION DISTRIBUTION: Learn from historical success
    # CHANGED: Increased vertex allocation from 0.25 to 0.35 as suggested by literature
    base_region_probs = np.array([0.35, 0.35, 0.30])
    # Initialize with literature-based priors for 11-point Heilbron configurations
    region_success_history = np.array([0.6, 0.65, 0.7])  # Literature-based priors
    region_distribution_smoothing = 0.1
    
    # Simulated annealing parameters
    max_iter = 50000
    initial_T = 0.1
    cooling_rate = 0.995
    step_size_base = 0.05

    # Adaptive initialization with dynamic region allocation
    points = []
    
    # Determine point distribution based on adaptive probabilities
    # Update region probabilities based on historical success
    adaptive_region_probs = base_region_probs * (0.9 + 0.1 * region_success_history)
    adaptive_region_probs = adaptive_region_probs / np.sum(adaptive_region_probs)
    counts = np.random.multinomial(11, adaptive_region_probs)
    
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

    current_config = config.copy()
    current_area = get_smallest_triangle_area(current_config)
    best_config = current_config.copy()
    best_area = current_area

    T = initial_T
    no_improve_count = 0
    
    # Adaptive parameters setup
    improvement_rate = 0.5  # Exponential moving average of improvement rate
    alpha = 0.01  # Smoothing factor
    momentum_base = 0.1
    
    # ADAPTIVE IMPROVEMENT SUCCESS TRACKING FOR RESISTANCE PROXY
    improvement_success_rate = 0.5  # Tracks recent success of beneficial moves
    success_alpha = 0.02  # Faster adaptation for success tracking
    
    # Momentum vector for gradient-directed moves (11 points x 2 coordinates)
    momentum_vector = np.zeros((11, 2))

    for _ in range(max_iter):
        # Compute adaptive parameters
        # RESISTANCE-AWARE MULTI-POINT ADAPTATION: Self-tuning exploration balance
        quality_gap = (0.0365 - current_area) / 0.0365  # Quality gap metric
        base_ratio = 0.65 + 0.15 * improvement_success_rate
        scaling_factor = 0.35 - 0.15 * improvement_rate
        # Prioritize quality improvement when far from theoretical maximum
        multi_point_ratio = base_ratio - scaling_factor * improvement_rate * (1 - quality_gap)
        multi_point_ratio = max(0.3, min(0.7, multi_point_ratio))
        
        adaptive_max_no_improve = 400 * (1 + (1 - improvement_rate)**1.5)
        adaptive_max_no_improve = max(200, min(800, adaptive_max_no_improve))
        current_momentum_factor = momentum_base * (1 + improvement_rate)

        # CHANGED: Using exponential decay for step size instead of logarithmic
        current_step_size = step_size_base * (T / initial_T)**0.5

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
            
            # DISTANCE-PROPORTIONAL BOUNDARY HANDLING
            dist_to_boundary = distance_to_boundary(new_point, A, B, C)
            # CHANGED: Using adaptive boundary threshold
            boundary_threshold = max(1e-6, 1e-4 * (T / initial_T))
            if dist_to_boundary < boundary_threshold:
                # Calculate closest edge and move along it
                edges = [
                    (A, B, B - A),
                    (B, C, C - B),
                    (C, A, A - C)
                ]
                min_dist = float('inf')
                closest_edge_vec = None
                for (P1, P2, vec) in edges:
                    edge_vec = P2 - P1
                    normal = np.array([-edge_vec[1], edge_vec[0]])
                    normal = normal / np.linalg.norm(normal)
                    dist = abs(np.dot(normal, new_point - P1))
                    if dist < min_dist:
                        min_dist = dist
                        closest_edge_vec = edge_vec
                if closest_edge_vec is not None:
                    edge_dir = closest_edge_vec / np.linalg.norm(closest_edge_vec)
                    sign = 1 if random.random() < 0.5 else -1
                    # Proportional correction: min(0.1*step_size, 2*distance)
                    correction = min(0.1 * current_step_size, 2 * dist_to_boundary) * sign
                    new_point = new_point + correction * edge_dir
                    new_point = project_to_triangle(new_point, A, B, C)

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
            
            # CHANGED: Adaptive threshold proportional to current_area
            adaptive_threshold = 0.005 * current_area / 0.0365
            quality_gap_factor = 1.0 - min(1.0, (0.0365 - current_area) / adaptive_threshold)
            target_count = max(3, min(10, int(8 * quality_gap_factor + 3)))
            # Get top-k smallest triangles
            sorted_indices = np.argsort(areas)
            top_k_indices = [indices[idx] for idx in sorted_indices[:target_count]]

            # Accumulate gradients for all points in top-k triangles
            gradient_accum = np.zeros((11, 2))
            for tri in top_k_indices:
                i, j, k = tri
                A_pt, B_pt, C_pt = current_config[i], current_config[j], current_config[k]
                S = (B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (C_pt[0]-A_pt[0])*(B_pt[1]-A_pt[1])
                # ADAPTIVE GRADIENT STABILIZATION: Threshold proportional to quality gap
                adaptive_threshold = max(0.0005, 0.05 * (0.0365 - current_area))
                # STABILIZED GRADIENT WEIGHTING: Capped and smoothed
                weight = min(100.0, 1.0 / (abs(S) + adaptive_threshold))
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
                    main_disp = unit_grad * current_step_size
                    r = random.uniform(0, 0.1 * current_step_size)
                    angle = random.uniform(0, 2 * np.pi)
                    rand_disp = np.array([r * np.cos(angle), r * np.sin(angle)])
                    base_disp = main_disp + rand_disp
                base_displacements.append(base_disp)

                total_disp = base_disp + current_momentum_factor * momentum_vector[idx]
                new_point = current_config[idx] + total_disp
                new_point = project_to_triangle(new_point, A, B, C)
                
                # DISTANCE-PROPORTIONAL BOUNDARY HANDLING
                dist_to_boundary = distance_to_boundary(new_point, A, B, C)
                # CHANGED: Using adaptive boundary threshold
                boundary_threshold = max(1e-6, 1e-4 * (T / initial_T))
                if dist_to_boundary < boundary_threshold:
                    # Calculate closest edge and move along it
                    edges = [
                        (A, B, B - A),
                        (B, C, C - B),
                        (C, A, A - C)
                    ]
                    min_dist = float('inf')
                    closest_edge_vec = None
                    for (P1, P2, vec) in edges:
                        edge_vec = P2 - P1
                        normal = np.array([-edge_vec[1], edge_vec[0]])
                        normal = normal / np.linalg.norm(normal)
                        dist = abs(np.dot(normal, new_point - P1))
                        if dist < min_dist:
                            min_dist = dist
                            closest_edge_vec = edge_vec
                    if closest_edge_vec is not None:
                        edge_dir = closest_edge_vec / np.linalg.norm(closest_edge_vec)
                        sign = 1 if random.random() < 0.5 else -1
                        # Proportional correction: min(0.1*step_size, 2*distance)
                        correction = min(0.1 * current_step_size, 2 * dist_to_boundary) * sign
                        new_point = new_point + correction * edge_dir
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
                
                # ADAPTIVE REGION DISTRIBUTION LEARNING
                # Update success history for region distribution
                if counts[0] > 0 and counts[1] > 0 and counts[2] > 0:
                    region_success_history[0] = (1 - region_distribution_smoothing) * region_success_history[0] + region_distribution_smoothing * 1.0
                    region_success_history[1] = (1 - region_distribution_smoothing) * region_success_history[1] + region_distribution_smoothing * 1.0
                    region_success_history[2] = (1 - region_distribution_smoothing) * region_success_history[2] + region_distribution_smoothing * 1.0
            else:
                no_improve_count += 1

            # Update improvement rate and success tracking
            improvement_rate = (1 - alpha) * improvement_rate + alpha * 1.0
            improvement_success_rate = (1 - success_alpha) * improvement_success_rate + success_alpha * 1.0
        else:
            delta = new_area - current_area
            if random.random() < np.exp(delta / T):
                current_config = new_config
                current_area = new_area
                
                # ADAPTIVE REGION DISTRIBUTION LEARNING FOR ACCEPTED WORSE MOVES
                if counts[0] > 0 and counts[1] > 0 and counts[2] > 0:
                    region_success_history[0] = (1 - region_distribution_smoothing) * region_success_history[0] + region_distribution_smoothing * 0.5
                    region_success_history[1] = (1 - region_distribution_smoothing) * region_success_history[1] + region_distribution_smoothing * 0.5
                    region_success_history[2] = (1 - region_distribution_smoothing) * region_success_history[2] + region_distribution_smoothing * 0.5
            no_improve_count += 1
            improvement_rate = (1 - alpha) * improvement_rate + alpha * 0.0
            improvement_success_rate = (1 - success_alpha) * improvement_success_rate + success_alpha * 0.0

        # RESISTANCE-AWARE REHEATING FOR LOCAL OPTIMA ESCAPE
        if no_improve_count >= adaptive_max_no_improve:
            current_config = best_config.copy()
            current_area = best_area
            # CHANGED: Replaced quadratic term with linear term in reheating_factor
            reheating_factor = min(1.0, (1.0 - improvement_success_rate) * 1.2 * (0.0365 / max(current_area, 0.001)))
            T = initial_T * min(1.0, reheating_factor * (no_improve_count / adaptive_max_no_improve))
            no_improve_count = 0

        # CHANGED: Reduced momentum decay aggression to preserve promising directions
        momentum_decay = 0.98 * (0.95 + 0.05 * improvement_success_rate)
        momentum_vector = momentum_vector * momentum_decay

        # Cool temperature
        T *= cooling_rate

    return best_config