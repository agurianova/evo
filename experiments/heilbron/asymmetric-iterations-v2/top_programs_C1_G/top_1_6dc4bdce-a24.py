import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def find_smallest_triangle(config: np.ndarray, threshold=0.15):
    n = len(config)
    min_area = float('inf')
    all_triangles = []  # Store all triangles

    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = 0.5 * abs((config[j,0]-config[i,0])*(config[k,1]-config[i,1]) - 
                                 (config[k,0]-config[i,0])*(config[j,1]-config[i,1]))
                all_triangles.append((area, i, j, k))
                if area < min_area:
                    min_area = area
    
    # Filter triangles within threshold of min_area
    critical_triangles = [(area, i, j, k) for (area, i, j, k) in all_triangles 
                          if area <= min_area * (1 + threshold)]
    
    # Return min area and critical points
    critical_points = set()
    for _, i, j, k in critical_triangles:
        critical_points.add(i)
        critical_points.add(j)
        critical_points.add(k)
        
    return min_area, list(critical_points), critical_triangles

def reflect_into_triangle(point: np.ndarray, tri: tuple, boundary_strength=1.0) -> np.ndarray:
    A, B, C = tri
    
    # Precompute edge information
    edge_AB = B - A
    edge_BC = C - B
    edge_AC = C - A
    
    # Compute edge lengths
    len_AB = np.linalg.norm(edge_AB)
    len_BC = np.linalg.norm(edge_BC)
    len_AC = np.linalg.norm(edge_AC)
    
    # Compute unit normals pointing inward
    n_AB = np.array([-edge_AB[1], edge_AB[0]])
    if np.dot(n_AB, C - A) < 0:
        n_AB = -n_AB
    n_AB = n_AB / len_AB

    n_BC = np.array([-edge_BC[1], edge_BC[0]])
    if np.dot(n_BC, A - B) < 0:
        n_BC = -n_BC
    n_BC = n_BC / len_BC

    n_AC = np.array([-edge_AC[1], edge_AC[0]])
    if np.dot(n_AC, B - A) < 0:
        n_AC = -n_AC
    n_AC = n_AC / len_AC
    
    # Check proximity to edges
    P = point.copy()
    d_AB = np.dot(P - A, n_AB)
    d_BC = np.dot(P - B, n_BC)
    d_AC = np.dot(P - A, n_AC)
    
    # If near an edge, use specialized projection
    edge_proximity_threshold = 0.05  # 5% of triangle size
    
    near_AB = abs(d_AB) < edge_proximity_threshold
    near_BC = abs(d_BC) < edge_proximity_threshold
    near_AC = abs(d_AC) < edge_proximity_threshold
    
    if near_AB and d_AB < 0:
        # Project onto AB edge with specialized handling
        t = np.dot(P - A, edge_AB) / (len_AB ** 2)
        t = max(0, min(1, t))
        projection = A + t * edge_AB
        P = projection
    elif near_BC and d_BC < 0:
        # Project onto BC edge
        t = np.dot(P - B, edge_BC) / (len_BC ** 2)
        t = max(0, min(1, t))
        projection = B + t * edge_BC
        P = projection
    elif near_AC and d_AC < 0:
        # Project onto AC edge
        t = np.dot(P - A, edge_AC) / (len_AC ** 2)
        t = max(0, min(1, t))
        projection = A + t * edge_AC
        P = projection
    else:
        # Standard reflection for interior points
        if d_AB < 0:
            P = P - 2 * boundary_strength * d_AB * n_AB
        if d_BC < 0:
            P = P - 2 * boundary_strength * d_BC * n_BC
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

def compute_gradient_direction(config: np.ndarray, idx: int, critical_triangles: list) -> np.ndarray:
    # Find triangles involving this point
    triangles_with_idx = []
    for (area, i, j, k) in critical_triangles:
        if idx in (i, j, k):
            triangles_with_idx.append((area, i, j, k))
    
    if not triangles_with_idx:
        return np.random.normal(0, 1, size=2)
    
    # Sort by area (smallest first)
    triangles_with_idx.sort(key=lambda x: x[0])
    
    # Compute composite gradient
    composite_grad = np.zeros(2)
    total_weight = 0
    
    min_area = triangles_with_idx[0][0]
    for (area, i, j, k) in triangles_with_idx:
        # Weight by how close this triangle's area is to the minimum
        weight = 1.0 / (area - min_area + 1e-10)
        total_weight += weight
        
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
        grad_norm = np.linalg.norm(grad)
        if grad_norm > 1e-5:
            composite_grad += weight * (grad / grad_norm)
    
    if total_weight > 0:
        composite_grad /= total_weight
    
    grad_norm = np.linalg.norm(composite_grad)
    if grad_norm > 1e-5:
        return composite_grad / grad_norm
    else:
        return np.random.normal(0, 1, size=2)

