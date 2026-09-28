import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def find_smallest_triangle(config: np.ndarray, min_area_threshold=0.15):
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

def reflect_into_triangle(point: np.ndarray, tri: tuple, boundary_strength=1.0) -> np.ndarray:
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
    
    # If near boundary, handle with specialized logic
    boundary_proximity = min(abs(d_AB), abs(d_BC), abs(d_AC))
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

def compute_composite_gradient(config: np.ndarray, idx: int, all_triangles: list, min_area: float) -> np.ndarray:
    # Only consider triangles within 10% of min_area threshold
    threshold = min_area * 1.1
    relevant_triangles = [t for t in all_triangles if t[0] <= threshold and idx in (t[1], t[2], t[3])]
    
    if not relevant_triangles:
        return np.random.normal(0, 1, size=2)

    # Weight gradients by how close they are to minimum area
    # Closer to minimum = higher weight
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
        
        # Weight by proximity to minimum area
        weight = 1.0 / (area - min_area + 1e-8)
        composite_grad += weight * grad
        total_weight += weight

    if total_weight > 1e-5:
        composite_grad = composite_grad / total_weight
        grad_norm = np.linalg.norm(composite_grad)
        if grad_norm > 1e-5:
            return composite_grad / grad_norm
    
    return np.random.normal(0, 1, size=2)

def generate_diverse_initial_config(tri, config_type=None):
    A, B, C = tri
    
    # Compute centroid and distance to vertex
    O = (A + B + C) / 3
    L = np.linalg.norm(A - O)
    
    # Randomly select configuration type if not specified
    if config_type is None:
        config_type = random.choice(['rotational', 'reflectional', 'randomized', 'hexagonal'])
    
    if config_type == 'rotational':
        # Rotational symmetry with adaptive parameters
        points = [O]
        
        # Random number of rings (2-3)
        num_rings = random.choice([2, 3])
        
        for ring in range(num_rings):
            # Adaptive radius based on ring number
            radius = (0.1 + 0.15 * ring + random.uniform(-0.03, 0.03)) * L
            
            # Random number of points in this ring (3-6)
            num_points = random.choice([3, 4, 5, 6])
            
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
        # Hexagonal lattice pattern
        points = []
        
        # Center point
        points.append(O)
        
        # First ring - 6 points
        radius1 = 0.12 * L + random.uniform(-0.01, 0.01)
        for i in range(6):
            angle = np.pi/3 * i
            direction = np.array([np.cos(angle), np.sin(angle)])
            points.append(O + radius1 * direction)
        
        # Second ring - 4 points
        radius2 = 0.25 * L + random.uniform(-0.02, 0.02)
        for i in range(4):
            angle = np.pi/2 * i + random.uniform(-np.pi/12, np.pi/12)
            direction = np.array([np.cos(angle), np.sin(angle)])
            points.append(O + radius2 * direction)

    else:  # 'randomized'
        # More randomized approach with adaptive clustering
        points = []
        
        # Center point
        points.append(O + np.random.normal(0, 0.01 * L, size=2))
        
        # Generate clusters
        num_clusters = random.choice([2, 3])
        cluster_points = random.choice([3, 4])
        
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
        config[i] = reflect_into_triangle(config[i], tri, 1.0)
        
    return config

def optimize_configuration(initial_config, tri):
    config = initial_config.copy()
    current_min_area = get_smallest_triangle_area(config)

    # Simulated annealing parameters
    temperature = 0.05  # More conservative initial temperature
    step_size = 0.04
    max_iter = 60000
    no_improve_count = 0
    max_no_improve = 250
    
    # Adaptive critical point threshold
    min_area_threshold = 0.15  # 15% threshold for relevant triangles

    # Track acceptance rate for adaptive step size
    acceptance_window = 50
    acceptance_history = []

    for iter in range(max_iter):
        # Find smallest triangles and all relevant triangles
        min_area, critical_points, all_triangles = find_smallest_triangle(config, min_area_threshold)

        # Adaptive critical point bias (decreases as we progress)
        critical_bias = max(0.4, 0.85 - 0.45 * (iter / max_iter))

        # Choose point to perturb with adaptive bias
        if critical_points and random.random() < critical_bias:
            idx = random.choice(critical_points)
            # Compute composite gradient for critical points
            if random.random() < 0.75:  # 75% chance to use gradient direction
                direction = compute_composite_gradient(config, idx, all_triangles, min_area)
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
        boundary_strength = 0.8 + 0.4 * (iter / max_iter)  # Moderate boundary strength
        candidate[idx] = reflect_into_triangle(candidate[idx], tri, boundary_strength)

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
            step_size *= 0.9996  # Slower decay
        else:
            no_improve_count += 1

        # Track acceptance for adaptive step size
        acceptance_history.append(1 if accepted else 0)
        if len(acceptance_history) > acceptance_window:
            acceptance_history.pop(0)
            
        # Adaptive step size based on acceptance rate
        if len(acceptance_history) == acceptance_window:
            acceptance_rate = sum(acceptance_history) / acceptance_window
            if acceptance_rate > 0.4:
                step_size = min(step_size * 1.05, 0.06)
            elif acceptance_rate < 0.2:
                step_size = max(step_size * 0.95, 0.02)

        # Adaptive step size control
        if no_improve_count >= max_no_improve:
            step_size = max(step_size * 0.9, 0.02)  # Moderate reduction
            no_improve_count = 0

        # Cool temperature
        temperature *= 0.9998

    return config

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    best_config = None
    best_min_area = -1
    
    # Try multiple restarts with diverse initial configurations
    for restart in range(8):  # Increased from 3 to 8 restarts
        # Use different configuration types for diversity
        config_types = ['rotational', 'reflectional', 'hexagonal', 'randomized']
        config_type = config_types[restart % len(config_types)]
        
        # Generate initial configuration with varied structure
        initial_config = generate_diverse_initial_config(tri, config_type)
        
        # Optimize the configuration
        optimized_config = optimize_configuration(initial_config, tri)
        
        # Evaluate
        min_area = get_smallest_triangle_area(optimized_config)
        if min_area > best_min_area:
            best_min_area = min_area
            best_config = optimized_config
    
    return best_config