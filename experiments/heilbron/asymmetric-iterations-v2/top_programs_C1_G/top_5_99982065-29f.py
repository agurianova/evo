import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def find_smallest_triangle(config: np.ndarray, min_area_threshold=0.08):
    n = len(config)
    min_area = float('inf')
    all_triangles = []  # Store all triangles for later filtering

    # First pass: find the absolute minimum area
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = 0.5 * abs((config[j,0]-config[i,0])*(config[k,1]-config[i,1]) - 
                                 (config[k,0]-config[i,0])*(config[j,1]-config[i,1]))
                if area < min_area:
                    min_area = area

    # Second pass: collect all triangles within threshold of minimum
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = 0.5 * abs((config[j,0]-config[i,0])*(config[k,1]-config[i,1]) - 
                                 (config[k,0]-config[i,0])*(config[j,1]-config[i,1]))
                # Include triangles within threshold OR at least 5 smallest triangles
                if area <= min_area * (1 + min_area_threshold) or len(all_triangles) < 5:
                    all_triangles.append((area, i, j, k))

    # Sort by area
    all_triangles.sort(key=lambda x: x[0])
    
    # Return min area and critical points from relevant triangles
    critical_points = set()
    for _, i, j, k in all_triangles:
        critical_points.add(i)
        critical_points.add(j)
        critical_points.add(k)
        
    return min_area, list(critical_points), all_triangles

def reflect_into_triangle(point: np.ndarray, tri: tuple, boundary_proximity: float, boundary_strength_base: float, max_iter: int, current_iter: int) -> np.ndarray:
    A, B, C = tri
    
    # Precompute inward normals for edges
    edge_AB = B - A
    n_AB = np.array([-edge_AB[1], edge_AB[0]])
    if np.dot(n_AB, C - A) < 0:
        n_AB = -n_AB
    n_AB = n_AB / np.linalg.norm(n_AB)

    edge_BC = C - B
    n_BC = np.array([-edge_BC[1], edge_BC[0]])
    if np.dot(n_BC, A - B) < 0:
        n_BC = -n_BC
    n_BC = n_BC / np.linalg.norm(n_BC)

    edge_AC = C - A
    n_AC = np.array([-edge_AC[1], edge_AC[0]])
    if np.dot(n_AC, B - A) < 0:
        n_AC = -n_AC
    n_AC = n_AC / np.linalg.norm(n_AC)

    P = point.copy()
    
    # Check proximity to boundaries for specialized handling
    d_AB = np.dot(P - A, n_AB)
    d_BC = np.dot(P - B, n_BC)
    d_AC = np.dot(P - A, n_AC)
    
    # Calculate actual boundary proximity (absolute value of smallest distance)
    boundary_proximity = min(abs(d_AB), abs(d_BC), abs(d_AC))
    
    # If near boundary, handle with specialized logic
    if boundary_proximity < 0.05:
        # Project to nearest boundary edge for constrained movement
        if abs(d_AB) <= abs(d_BC) and abs(d_AB) <= abs(d_AC):
            # Near AB edge
            t = np.dot(P - A, edge_AB) / np.dot(edge_AB, edge_AB)
            t = max(0, min(1, t))
            P = A + t * edge_AB
        elif abs(d_BC) <= abs(d_AB) and abs(d_BC) <= abs(d_AC):
            # Near BC edge
            t = np.dot(P - B, edge_BC) / np.dot(edge_BC, edge_BC)
            t = max(0, min(1, t))
            P = B + t * edge_BC
        else:
            # Near AC edge
            t = np.dot(P - A, edge_AC) / np.dot(edge_AC, edge_AC)
            t = max(0, min(1, t))
            P = A + t * edge_AC
    else:
        # Three reflection passes with adjustable strength
        # Position-dependent boundary strength: reduce when far from boundaries
        boundary_strength = boundary_strength_base * (1.0 if boundary_proximity < 0.1 else 0.5)
        
        for _ in range(3):
            d_AB = np.dot(P - A, n_AB)
            if d_AB < 0:
                P = P - 2 * boundary_strength * d_AB * n_AB
            
            d_BC = np.dot(P - B, n_BC)
            if d_BC < 0:
                P = P - 2 * boundary_strength * d_BC * n_BC
            
            d_AC = np.dot(P - A, n_AC)
            if d_AC < 0:
                P = P - 2 * boundary_strength * d_AC * n_AC

    # Safeguard: move toward centroid if still outside
    if not is_inside_triangle(P, A, B, C):
        centroid = (A + B + C) / 3
        for _ in range(10):
            P = 0.9 * P + 0.1 * centroid
            if is_inside_triangle(P, A, B, C):
                break
                
    return P