def generate_rotational_symmetric_config(tri, symmetry_perturbation=0.0):
    A, B, C = tri
    
    # Compute centroid and distance to vertex
    O = (A + B + C) / 3
    L = np.linalg.norm(A - O)
    
    # Parameterized radii with wider exploration range
    r1 = (0.15 + random.uniform(-0.05, 0.05)) * L
    r2 = (0.35 + random.uniform(-0.05, 0.05)) * L
    
    # Unit vectors for median directions
    v0 = (A - O) / L
    v120 = (B - O) / L
    v240 = (C - O) / L
    
    # Perpendicular vector for 60° rotations
    n_perp = np.array([-v0[1], v0[0]])
    
    points = [O]
    
    # 3 points at r1: 0°, 120°, 240° (along medians)
    for v in [v0, v120, v240]:
        points.append(O + r1 * v)
    
    # 3 points at r1: 60°, 180°, 300° (rotated)
    for angle in [60, 180, 300]:
        rad = np.deg2rad(angle)
        direction = np.cos(rad) * v0 + np.sin(rad) * n_perp
        points.append(O + r1 * direction)
    
    # 3 points at r2: 0°, 120°, 240° (along medians)
    for v in [v0, v120, v240]:
        points.append(O + r2 * v)
    
    # 1 point at r2: 60° (completes 11 points)
    rad = np.deg2rad(60)
    direction = np.cos(rad) * v0 + np.sin(rad) * n_perp
    points.append(O + r2 * direction)

    # Apply symmetry breaking perturbations
    config = np.array(points)
    for i in range(len(config)):
        if i == 0:  # Skip centroid
            continue
        # Apply perturbation proportional to distance from center
        dist = np.linalg.norm(config[i] - O)
        perturbation = np.random.normal(0, symmetry_perturbation * dist, size=2)
        config[i] += perturbation
        
    return config

def generate_reflectional_symmetric_config(tri, symmetry_perturbation=0.0):
    A, B, C = tri
    
    # Compute centroid and distance to vertex
    O = (A + B + C) / 3
    L = np.linalg.norm(A - O)
    
    # Create reflectional symmetry across median from A
    median_A = (B + C) / 2 - A
    median_A = median_A / np.linalg.norm(median_A)
    perp_A = np.array([-median_A[1], median_A[0]])
    
    # Points along the median
    points = [O]
    points.append(A + 0.3 * (O - A))
    points.append(A + 0.6 * (O - A))
    
    # Points symmetric across the median
    for i in range(4):
        dist = 0.2 + random.uniform(-0.05, 0.05)
        height = 0.1 + random.uniform(-0.03, 0.03)
        point = A + dist * (O - A) + height * perp_A
        points.append(point)
        points.append(A + dist * (O - A) - height * perp_A)
    
    # Add one more point for total of 11
    points.append(O + 0.5 * (B - O) + 0.1 * perp_A)

    # Apply symmetry breaking perturbations
    config = np.array(points)
    for i in range(len(config)):
        if i == 0:  # Skip centroid
            continue
        dist = np.linalg.norm(config[i] - O)
        perturbation = np.random.normal(0, symmetry_perturbation * dist, size=2)
        config[i] += perturbation
        
    return config

def generate_hexagonal_symmetric_config(tri, symmetry_perturbation=0.0):
    A, B, C = tri
    
    # Compute centroid and distance to vertex
    O = (A + B + C) / 3
    L = np.linalg.norm(A - O)
    
    # Hexagonal pattern with 6-fold symmetry
    points = [O]
    
    # Inner ring - 6 points
    for i in range(6):
        angle = i * 60
        rad = np.deg2rad(angle)
        direction = np.array([np.cos(rad), np.sin(rad)])
        r = 0.2 * L + random.uniform(-0.03, 0.03) * L
        points.append(O + r * direction)
    
    # Outer ring - 4 points (hexagonal pattern with some variation)
    for i in range(4):
        angle = i * 90 + 30
        rad = np.deg2rad(angle)
        direction = np.array([np.cos(rad), np.sin(rad)])
        r = 0.4 * L + random.uniform(-0.05, 0.05) * L
        points.append(O + r * direction)

    # Apply symmetry breaking perturbations
    config = np.array(points)
    for i in range(len(config)):
        if i == 0:  # Skip centroid
            continue
        dist = np.linalg.norm(config[i] - O)
        perturbation = np.random.normal(0, symmetry_perturbation * dist, size=2)
        config[i] += perturbation
        
    return config

