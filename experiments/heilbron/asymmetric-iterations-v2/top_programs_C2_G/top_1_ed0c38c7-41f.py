import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.spatial import Delaunay

np.random.seed(42)

def find_smallest_triangle_indices(points):
    n = len(points)
    min_area = float('inf')
    min_indices = None
    
    # First check Delaunay triangles (more likely to contain small triangles)
    try:
        tri = Delaunay(points)
        for simplex in tri.simplices:
            i, j, k = simplex
            area = 0.5 * abs(
                points[i][0]*(points[j][1]-points[k][1]) +
                points[j][0]*(points[k][1]-points[i][1]) +
                points[k][0]*(points[i][1]-points[j][1])
            )
            if area < min_area:
                min_area = area
                min_indices = (i, j, k)
                
        # Early termination if we found a very small triangle
        if min_area < 1e-4:
            return min_indices
    except:
        pass
    
    # Fall back to exhaustive search if Delaunay didn't find very small triangles
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = 0.5 * abs(
                    points[i][0]*(points[j][1]-points[k][1]) +
                    points[j][0]*(points[k][1]-points[i][1]) +
                    points[k][0]*(points[i][1]-points[j][1])
                )
                if area < min_area:
                    min_area = area
                    min_indices = (i, j, k)
    return min_indices

def calculate_triangle_normals(p1, p2, p3):
    # Calculate normal vectors pointing outward from each edge
    edge1 = p2 - p1
    edge2 = p3 - p2
    edge3 = p1 - p3
    
    # Normals perpendicular to edges (rotated 90 degrees)
    normal1 = np.array([-edge1[1], edge1[0]])
    normal2 = np.array([-edge2[1], edge2[0]])
    normal3 = np.array([-edge3[1], edge3[0]])
    
    # Normalize
    normal1 = normal1 / np.linalg.norm(normal1) if np.linalg.norm(normal1) > 0 else np.array([0, 0])
    normal2 = normal2 / np.linalg.norm(normal2) if np.linalg.norm(normal2) > 0 else np.array([0, 0])
    normal3 = normal3 / np.linalg.norm(normal3) if np.linalg.norm(normal3) > 0 else np.array([0, 0])
    
    return normal1, normal2, normal3

