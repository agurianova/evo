from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Precompute edge lengths and normals for boundary calculations
    len_AB = np.linalg.norm(B - A)
    len_BC = np.linalg.norm(C - B)
    len_CA = np.linalg.norm(A - C)

    def project_to_triangle(p):
        """Project point to triangle boundary with collinearity avoidance"""
        proj_ab = project_point_to_segment(p, A, B)
        proj_bc = project_point_to_segment(p, B, C)
        proj_ca = project_point_to_segment(p, C, A)
        d_ab = np.linalg.norm(p - proj_ab)
        d_bc = np.linalg.norm(p - proj_bc)
        d_ca = np.linalg.norm(p - proj_ca)
        
        if d_ab <= d_bc and d_ab <= d_ca:
            proj = proj_ab
            edge = 'AB'
        elif d_bc <= d_ab and d_bc <= d_ca:
            proj = proj_bc
            edge = 'BC'
        else:
            proj = proj_ca
            edge = 'CA'

        # Nudge boundary points inward to avoid collinearity (except vertices)
        if edge == 'AB':
            t = np.dot(proj - A, B - A) / len_AB**2
            if 0 < t < 1:
                normal = np.array([-(B[1]-A[1]), B[0]-A[0]])
                if np.dot(normal, C - (A+B)/2) < 0:
                    normal = -normal
                normal = normal / (np.linalg.norm(normal) + 1e-10)
                proj = proj + 1e-5 * normal
        elif edge == 'BC':
            t = np.dot(proj - B, C - B) / len_BC**2
            if 0 < t < 1:
                normal = np.array([-(C[1]-B[1]), C[0]-B[0]])
                if np.dot(normal, A - (B+C)/2) < 0:
                    normal = -normal
                normal = normal / (np.linalg.norm(normal) + 1e-10)
                proj = proj + 1e-5 * normal
        else:  # CA
            t = np.dot(proj - C, A - C) / len_CA**2
            if 0 < t < 1:
                normal = np.array([-(A[1]-C[1]), A[0]-C[0]])
                if np.dot(normal, B - (C+A)/2) < 0:
                    normal = -normal
                normal = normal / (np.linalg.norm(normal) + 1e-10)
                proj = proj + 1e-5 * normal

        return proj

    def project_point_to_segment(p, a, b):
        ab = b - a
        ap = p - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
        t = max(0, min(1, t))
        return a + t * ab

    def get_top_k_triangles(points, k=5):
        """Get top k smallest triangles by area"""
        n = points.shape[0]
        triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k_idx in range(j+1, n):
                    area = 0.5 * abs(
                        (points[j,0] - points[i,0]) * (points[k_idx,1] - points[i,1]) -
                        (points[j,1] - points[i,1]) * (points[k_idx,0] - points[i,0])
                    )
                    triangles.append((area, i, j, k_idx))
        triangles.sort(key=lambda x: x[0])
        return triangles[:k]

    def anneal(config, steps, initial_temp, cooling_rate, no_improve_threshold):
        current = config.copy()
        current_score = get_smallest_triangle_area(current)
        best_in_anneal = current.copy()
        best_score_in_anneal = current_score
        temperature = initial_temp
        no_improve_count = 0

        for step in range(steps):
            if no_improve_count >= no_improve_threshold:
                break

            # Get top 5 smallest triangles for multi-objective direction
            top_triangles = get_top_k_triangles(current, k=5)
            
            # Coordinated move: 50% chance to perturb all three points of a top triangle
            if np.random.rand() < 0.5 and top_triangles:
                # Select random top triangle
                tri = top_triangles[np.random.randint(0, len(top_triangles))]
                _, i, j, k = tri
                triangle_points = [i, j, k]
                
                # Compute directions for each point in the triangle