def is_distinct(config: np.ndarray, idx: int, tol: float) -> bool:
    for i in range(len(config)):
        if i == idx:
            continue
        if np.linalg.norm(config[idx] - config[i]) < tol:
            return False
    return True

def compute_composite_gradient(config: np.ndarray, idx: int, all_triangles: list, min_area: float, gradient_threshold: float) -> np.ndarray:
    # Only consider triangles within threshold of min_area
    threshold = min_area * (1 + gradient_threshold)
    relevant_triangles = [t for t in all_triangles if t[0] <= threshold and idx in (t[1], t[2], t[3])]
    
    if not relevant_triangles:
        return np.random.normal(0, 1, size=2)

    # Weight gradients by how close they are to minimum area
    total_weight = 0.0
    composite_grad = np.zeros(2)
    
    for area, i, j, k in relevant_triangles:
        # Get the other two points in the triangle
        other_pts = [p for p in [i, j, k] if p != idx]
        if len(other_pts) != 2:
            continue
        
        j_idx, k_idx = other_pts
        P_i = config[idx]
        P_j = config[j_idx]
        P_k = config[k_idx]
        
        # Compute the gradient direction that would increase the triangle area
        f = (P_j[0]-P_i[0])*(P_k[1]-P_i[1]) - (P_k[0]-P_i[0])*(P_j[1]-P_i[1])
        sign_f = 1.0 if f >= 0 else -1.0
        grad = np.array([P_j[1] - P_k[1], P_k[0] - P_j[0]]) * sign_f
        
        # Use exponential decay weighting to focus on triangles very close to minimum
        weight = np.exp(-5.0 * (area - min_area) / (min_area + 1e-8))
        composite_grad += weight * grad
        total_weight += weight

    if total_weight > 1e-5:
        composite_grad = composite_grad / total_weight
        grad_norm = np.linalg.norm(composite_grad)
        if grad_norm > 1e-5:
            return composite_grad / grad_norm
    
    return np.random.normal(0, 1, size=2)

