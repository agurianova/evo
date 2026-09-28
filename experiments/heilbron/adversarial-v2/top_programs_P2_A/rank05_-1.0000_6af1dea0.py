import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import math
import random
from scipy.spatial import ConvexHull

np.random.seed(42)
random.seed(42)

def compute_triangle_area(a, b, c):
    return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

def get_critical_triangles(points, epsilon=1e-6):
    n = len(points)
    min_area = float('inf')
    critical_triplets = []
    
    # First pass to find minimum area
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = compute_triangle_area(points[i], points[j], points[k])
                if area < min_area:
                    min_area = area
    
    # Second pass to collect all triangles within epsilon of minimum
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = compute_triangle_area(points[i], points[j], points[k])
                if abs(area - min_area) < epsilon:
                    critical_triplets.append((i, j, k))
    
    return critical_triplets, min_area

def project_to_triangle(point, A, B, C):
    """Project point back into triangle with boundary awareness"""
    if is_inside_triangle(point, A, B, C):
        return point.copy()
    
    edges = [(A, B), (B, C), (C, A)]
    projections = []
    
    for (p1, p2) in edges:
        v = p2 - p1
        w = point - p1
        c1 = np.dot(w, v)
        c2 = np.dot(v, v)
        if c2 == 0:
            b = p1
        else:
            b = max(0, min(1, c1/c2))
            b = p1 + b * v
        
        dist = np.linalg.norm(point - b)
        projections.append((dist, b))
    
    # Return closest projection
    _, closest = min(projections, key=lambda x: x[0])
    return closest

def generate_initial_configurations(A, B, C):
    """Generate multiple high-quality starting configurations based on known Heilbronn patterns"""
    configs = []
    
    # Pattern 1: Concentric triangles
    center = (A + B + C) / 3
    side_length = np.linalg.norm(B - A)
    
    # Inner triangle (3 points)
    r1 = 0.25 * side_length
    angles = [0, 2*math.pi/3, 4*math.pi/3]
    inner_points = [center + r1 * np.array([math.cos(a), math.sin(a)]) for a in angles]
    
    # Middle triangle (4 points)
    r2 = 0.5 * side_length
    angles = [math.pi/6, math.pi/6 + 2*math.pi/4, math.pi/6 + 4*math.pi/4, math.pi/6 + 6*math.pi/4]
    middle_points = [center + r2 * np.array([math.cos(a), math.sin(a)]) for a in angles]
    
    # Outer points (4 points)
    r3 = 0.75 * side_length
    angles = [math.pi/6, math.pi/6 + 2*math.pi/4, math.pi/6 + 4*math.pi/4, math.pi/6 + 6*math.pi/4]
    outer_points = [center + r3 * np.array([math.cos(a), math.sin(a)]) for a in angles]
    
    # Combine and filter points inside triangle
    config1 = np.array([p for p in inner_points + middle_points + outer_points 
                       if is_inside_triangle(p, A, B, C)])
    # Add random points if needed
    while len(config1) < 11:
        r1, r2 = random.random(), random.random()
        s = math.sqrt(r1)
        p = (1 - s) * A + s * (1 - r2) * B + s * r2 * C
        config1 = np.vstack([config1, p])
    configs.append(config1[:11])
    
    # Pattern 2: Parabolic arc (known good for n=11)
    # Scale to fit within triangle
    base = A
    height = C[1]
    width = B[0] - A[0]
    
    # Create points along a parabola y = a*x*(width-x)
    a = 0.8 * height / (width/2)**2  # Scale factor to fit within triangle
    x_vals = np.linspace(0.1*width, 0.9*width, 11)
    y_vals = a * x_vals * (width - x_vals)
    
    # Add some random perturbation to avoid symmetry traps
    config2 = np.array([[x + width*0.02*random.uniform(-1,1), 
                        y + height*0.02*random.uniform(-1,1)] 
                       for x, y in zip(x_vals, y_vals)])
    
    # Project all points to ensure they're inside the triangle
    config2 = np.array([project_to_triangle(p, A, B, C) for p in config2])
    configs.append(config2)
    
    # Pattern 3: Grid with perturbation
    grid_points = []
    for i in range(4):
        for j in range(4 - i):
            # Barycentric coordinates
            alpha = i/3.0 + random.uniform(-0.05, 0.05)
            beta = j/3.0 + random.uniform(-0.05, 0.05)
            gamma = 1 - alpha - beta + random.uniform(-0.05, 0.05)
            # Ensure valid barycentric coordinates
