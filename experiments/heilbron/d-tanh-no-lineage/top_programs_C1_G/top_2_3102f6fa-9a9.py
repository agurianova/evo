import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

def entrypoint() -> np.ndarray:
    np.random.seed(42)
    A, B, C = get_unit_triangle()
    n = 11

    def project_to_boundary(P, A, B, C):
        def closest_on_segment(P, A, B):
            AB = B - A
            if np.linalg.norm(AB) < 1e-10:
                return A
            t = np.dot(P - A, AB) / np.dot(AB, AB)
            t = max(0.0, min(1.0, t))
            return A + t * AB
        
        proj_AB = closest_on_segment(P, A, B)
        proj_BC = closest_on_segment(P, B, C)
        proj_CA = closest_on_segment(P, C, A)
        
        d_AB = np.linalg.norm(P - proj_AB)
        d_BC = np.linalg.norm(P - proj_BC)
        d_CA = np.linalg.norm(P - proj_CA)
        
        if d_AB <= d_BC and d_AB <= d_CA:
            return proj_AB
        elif d_BC <= d_AB and d_BC <= d_CA:
            return proj_BC
        else:
            return proj_CA

    best_points = None
    best_min_area = -1
    no_improve_count = 0

    for restart in range(50):
        # Generate initial points with Poisson disk (rejection method)
        points = []
        min_dist = 0.25
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

        # Apply increased jitter
        jitter = 0.05 * (2 * np.random.rand(n, 2) - 1)
        for i in range(n):
            new_point = points[i] + jitter[i]
            if is_inside_triangle(new_point.reshape(1, 2), A, B, C):
                points[i] = new_point

        # Local optimization
        n_points = len(points)
        max_iter = 1000
        current_best_points = points.copy()
        current_best_min_area = get_smallest_triangle_area(points)

        for iter in range(max_iter):
            triangles = []
            for i in range(n_points):
                for j in range(i + 1, n_points):
                    for k in range(j + 1, n_points):
                        Ax, Ay = points[i]
                        Bx, By = points[j]
                        Cx, Cy = points[k]
                        area = 0.5 * abs((Bx - Ax) * (Cy - Ay) - (Cx - Ax) * (By - Ay))
                        triangles.append((area, i, j, k))

            # Random tie-breaking in sort
            triangles.sort(key=lambda x: (x[0], np.random.rand()))

            # Adaptive k selection
            min_area_val = triangles[0][0]
            k = 0
            for i in range(len(triangles)):
                if triangles[i][0] <= min_area_val * 1.1:
                    k = i + 1
                else:
                    break
            k = min(k, 20)
            top_triangles = triangles[:k]

            displacement_vector = [None] * n_points

            for (area, i, j, k_idx) in top_triangles:
                # Displacement for i
                base_jk = points[k_idx] - points[j]
                normal_jk = np.array([-base_jk[1], base_jk[0]])
                norm_jk = np.linalg.norm(normal_jk)
                if norm_jk > 1e-10:
                    normal_jk = normal_jk / norm_jk
                    d_i = np.dot(points[i] - points[j], normal_jk)
                    dir_i = np.sign(d_i) * normal_jk
                else:
                    dir_i = np.zeros(2)

                # Displacement for j
                base_ik = points[k_idx] - points[i]
                normal_ik = np.array([-base_ik[1], base_ik[0]])
                norm_ik = np.linalg.norm(normal_ik)
                if norm_ik > 1e-10:
                    normal_ik = normal_ik / norm_ik
                    d_j = np.dot(points[j] - points[i], normal_ik)
                    dir_j = np.sign(d_j) * normal_ik
                else:
                    dir_j = np.zeros(2)

                # Displacement for k
                base_ij = points[j] - points[i]
                normal_ij = np.array([-base_ij[1], base_ij[0]])
                norm_ij = np.linalg.norm(normal_ij)
                if norm_ij > 1e-10:
                    normal_ij = normal_ij / norm_ij
                    d_k = np.dot(points[k_idx] - points[i], normal_ij)
                    dir_k = np.sign(d_k) * normal_ij
                else:
                    dir_k = np.zeros(2)

                if displacement_vector[i] is None:
                    displacement_vector[i] = dir_i
                if displacement_vector[j] is None:
                    displacement_vector[j] = dir_j
                if displacement_vector[k_idx] is None:
                    displacement_vector[k_idx] = dir_k

            step_size = 0.1 * (0.995 ** iter)
            new_points = points.copy()

            for idx in range(n_points):
                if displacement_vector[idx] is not None:
                    displacement = step_size * displacement_vector[idx]
                    new_point = points[idx] + displacement
                    if is_inside_triangle(new_point.reshape(1, 2), A, B, C):
                        new_points[idx] = new_point
                    else:
                        new_points[idx] = project_to_boundary(new_point, A, B, C)

            points = new_points
            min_area_val = get_smallest_triangle_area(points)
            if min_area_val > current_best_min_area:
                current_best_min_area = min_area_val
                current_best_points = points.copy()

        if current_best_min_area > best_min_area:
            best_min_area = current_best_min_area
            best_points = current_best_points.copy()
            no_improve_count = 0
        else:
            no_improve_count += 1

        if no_improve_count >= 10:
            break

    return best_points