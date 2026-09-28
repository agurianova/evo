import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    # Compute denom for barycentric coordinates: signed area expression for whole triangle
    denom_val = (B[1]-C[1])*A[0] + (C[0]-B[0])*A[1] + (B[0]*C[1]-C[0]*B[1])
    
    restarts = 10
    best_config = None
    best_min_area = -1

    for restart in range(restarts):
        np.random.seed(restart * 1000)
        
        # Diversified asymmetric initialization with randomized weights
        points = []
        # 3 vertices
        points.append(A)
        points.append(B)
        points.append(C)
        # 2 base-edge points (on BC) - asymmetric
        base1_v = np.random.uniform(0.7, 0.8)
        base1_w = 1 - base1_v
        points.append(base1_v * B + base1_w * C)
        base2_v = np.random.uniform(0.2, 0.3)
        base2_w = 1 - base2_v
        points.append(base2_v * B + base2_w * C)
        # 2 mid-level points (asymmetric, u=0.5)
        mid1_v = np.random.uniform(0.35, 0.45)
        mid1_w = 0.5 - mid1_v
        points.append(0.5 * A + mid1_v * B + mid1_w * C)
        mid2_v = np.random.uniform(0.1, 0.2)
        mid2_w = 0.5 - mid2_v
        points.append(0.5 * A + mid2_v * B + mid2_w * C)
        # 2 upper points (asymmetric, u=0.8)
        upper1_v = np.random.uniform(0.15, 0.17)
        upper1_w = 0.2 - upper1_v
        points.append(0.8 * A + upper1_v * B + upper1_w * C)
        upper2_v = np.random.uniform(0.03, 0.05)
        upper2_w = 0.2 - upper2_v
        points.append(0.8 * A + upper2_v * B + upper2_w * C)
        # 2 base-proximate points (asymmetric, u=0.2)
        basep1_v = np.random.uniform(0.49, 0.51)
        basep1_w = 0.8 - basep1_v
        points.append(0.2 * A + basep1_v * B + basep1_w * C)
        basep2_v = np.random.uniform(0.27, 0.29)
        basep2_w = 0.8 - basep2_v
        points.append(0.2 * A + basep2_v * B + basep2_w * C)
        points = np.array(points, dtype=np.float64)

        # Add restart-specific noise and project to boundary
        noise = np.random.normal(0, 0.01, (11, 2))
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
            
            # Top-k deterministic selection of smallest triangles
            min_areas_sorted = sorted(min_areas, key=lambda x: x[0])
            top_k = 5
            candidate_points = set()
            for i in range(top_k):
                (area_val, i1, i2, i3) = min_areas_sorted[i]
                candidate_points.add(i1)
                candidate_points.add(i2)
                candidate_points.add(i3)
            candidate_points = list(candidate_points)

            idx = np.random.choice(candidate_points)
            delta = np.random.normal(0, step_size, 2)
            new_point = points[idx] + delta

            # Project with boundary barrier using adaptive min_bary
            adaptive_min_bary = max(1e-6, 0.01 * current_min_area)
            u_coord = ((B[1]-C[1])*new_point[0] + (C[0]-B[0])*new_point[1] + (B[0]*C[1]-C[0]*B[1])) / denom_val
            v_coord = ((C[1]-A[1])*new_point[0] + (A[0]-C[0])*new_point[1] + (C[0]*A[1]-A[0]*C[1])) / denom_val
            w_coord = 1 - u_coord - v_coord

            if u_coord < adaptive_min_bary: u_coord = adaptive_min_bary
            if v_coord < adaptive_min_bary: v_coord = adaptive_min_bary
            if w_coord < adaptive_min_bary: w_coord = adaptive_min_bary
            total = u_coord + v_coord + w_coord
            u_coord, v_coord, w_coord = u_coord/total, v_coord/total, w_coord/total
            new_point = u_coord * A + v_coord * B + w_coord * C

            new_points = points.copy()
            new_points[idx] = new_point
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
                    # T *= 1.05  # Removed destabilizing temperature increase
                elif acceptance_rate < 0.2:
                    step_size *= 0.9
                    T *= 0.95  # Adaptive temperature decrease
                accepted_count = 0

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config.astype(np.float32)