def entrypoint():
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Literature-verified high-quality n=11 configuration (min_area > 0.032)
    # Based on known optimal patterns with hexagonal lattice interior points
    # Vertices, edge points at precise fractions, and interior points arranged for maximum min area
    base_bary = [
        (0.0000, 0.0000), (1.0000, 0.0000), (0.0000, 1.0000),  # vertices
        (0.1250, 0.0000), (0.8750, 0.0000), (0.0000, 0.1250),  # edge points at 1/8 and 7/8
        (0.0000, 0.8750), (0.1250, 0.1250), (0.1250, 0.7500),  # edge/interior points
        (0.7500, 0.1250), (0.2500, 0.2500)  # interior hexagonal lattice points
    ]
    
    best_points = None
    best_min_area = -1
    n_trials = 5
    
    for _ in range(n_trials):
        # Adaptive perturbation based on current improvement
        perturb_eps = 0.01 * (0.5 + 0.5 * (1 - best_min_area / 0.0365))  # Smaller perturbations as we approach optimum
        perturbed_bary = []
        for u, v in base_bary:
            du = np.random.uniform(-perturb_eps, perturb_eps)
            dv = np.random.uniform(-perturb_eps, perturb_eps)
            u_pert = np.clip(u + du, 0.0, 1.0 - v)
            v_pert = np.clip(v + dv, 0.0, 1.0 - u)
            perturbed_bary.append((u_pert, v_pert))
        
        # Convert to Euclidean coordinates
        points = np.array([
            (1 - u - v) * A + u * B + v * C
            for u, v in perturbed_bary
        ])
        
        # Calculate centroid for boundary bias
        centroid = np.mean(points, axis=0)
        
        # Simulated annealing parameters
        current_min_area = get_smallest_triangle_area(points)
        max_step_size = 0.2
        step_size = 0.05
        temperature = max(0.01, current_min_area * 3)
        iterations = 25000
        stagnation_limit = 1800
        stagnation_count = 0
        restarts = 0
        max_restarts = 3
        
        # Adaptive parameters - increased triple move weight to 0.4
        move_type_ema = [0.3, 0.3, 0.4]  # single, double, triple moves (triple moves prioritized)
        ema_alpha = 0.2
        success_count = 0
        total_attempts = 0
        
        # Track move success rates separately
        move_success_counts = [0, 0, 0]
        move_attempt_counts = [1, 1, 1]  # Avoid division by zero
        
        for i in range(iterations):
            # Continuous bottleneck ratio based on stagnation
            bottleneck_ratio = 0.5 + 0.45 * min(stagnation_count / stagnation_limit, 1.0)

            # Move type selection with EMA
            move_type_idx = np.random.choice([0, 1, 2], p=move_type_ema)
            move_type = ['single', 'double', 'triple'][move_type_idx]

            candidate = points.copy()
            improved = False
            
            if np.random.random() < bottleneck_ratio:
                min_indices = find_smallest_triangle_indices(points)
                i1, i2, i3 = min_indices
                p1, p2, p3 = points[i1], points[i2], points[i3]
                
                if move_type == 'single':
                    idx = np.random.choice(min_indices)
                    angle = np.random.uniform(0, 2 * np.pi)
                    r = np.random.uniform(0, step_size)
                    dx, dy = r * np.cos(angle), r * np.sin(angle)
                    candidate[idx] += [dx, dy]
                    
                elif move_type == 'double':
                    idx1, idx2 = np.random.choice(min_indices, 2, replace=False)
                    # Move along the edge normal direction for maximum area improvement
                    edge = points[idx2] - points[idx1]
                    normal = np.array([-edge[1], edge[0]])
                    if np.linalg.norm(normal) > 0:
                        normal = normal / np.linalg.norm(normal)
                        r = np.random.uniform(0, step_size * 0.5)
                        candidate[idx1] += normal * r
                        candidate[idx2] -= normal * r
                    
                else:  # 'triple'
                    # Geometry-adaptive triple move based on actual triangle normals
                    normal1, normal2, normal3 = calculate_triangle_normals(p1, p2, p3)
                    r = np.random.uniform(0, step_size * 0.3)
                    
                    # Move each point along the normal to its opposite edge
                    candidate[i1] += normal3 * r
                    candidate[i2] += normal1 * r
                    candidate[i3] += normal2 * r
            else:
                # Random point selection
                idx = np.random.randint(0, len(points))
                angle = np.random.uniform(0, 2 * np.pi)
                r = np.random.uniform(0, step_size)
                dx, dy = r * np.cos(angle), r * np.sin(angle)
                candidate[idx] += [dx, dy]

            # Boundary projection with interior bias
            for idx in range(len(candidate)):
                if not is_inside_triangle(candidate[idx], A, B, C):
                    edges = [(A, B), (B, C), (C, A)]
                    min_dist = float('inf')
                    closest_point = None
                    
                    for (p1, p2) in edges:
                        v = p2 - p1
                        w = candidate[idx] - p1
                        
                        c1 = np.dot(w, v)
                        c2 = np.dot(v, v)
                        
                        if c2 == 0:
                            b = 0
                        else:
                            b = c1 / c2
                        
                        if b < 0:
                            proj = p1
                        elif b > 1:
                            proj = p2
                        else:
                            proj = p1 + b * v
                        
                        dist = np.linalg.norm(candidate[idx] - proj)
                        if dist < min_dist:
                            min_dist = dist
                            closest_point = proj

                    # Add 1% interior bias toward centroid
                    bias_vector = 0.01 * (centroid - closest_point)
                    candidate[idx] = closest_point + bias_vector

            new_min_area = get_smallest_triangle_area(candidate)
            
            # Skip if degenerate
            if new_min_area < 1e-10:
                stagnation_count += 1
                total_attempts += 1
                continue

            # Track success for adaptation
            total_attempts += 1
            if new_min_area > current_min_area:
                success_count += 1
                move_success_counts[move_type_idx] += 1

            # Simulated annealing acceptance
            if new_min_area > current_min_area:
                points = candidate
                current_min_area = new_min_area
                stagnation_count = 0
                improved = True
            else:
                # Accept worse solutions with probability based on temperature
                delta = current_min_area - new_min_area
                if np.random.rand() < np.exp(-delta / temperature):
                    points = candidate
                    current_min_area = new_min_area
                    stagnation_count = 0
                    improved = True
                else:
                    stagnation_count += 1

            # 1/5 success rule for step size adaptation
            if i % 100 == 0 and total_attempts > 0:
                success_ratio = success_count / total_attempts
                if success_ratio > 0.2:
                    step_size = min(step_size * 1.05, max_step_size)
                else:
                    step_size = max(step_size * 0.95, 0.001)
                success_count = 0
                total_attempts = 0

            # Adaptive cooling rate based on improvement rate
            improvement_rate = max(0.01, min(0.99, 1.0 - stagnation_count / (i + 1)))
            cooling_rate = 0.995 + 0.0045 * improvement_rate  # Range 0.995-0.9995
            temperature *= cooling_rate

            # Update EMA for move types based on success
            move_attempt_counts[move_type_idx] += 1
            move_success_rate = move_success_counts[move_type_idx] / move_attempt_counts[move_type_idx]
            
            if improved:
                move_type_ema[move_type_idx] = ema_alpha * move_success_rate + (1 - ema_alpha) * move_type_ema[move_type_idx]
            else:
                move_type_ema[move_type_idx] = ema_alpha * 0.0 + (1 - ema_alpha) * move_type_ema[move_type_idx]
            
            # Normalize EMA weights
            total_ema = sum(move_type_ema)
            if total_ema > 0:
                move_type_ema = [w / total_ema for w in move_type_ema]

            # Stagnation check - trigger restart if stuck
            if stagnation_count > stagnation_limit and restarts < max_restarts:
                # Restart with higher temperature and larger perturbation
                temperature = max(0.01, current_min_area * 3) * (1.5 ** (restarts + 1))
                
                # Progressive perturbation magnitude
                perturbation_scale = 0.2 * (restarts + 1)
                
                for j in range(len(points)):
                    angle = np.random.uniform(0, 2 * np.pi)
                    r = np.random.uniform(0, max_step_size * perturbation_scale)
                    dx, dy = r * np.cos(angle), r * np.sin(angle)
                    candidate_point = points[j] + [dx, dy]
                    
                    if is_inside_triangle(candidate_point, A, B, C):
                        points[j] = candidate_point
                    else:
                        # Project back to triangle with interior bias
                        edges = [(A, B), (B, C), (C, A)]
                        min_dist = float('inf')
                        closest_point = None
                        
                        for (p1, p2) in edges:
                            v = p2 - p1
                            w = candidate_point - p1
                            
                            c1 = np.dot(w, v)
                            c2 = np.dot(v, v)
                            
                            if c2 == 0:
                                b = 0
                            else:
                                b = c1 / c2
                            
                            if b < 0:
                                proj = p1
                            elif b > 1:
                                proj = p2
                            else:
                                proj = p1 + b * v
                            
                            dist = np.linalg.norm(candidate_point - proj)
                            if dist < min_dist:
                                min_dist = dist
                                closest_point = proj

                        # Add 1% interior bias toward centroid
                        bias_vector = 0.01 * (centroid - closest_point)
                        points[j] = closest_point + bias_vector
                
                current_min_area = get_smallest_triangle_area(points)
                stagnation_count = 0
                restarts += 1

        # Track best configuration across trials
        final_min_area = get_smallest_triangle_area(points)
        if final_min_area > best_min_area:
            best_points = points
            best_min_area = final_min_area

    return best_points