n            if gamma < 0:
                excess = -gamma
                gamma = 0
                alpha -= excess/2
                beta -= excess/2
            elif alpha < 0:
                excess = -alpha
                alpha = 0
                beta -= excess/2
                gamma -= excess/2
            elif beta < 0:
                excess = -beta
                beta = 0
                alpha -= excess/2
                gamma -= excess/2
            
            point = alpha * A + beta * B + gamma * C
            if is_inside_triangle(point, A, B, C):
                grid_points.append(point)
    
    if len(grid_points) >= 11:
        config3 = np.array(random.sample(grid_points, 11))
    else:
        # Add random points if needed
        config3 = np.array(grid_points)
        while len(config3) < 11:
            r1, r2 = random.random(), random.random()
            s = math.sqrt(r1)
            p = (1 - s) * A + s * (1 - r2) * B + s * r2 * C
            config3 = np.vstack([config3, p])
    configs.append(config3)
    
    return configs

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()

    # Generate informed starting configurations
    initial_configs = generate_initial_configurations(A, B, C)
    
    # Evaluate initial configurations
    best_config = None
    best_min_area = -1
    for config in initial_configs:
        min_area = get_smallest_triangle_area(config)
        if min_area > best_min_area:
            best_min_area = min_area
            best_config = config

    # Simulated annealing with critical triangle focus
    current = best_config.copy()
    current_min_area = best_min_area
    
    # Parameters
    initial_temp = 0.05
    cooling_rate = 0.995
    max_iter = 5000
    min_temp = 1e-6
    critical_epsilon = 1e-5
    step_size = 0.02
    
    temp = initial_temp
    iter_count = 0
    no_improve_count = 0
    max_no_improve = 500
    
    while temp > min_temp and iter_count < max_iter and no_improve_count < max_no_improve:
        iter_count += 1
        
        # Identify critical triangles
        critical_triplets, min_area = get_critical_triangles(current, critical_epsilon)
        
        # If we're at a local optimum (no improvements possible with current step)
        if min_area > current_min_area * 0.9999:
            no_improve_count += 1
        else:
            no_improve_count = 0
        
        # Create a candidate configuration by moving points in critical triangles
        candidate = current.copy()
        
        # For each critical triangle, calculate displacement vectors
        displacement_vectors = np.zeros((11, 2))
        point_weights = np.zeros(11)
        critical_points = set()
        
        for triplet in critical_triplets:
            i, j, k = triplet
            critical_points.update([i, j, k])
            
            # For each point in the triplet, calculate direction to move
            for idx in triplet:
                others = [x for x in triplet if x != idx]
                p0 = candidate[others[0]]
                p1 = candidate[others[1]]
                base_vector = p1 - p0
                normal = np.array([-base_vector[1], base_vector[0]])
                vec = candidate[idx] - p0
                if np.dot(normal, vec) < 0:
                    normal = -normal
                norm = np.linalg.norm(normal)
                if norm > 1e-10:
                    normal = normal / norm
                    displacement_vectors[idx] += normal
                    point_weights[idx] += 1

        # Apply displacements with adaptive step size
        for idx in range(11):
            if point_weights[idx] > 0:
                direction = displacement_vectors[idx] / point_weights[idx]
                # Add some randomness to escape local minima
                noise = np.random.normal(0, step_size/3, 2)
                displacement = step_size * direction + noise
                candidate[idx] += displacement

        # Project all points back into triangle
        for idx in range(11):
            candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

        # Evaluate candidate
        candidate_min_area = get_smallest_triangle_area(candidate)
        
        # Simulated annealing acceptance
        delta = candidate_min_area - current_min_area
        if delta > 0 or np.random.rand() < np.exp(delta / temp):
            current = candidate
            current_min_area = candidate_min_area

        # Adaptive step size - increase if we're making progress, decrease if stuck
        if candidate_min_area > current_min_area:
            step_size = min(0.05, step_size * 1.02)
        else:
            step_size = max(0.001, step_size * 0.98)

        # Update temperature
        temp *= cooling_rate

    return current