def generate_diverse_initial_config(tri, config_type=None, restart_idx=0, quality=0.0):
    A, B, C = tri
    
    # Compute centroid and distance to vertex
    O = (A + B + C) / 3
    L = np.linalg.norm(A - O)
    
    # Randomly select configuration type if not specified
    if config_type is None:
        config_type = random.choice(['rotational', 'reflectional', 'hexagonal', 'hex-rotational', 'randomized'])
    
    if config_type == 'rotational':
        # Rotational symmetry with continuous adaptation
        points = [O]
        
        # Continuous number of rings based on quality with noise
        num_rings = max(1, min(3, int(round(1.8 + 1.2 * quality + random.gauss(0, 0.2)))))
        
        for ring in range(num_rings):
            # Adaptive radius based on ring number and quality
            radius = (0.1 + 0.15 * ring + random.uniform(-0.03, 0.03)) * L * (0.8 + 0.4 * quality)
            
            # Adaptive number of points in this ring
            num_points = max(3, min(6, 3 + int(3 * quality + random.gauss(0, 0.5))))
            
            # Random starting angle
            start_angle = random.uniform(0, 2 * np.pi)
            
            for i in range(num_points):
                angle = start_angle + 2 * np.pi * i / num_points
                direction = np.array([np.cos(angle), np.sin(angle)])
                points.append(O + radius * direction)

    elif config_type == 'reflectional':
        # Reflection symmetry across median
        points = [O]
        
        # Points along the median
        for i in range(1, 4):
            radius = (0.1 * i + random.uniform(-0.02, 0.02)) * L
            points.append(O + radius * ((A - O) / L))
            
        # Reflection pairs off the median
        for i in range(3):
            radius = (0.15 + 0.1 * i + random.uniform(-0.02, 0.02)) * L
            angle = np.pi/6 + random.uniform(-np.pi/12, np.pi/12)
            
            # First point
            direction1 = np.array([np.cos(angle), np.sin(angle)])
            points.append(O + radius * direction1)
            
            # Reflected point
            direction2 = np.array([np.cos(-angle), np.sin(-angle)])
            points.append(O + radius * direction2)

    elif config_type == 'hexagonal':
        # Hexagonal lattice pattern with adaptive parameters
        points = []
        
        # Center point
        points.append(O)
        
        # Adaptive radii based on quality to explore different configurations
        base_radius1 = 0.10 + 0.03 * quality
        base_radius2 = 0.20 + 0.05 * quality
        
        # First ring - 6 points
        radius1 = base_radius1 * L + random.uniform(-0.01, 0.01)
        for i in range(6):
            angle = np.pi/3 * i
            direction = np.array([np.cos(angle), np.sin(angle)])
            points.append(O + radius1 * direction)
        
        # Second ring - 4 points
        radius2 = base_radius2 * L + random.uniform(-0.02, 0.02)
        for i in range(4):
            angle = np.pi/2 * i + random.uniform(-np.pi/12, np.pi/12)
            direction = np.array([np.cos(angle), np.sin(angle)])
            points.append(O + radius2 * direction)

    elif config_type == 'hex-rotational':
        # Hexagonal-rotational hybrid with adaptive parameters
        points = [O]
        
        # Continuous number of rings based on quality
        num_rings = max(1, min(3, int(round(1.8 + 1.2 * quality + random.gauss(0, 0.2)))))
        
        for ring in range(num_rings):
            # Adaptive radius with hexagonal spacing
            radius = (0.1 + 0.15 * ring + random.uniform(-0.03, 0.03)) * L * (0.8 + 0.4 * quality)
            
            # Hexagonal symmetry (6 points per ring) but with rotational offset
            num_points = 6
            start_angle = random.uniform(0, np.pi/3)  # Random offset within hexagonal symmetry
            
            for i in range(num_points):
                angle = start_angle + 2 * np.pi * i / num_points
                direction = np.array([np.cos(angle), np.sin(angle)])
                points.append(O + radius * direction)

    else:  # 'randomized'
        # More randomized approach with adaptive clustering
        points = []
        
        # Center point
        points.append(O + np.random.normal(0, 0.01 * L, size=2))
        
        # Generate clusters
        num_clusters = 2 if quality < 0.6 else 3
        cluster_points = 3 if quality < 0.8 else 4
        
        for c in range(num_clusters):
            # Random cluster center
            radius = (0.15 + 0.1 * c + random.uniform(-0.02, 0.02)) * L
            angle = random.uniform(0, 2 * np.pi)
            center = O + radius * np.array([np.cos(angle), np.sin(angle)])
            
            # Points around cluster center
            for i in range(cluster_points):
                cluster_radius = 0.03 * L + random.uniform(-0.005, 0.005)
                cluster_angle = 2 * np.pi * i / cluster_points + random.uniform(-0.1, 0.1)
                direction = np.array([np.cos(cluster_angle), np.sin(cluster_angle)])
                points.append(center + cluster_radius * direction)

    # Ensure we have exactly 11 points
    if len(points) > 11:
        points = points[:11]
    elif len(points) < 11:
        # Add random points to reach 11
        while len(points) < 11:
            radius = random.uniform(0.05, 0.3) * L
            angle = random.uniform(0, 2 * np.pi)
            direction = np.array([np.cos(angle), np.sin(angle)])
            new_point = O + radius * direction
            points.append(new_point)

    # Convert to numpy array and validate
    config = np.array(points)
    for i in range(len(config)):
        config[i] = reflect_into_triangle(config[i], tri, 0.0, 0.5, 60000, 0)
        
    return config