n                directions = []
                for idx, base_points in zip([i, j, k], [(j,k), (i,k), (i,j)]):
                    j_idx, k_idx = base_points
                    base_vec = current[k_idx] - current[j_idx]
                    base_length = np.linalg.norm(base_vec)
                    if base_length < 1e-10:
                        directions.append(np.random.normal(0, 1, 2))
                        continue
                    
                    normal = np.array([-base_vec[1], base_vec[0]])
                    normal = normal / base_length
                    vec_ij = current[idx] - current[j_idx]
                    cross_val = base_vec[0] * vec_ij[1] - base_vec[1] * vec_ij[0]
                    direction = normal * np.sign(cross_val) if cross_val != 0 else normal
                    directions.append(direction)

                # Generate candidate by moving all three points
                candidate = current.copy()
                for idx, direction in zip(triangle_points, directions):
                    p = current[idx]
                    # Boundary distance calculation
                    cross_AB = abs((B[0]-A[0])*(p[1]-A[1]) - (B[1]-A[1])*(p[0]-A[0]))
                    dist_AB = cross_AB / len_AB
                    cross_BC = abs((C[0]-B[0])*(p[1]-B[1]) - (C[1]-B[1])*(p[0]-B[0]))
                    dist_BC = cross_BC / len_BC
                    cross_CA = abs((A[0]-C[0])*(p[1]-C[1]) - (A[1]-C[1])*(p[0]-C[0]))
                    dist_CA = cross_CA / len_CA
                    min_distance = min(dist_AB, dist_BC, dist_CA)

                    step_size = temperature * min(1.0, min_distance * 50.0) * 0.3  # Reduced for stability
                    if step_size < 1e-5:
                        step_size = 1e-5

                    perturbation = step_size * direction
                    candidate[idx] += perturbation

            else:
                # Single-point move using multi-triangle directions
                if not top_triangles:
                    idx = np.random.randint(0, 11)
                    direction = np.random.normal(0, 1, 2)
                    direction = direction / (np.linalg.norm(direction) + 1e-10)
                else:
                    # Collect points in top triangles
                    candidate_points = set()
                    for tri in top_triangles:
                        _, i, j, k = tri
                        candidate_points.add(i)
                        candidate_points.add(j)
                        candidate_points.add(k)
                    idx = np.random.choice(list(candidate_points))

                    # Compute average direction across all top triangles containing idx
                    directions = []
                    for tri in top_triangles:
                        area, i, j, k = tri
                        if idx not in (i, j, k):
                            continue
                        
                        if idx == i:
                            base_points = (j, k)
                        elif idx == j:
                            base_points = (i, k)
                        else:
                            base_points = (i, j)
                        j_idx, k_idx = base_points

                        base_vec = current[k_idx] - current[j_idx]
                        base_length = np.linalg.norm(base_vec)
                        if base_length < 1e-10:
                            directions.append(np.random.normal(0, 1, 2))
                            continue

                        normal = np.array([-base_vec[1], base_vec[0]])
                        normal = normal / base_length
                        vec_ij = current[idx] - current[j_idx]
                        cross_val = base_vec[0] * vec_ij[1] - base_vec[1] * vec_ij[0]
                        direction = normal * np.sign(cross_val) if cross_val != 0 else normal
                        directions.append(direction)

                    if directions:
                        avg_dir = np.mean(directions, axis=0)
                        direction = avg_dir / (np.linalg.norm(avg_dir) + 1e-10)
                    else:
                        direction = np.random.normal(0, 1, 2)
                        direction = direction / (np.linalg.norm(direction) + 1e-10)

                # Generate candidate by moving single point
                candidate = current.copy()
                p = current[idx]
                cross_AB = abs((B[0]-A[0])*(p[1]-A[1]) - (B[1]-A[1])*(p[0]-A[0]))
                dist_AB = cross_AB / len_AB
                cross_BC = abs((C[0]-B[0])*(p[1]-B[1]) - (C[1]-B[1])*(p[0]-B[0]))
                dist_BC = cross_BC / len_BC
                cross_CA = abs((A[0]-C[0])*(p[1]-C[1]) - (A[1]-C[1])*(p[0]-C[0]))
                dist_CA = cross_CA / len_CA
                min_distance = min(dist_AB, dist_BC, dist_CA)

                step_size = temperature * min(1.0, min_distance * 50.0)
                if step_size < 1e-5:
                    step_size = 1e-5

                perturbation = step_size * direction
                candidate[idx] += perturbation

            # Enforce triangle containment
            valid = True
            for i in range(11):
                if not is_inside_triangle(candidate[i:i+1], A, B, C):
                    candidate[i] = project_to_triangle(candidate[i])
                    # Re-check after projection
                    if not is_inside_triangle(candidate[i:i+1], A, B, C):
                        valid = False
                        break

            if not valid:
                no_improve_count += 1
                temperature *= cooling_rate
                continue

            score = get_smallest_triangle_area(candidate)

            if score > current_score:
                accept = True
            else:
                delta = score - current_score
                probability = np.exp(delta / temperature) if temperature > 1e-5 else 0.0
                accept = np.random.rand() < probability

            if accept:
                current = candidate
                current_score = score
                if score > best_score_in_anneal:
                    best_score_in_anneal = score
                    best_in_anneal = candidate.copy()
                    no_improve_count = 0
                else:
                    no_improve_count += 1
            else:
                no_improve_count += 1

            temperature *= cooling_rate

        return best_in_anneal, best_score_in_anneal

    def improve(points):
        base_min_area = get_smallest_triangle_area(points)
        # Dynamically set restart count based on difficulty
        num_restarts = max(5, min(15, 5 + 5 * (base_min_area / 0.0365)))
        
        restart_candidates = []

        for restart in range(int(num_restarts)):
            if restart == 0:
                initial = points.copy()
            else:
                best_so_far = restart_candidates[0][1] if restart_candidates else points.copy()
                current = best_so_far.copy()
                
                # Compute current gap for adaptive perturbation
                current_min_area = get_smallest_triangle_area(current)
                gap = 0.0365 - current_min_area
                restart_perturbation_std = 0.01 * (gap / 0.0365)
                
                perturbation = np.random.normal(0, restart_perturbation_std, size=(11, 2))
                current += perturbation
                
                # Project out-of-bound points
                for i in range(11):
                    if not is_inside_triangle(current[i:i+1], A, B, C):
                        current[i] = project_to_triangle(current[i])
                initial = current

            # Compute gap for adaptive annealing
            current_min_area = get_smallest_triangle_area(initial)
            gap = 0.0365 - current_min_area
            initial_temp = 0.01 * (gap / 0.0365)

            best_in_restart, best_score_in_restart = anneal(
                initial, 
                steps=500,
                initial_temp=initial_temp,
                cooling_rate=0.995,
                no_improve_threshold=50
            )
            restart_candidates.append((best_score_in_restart, best_in_restart))
            restart_candidates.sort(key=lambda x: x[0], reverse=True)

            # Crossover diversification with biased weighting
            if restart in [2, 5, 8] and len(restart_candidates) >= 2:
                cand1 = restart_candidates[0][1]
                cand2 = restart_candidates[1][1]
                score1 = restart_candidates[0][0]
                score2 = restart_candidates[1][0]
                
                # Bias weight toward better parent
                total = score1 + score2
                if total > 0:
                    weight = 0.5 + 0.4 * (score1 - score2) / total
                else:
                    weight = 0.5
                weight = max(0.3, min(0.7, weight))
                
                child = weight * cand1 + (1 - weight) * cand2
                
                # Project child configuration to triangle
                for i in range(11):
                    if not is_inside_triangle(child[i:i+1], A, B, C):
                        child[i] = project_to_triangle(child[i])
                
                # Refine crossover child
                child_refined, child_score = anneal(
                    child,
                    steps=100,
                    initial_temp=initial_temp * 0.5,
                    cooling_rate=0.995,
                    no_improve_threshold=20
                )
                restart_candidates.append((child_score, child_refined))
                restart_candidates.sort(key=lambda x: x[0], reverse=True)

        return restart_candidates[0][1]

    return improve