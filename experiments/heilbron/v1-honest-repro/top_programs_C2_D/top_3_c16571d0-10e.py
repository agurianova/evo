from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A_big, B_big, C_big = get_unit_triangle()
    
    # Precompute barycentric constants for the fixed unit triangle
    v0 = B_big - A_big
    v1 = C_big - A_big
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    denom = d00 * d11 - d01 * d01

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        max_iter = 200
        initial_step = 0.05
        initial_temp = 0.01
        cooling_rate = 0.99
        temp = initial_temp
        
        for iter in range(max_iter):
            # Collect top-k smallest triangles (k=3)
            triangles = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        A_pt = current[i]
                        B_pt = current[j]
                        C_pt = current[k]
                        signed_area = (B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (B_pt[1]-A_pt[1])*(C_pt[0]-A_pt[0])
                        abs_area = 0.5 * abs(signed_area)
                        triangles.append((abs_area, i, j, k))
            
            # Sort and get top 3 smallest triangles
            triangles.sort(key=lambda x: x[0])
            top_k = triangles[:3]

            # Use smallest triangle to select point to move
            _, i, j, k = top_k[0]
            idx = np.random.choice([i, j, k])
            
            # Compute direction from all top-k triangles containing idx
            directions = []
            for area, i_tri, j_tri, k_tri in top_k:
                if idx in (i_tri, j_tri, k_tri):
                    # Identify P (the point to move) and Q,R (the other two)
                    if idx == i_tri:
                        P = current[i_tri]
                        Q = current[j_tri]
                        R = current[k_tri]
                    elif idx == j_tri:
                        P = current[j_tri]
                        Q = current[i_tri]
                        R = current[k_tri]
                    else:
                        P = current[k_tri]
                        Q = current[i_tri]
                        R = current[j_tri]
                    
                    s = (Q[0]-P[0])*(R[1]-P[1]) - (Q[1]-P[1])*(R[0]-P[0])
                    dir_vec_tri = np.sign(s) * np.array([Q[1]-R[1], R[0]-Q[0]])
                    norm_dir = np.linalg.norm(dir_vec_tri)
                    if norm_dir > 1e-10:
                        dir_vec_tri = dir_vec_tri / norm_dir
                        directions.append(dir_vec_tri)

            if directions:
                dir_vec = np.mean(directions, axis=0)
                norm_dir = np.linalg.norm(dir_vec)
                if norm_dir > 1e-10:
                    dir_vec = dir_vec / norm_dir
                else:
                    # Fallback to single triangle direction if vectors cancel
                    s = (Q[0]-P[0])*(R[1]-P[1]) - (Q[1]-P[1])*(R[0]-P[0])
                    dir_vec = np.sign(s) * np.array([Q[1]-R[1], R[0]-Q[0]])
                    norm_dir = np.linalg.norm(dir_vec)
                    if norm_dir > 1e-10:
                        dir_vec = dir_vec / norm_dir
                    else:
                        continue
            else:
                continue

            # Adaptive step size
            step_size = initial_step * (cooling_rate ** iter)
            
            candidate = current.copy()
            candidate_point = current[idx] + step_size * dir_vec
            
            # Boundary handling via barycentric projection
            if is_inside_triangle(candidate_point, A_big, B_big, C_big):
                candidate[idx] = candidate_point
                valid = True
            else:
                # Convert to barycentric coordinates
                v2 = candidate_point - A_big
                d20 = np.dot(v2, v0)
                d21 = np.dot(v2, v1)
                v_val = (d11 * d20 - d01 * d21) / denom
                w_val = (d00 * d21 - d01 * d20) / denom
                u_val = 1 - v_val - w_val

                u, v, w = u_val, v_val, w_val
                # Clamp negative coordinates and renormalize
                if u < 0:
                    u = 0
                    total = v + w
                    if total > 0:
                        v /= total
                        w /= total
                    else:
                        v = 0.5
                        w = 0.5
                if v < 0:
                    v = 0
                    total = u + w
                    if total > 0:
                        u /= total
                        w /= total
                    else:
                        u = 0.5
                        w = 0.5
                if w < 0:
                    w = 0
                    total = u + v
                    if total > 0:
                        u /= total
                        v /= total
                    else:
                        u = 0.5
                        v = 0.5

                projected_point = u * A_big + v * B_big + w * C_big
                candidate[idx] = projected_point
                valid = True

            if not valid:
                continue
                
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