import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    restarts = 10
    best_config = None
    best_min_area = -1

    for restart in range(restarts):
        np.random.seed(restart * 1000)
        
        # Compute base width and height from vertices
        base_width = abs(B[0] - C[0])
        H = B[1]  # Base height (y-coordinate of base vertices)

        points = []
        # Level 0: Apex (A)
        points.append(A)

        # Level 1: 3 points at relative height 0.275
        t1 = 0.275
        y1 = t1 * H
        width1 = base_width * t1
        for i in range(3):
            x = -width1/2 + i * (width1 / 2.0)
            points.append([x, y1])

        # Level 2: 2 points at relative height 0.55
        t2 = 0.55
        y2 = t2 * H
        width2 = base_width * t2
        for i in range(2):
            x = -width2/2 + i * width2
            points.append([x, y2])

        # Level 3: 1 point at relative height 0.825
        t3 = 0.825
        y3 = t3 * H
        points.append([0, y3])

        # Level 4: 4 points at base (relative height 1.0)
        t4 = 1.0
        y4 = t4 * H
        width4 = base_width * t4
        for i in range(4):
            x = -width4/2 + i * (width4 / 3.0)
            points.append([x, y4])

        points = np.array(points, dtype=np.float64)

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
            top_k = min_areas[:3]
            candidate_points = set()
            for (area, i, j, k) in top_k:
                candidate_points.add(i)
                candidate_points.add(j)
                candidate_points.add(k)
            candidate_points = list(candidate_points)

            idx = np.random.choice(candidate_points)
            delta = np.random.normal(0, step_size, 2)
            new_point = points[idx] + delta

            # Project with boundary barrier
            denom = 2.0
            u_coord = ((B[1]-C[1])*new_point[0] + (C[0]-B[0])*new_point[1] + (B[0]*C[1]-C[0]*B[1])) / denom
            v_coord = ((C[1]-A[1])*new_point[0] + (A[0]-C[0])*new_point[1] + (C[0]*A[1]-A[0]*C[1])) / denom
            w_coord = 1 - u_coord - v_coord

            if u_coord < min_bary: u_coord = min_bary
            if v_coord < min_bary: v_coord = min_bary
            if w_coord < min_bary: w_coord = min_bary
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
                elif acceptance_rate < 0.2:
                    step_size *= 0.9
                accepted_count = 0

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config.astype(np.float32)