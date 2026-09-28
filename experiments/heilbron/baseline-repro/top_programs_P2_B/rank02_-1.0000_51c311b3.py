from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_segment(p, a, b):
        ap = p - a
        ab = b - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
        t = np.clip(t, 0.0, 1.0)
        return a + t * ab

    def project_to_triangle(p, A, B, C):
        if is_inside_triangle(p, A, B, C):
            return p
        proj_ab = project_to_segment(p, A, B)
        proj_bc = project_to_segment(p, B, C)
        proj_ca = project_to_segment(p, C, A)
        d_ab = np.linalg.norm(p - proj_ab)
        d_bc = np.linalg.norm(p - proj_bc)
        d_ca = np.linalg.norm(p - proj_ca)
        if d_ab <= d_bc and d_ab <= d_ca:
            return proj_ab
        elif d_bc <= d_ab and d_bc <= d_ca:
            return proj_bc
        else:
            return proj_ca

    def improve(points):
        initial_min_area_val = get_smallest_triangle_area(points)
        
        # Calculate difficulty as how close we are to the optimum
        difficulty = 1.0 - initial_min_area_val / 0.0365
        
        # Allocate more iterations for harder problems (closer to optimum)
        total_iters = max(1000, int(1000 + 10000 * difficulty))
        
        # Slower cooling for harder problems
        decay_rate = 0.5 + 1.5 * difficulty
        
        # Prevent premature cooling
        initial_temp = 0.1 * (1.0 + 10 * difficulty)
        restart_duration = max(10, int(0.1 * total_iters))
        max_stagnation = 50 * (1.0 + 10.0 * difficulty)  # Adaptive stagnation threshold

        initial_step = 0.05
        tolerance = 1e-10

        # Precompute triangle indexing structures
        n = points.shape[0]
        triangle_list = []
        triangle_areas = []
        point_to_triangles = [[] for _ in range(n)]
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    idx = len(triangle_list)
                    triangle_list.append((i, j, k))
                    x1, y1 = points[i]
                    x2, y2 = points[j]
                    x3, y3 = points[k]
                    area = 0.5 * abs((x2-x1)*(y3-y1) - (x3-x1)*(y2-y1))
                    triangle_areas.append(area)
                    point_to_triangles[i].append(idx)
                    point_to_triangles[j].append(idx)
                    point_to_triangles[k].append(idx)
        
        best = points.copy()
        best_score = initial_min_area_val
        best_triangle_areas = triangle_areas.copy()
        current = best.copy()
        current_triangle_areas = triangle_areas.copy()
        current_score = best_score
        restart_countdown = 0
        stagnation_count = 0
        restart_counter = 0  # Track number of restarts

        for i_iter in range(total_iters):
            # Cosine annealing for step size
            base_step = initial_step * 0.5 * (1 + np.cos(np.pi * i_iter / total_iters))
            
            # Adaptive temperature decay
            current_temp = max(1e-5, initial_temp * np.exp(-decay_rate * i_iter / total_iters))
            
            if restart_countdown > 0:
                step_size = 3.0 * base_step
                restart_countdown -= 1
            else:
                step_size = base_step

            # With 5% probability, do an exploration move (perturb one point) instead of gradient move
            if not (restart_countdown > 0) and np.random.rand() < 0.05:
                # Exploration move: perturb one random point
                candidate = current.copy()
                idx = np.random.randint(0, n)
                # Move the point by step_size in a random direction
                candidate[idx] += step_size * (np.random.rand(2) - 0.5)
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
                # Update candidate_triangle_areas for triangles that include idx
                candidate_triangle_areas = current_triangle_areas.copy()
                affected_triangles = set()
                affected_triangles.update(point_to_triangles[idx])
                for tri_idx in affected_triangles:
                    i, j, k = triangle_list[tri_idx]
                    x1, y1 = candidate[i]
                    x2, y2 = candidate[j]
                    x3, y3 = candidate[k]
                    area = 0.5 * abs((x2-x1)*(y3-y1) - (x3-x1)*(y2-y1))
                    candidate_triangle_areas[tri_idx] = area
                min_area_candidate = min(candidate_triangle_areas)
            else:
                # Select critical triangles adaptively based on difficulty
                idx_sorted = np.argsort(current_triangle_areas)
                num_critical = min(10, max(3, int(10 * difficulty)))
                critical_triangles = []
                for i in range(num_critical):
                    tri_idx = idx_sorted[i]
                    area_val = current_triangle_areas[tri_idx]
                    critical_triangles.append((area_val, triangle_list[tri_idx]))
                
                # Multi-triangle gradient optimization with area weighting
                displacement_per_vertex = np.zeros_like(current)
                weight_sum_per_vertex = np.zeros(n)
                
                for area_val, tri in critical_triangles:
                    i, j, k = tri
                    # Weight by inverse square root of area to broaden focus
                    weight = 1.0 / np.sqrt(area_val + 1e-10)
                    
                    # For vertex i
                    a, b = j, k
                    v = i
                    s = 0.5 * ((current[a,0]-current[v,0])*(current[b,1]-current[v,1]) - 
                              (current[b,0]-current[v,0])*(current[a,1]-current[v,1]))
                    sign_s = 1.0 if s >= 0 else -1.0
                    ab = current[a] - current[b]
                    ab_norm = np.linalg.norm(ab)
                    if ab_norm > 1e-10:
                        direction = np.array([current[a,1] - current[b,1], 
                                             current[b,0] - current[a,0]])
                        unit_direction = direction / ab_norm
                        displacement_per_vertex[v] += weight * sign_s * unit_direction
                        weight_sum_per_vertex[v] += weight

                    # For vertex j
                    a, b = i, k
                    v = j
                    s = 0.5 * ((current[a,0]-current[v,0])*(current[b,1]-current[v,1]) - 
                              (current[b,0]-current[v,0])*(current[a,1]-current[v,1]))
                    sign_s = 1.0 if s >= 0 else -1.0
                    ab = current[a] - current[b]
                    ab_norm = np.linalg.norm(ab)
                    if ab_norm > 1e-10:
                        direction = np.array([current[a,1] - current[b,1], 
                                             current[b,0] - current[a,0]])
                        unit_direction = direction / ab_norm
                        displacement_per_vertex[v] += weight * sign_s * unit_direction
                        weight_sum_per_vertex[v] += weight

                    # For vertex k
                    a, b = i, j
                    v = k
                    s = 0.5 * ((current[a,0]-current[v,0])*(current[b,1]-current[v,1]) - 
                              (current[b,0]-current[v,0])*(current[a,1]-current[v,1]))
                    sign_s = 1.0 if s >= 0 else -1.0
                    ab = current[a] - current[b]
                    ab_norm = np.linalg.norm(ab)
                    if ab_norm > 1e-10:
                        direction = np.array([current[a,1] - current[b,1], 
                                             current[b,0] - current[a,0]])
                        unit_direction = direction / ab_norm
                        displacement_per_vertex[v] += weight * sign_s * unit_direction
                        weight_sum_per_vertex[v] += weight

                # Normalize displacements per vertex using weighted average
                for v in range(n):
                    if weight_sum_per_vertex[v] > 1e-10:
                        displacement_per_vertex[v] /= weight_sum_per_vertex[v]
                        disp_norm = np.linalg.norm(displacement_per_vertex[v])
                        if disp_norm > 1e-10:
                            displacement_per_vertex[v] = step_size * displacement_per_vertex[v] / disp_norm
                        else:
                            displacement_per_vertex[v] = 0
                    else:
                        displacement_per_vertex[v] = 0

                candidate = current + displacement_per_vertex
                # Project moved points to triangle
                for v in range(n):
                    candidate[v] = project_to_triangle(candidate[v], A, B, C)

                # Update affected triangle areas
                candidate_triangle_areas = current_triangle_areas.copy()
                affected_triangles = set()
                for area_val, tri in critical_triangles:
                    for v in tri:
                        affected_triangles.update(point_to_triangles[v])
                
                for tri_idx in affected_triangles:
                    i, j, k = triangle_list[tri_idx]
                    x1, y1 = candidate[i]
                    x2, y2 = candidate[j]
                    x3, y3 = candidate[k]
                    area = 0.5 * abs((x2-x1)*(y3-y1) - (x3-x1)*(y2-y1))
                    candidate_triangle_areas[tri_idx] = area
                
                min_area_candidate = min(candidate_triangle_areas)

            if min_area_candidate < tolerance:
                stagnation_count += 1
                continue

            score = min_area_candidate
            delta = score - current_score
            if delta > 0:
                accept = True
            else:
                if current_temp < 1e-10:
                    accept = False
                else:
                    p_accept = np.exp(delta / current_temp)
                    accept = np.random.rand() < p_accept

            if accept:
                current = candidate
                current_triangle_areas = candidate_triangle_areas
                current_score = score

                if score > best_score:
                    best = candidate.copy()
                    best_score = score
                    best_triangle_areas = candidate_triangle_areas.copy()
                    stagnation_count = 0
                else:
                    stagnation_count += 1
            else:
                stagnation_count += 1

            # Stagnation-based restart
            if stagnation_count > max_stagnation and restart_countdown == 0:
                # Perturb the best solution to escape deep local optima
                current = best.copy()
                gap = 0.0365 - best_score
                noise_std = max(0.001, 0.01 * gap)  # Minimum noise level added
                current += noise_std * np.random.randn(n, 2)
                for v in range(n):
                    current[v] = project_to_triangle(current[v], A, B, C)
                # Recalculate all triangle areas for the perturbed current
                current_triangle_areas = []
                for (i,j,k) in triangle_list:
                    x1, y1 = current[i]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    area = 0.5 * abs((x2-x1)*(y3-y1) - (x3-x1)*(y2-y1))
                    current_triangle_areas.append(area)
                current_triangle_areas = np.array(current_triangle_areas)
                current_score = min(current_triangle_areas)
                restart_countdown = restart_duration
                stagnation_count = 0
                
                # Track restarts for global search trigger
                restart_counter += 1
                
                # After 3 restarts, trigger global restructuring
                if restart_counter >= 3:
                    # Count how many small triangles each point is involved in
                    point_counts = np.zeros(n)
                    for i in range(min(20, len(current_triangle_areas))):  # Look at top 20 smallest triangles
                        tri_idx = np.argsort(current_triangle_areas)[i]
                        i_idx, j_idx, k_idx = triangle_list[tri_idx]
                        point_counts[i_idx] += 1
                        point_counts[j_idx] += 1
                        point_counts[k_idx] += 1
                    
                    # Get top 3 points involved in most small triangles
                    top_points = np.argsort(-point_counts)[:3]
                    
                    # For each top point, perform a grid search in its local region
                    best_grid_candidate = current.copy()
                    best_grid_score = current_score
                    
                    grid_size = 5  # 5x5 grid search
                    search_radius = 0.05 * (1.0 - best_score/0.0365)  # Smaller radius near optimum
                    
                    for point_idx in top_points:
                        x, y = current[point_idx]
                        for dx in np.linspace(-search_radius, search_radius, grid_size):
                            for dy in np.linspace(-search_radius, search_radius, grid_size):
                                candidate = current.copy()
                                candidate[point_idx] = [x + dx, y + dy]
                                candidate[point_idx] = project_to_triangle(candidate[point_idx], A, B, C)
                                
                                # Update triangle areas for candidate
