import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    restarts = 10
    best_config = None
    best_min_area = -1

    for restart in range(restarts):
        np.random.seed(restart * 1000)
        
        # Symmetric initialization based on known high-fitness pattern
        if np.allclose(A, [0, 0], atol=1e-5):
            apex = A
            base1, base2 = B, C
        elif np.allclose(B, [0, 0], atol=1e-5):
            apex = B
            base1, base2 = A, C
        else:
            apex = C
            base1, base2 = A, B

        f_levels = [0, 0.275, 0.55, 0.825, 1.0]
        num_points = [1, 3, 2, 1, 4]
        points = []

        for i in range(len(f_levels)):
            f = f_levels[i]
            k = num_points[i]
            if k == 1:
                t_vals = [0.5]
            elif k == 2:
                t_vals = [0.3, 0.7]
            elif k == 3:
                t_vals = [0.25, 0.5, 0.75]
            elif k == 4:
                t_vals = [0.0, 1/3, 2/3, 1.0]
            else:
                t_vals = np.linspace(0, 1, k)

            for t in t_vals:
                P = (1 - f) * apex + f * ((1 - t) * base1 + t * base2)
                points.append(P)

        points = np.array(points, dtype=np.float64)

        current_min_area = get_smallest_triangle_area(points)
        T = 0.5
        alpha = 0.995
        step_size = 0.05
        min_bary = 1e-6
        max_iter = 5000
        min_iter = 100
        accepted_count = 0
        best_min_in_run = current_min_area
        stagnation_counter = 0

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

            # Update stagnation counter and reset step_size if stuck
            if current_min_area > best_min_in_run:
                best_min_in_run = current_min_area
                stagnation_counter = 0
            else:
                stagnation_counter += 1

            if stagnation_counter >= 500:
                step_size = 0.1
                stagnation_counter = 0

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config.astype(np.float32)