import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    restarts = 10
    best_config = None
    best_min_area = -1

    for restart in range(restarts):
        np.random.seed(restart * 1000)
        
        # Symmetric initialization based on known Heilbronn structure
        points = []
        # 3 vertices
        points.append(A)
        points.append(B)
        points.append(C)
        # 2 base-edge points (on BC)
        points.append(0.75 * B + 0.25 * C)
        points.append(0.25 * B + 0.75 * C)
        # 2 mid-level points (symmetric)
        points.append(0.5 * A + 0.35 * B + 0.15 * C)
        points.append(0.5 * A + 0.15 * B + 0.35 * C)
        # 2 upper points
        points.append(0.8 * A + 0.15 * B + 0.05 * C)
        points.append(0.8 * A + 0.05 * B + 0.15 * C)
        # 2 base-proximate points
        points.append(0.2 * A + 0.5 * B + 0.3 * C)
        points.append(0.2 * A + 0.3 * B + 0.5 * C)
        points = np.array(points, dtype=np.float64)

        current_min_area = get_smallest_triangle_area(points)
        T = 0.5  # Increased from 0.1
        alpha = 0.995  # Slowed from 0.99
        step_size = 0.05
        min_bary = 1e-6  # Relaxed from 0.01
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