n                                candidate_triangle_areas = current_triangle_areas.copy()
                                affected_triangles = set()
                                affected_triangles.update(point_to_triangles[point_idx])
                                for tri_idx in affected_triangles:
                                    i, j, k = triangle_list[tri_idx]
                                    x1, y1 = candidate[i]
                                    x2, y2 = candidate[j]
                                    x3, y3 = candidate[k]
                                    area = 0.5 * abs((x2-x1)*(y3-y1) - (x3-x1)*(y2-y1))
                                    candidate_triangle_areas[tri_idx] = area
                                
                                min_area_candidate = min(candidate_triangle_areas)
                                if min_area_candidate > best_grid_score:
                                    best_grid_candidate = candidate
                                    best_grid_score = min_area_candidate
                        
                    # If grid search found improvement, use it
                    if best_grid_score > current_score:
                        current = best_grid_candidate
                        current_triangle_areas = []
                        for (i,j,k) in triangle_list:
                            x1, y1 = current[i]
                            x2, y2 = current[j]
                            x3, y3 = current[k]
                            area = 0.5 * abs((x2-x1)*(y3-y1) - (x3-x1)*(y2-y1))
                            current_triangle_areas.append(area)
                        current_triangle_areas = np.array(current_triangle_areas)
                        current_score = best_grid_score
                        
                    # Reset restart counter after global search
                    restart_counter = 0

        return best

    return improve