def optimize_configuration(initial_config, tri):
    config = initial_config.copy()
    current_min_area = get_smallest_triangle_area(config)

    # Simulated annealing parameters
    temperature = 0.1
    step_size = 0.05
    max_iter = 60000
    no_improve_count = 0
    max_no_improve = 300
    
    # Adaptive critical point bias
    critical_bias = 0.95
    
    # For step size adaptation
    acceptance_window = 50
    acceptance_history = []
    target_acceptance_rate = 0.3  # 30% acceptance rate
    
    for iter in range(max_iter):
        # Find smallest triangles with threshold
        min_area, critical_points, critical_triangles = find_smallest_triangle(config, threshold=0.15)

        # Adaptive critical point bias (decreases as we progress)
        critical_bias = max(0.3, 0.95 - 0.65 * (iter / max_iter))

        # Choose point to perturb with adaptive bias
        if critical_points and random.random() < critical_bias:
            idx = random.choice(critical_points)
            # Compute gradient direction for critical points
            if random.random() < 0.7:
                direction = compute_gradient_direction(config, idx, critical_triangles)
                d = direction * step_size * random.uniform(0.8, 1.2)
            else:
                d = np.random.normal(0, step_size, size=2)
        else:
            idx = random.randint(0, 10)
            d = np.random.normal(0, step_size, size=2)

        candidate = config.copy()
        candidate[idx] += d

        # Boundary reflection with stronger boundary exploration
        boundary_strength = 1.0 + 0.5 * (iter / max_iter)
        candidate[idx] = reflect_into_triangle(candidate[idx], tri, boundary_strength)

        # Distinctness check
        if not is_distinct(candidate, idx, 1e-8):
            # Record rejection for adaptation
            acceptance_history.append(0)
            if len(acceptance_history) > acceptance_window:
                acceptance_history.pop(0)
            continue

        new_min_area = get_smallest_triangle_area(candidate)

        # Simulated annealing acceptance
        delta = new_min_area - current_min_area
        accepted = False
        if delta > 0 or random.random() < np.exp(delta / temperature):
            config = candidate
            current_min_area = new_min_area
            no_improve_count = 0
            step_size *= 0.9995
            accepted = True
        else:
            no_improve_count += 1
            accepted = False

        # Record acceptance for adaptation
        acceptance_history.append(1 if accepted else 0)
        if len(acceptance_history) > acceptance_window:
            acceptance_history.pop(0)
            
        # Adapt step size based on acceptance rate
        if len(acceptance_history) == acceptance_window:
            acceptance_rate = sum(acceptance_history) / acceptance_window
            if acceptance_rate > target_acceptance_rate + 0.1:
                step_size *= 1.1  # Increase step size
            elif acceptance_rate < target_acceptance_rate - 0.1:
                step_size *= 0.9  # Decrease step size
                
            # Constrain step size to reasonable bounds
            step_size = max(0.001, min(step_size, 0.2))

        # Adaptive step size control
        if no_improve_count >= max_no_improve:
            step_size *= 0.95
            no_improve_count = 0

        # Cool temperature
        temperature *= 0.99985

    return config

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    best_config = None
    best_min_area = -1
    
    # Try multiple restarts with different initial conditions
    for restart in range(8):  # Increased from 3 to 8 restarts
        # Vary symmetry type and parameters
        symmetry_type = restart % 3  # 0: rotational, 1: reflectional, 2: hexagonal
        
        if symmetry_type == 0:  # Rotational symmetry
            symmetry_perturbation = 0.05 * (restart + 1) / 8
            initial_config = generate_rotational_symmetric_config(tri, symmetry_perturbation)
        elif symmetry_type == 1:  # Reflectional symmetry
            symmetry_perturbation = 0.05 * (restart + 1) / 8
            initial_config = generate_reflectional_symmetric_config(tri, symmetry_perturbation)
        else:  # Hexagonal symmetry
            symmetry_perturbation = 0.05 * (restart + 1) / 8
            initial_config = generate_hexagonal_symmetric_config(tri, symmetry_perturbation)
        
        # Optimize the configuration
        optimized_config = optimize_configuration(initial_config, tri)
        
        # Evaluate
        min_area = get_smallest_triangle_area(optimized_config)
        if min_area > best_min_area:
            best_min_area = min_area
            best_config = optimized_config
    
    return best_config