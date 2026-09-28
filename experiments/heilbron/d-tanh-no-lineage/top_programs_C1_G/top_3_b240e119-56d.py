import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    n = 11

    best_points = None
    best_min_area = -1
    no_improve_count = 0

    for restart in range(50):
        # Generate initial points with Poisson disk (rejection method)
        points = []
        min_dist = 0.20
        max_attempts = 10000
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
            while len(points) < n:
                u = np.random.rand()
                v = np.random.rand()
                if u + v > 1:
                    u = 1 - u
                    v = 1 - v
                P = A + u * (B - A) + v * (C - A)
                if is_inside_triangle(P.reshape(1, 2), A, B, C):
                    points.append(P)
        points = np.array(points)

        # Apply decayed jitter
        jitter_magnitude = 0.05 * (0.95 ** restart)
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
            # Compute top-3 smallest triangles for stable gradient calculation
            top_k = 3
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

            # Boundary handling: reject out-of-bounds moves
            for i in range(n_points):
                if not is_inside_triangle(new_points[i].reshape(1, 2), A, B, C):
                    new_points[i] = points[i]

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