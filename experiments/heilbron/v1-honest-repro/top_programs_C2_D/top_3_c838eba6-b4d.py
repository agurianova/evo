from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A_big, B_big, C_big = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        max_iter = 250
        initial_step = 0.05
        initial_temp = 0.01
        cooling_rate = 0.99
        temp = initial_temp
        
        # Precompute all triangle areas once per iteration
        def compute_all_triangle_areas(points):
            n = len(points)
            areas = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        A_pt = points[i]
                        B_pt = points[j]
                        C_pt = points[k]
                        signed_area = (B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (B_pt[1]-A_pt[1])*(C_pt[0]-A_pt[0])
                        abs_area = 0.5 * abs(signed_area)
                        areas.append((abs_area, i, j, k))
            areas.sort(key=lambda x: x[0])
            return areas
        
        for iter in range(max_iter):
            # Get k smallest triangles instead of just one
            triangle_areas = compute_all_triangle_areas(current)
            k = min(3, len(triangle_areas))
            candidate_moves = []
            
            # Evaluate all points in the k smallest triangles
            for idx in range(k):
                area_val, i, j, k_idx = triangle_areas[idx]
                triplet = [i, j, k_idx]
                
                for point_idx in triplet:
                    # Points in the triplet excluding current point
                    others = [x for x in triplet if x != point_idx]
                    P = current[point_idx]
                    Q = current[others[0]]
                    R = current[others[1]]
                    
                    # Compute direction vector
                    s = (Q[0]-P[0])*(R[1]-P[1]) - (Q[1]-P[1])*(R[0]-P[0])
                    dir_vec = np.sign(s) * np.array([Q[1]-R[1], R[0]-Q[0]])
                    norm_dir = np.linalg.norm(dir_vec)
                    if norm_dir < 1e-10:
                        continue
                    dir_vec = dir_vec / norm_dir
                    
                    # Temperature-proportional step size
                    step_size = initial_step * (temp / initial_temp)
                    
                    # Check potential improvement
                    candidate = current.copy()
                    candidate_point = P + step_size * dir_vec
                    candidate[point_idx] = candidate_point
                    
                    # Verify point is inside triangle
                    if not is_inside_triangle(candidate_point, A_big, B_big, C_big):
                        # Try boundary projection as fallback
                        v = candidate_point - A_big
                        AB = B_big - A_big
                        AC = C_big - A_big
                        
                        # Project onto triangle using barycentric coordinates
                        denom = AB[0]*AC[1] - AB[1]*AC[0]
                        if abs(denom) > 1e-10:
                            u = (v[0]*AC[1] - v[1]*AC[0]) / denom
                            v_coord = (v[1]*AB[0] - v[0]*AB[1]) / denom
                            w = 1 - u - v_coord
                            
                            # Clamp to valid barycentric coordinates
                            if u < 0: u, v_coord, w = 0, max(0, min(1, v_coord)), 1 - v_coord
                            if v_coord < 0: u, v_coord, w = max(0, min(1, u)), 0, 1 - u
                            if w < 0: u, v_coord, w = u/(u+v_coord), v_coord/(u+v_coord), 0
                            
                            candidate_point = u * B_big + v_coord * C_big + w * A_big
                            candidate[point_idx] = candidate_point
                        else:
                            continue

                    # Evaluate impact on next few smallest triangles
                    new_score = get_smallest_triangle_area(candidate)
                    potential_improvement = new_score - current_score
                    
                    candidate_moves.append((potential_improvement, candidate, point_idx, dir_vec, step_size))

            # Sort by potential improvement
            candidate_moves.sort(key=lambda x: x[0], reverse=True)
            
            if not candidate_moves:
                # Try boundary retries with halving
                valid = False
                step_size = initial_step * (temp / initial_temp)
                for _ in range(10):  # Increased from 5 to 10 retries
                    candidate = current.copy()
                    idx = np.random.randint(0, 11)
                    dir_vec = np.random.uniform(-1, 1, size=2)
                    dir_vec = dir_vec / np.linalg.norm(dir_vec)
                    candidate_point = current[idx] + step_size * dir_vec
                    
                    if is_inside_triangle(candidate_point, A_big, B_big, C_big):
                        candidate[idx] = candidate_point
                        new_score = get_smallest_triangle_area(candidate)
                        delta = new_score - current_score
                        
                        if delta > 0 or np.random.rand() < np.exp(delta / temp):
                            current = candidate
                            current_score = new_score
                            if new_score > best_score:
                                best = candidate
                                best_score = new_score
                            valid = True
                            break
                    
                    step_size *= 0.5
                
                if not valid:
                    temp *= cooling_rate
                    continue

            # Take the best candidate move
            _, candidate, _, _, _ = candidate_moves[0]
            new_score = get_smallest_triangle_area(candidate)
            delta = new_score - current_score
            
            # Simulated annealing acceptance
            if delta > 0 or np.random.rand() < np.exp(delta / temp):
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
            
            # Cool down
            temp *= cooling_rate

        return best

    return improve