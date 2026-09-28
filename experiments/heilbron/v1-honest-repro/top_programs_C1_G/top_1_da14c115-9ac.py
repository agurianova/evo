import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import itertools


def barycentric_to_cartesian(u, v, w, A, B, C):
    return u * A + v * B + w * C

def cartesian_to_barycentric(p, A, B, C):
    # Compute barycentric coordinates (u, v, w) for point p in triangle ABC
    v0 = B - A
    v1 = C - A
    v2 = p - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-10:
        return (1/3, 1/3, 1/3)
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    return (u, v, w)

def get_affected_triangles(moved_indices, n_points):
    # Returns indices of triangles that include any moved point
    triangles = []
    for i in range(n_points):
        for j in range(i+1, n_points):
            for k in range(j+1, n_points):
                if i in moved_indices or j in moved_indices or k in moved_indices:
                    triangles.append((i, j, k))
    return triangles

def calculate_min_area(points, affected_triangles=None):
    if affected_triangles is None:
        return get_smallest_triangle_area(points)
    
    min_area = float('inf')
    for i, j, k in affected_triangles:
        area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                        (points[j,1]-points[i,1])*(points[k,0]-points[i,0]))
        if area < min_area:
            min_area = area
    return min_area

def generate_diverse_initialization(A, B, C):
    # Strategy 1: Symmetric pattern based on known good configurations
    strategy1 = []
    # Center point
    strategy1.append(0.333*A + 0.333*B + 0.333*C)
    # Points at different radii from center
    radii = [0.2, 0.4, 0.6, 0.8]
    for r in radii:
        n_points = 2 + int(r*10)
        for i in range(n_points):
            angle = 2 * np.pi * i / n_points
            # Convert polar to barycentric (simplified approximation)
            u = 0.333 + r * np.cos(angle) * 0.5
            v = 0.333 + r * np.sin(angle) * 0.5
            w = 1 - u - v
            # Project back to valid barycentric coordinates
            if u < 0 or v < 0 or w < 0:
                u = max(0, u)
                v = max(0, v)
                w = max(0, 1 - u - v)
            strategy1.append(barycentric_to_cartesian(u, v, w, A, B, C))
    strategy1 = np.array(strategy1[:11])

    # Strategy 2: Perturbed lattice
    rows = 4
    n_per_row = [3, 3, 3, 2]
    strategy2 = []
    for i in range(rows):
        v = i / (rows - 1) if rows > 1 else 0
        n_points = n_per_row[i]
        available_u = 1 - v
        step = available_u / max(1, n_points - 1)
        offset = 0.5 * step if i % 2 == 1 else 0.0
        
        for j in range(n_points):
            u = j * step + offset
            u = min(max(0, u), available_u)
            w = 1 - u - v
            strategy2.append(barycentric_to_cartesian(u, v, w, A, B, C))
    strategy2 = np.array(strategy2[:11])

    # Strategy 3: Delaunay triangulation of random points
    np.random.seed(42)
    random_points = []
    while len(random_points) < 11:
        u = np.random.random()
        v = np.random.random() * (1 - u)
        w = 1 - u - v
        p = barycentric_to_cartesian(u, v, w, A, B, C)
        if is_inside_triangle(p, A, B, C):
            random_points.append(p)
    strategy3 = np.array(random_points)

    # Evaluate each strategy and return the best one
    strategies = [strategy1, strategy2, strategy3]
    scores = [get_smallest_triangle_area(s) for s in strategies]
    return strategies[np.argmax(scores)]

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Generate diverse initial configuration
    points = generate_diverse_initialization(A, B, C)
    
    # Simulated annealing parameters
    initial_temp = 0.001
    cooling_rate = 0.99
    max_iter = 2000
    current_temp = initial_temp
    
    # Track best solution found
    best_points = points.copy()
    best_score = get_smallest_triangle_area(points)
    
    for iter in range(max_iter):
        # Adaptive noise magnitude based on progress
        noise_magnitude = 0.05 * (1.0 - best_score / 0.0365)
        noise_magnitude = max(0.005, min(0.05, noise_magnitude))
        
        # Select points to perturb (focus on critical areas)
        if np.random.rand() < 0.7:
            # Perturb points from the smallest triangle
            min_area, min_indices = float('inf'), None
            for i, j, k in itertools.combinations(range(11), 3):
                area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                (points[j,1]-points[i,1])*(points[k,0]-points[i,0]))
                if area < min_area:
                    min_area = area
                    min_indices = (i, j, k)
            points_to_perturb = list(min_indices)
        else:
            # Random point perturbation
            points_to_perturb = [np.random.randint(0, 11)]

        # Create candidate solution
        candidate = points.copy()
        affected_triangles = get_affected_triangles(points_to_perturb, 11)
        
        for idx in points_to_perturb:
            # Convert to barycentric coordinates
            u, v, w = cartesian_to_barycentric(points[idx], A, B, C)
            
            # Apply controlled perturbation in barycentric space
            du = np.random.normal(0, noise_magnitude)
            dv = np.random.normal(0, noise_magnitude)
            u_new, v_new = u + du, v + dv
            
            # Project back to valid simplex
            u_new = max(0, u_new)
            v_new = max(0, v_new)
            total = u_new + v_new
            if total > 1:
                u_new, v_new = u_new/total, v_new/total
            w_new = 1 - u_new - v_new
            
            # Convert back to Cartesian
            candidate[idx] = barycentric_to_cartesian(u_new, v_new, w_new, A, B, C)

        # Evaluate candidate
        candidate_score = calculate_min_area(candidate, affected_triangles)
        
        # Energy function (we want to minimize -min_area)
        current_score = calculate_min_area(points, affected_triangles)
        delta = candidate_score - current_score
        
        # Simulated annealing acceptance
        if delta > 0 or np.random.rand() < np.exp(delta / current_temp):
            points = candidate
            current_score = candidate_score
            
            # Update best solution if improved
            if candidate_score > best_score:
                best_points = candidate.copy()
                best_score = candidate_score

        # Cool temperature
        current_temp *= cooling_rate
        
        # Early termination if we've hit near-optimal
        if best_score >= 0.036:
            break

    return best_points