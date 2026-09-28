import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import math

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    n = 11
    
    # Compute triangle properties
    AB = B - A
    AC = C - A
    side_length = np.linalg.norm(AB)
    height = np.sqrt(3)/2 * side_length
    centroid = (A + B + C) / 3
    
    # MULTI-STRATEGY INITIALIZATION ENSEMBLE
    def create_hexagonal_lattice():
        points = []
        # Hexagonal grid with 11 points
        rows = 4
        points_per_row = [1, 2, 3, 4, 1]  # Total 11 points
        
        # Calculate spacing based on triangle dimensions
        y_spacing = height / (rows + 1)
        x_spacing = side_length / max(points_per_row)
        
        for i, count in enumerate(points_per_row):
            y = y_spacing * (i + 1)
            # Convert y to coordinate in our triangle
            y_coord = A[1] + y
            
            # Calculate x range at this height
            left_x = A[0] + (B[0] - A[0]) * (y / height)
            right_x = C[0] - (C[0] - B[0]) * (y / height)
            row_width = right_x - left_x
            
            for j in range(count):
                x = left_x + row_width * (j + 0.5) / count
                points.append(np.array([x, y_coord]))
        
        return np.array(points[:n])

    def create_perturbed_symmetric():
        points = []
        
        # 1. Central point
        points.append(centroid)
        
        # 2. Points along altitudes with controlled perturbations
        for vertex, midpoint in [(A, (B+C)/2), (B, (A+C)/2), (C, (A+B)/2)]:
            # 30% from vertex with random perturbation
            base = vertex + 0.3 * (midpoint - vertex)
            points.append(base + np.random.normal(0, 0.02 * side_length, 2))
            # 60% from vertex with random perturbation
            base = vertex + 0.6 * (midpoint - vertex)
            points.append(base + np.random.normal(0, 0.02 * side_length, 2))
        
        # 3. Points near vertices but inset with systematic symmetry breaking
        inset = 0.1 * side_length
        for i, vertex in enumerate([A, B, C]):
            # Move inward along the direction to centroid with increasing perturbation
            direction = centroid - vertex
            direction = direction / np.linalg.norm(direction)
            base = vertex + inset * direction
            # Progressive perturbation magnitude (0.01 to 0.03)
            magnitude = 0.01 + 0.02 * (i / 2)
            angle = np.random.uniform(0, 2 * np.pi)
            perturbation = np.array([magnitude * np.cos(angle), 
                                   magnitude * np.sin(angle)])
            points.append(base + perturbation * side_length)
        
        return np.array(points)

    def create_random_rejection():
        points = []
        # Generate points using rejection sampling
        while len(points) < n:
            # Generate random barycentric coordinates
            u = random.random()
            v = random.random()
            if u + v > 1:
                u, v = 1 - u, 1 - v
            w = 1 - u - v
            # Convert to Cartesian
            point = u * A + v * B + w * C
            
            # Check distinctness
            is_duplicate = False
            for p in points:
                if np.linalg.norm(point - p) < 1e-3:
                    is_duplicate = True
                    break
            
            if not is_duplicate and is_inside_triangle(point, A, B, C):
                points.append(point)
        
        return np.array(points)

    # Evaluate all initialization strategies and pick the best
    initializations = [
        create_hexagonal_lattice(),
        create_perturbed_symmetric(),
        create_random_rejection()
    ]
    
    # Select the best initialization based on min_area
    best_init_idx = 0
    best_init_score = 0
    for i, init in enumerate(initializations):
        score = get_smallest_triangle_area(init)
        if score > best_init_score:
            best_init_score = score
            best_init_idx = i
    
    points = initializations[best_init_idx].copy()
    
    # Ensure we have exactly 11 distinct points inside the triangle
    filtered_points = []
    for p in points:
        if is_inside_triangle(p, A, B, C):
            # Check distinctness
            is_duplicate = False
            for q in filtered_points:
                if np.linalg.norm(p - q) < 1e-5:
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered_points.append(p)
        if len(filtered_points) >= n:
            break
    
    # If we don't have enough points, add some more strategically
    while len(filtered_points) < n:
        # Add points near the centroid but offset
        angle = random.uniform(0, 2*np.pi)
        radius = random.uniform(0.05, 0.15)
        offset = np.array([radius * math.cos(angle), radius * math.sin(angle)])
        new_point = centroid + offset
        if is_inside_triangle(new_point, A, B, C):
            # Check distinctness
            is_duplicate = False
            for q in filtered_points:
                if np.linalg.norm(new_point - q) < 1e-5:
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered_points.append(new_point)
    
    points = np.array(filtered_points[:n])
    
    # ADAPTIVE SIMULATED ANNEALING OPTIMIZATION
    current_min_area = get_smallest_triangle_area(points)
    
    # Initialize temperature based on initial solution quality
    initial_temp = 0.002
    if current_min_area < 0.01:
        initial_temp = 0.01
    
    # ADAPTIVE PARAMETERS
    temperature = initial_temp
    base_step_size = 0.03
    step_size = base_step_size
    no_improve_count = 0
    max_no_improve = 1000
    
    # Track improvement statistics for adaptation
    improvement_history = []
    max_history_length = 100
    
    # Find smallest triangle function
    def find_smallest_triangle(points):
        n = len(points)
        min_area = float('inf')
        critical_indices = None
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    # Calculate triangle area using determinant formula
                    area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                     (points[k,0]-points[i,0])*(points[j,1]-points[i,1]))
                    if area < min_area:
                        min_area = area
                        critical_indices = (i, j, k)
        
        return min_area, critical_indices
    
    # Precompute inward unit normals for the three edges (for boundary reflection)
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
    
    # Main optimization loop with adaptive parameters
    while no_improve_count < max_no_improve:
        # Determine which point to perturb (bias toward critical points)
        current_min_area, critical_indices = find_smallest_triangle(points)
        if critical_indices is None:
            break
            
        # Adaptive critical point targeting probability
        targeting_prob = 0.6 + 0.3 * (0.0365 - current_min_area) / 0.0365
        targeting_prob = min(max(targeting_prob, 0.5), 0.95)
        
        if np.random.rand() < targeting_prob:
            idx = np.random.choice(critical_indices)
        else:
            idx = np.random.randint(0, n)
        
        # Generate perturbation
        dx = np.random.normal(0, step_size)
        dy = np.random.normal(0, step_size)
        new_point = points[idx] + np.array([dx, dy])
        
        # Boundary reflection
        P = new_point
        for _ in range(3):
            d_ab = np.dot(P - A, n_AB)
            if d_ab < 0:
                P = P - 2 * d_ab * n_AB
            d_bc = np.dot(P - B, n_BC)
            if d_bc < 0:
                P = P - 2 * d_bc * n_BC
            d_ac = np.dot(P - A, n_AC)
            if d_ac < 0:
                P = P - 2 * d_ac * n_AC
        
        # Safeguard: move toward centroid if still outside
        if not is_inside_triangle(P, A, B, C):
            for _ in range(10):
                P = 0.9 * P + 0.1 * centroid
                if is_inside_triangle(P, A, B, C):
                    break
        
        # Skip if still outside
        if not is_inside_triangle(P, A, B, C):
            no_improve_count += 1
            continue
        
        # Check distinctness
        dists = np.linalg.norm(points - P, axis=1)
        dists[idx] = np.inf  # Ignore self
        if np.min(dists) < 1e-5:  # Too close to existing point
            no_improve_count += 1
            continue
        
        # Create candidate configuration
        candidate = points.copy()
        candidate[idx] = P
        
        # Evaluate candidate
        candidate_min_area = get_smallest_triangle_area(candidate)
        
        # Simulated annealing acceptance
        delta = candidate_min_area - current_min_area
        if delta > 0 or np.random.rand() < np.exp(delta / temperature):
            points = candidate
            current_min_area = candidate_min_area
            
            # Record improvement
            improvement_history.append(delta)
            if len(improvement_history) > max_history_length:
                improvement_history.pop(0)
            
            # Reset no-improve counter on improvement
            no_improve_count = 0
            
            # Increase step size slightly on improvement for continued exploration
            step_size = min(step_size * 1.05, 0.05)
        else:
            no_improve_count += 1
            
        # ADAPTIVE COOLING AND STEP SIZE
        # Adjust cooling rate based on recent improvement history
        if len(improvement_history) > 0:
            avg_improvement = sum(improvement_history) / len(improvement_history)
            # Slow cooling if improvements are small
            if avg_improvement < 1e-5:
                cooling_factor = 0.9999
            else:
                cooling_factor = 0.9995
        else:
            cooling_factor = 0.9995
        
        # Cooling schedule - adaptive decay
        temperature *= cooling_factor
        
        # Gradually reduce step size, but adapt based on improvement rate
        if len(improvement_history) > 0 and sum(improvement_history) > 0:
            # If we're making good progress, maintain larger step size
            step_size *= 0.9995
        else:
            # If stuck, reduce step size more aggressively to explore local area
            step_size *= 0.998
        
        # Ensure minimum step size for exploration
        step_size = max(step_size, 0.005)

    # GRADIENT-BASED REFINEMENT TARGETING MINIMAL TRIANGLES
    refinement_iterations = 500
    refinement_step = 0.005
    
    for _ in range(refinement_iterations):
        current_min_area, critical_indices = find_smallest_triangle(points)
        if critical_indices is None:
            break
            
        # For each minimal triangle, compute gradient to increase area
        i, j, k = critical_indices
        p_i, p_j, p_k = points[[i, j, k]]
        
        # Compute area gradient with respect to each point
        # Area = 0.5 * |(p_j - p_i) × (p_k - p_i)|
        # Gradient w.r.t p_i = 0.5 * [(p_j - p_k)_y, (p_k - p_j)_x]
        # Gradient w.r.t p_j = 0.5 * [(p_k - p_i)_y, (p_i - p_k)_x]
        # Gradient w.r.t p_k = 0.5 * [(p_i - p_j)_y, (p_j - p_i)_x]
        
        grad_i = 0.5 * np.array([p_j[1] - p_k[1], p_k[0] - p_j[0]])
        grad_j = 0.5 * np.array([p_k[1] - p_i[1], p_i[0] - p_k[0]])
        grad_k = 0.5 * np.array([p_i[1] - p_j[1], p_j[0] - p_i[0]])
        
        # Normalize gradients
        if np.linalg.norm(grad_i) > 0:
            grad_i = grad_i / np.linalg.norm(grad_i)
        if np.linalg.norm(grad_j) > 0:
            grad_j = grad_j / np.linalg.norm(grad_j)
        if np.linalg.norm(grad_k) > 0:
            grad_k = grad_k / np.linalg.norm(grad_k)
        
        # Move points in direction of gradient
        candidate = points.copy()
        candidate[i] += refinement_step * grad_i
        candidate[j] += refinement_step * grad_j
        candidate[k] += refinement_step * grad_k
        
        # Boundary reflection for all three points
        for idx in [i, j, k]:
            P = candidate[idx]
            for _ in range(3):
                d_ab = np.dot(P - A, n_AB)
                if d_ab < 0:
                    P = P - 2 * d_ab * n_AB
                d_bc = np.dot(P - B, n_BC)
                if d_bc < 0:
                    P = P - 2 * d_bc * n_BC
                d_ac = np.dot(P - A, n_AC)
                if d_ac < 0:
                    P = P - 2 * d_ac * n_AC
            
            if is_inside_triangle(P, A, B, C):
                candidate[idx] = P
            else:
                # Fallback to centroid projection
                for _ in range(10):
                    P = 0.9 * P + 0.1 * centroid
                    if is_inside_triangle(P, A, B, C):
                        candidate[idx] = P
                        break

        # Check distinctness
        valid = True
        for idx in [i, j, k]:
            dists = np.linalg.norm(candidate - candidate[idx], axis=1)
            dists[idx] = np.inf
            if np.min(dists) < 1e-5:
                valid = False
                break
        
        if not valid:
            continue
        
        # Evaluate candidate
        candidate_min_area = get_smallest_triangle_area(candidate)
        
        # Accept if improvement
        if candidate_min_area > current_min_area:
            points = candidate

    return points