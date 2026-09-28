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

        # Generate random initial configuration with 6 levels (avoiding collinearity)
        # 4 intermediate height ratios between 0.1 and 0.9, sorted
        t_interm = np.sort(np.random.uniform(0.1, 0.9, 4))
        heights = [0.0] + list(t_interm) + [1.0]  # [0, t0, t1, t2, t3, 1]
        
        # Fixed counts: apex (1 point), 5 intermediate levels (2 points each)
        counts = [1, 2, 2, 2, 2, 2]
        
        points = []
        # Level 0: Apex
        points.append(A)
        
        # Levels 1 to 5
        for i in range(1, 6):
            t = heights[i]
            y = t * H
            width_i = base_width * t
            n = counts[i]
            
            if n == 1:
                x_vals = [0.0]
            elif n == 2:
                # Random offsets to avoid endpoints and ensure distinctness
                offset1 = np.random.uniform(0.1, 0.4)
                offset2 = np.random.uniform(0.6, 0.9)
                x1 = -width_i/2 + width_i * offset1
                x2 = -width_i/2 + width_i * offset2
                x_vals = [x1, x2]
            else:
                x_vals = []
                
            for x in x_vals:
                points.append([x, y])

        points = np.array(points, dtype=np.float64)

        current_min_area = get_smallest_triangle_area(points)
        T = 0.5
        alpha = 0.995
        step_size = 0.05
        min_iter = 100
        max_iter = 5000
        accepted_count = 0

        for iter in range(max_iter):
            # Compute all triangle areas
            min_areas = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        Ax, Ay = points[i]
                        Bx, By = points[j]
                        Cx, Cy = points[k]
                        area = 0.5 * abs((Bx - Ax) * (Cy - Ay) - (Cx - Ax) * (By - Ay))
                        min_areas.append((area, i, j, k))
            
            # Probabilistic selection weighted by 1/area
            areas_list = [x[0] for x in min_areas]
            weights = [1.0 / (a + 1e-10) for a in areas_list]
            total_weight = sum(weights)
            if total_weight > 0:
                p = [w / total_weight for w in weights]
            else:
                p = [1.0 / len(weights)] * len(weights)
            
            tri_idx = np.random.choice(len(min_areas), p=p)
            _, i, j, k = min_areas[tri_idx]
            candidate_points = [i, j, k]
            idx = np.random.choice(candidate_points)

            # Perturb the selected point
            delta = np.random.normal(0, step_size, 2)
            new_point = points[idx] + delta

            # Adaptive boundary handling
            min_bary_current = max(1e-6, 0.01 * (1 - current_min_area / 0.0365))
            
            # Project to triangle using barycentric coordinates
            denom = 2.0
            u_coord = ((B[1]-C[1])*new_point[0] + (C[0]-B[0])*new_point[1] + (B[0]*C[1]-C[0]*B[1])) / denom
            v_coord = ((C[1]-A[1])*new_point[0] + (A[0]-C[0])*new_point[1] + (C[0]*A[1]-A[0]*C[1])) / denom
            w_coord = 1 - u_coord - v_coord

            # Apply adaptive boundary buffer
            if u_coord < min_bary_current: u_coord = min_bary_current
            if v_coord < min_bary_current: v_coord = min_bary_current
            if w_coord < min_bary_current: w_coord = min_bary_current
            total = u_coord + v_coord + w_coord
            u_coord, v_coord, w_coord = u_coord/total, v_coord/total, w_coord/total
            new_point = u_coord * A + v_coord * B + w_coord * C

            new_points = points.copy()
            new_points[idx] = new_point
            new_min_area = get_smallest_triangle_area(new_points)

            # Acceptance probability
            acceptance_prob = np.exp((new_min_area - current_min_area) / T)
            if np.random.rand() < acceptance_prob:
                points = new_points
                current_min_area = new_min_area
                accepted_count += 1

            T *= alpha

            # Adaptive step size adjustment
            if (iter+1) % min_iter == 0:
                acceptance_rate = accepted_count / min_iter
                if acceptance_rate > 0.5:
                    step_size *= 1.2  # More aggressive increase
                elif acceptance_rate < 0.2:
                    step_size *= 0.8  # More aggressive decrease
                accepted_count = 0

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config.astype(np.float32)