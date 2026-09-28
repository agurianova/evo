import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import scipy.spatial

np.random.seed(42)

def find_candidate_small_triangles(points):
    # Use Delaunay triangulation to identify candidate small triangles
    # The smallest triangle must be a Delaunay triangle
    tri = scipy.spatial.Delaunay(points)
    min_area = float('inf')
    min_indices = None
    
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
        perturb_eps = 0.01
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
        stagnation_limit = 3000
        stagnation_count = 0
        restarts = 0
        max_restarts = 2
        
        # Track success rate for adaptive cooling
        recent_successes = 0
        success_window = 500
        
        for i in range(iterations):
            # Dynamic bottleneck targeting ratio based on stagnation
            base_target_ratio = 0.5
            if stagnation_count > stagnation_limit * 0.5:
                target_ratio = 0.75
            elif stagnation_count > stagnation_limit * 0.75:
                target_ratio = 0.9
            else:
                target_ratio = base_target_ratio

            # Target bottleneck triangles with dynamic probability
            if np.random.random() < target_ratio:
                min_indices = find_candidate_small_triangles(points)
                idx = np.random.choice(min_indices)
            else:
                idx = np.random.randint(0, len(points))
            
            # Generate directional move
            angle = np.random.uniform(0, 2 * np.pi)
            r = np.random.uniform(0, step_size)
            dx, dy = r * np.cos(angle), r * np.sin(angle)
            
            candidate = points.copy()
            candidate[idx] += [dx, dy]
            
            if not is_inside_triangle(candidate[idx], A, B, C):
                # Project back to triangle boundary if outside
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
                
                candidate[idx] = closest_point

            new_min_area = get_smallest_triangle_area(candidate)
            
            # Skip if degenerate
            if new_min_area < 1e-10:
                stagnation_count += 1
                continue

            # Track success rate for adaptation
            if new_min_area > current_min_area:
                recent_successes += 1
            
            # Simulated annealing acceptance
            if new_min_area > current_min_area:
                # Always accept improvements
                points = candidate
                current_min_area = new_min_area
                
                # 1/5 success rule for step size adaptation
                if i > success_window:
                    success_rate = recent_successes / success_window
                    if success_rate > 0.2:
                        step_size = min(step_size * 1.05, max_step_size)
                    else:
                        step_size = max(step_size * 0.9, 0.01)
                
                stagnation_count = 0
            else:
                # Accept worse solutions with probability based on temperature
                delta = current_min_area - new_min_area
                if np.random.rand() < np.exp(-delta / temperature):
                    points = candidate
                    current_min_area = new_min_area
                    
                    # 1/5 success rule for step size adaptation
                    if i > success_window:
                        success_rate = recent_successes / success_window
                        if success_rate > 0.2:
                            step_size = min(step_size * 1.05, max_step_size)
                        else:
                            step_size = max(step_size * 0.9, 0.01)
                    
                    stagnation_count = 0
                else:
                    stagnation_count += 1

            # Adaptive cooling rate based on recent success
            if i > success_window:
                success_rate = recent_successes / success_window
                if success_rate > 0.3:
                    cooling_rate = 0.9995  # Cool slower when making good progress
                elif success_rate < 0.1:
                    cooling_rate = 0.998   # Cool faster to escape local optima
                else:
                    cooling_rate = 0.999
            else:
                cooling_rate = 0.999

            # Cool down
            temperature *= cooling_rate
            
            # Temperature reheating on prolonged stagnation
            if stagnation_count > stagnation_limit * 0.9:
                temperature = max(temperature * 1.2, current_min_area * 3)

            # Periodically reset success counter
            if i % success_window == 0:
                recent_successes = 0

            # Stagnation check - trigger restart if stuck
            if stagnation_count > stagnation_limit and restarts < max_restarts:
                # Restart with higher temperature and larger perturbation
                temperature = max(0.01, current_min_area * 3) * (1.5 ** (restarts + 1))
                # Perturb all points
                for j in range(len(points)):
                    angle = np.random.uniform(0, 2 * np.pi)
                    r = np.random.uniform(0, max_step_size * 1.5)
                    dx, dy = r * np.cos(angle), r * np.sin(angle)
                    candidate_point = points[j] + [dx, dy]
                    if is_inside_triangle(candidate_point, A, B, C):
                        points[j] = candidate_point
                    else:
                        # Project back to triangle
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