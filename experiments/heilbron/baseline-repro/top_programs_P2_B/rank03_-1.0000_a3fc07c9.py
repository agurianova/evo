from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    # Precompute triangle edges for boundary handling
    AB = B - A
    BC = C - B
    CA = A - C
    edge_normals = [
        np.array([-AB[1], AB[0]]),
        np.array([-BC[1], BC[0]]),
        np.array([-CA[1], CA[0]])
    ]
    edge_normals = [n / np.linalg.norm(n) for n in edge_normals]
    
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

    def is_on_boundary(p, A, B, C, tol=1e-5):
        """Check if point is on triangle boundary within tolerance"""
        d_ab = np.abs(np.cross(B-A, p-A)) / np.linalg.norm(B-A)
        d_bc = np.abs(np.cross(C-B, p-B)) / np.linalg.norm(C-B)
        d_ca = np.abs(np.cross(A-C, p-C)) / np.linalg.norm(A-C)
        return min(d_ab, d_bc, d_ca) < tol

    def get_boundary_direction(p, A, B, C):
        """Return tangent direction for boundary point"""
        d_ab = np.abs(np.cross(B-A, p-A)) / np.linalg.norm(B-A)
        d_bc = np.abs(np.cross(C-B, p-B)) / np.linalg.norm(C-B)
        d_ca = np.abs(np.cross(A-C, p-C)) / np.linalg.norm(A-C)
        
        if d_ab < d_bc and d_ab < d_ca:
            return (B - A) / np.linalg.norm(B - A)
        elif d_bc < d_ab and d_bc < d_ca:
            return (C - B) / np.linalg.norm(C - B)
        else:
            return (A - C) / np.linalg.norm(A - C)

    def improve(points):
        initial_min_area_val = get_smallest_triangle_area(points)
        
        # Dynamic iteration count based on initial gap
        gap_initial = max(0.0, 0.0365 - initial_min_area_val)
        total_iters = max(1000, int(1000 * (1 + 5 * gap_initial)))
        
        # Improved cooling schedule to prevent premature convergence
        initial_temp = 0.1 * (1.0 + 10 * gap_initial)
        # Ensure minimum exploration even for near-optimal configs
        decay_rate = max(0.2, 2.0 / (1.0 + 5.0 * max(gap_initial, 0.01)))
        restart_duration = max(10, int(0.1 * total_iters))
        max_stagnation = max(50, int(100 * np.sqrt(gap_initial)))

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

        # Adaptive move type probabilities
        move_probs = np.array([0.6, 0.2, 0.2])  # [gradient, swap, perturbation]
        base_probs = move_probs.copy()

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

            # Adaptive move type selection based on stagnation
            if stagnation_count > 10:
                # Increase exploration as stagnation grows
                extra_explore = min(0.4, 0.05 * (stagnation_count // 10))
                move_probs[0] = max(0.2, base_probs[0] - extra_explore)
                move_probs[1] = base_probs[1] + 0.5 * extra_explore
                move_probs[2] = base_probs[2] + 0.5 * extra_explore
            else:
                move_probs = base_probs.copy()

            move_type = np.random.choice(3, p=move_probs)

            if move_type == 0:  # Gradient move (original approach)
                # Adaptive critical triangle selection
                min_area = min(current_triangle_areas)
                threshold = min_area * 1.1  # Within 10% of smallest
                critical_indices = [i for i, area in enumerate(current_triangle_areas) 
                                  if area <= threshold]
                num_critical = max(3, min(6, len(critical_indices)))
                
                # Sort by area and take top num_critical
                idx_sorted = np.argsort(current_triangle_areas)
                critical_triangles = []
                for i in range(num_critical):
                    tri_idx = idx_sorted[i]
                    area_val = current_triangle_areas[tri_idx]
                    critical_triangles.append((area_val, triangle_list[tri_idx]))
                
                # Parameterized weight function
                alpha = 0.5 + 1.5 * gap_initial
                
                # Multi-triangle gradient optimization with area weighting
                displacement_per_vertex = np.zeros_like(current)
                weight_sum_per_vertex = np.zeros(n)
                
                for area_val, tri in critical_triangles:
                    i, j, k = tri
                    # Weight by inverse power of area
                    weight = 1.0 / (area_val ** alpha + 1e-10)
                    
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

            elif move_type == 1:  # Point swap
                # Select two random points to swap
                i, j = np.random.choice(n, 2, replace=False)
                candidate = current.copy()
                candidate[i], candidate[j] = candidate[j].copy(), candidate[i].copy()

            else:  # Random perturbation
                # Add Gaussian noise to all points
                noise = np.random.normal(0, step_size * 0.5, current.shape)
                candidate = current + noise

            # Enhanced boundary handling with direction constraints
            for v in range(n):
                # Check if near boundary
                dist_to_boundary = min(
                    np.abs(np.cross(B-A, candidate[v]-A)) / np.linalg.norm(B-A),
                    np.abs(np.cross(C-B, candidate[v]-B)) / np.linalg.norm(C-B),
                    np.abs(np.cross(A-C, candidate[v]-C)) / np.linalg.norm(A-C)
                )
                
                if dist_to_boundary < 1e-4:  # In boundary zone
                    # Project to ensure validity
                    candidate[v] = project_to_triangle(candidate[v], A, B, C)
                    
                    # Constrain movement direction for boundary points
                    if dist_to_boundary < 1e-5:  # On boundary
                        tangent = get_boundary_direction(candidate[v], A, B, C)
                        # Project displacement onto tangent direction
                        if move_type == 0:  # Only adjust gradient moves
                            disp = candidate[v] - current[v]
                            proj = np.dot(disp, tangent) * tangent
n                            candidate[v] = current[v] + proj
                    else:  # In transition zone (1e-5 to 1e-4)
                        # Smooth transition between full and constrained movement
                        t = (dist_to_boundary - 1e-5) / (1e-4 - 1e-5)
                        tangent = get_boundary_direction(candidate[v], A, B, C)
                        if move_type == 0:
                            disp = candidate[v] - current[v]
                            proj = np.dot(disp, tangent) * tangent
                            candidate[v] = current[v] + t * disp + (1-t) * proj

            # Ensure all points are inside triangle
            for v in range(n):
                candidate[v] = project_to_triangle(candidate[v], A, B, C)

            # Update affected triangle areas
            candidate_triangle_areas = current_triangle_areas.copy()
            affected_triangles = set()
            
            if move_type == 0:  # Gradient move
                for area_val, tri in critical_triangles:
                    for v in tri:
                        affected_triangles.update(point_to_triangles[v])
            else:  # Swap or perturbation affects all triangles with moved points
                affected_points = list(range(n))
                if move_type == 1:  # Swap
                    affected_points = [i, j]
                for v in affected_points:
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

            # Stagnation-based restart with diminishing perturbation
            if stagnation_count > max_stagnation and restart_countdown == 0:
                # Perturb best solution with diminishing magnitude
                perturb_mag = 0.01 * (0.0365 - best_score) * (1.0 - best_score/0.0365)
                perturbation = np.random.normal(0, perturb_mag, best.shape)
                current = np.clip(best + perturbation, 0, 1.5)
                
                # Re-project to ensure validity
                for v in range(n):
                    current[v] = project_to_triangle(current[v], A, B, C)

                # Recompute triangle areas
                for tri_idx in range(len(triangle_list)):
                    i, j, k = triangle_list[tri_idx]
                    x1, y1 = current[i]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    area = 0.5 * abs((x2-x1)*(y3-y1) - (x3-x1)*(y2-y1))
                    current_triangle_areas[tri_idx] = area
                
                current_score = min(current_triangle_areas)
                restart_countdown = restart_duration
                stagnation_count = 0

        return best

    return improve