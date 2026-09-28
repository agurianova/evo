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

    def generate_random_config(density_factor, jitter_magnitude):
        points = []
        min_dist = density_factor * np.sqrt(1.0 / n)
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

        jitter = jitter_magnitude * (2 * np.random.rand(n, 2) - 1)
        for i in range(n):
            new_point = points[i] + jitter[i]
            if is_inside_triangle(new_point.reshape(1, 2), A, B, C):
                points[i] = new_point
            else:
                points[i] = project_to_boundary(new_point, A, B, C)
        return points

    def local_optimization(points, max_iter, k_max, step_decay):
        n_points = len(points)
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

            triangles.sort(key=lambda x: (x[0], np.random.rand()))

            min_area_val = triangles[0][0]
            k = 0
            for i in range(len(triangles)):
                if triangles[i][0] <= min_area_val * 1.1:
                    k = i + 1
                else:
                    break

            adaptive_k = int(20 * (1 - iter / max_iter))
            adaptive_k = max(5, min(k_max, adaptive_k))
            k = min(k, adaptive_k)
            top_triangles = triangles[:k]

            displacement_vector = [np.zeros(2) for _ in range(n_points)]

            for (area, i, j, k_idx) in top_triangles:
                base_jk = points[k_idx] - points[j]
                normal_jk = np.array([-base_jk[1], base_jk[0]])
                norm_jk = np.linalg.norm(normal_jk)
                if norm_jk > 1e-10:
                    normal_jk = normal_jk / norm_jk
                    d_i = np.dot(points[i] - points[j], normal_jk)
                    dir_i = np.sign(d_i) * normal_jk
                else:
                    dir_i = np.zeros(2)

                base_ik = points[k_idx] - points[i]
                normal_ik = np.array([-base_ik[1], base_ik[0]])
                norm_ik = np.linalg.norm(normal_ik)
                if norm_ik > 1e-10:
                    normal_ik = normal_ik / norm_ik
                    d_j = np.dot(points[j] - points[i], normal_ik)
                    dir_j = np.sign(d_j) * normal_ik
                else:
                    dir_j = np.zeros(2)

                base_ij = points[j] - points[i]
                normal_ij = np.array([-base_ij[1], base_ij[0]])
                norm_ij = np.linalg.norm(normal_ij)
                if norm_ij > 1e-10:
                    normal_ij = normal_ij / norm_ij
                    d_k = np.dot(points[k_idx] - points[i], normal_ij)
                    dir_k = np.sign(d_k) * normal_ij
                else:
                    dir_k = np.zeros(2)

                displacement_vector[i] += dir_i
                displacement_vector[j] += dir_j
                displacement_vector[k_idx] += dir_k

            for idx in range(n_points):
                vec = displacement_vector[idx]
                norm = np.linalg.norm(vec)
                if norm > 1e-10:
                    displacement_vector[idx] = vec / norm
                else:
                    displacement_vector[idx] = np.zeros(2)

            step_size = 0.1 * (step_decay ** iter)
            new_points = points.copy()

            for idx in range(n_points):
                vec = displacement_vector[idx]
                norm = np.linalg.norm(vec)
                if norm > 1e-10:
                    displacement = step_size * vec
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

        return current_best_points, current_best_min_area

    pop_size = 5
    population = []

    for _ in range(pop_size):
        points = generate_random_config(0.9, 0.01)
        points, min_area = local_optimization(points, max_iter=1000, k_max=15, step_decay=0.99)
        population.append((points, min_area))

    population.sort(key=lambda x: x[1], reverse=True)

    for restart in range(50):
        if np.random.rand() < 0.8:
            parent1, parent2 = population[0][0], population[1][0]
            child_points = 0.5 * parent1 + 0.5 * parent2
            for i in range(n):
                if not is_inside_triangle(child_points[i].reshape(1, 2), A, B, C):
                    child_points[i] = project_to_boundary(child_points[i], A, B, C)
        else:
            density_factor = 0.9 * (0.95 ** restart)
            jitter_magnitude = 0.01 * (0.95 ** restart)
            child_points = generate_random_config(density_factor, jitter_magnitude)

        child_points, child_min_area = local_optimization(child_points, max_iter=1000, k_max=15, step_decay=0.99)

        if child_min_area > population[-1][1]:
            population[-1] = (child_points, child_min_area)
            population.sort(key=lambda x: x[1], reverse=True)

    return population[0][0]