def optimize_configuration(initial_config, tri, quality=0.0):
    config = initial_config.copy()
    current_min_area = get_smallest_triangle_area(config)

    # Calculate adaptive parameters based on quality
    min_step = 0.005 + 0.015 * (1 - quality)
    max_step = 0.04 + 0.04 * quality

    # Simulated annealing parameters
    temperature = 0.05  # More conservative initial temperature
    step_size = 0.04
    max_iter = 60000
    no_improve_count = 0
    max_no_improve = 250
    
    # Adaptive critical point threshold - wider when quality is low
    min_area_threshold = min(0.15, max(0.05, 0.20 * (0.0365 - current_min_area) / 0.0365))

    # Track acceptance rate for adaptive step size
    acceptance_window = 50
    acceptance_history = []

    for iter in range(max_iter):
        # Find smallest triangles and all relevant triangles
        min_area, critical_points, all_triangles = find_smallest_triangle(config, min_area_threshold)

        # Adaptive critical point bias based on quality and resistance
        # More aggressive when resistance is high but quality is low
        critical_bias = min(0.98, max(0.3, 0.3 + 0.65 * quality))

        # Adaptive gradient threshold
        gradient_threshold = 0.05 + 0.07 * (1 - quality)

        # Choose point to perturb with adaptive bias
        if critical_points and random.random() < critical_bias:
            idx = random.choice(critical_points)
            # Compute composite gradient for critical points
            if random.random() < 0.75:  # 75% chance to use gradient direction
                direction = compute_composite_gradient(config, idx, all_triangles, min_area, gradient_threshold)
                # Adaptive step size based on gradient relevance
                step_factor = 0.8 + 0.4 * (min_area / (min_area + 1e-8))
                d = direction * step_size * step_factor * random.uniform(0.85, 1.15)
            else:
                d = np.random.normal(0, step_size, size=2)
        else:
            idx = random.randint(0, 10)
            d = np.random.normal(0, step_size, size=2)

        candidate = config.copy()
        candidate[idx] += d

        # Boundary reflection with specialized handling
        boundary_proximity = 0.0  # Will be calculated in reflect_into_triangle
        boundary_strength_base = 0.5 + 0.5 * (iter / max_iter)
        candidate[idx] = reflect_into_triangle(candidate[idx], tri, boundary_proximity, boundary_strength_base, max_iter, iter)

        # Distinctness check
        if not is_distinct(candidate, idx, 1e-8):
            # Instead of skipping, make a small adjustment
            direction = np.random.normal(0, 1, size=2)
            direction = direction / (np.linalg.norm(direction) + 1e-8)
            candidate[idx] += direction * 1e-7

        new_min_area = get_smallest_triangle_area(candidate)

        # Simulated annealing acceptance
        delta = new_min_area - current_min_area
        accepted = False
        
        if delta > 0 or random.random() < np.exp(delta / temperature):
            config = candidate
            current_min_area = new_min_area
            no_improve_count = 0
            accepted = True
            
            # Adaptive step size bounds
            step_size = min(max(step_size * 1.001, min_step), max_step)
        else:
            no_improve_count += 1
            # Reduce step size if stuck
            step_size = max(step_size * 0.999, min_step)

        # Track acceptance for adaptive step size
        acceptance_history.append(1 if accepted else 0)
        if len(acceptance_history) > acceptance_window:
            acceptance_history.pop(0)
            
        # Adaptive step size based on acceptance rate
        if len(acceptance_history) == acceptance_window:
            # Adaptive thresholds based on quality
            upper_threshold = 0.5 - 0.1 * quality
            lower_threshold = 0.1 + 0.1 * quality
            
            acceptance_rate = sum(acceptance_history) / acceptance_window
            if acceptance_rate > upper_threshold:
                step_size = min(step_size * 1.05, max_step)
            elif acceptance_rate < lower_threshold:
                step_size = max(step_size * 0.95, min_step)

        # Adaptive step size control
        if no_improve_count >= max_no_improve:
            step_size = max(step_size * 0.9, min_step)
            no_improve_count = 0

        # Cool temperature
        temperature *= 0.9998

    return config

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # UCB bandit for config type selection
    config_types = ['rotational', 'reflectional', 'hexagonal', 'hex-rotational', 'randomized']
    type_counts = {t: 0 for t in config_types}
    type_rewards = {t: [] for t in config_types}
    
    best_config = None
    best_min_area = -1
    
    # Dynamic restart allocation using UCB
    total_restarts = 0
    while total_restarts < 12:
        # Calculate UCB scores
        ucb_scores = {}
        for t in config_types:
            if type_counts[t] == 0:
                ucb_scores[t] = float('inf')  # Prioritize untried types
            else:
                avg_reward = sum(type_rewards[t]) / len(type_rewards[t])
                # Increased exploration coefficient from 2 to 3.5
                exploration = np.sqrt(3.5 * np.log(total_restarts) / type_counts[t])
                ucb_scores[t] = avg_reward + exploration
        
        # Select config type with highest UCB score
        selected_type = max(ucb_scores, key=ucb_scores.get)
        
        # Generate initial configuration with quality estimate (using previous avg)
        quality_estimate = sum(type_rewards[selected_type]) / len(type_rewards[selected_type]) if type_rewards[selected_type] else 0.0
        initial_config = generate_diverse_initial_config(tri, selected_type, total_restarts, quality_estimate)
        
        # Optimize the configuration
        optimized_config = optimize_configuration(initial_config, tri, quality_estimate)
        
        # Evaluate
        min_area = get_smallest_triangle_area(optimized_config)
        quality = min(min_area / 0.0365, 1.0)
        
        # Update bandit statistics
        type_counts[selected_type] += 1
        type_rewards[selected_type].append(min_area)
        total_restarts += 1
        
        # Track best configuration
        if min_area > best_min_area:
            best_min_area = min_area
            best_config = optimized_config
    
    return best_config