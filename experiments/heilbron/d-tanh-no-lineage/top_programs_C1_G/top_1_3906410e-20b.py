import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    n = 11

    # Helper: project point to nearest location on triangle boundary
    def point_to_line_segment(p, a, b):
        ab = b - a
        ap = p - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
        t = np.clip(t, 0.0, 1.0)
        return a + t * ab

    def project_to_triangle(point, A, B, C):
        p1 = point_to_line_segment(point, A, B)
        p2 = point_to_line_segment(point, B, C)
        p3 = point_to_line_segment(point, C, A)
        d1 = np.linalg.norm(point - p1)
        d2 = np.linalg.norm(point - p2)
        d3 = np.linalg.norm(point - p3)
        if d1 <= d2 and d1 <= d3:
            return p1
        elif d2 <= d1 and d2 <= d3:
            return p2
        else:
            return p3

    best_points = None
    best_min_area = -1
    no_improve_count = 0

    for restart in range(50):
        # Generate initial points with adaptive min_dist
        points = []
        min_dist_base = 0.8 * np.sqrt(1.0 / n)
        min_dist = min_dist_base
        max_attempts = 10000
        attempts = 0
        
        while len(points) < n and min_dist > 0.01:
            points = []
            attempts = 0
            while len(points) < n and attempts < max_attempts:
                u = np.random.rand()
                v = np.random.rand()
                if u + v > 1:
                    u = 1 - u
                    v = 1 - v
                P = A + u * (B - A) + v * (C - A)
                if not is_inside_triangle(P.reshape(1, 2), A, B, C):
                    attempts += 1
                    continue
                too_close = False
                for p in points:
                    if np.linalg.norm(P - p) < min_dist:
                        too_close = True
                        break
                if not too_close:
                    points.append(P)
                attempts += 1
            
            if len(points) < n:
                min_dist *= 0.95

        points = np.array(points)

        # Apply decayed jitter with slower decay
        jitter_magnitude = 0.05 * (0.99 ** restart)
        jitter = jitter_magnitude * (2 * np.random.rand(n, 2) - 1)
        for i in range(n):
            new_point = points[i] + jitter[i]
            if is_inside_triangle(new_point.reshape(1, 2), A, B, C):
                points[i] = new_point

        # Local optimization
        n_points = len(points)
        max_iter = 1000
        current_best_points = points.copy()
        current_best_min_area = get_smallest_triangle_area(points)
        current_min_area_val = current_best_min_area

        # Simulated annealing setup
        T = 0.1  # Initial temperature
        base_step = 0.1

        for iter in range(max_iter):
            # Compute top-k smallest triangles (k=5) for stable gradient
            top_k = 5
            triangles = []  # (area, i, j, k)
            for i in range(n_points):
                for j in range(i+1, n_points):
                    for k in range(j+1, n_points):
                        a, b, c = points[i], points[j], points[k]
                        area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                        triangles.append((area_val, i, j, k))
            triangles.sort(key=lambda x: x[0])
            top_triangles = triangles[:top_k]

            # Initialize gradient as zeros
            gradient = np.zeros((n_points, 2))
            for (area_val, i, j, k) in top_triangles:
                A_tri, B_tri, C_tri = points[i], points[j], points[k]
                S = (B_tri[0]-A_tri[0])*(C_tri[1]-A_tri[1]) - (C_tri[0]-A_tri[0])*(B_tri[1]-A_tri[1])
                sign_S = 1.0 if S >= 0 else -1.0
                grad_i = np.array([0.5 * sign_S * (B_tri[1] - C_tri[1]), 
                                  0.5 * sign_S * (C_tri[0] - B_tri[0])])
                grad_j = np.array([0.5 * sign_S * (C_tri[1] - A_tri[1]), 
                                  0.5 * sign_S * (A_tri[0] - C_tri[0])])
                grad_k = np.array([0.5 * sign_S * (A_tri[1] - B_tri[1]), 
                                  0.5 * sign_S * (B_tri[0] - A_tri[0])])
                gradient[i] += grad_i
                gradient[j] += grad_j
                gradient[k] += grad_k

            # Determine step size with slow decay
            step_size = base_step * (0.99 ** iter)

            # Update points
            new_points = points + step_size * gradient

            # Boundary handling: project out-of-bounds points to boundary
            for i in range(n_points):
                if not is_inside_triangle(new_points[i].reshape(1, 2), A, B, C):
                    new_points[i] = project_to_triangle(new_points[i], A, B, C)

            # Evaluate new configuration
            new_min_area = get_smallest_triangle_area(new_points)

            # Simulated annealing acceptance
            if new_min_area >= current_min_area_val:
                # Always accept improvements
                points = new_points
                current_min_area_val = new_min_area
            else:
                # Accept worsening moves probabilistically
                delta = new_min_area - current_min_area_val
                if np.random.rand() < np.exp(delta / T):
                    points = new_points
                    current_min_area_val = new_min_area
                # Else reject: points remain unchanged

            # Update best solution
            if current_min_area_val > current_best_min_area:
                current_best_min_area = current_min_area_val
                current_best_points = points.copy()

            # Update temperature with slower decay
            T *= 0.999

        if current_best_min_area > best_min_area:
            best_min_area = current_best_min_area
            best_points = current_best_points.copy()
            no_improve_count = 0
        else:
            no_improve_count += 1

        if no_improve_count >= 45:
            break

    return best_points