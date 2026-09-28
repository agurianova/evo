import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.stats import qmc

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    # Compute denom for barycentric coordinates: signed area expression for whole triangle
    denom_val = (B[1]-C[1])*A[0] + (C[0]-B[0])*A[1] + (B[0]*C[1]-C[0]*B[1])
    
    MIN_BARY = 0.001  # Updated from 0.0 to 0.001 to avoid boundary degeneracies

    restarts = 100  # Increased from 50 to 100

    best_config = None
    best_min_area = -1

    for restart in range(restarts):
        np.random.seed(restart * 1000)
        
        # Generate 11 points via Halton sequence for low-discrepancy uniform sampling in the triangle
        sampler = qmc.Halton(d=2, scramble=False)
        halton_points = sampler.random(n=11)  # (11, 2)
        points = []
        for i in range(11):
            x, y = halton_points[i]
            u_val = 1 - np.sqrt(x)
            v_val = y * np.sqrt(x)
            w_val = 1 - u_val - v_val
            points.append(u_val * A + v_val * B + w_val * C)
        points = np.array(points, dtype=np.float64)

        # Add restart-specific noise (increased magnitude for better exploration)
        noise = np.random.normal(0, 0.05, (11, 2))  # std=0.05 (was 0.01)
        points += noise
        projected_points = []
        for p in points:
            u_coord = ((B[1]-C[1])*p[0] + (C[0]-B[0])*p[1] + (B[0]*C[1]-C[0]*B[1])) / denom_val
            v_coord = ((C[1]-A[1])*p[0] + (A[0]-C[0])*p[1] + (C[0]*A[1]-A[0]*C[1])) / denom_val
            w_coord = 1 - u_coord - v_coord

            # Enforce minimum barycentric coordinates (with buffer)
            if u_coord < MIN_BARY: u_coord = MIN_BARY
            if v_coord < MIN_BARY: v_coord = MIN_BARY
            if w_coord < MIN_BARY: w_coord = MIN_BARY
            total = u_coord + v_coord + w_coord
            u_coord, v_coord, w_coord = u_coord/total, v_coord/total, w_coord/total
            new_p = u_coord * A + v_coord * B + w_coord * C
            projected_points.append(new_p)
        points = np.array(projected_points, dtype=np.float64)

        current_min_area = get_smallest_triangle_area(points)
        T = 0.5
        alpha = 0.99
        step_size = 0.05
        max_iter = 5000
        min_iter = 50  # Reduced from 100 for more frequent adaptation
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
            
            # Increased top_k from 5 to 10 to include more critical triangles
            min_areas_sorted = sorted(min_areas, key=lambda x: x[0])
            top_k = 10
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

            # Project with corrected MIN_BARY
            u_coord = ((B[1]-C[1])*new_point[0] + (C[0]-B[0])*new_point[1] + (B[0]*C[1]-C[0]*B[1])) / denom_val
            v_coord = ((C[1]-A[1])*new_point[0] + (A[0]-C[0])*new_point[1] + (C[0]*A[1]-A[0]*C[1])) / denom_val
            w_coord = 1 - u_coord - v_coord

            if u_coord < MIN_BARY: u_coord = MIN_BARY
            if v_coord < MIN_BARY: v_coord = MIN_BARY
            if w_coord < MIN_BARY: w_coord = MIN_BARY
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
                    step_size *= 1.2  # Increased from 1.05 for more aggressive exploration
                elif acceptance_rate < 0.2:
                    step_size *= 0.8   # Increased from 0.95 for more aggressive reduction
                    # Removed: T *= 0.95 (to prevent premature cooling)
                accepted_count = 0

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config.astype(np.float32)