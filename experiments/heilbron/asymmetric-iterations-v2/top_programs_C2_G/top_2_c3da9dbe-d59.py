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

def entrypoint():
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Literature-based near-optimal configuration for n=11 (barycentric coordinates)
    base_bary = [
        (0.0000, 0.0000), (1.0000, 0.0000), (0.0000, 1.0000),  # vertices
        (0.2113, 0.0000), (0.7887, 0.0000), (0.0000, 0.2113),  # edge points
        (0.0000, 0.7887), (0.2113, 0.2113), (0.2113, 0.5774),  # more edge/interior
        (0.5774, 0.2113), (0.3660, 0.3660)  # interior points
    ]
    
    best_points = None
    best_min_area = -1
    n_trials = 5
    
    for _ in range(n_trials):
        # Perturb base configuration with controlled randomness
        perturb_eps = 0.01 * (1 + _ * 0.2)  # Increase perturbation with trial number
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
        
        # Simulated annealing parameters
        current_min_area = get_smallest_triangle_area(points)
        max_step_size = 0.2
        step_size = 0.05
        temperature = max(0.01, current_min_area * 3)
        iterations = 20000
        stagnation_limit = 1500  # Reduced from 3000
        stagnation_count = 0
        restarts = 0
        max_restarts = 3  # Increased from 2
        
        # Adaptive parameters
        move_type_ema = [0.4, 0.3, 0.3]  # single, double, triple moves
        ema_alpha = 0.2
        success_count = 0
        total_attempts = 0
        
        for i in range(iterations):
            # Dynamic bottleneck targeting ratio
            bottleneck_ratio = 0.5
            if stagnation_count > stagnation_limit * 0.3:
                bottleneck_ratio = 0.7
            if stagnation_count > stagnation_limit * 0.6:
                bottleneck_ratio = 0.95

            # Move type selection with EMA
            move_type_idx = np.random.choice([0, 1, 2], p=move_type_ema)
            move_type = ['single', 'double', 'triple'][move_type_idx]

            candidate = points.copy()
            improved = False
            
            if np.random.random() < bottleneck_ratio:
                min_indices = find_smallest_triangle_indices(points)
                
                if move_type == 'single':
                    idx = np.random.choice(min_indices)
                    angle = np.random.uniform(0, 2 * np.pi)
                    r = np.random.uniform(0, step_size)
                    dx, dy = r * np.cos(angle), r * np.sin(angle)
                    candidate[idx] += [dx, dy]
                    
                elif move_type == 'double':
                    idx1, idx2, _ = min_indices
                    angle = np.random.uniform(0, 2 * np.pi)
                    r = np.random.uniform(0, step_size * 0.5)
                    dx1, dy1 = r * np.cos(angle), r * np.sin(angle)
                    dx2, dy2 = -dx1, -dy1  # Opposite directions
                    candidate[idx1] += [dx1, dy1]
                    candidate[idx2] += [dx2, dy2]
                    
                else:  # 'triple'
                    idx1, idx2, idx3 = min_indices
                    angle = np.random.uniform(0, 2 * np.pi)
                    r = np.random.uniform(0, step_size * 0.3)
                    dx1, dy1 = r * np.cos(angle), r * np.sin(angle)
                    dx2, dy2 = r * np.cos(angle + 2*np.pi/3), r * np.sin(angle + 2*np.pi/3)
                    dx3, dy3 = r * np.cos(angle + 4*np.pi/3), r * np.sin(angle + 4*np.pi/3)
                    candidate[idx1] += [dx1, dy1]
                    candidate[idx2] += [dx2, dy2]
                    candidate[idx3] += [dx3, dy3]
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

                    # Interior bias: push slightly inward if very close to boundary
                    boundary_margin = 0.005
                    if min_dist < boundary_margin:
                        direction = np.zeros(2)
                        for (p1, p2) in edges:
                            v = p2 - p1
                            w = candidate[idx] - p1
                            c1 = np.dot(w, v)
                            c2 = np.dot(v, v)
                            b = 0 if c2 == 0 else c1 / c2
                            b = max(0.0, min(1.0, b))
                            proj = p1 + b * v
                            normal = np.array([-(p2[1]-p1[1]), p2[0]-p1[0]])
                            normal = normal / np.linalg.norm(normal)
                            if np.dot(normal, C - p1) < 0:
                                normal = -normal
                            direction += normal
                        
                        if np.linalg.norm(direction) > 0:
                            direction = direction / np.linalg.norm(direction)
                            candidate[idx] = candidate[idx] + direction * (boundary_margin - min_dist)
                            
                        # Final check
                        if is_inside_triangle(candidate[idx], A, B, C):
                            continue

                    candidate[idx] = closest_point

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
            if improved:
                move_type_ema[move_type_idx] = ema_alpha * 1.0 + (1 - ema_alpha) * move_type_ema[move_type_idx]
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

                        # Interior bias
                        boundary_margin = 0.005
                        if min_dist < boundary_margin:
                            direction = np.zeros(2)
                            for (p1, p2) in edges:
                                v = p2 - p1
                                w = candidate_point - p1
                                c1 = np.dot(w, v)
                                c2 = np.dot(v, v)
                                b = 0 if c2 == 0 else c1 / c2
                                b = max(0.0, min(1.0, b))
                                proj = p1 + b * v
                                normal = np.array([-(p2[1]-p1[1]), p2[0]-p1[0]])
                                normal = normal / np.linalg.norm(normal)
                                if np.dot(normal, C - p1) < 0:
                                    normal = -normal
                                direction += normal
                            
                            if np.linalg.norm(direction) > 0:
                                direction = direction / np.linalg.norm(direction)
                                candidate_point = candidate_point + direction * (boundary_margin - min_dist)
                                
                            if is_inside_triangle(candidate_point, A, B, C):
                                points[j] = candidate_point
                                continue

                        points[j] = closest_point
                
                current_min_area = get_smallest_triangle_area(points)
                stagnation_count = 0
                restarts += 1

        # Track best configuration across trials
        final_min_area = get_smallest_triangle_area(points)
        if final_min_area > best_min_area:
            best_points = points
            best_min_area = final_min_area

    return best_points