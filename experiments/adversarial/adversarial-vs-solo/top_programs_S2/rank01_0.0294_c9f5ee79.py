import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    # Compute geometric constants for accuracy
    denom_val = (B[0]-A[0])*(C[1]-A[1]) - (B[1]-A[1])*(C[0]-A[0])
    base_length = np.linalg.norm(B - C)
    
    restarts = 10
    best_config = None
    best_min_area = -1

    for restart in range(restarts):
        np.random.seed(restart * 1000)
        
        # Asymmetric initialization using random barycentric coordinates
        points = []
        # 3 vertices
        points.append(A)
        points.append(B)
        points.append(C)
        # 8 interior points via Dirichlet distribution (uniform over simplex)
        weights = np.random.dirichlet(np.ones(3), size=8)
        for w in weights:
            p = w[0] * A + w[1] * B + w[2] * C
            points.append(p)
        points = np.array(points, dtype=np.float64)

        # Add restart-specific noise scaled by triangle dimensions
        noise = np.random.normal(0, 0.01 * base_length, (11, 2))
        points += noise
        min_bary = 1e-6
        projected_points = []
        for p in points:
            u_coord = ((B[1]-C[1])*p[0] + (C[0]-B[0])*p[1] + (B[0]*C[1]-C[0]*B[1])) / denom_val
            v_coord = ((C[1]-A[1])*p[0] + (A[0]-C[0])*p[1] + (C[0]*A[1]-A[0]*C[1])) / denom_val
            w_coord = 1 - u_coord - v_coord

            if u_coord < min_bary: u_coord = min_bary
            if v_coord < min_bary: v_coord = min_bary
            if w_coord < min_bary: w_coord = min_bary
            total = u_coord + v_coord + w_coord
            u_coord, v_coord, w_coord = u_coord/total, v_coord/total, w_coord/total
            new_p = u_coord * A + v_coord * B + w_coord * C
            projected_points.append(new_p)
        points = np.array(projected_points, dtype=np.float64)

        current_min_area = get_smallest_triangle_area(points)
        T = 0.5
        alpha = 0.995
        step_size = 0.05
        min_bary = 1e-6
        max_iter = 5000
        min_iter = 100
        accepted_count = 0

        for iter in range(max_iter):
            min_areas = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        Ax, Ay = points[i]
                        Bx, By = points[j]
                        Cx, Cy = points[k]
                        area = 0.5 * abs((Bx - Ax) * (Cy - Ay) - (Cx - Ax) * (By - Ay))
                        min_areas.append((area, i, j, k))
            min_areas.sort(key=lambda x: x[0])
            top_k = 5  # Increased from 3 to avoid premature convergence
            top_triangles = min_areas[:top_k]
            
            candidate_points = set()
            for (area, i, j, k) in top_triangles:
                candidate_points.add(i)
                candidate_points.add(j)
                candidate_points.add(k)
            candidate_points = list(candidate_points)

            # 80% chance: single-point move, 20% chance: dual-point move
            if np.random.rand() < 0.2:
                # Dual-point move: select smallest triangle and two random points
                _, i0, j0, k0 = top_triangles[0]
                two_points = np.random.choice([i0, j0, k0], size=2, replace=False)
                idx1, idx2 = two_points

                # Generate and project first point
                delta1 = np.random.normal(0, step_size, 2)
                new_point1 = points[idx1] + delta1
                u1 = ((B[1]-C[1])*new_point1[0] + (C[0]-B[0])*new_point1[1] + (B[0]*C[1]-C[0]*B[1])) / denom_val
                v1 = ((C[1]-A[1])*new_point1[0] + (A[0]-C[0])*new_point1[1] + (C[0]*A[1]-A[0]*C[1])) / denom_val
                w1 = 1 - u1 - v1
                if u1 < min_bary: u1 = min_bary
                if v1 < min_bary: v1 = min_bary
                if w1 < min_bary: w1 = min_bary
                total1 = u1 + v1 + w1
                u1, v1, w1 = u1/total1, v1/total1, w1/total1
                new_point1_proj = u1 * A + v1 * B + w1 * C

                # Generate and project second point
                delta2 = np.random.normal(0, step_size, 2)
                new_point2 = points[idx2] + delta2
                u2 = ((B[1]-C[1])*new_point2[0] + (C[0]-B[0])*new_point2[1] + (B[0]*C[1]-C[0]*B[1])) / denom_val
                v2 = ((C[1]-A[1])*new_point2[0] + (A[0]-C[0])*new_point2[1] + (C[0]*A[1]-A[0]*C[1])) / denom_val
                w2 = 1 - u2 - v2
                if u2 < min_bary: u2 = min_bary
                if v2 < min_bary: v2 = min_bary
                if w2 < min_bary: w2 = min_bary
                total2 = u2 + v2 + w2
                u2, v2, w2 = u2/total2, v2/total2, w2/total2
                new_point2_proj = u2 * A + v2 * B + w2 * C

                new_points = points.copy()
                new_points[idx1] = new_point1_proj
                new_points[idx2] = new_point2_proj
                new_min_area = get_smallest_triangle_area(new_points)
            else:
                # Single-point move (original approach)
                idx = np.random.choice(candidate_points)
                delta = np.random.normal(0, step_size, 2)
                new_point = points[idx] + delta

                # Project new point
                u_coord = ((B[1]-C[1])*new_point[0] + (C[0]-B[0])*new_point[1] + (B[0]*C[1]-C[0]*B[1])) / denom_val
                v_coord = ((C[1]-A[1])*new_point[0] + (A[0]-C[0])*new_point[1] + (C[0]*A[1]-A[0]*C[1])) / denom_val
                w_coord = 1 - u_coord - v_coord

                if u_coord < min_bary: u_coord = min_bary
                if v_coord < min_bary: v_coord = min_bary
                if w_coord < min_bary: w_coord = min_bary
                total = u_coord + v_coord + w_coord
                u_coord, v_coord, w_coord = u_coord/total, v_coord/total, w_coord/total
                new_point_proj = u_coord * A + v_coord * B + w_coord * C

                new_points = points.copy()
                new_points[idx] = new_point_proj
                new_min_area = get_smallest_triangle_area(new_points)

            acceptance_prob = np.exp((new_min_area - current_min_area) / T)
            if np.random.rand() < acceptance_prob:
                points = new_points
                current_min_area = new_min_area
                accepted_count += 1

            T *= alpha

            if (iter+1) % min_iter == 0:
                acceptance_rate = accepted_count / min_iter
                if acceptance_rate > 0.5:
                    step_size *= 1.1
                elif acceptance_rate < 0.2:
                    step_size *= 0.9
                accepted_count = 0

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config.astype(np.float32)