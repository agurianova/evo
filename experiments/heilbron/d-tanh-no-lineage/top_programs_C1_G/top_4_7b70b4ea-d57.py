import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

np.random.seed(42)

def entrypoint() -> np.ndarray:
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

    # Population parameters
    pop_size = 5
    population = []  # List of (min_area, points)

    # Configuration parameters
    density_factor = 0.95  # Increased from 0.9
    k_max = 15            # Increased from 10
    initial_jitter = 0.1  # Increased from 0.05
    jitter_decay = 0.99

    no_improve_count = 0
    global_best = -1

    for restart in range(50):
        # Generate initial points (with population crossover 50% of restarts after first)
        if restart > 0 and np.random.rand() < 0.5 and len(population) >= 2:
            # Crossover: select two parents
            idx1, idx2 = np.random.choice(len(population), 2, replace=False)
            parent1 = population[idx1][1]
            parent2 = population[idx2][1]
            # Arithmetic crossover
            points = 0.5 * parent1 + 0.5 * parent2
            # Project any outside points back to boundary
            for i in range(n):
                if not is_inside_triangle(points[i].reshape(1, 2), A, B, C):
                    points[i] = project_to_boundary(points[i], A, B, C)
        else:
            # Poisson disk with adaptive density
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

        # Apply adaptive jitter
        current_jitter = initial_jitter * (jitter_decay ** restart)
        jitter = current_jitter * (2 * np.random.rand(n, 2) - 1)
        for i in range(n):
            new_point = points[i] + jitter[i]
            if is_inside_triangle(new_point.reshape(1, 2), A, B, C):
                points[i] = new_point
            else:
                points[i] = project_to_boundary(new_point, A, B, C)

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

            # Calculate weights based on proximity to minimum area
            min_area_val = min(tri[0] for tri in triangles)
            eps = 1e-10
            weights = [1.0 / (tri[0] - min_area_val + eps) for tri in triangles]
            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]

            # Initialize displacement vectors to zero
            displacement_vector = [np.zeros(2) for _ in range(n_points)]

            # Use weighted displacement for all triangles
            for idx, (area, i, j, k_idx) in enumerate(triangles):
                weight = weights[idx]
                
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

                # Accumulate displacement vectors with weight
                displacement_vector[i] += weight * dir_i
                displacement_vector[j] += weight * dir_j
                displacement_vector[k_idx] += weight * dir_k

            # Normalize displacement vectors
            for idx in range(n_points):
                vec = displacement_vector[idx]
                norm = np.linalg.norm(vec)
                if norm > 1e-10:
                    displacement_vector[idx] = vec / norm
                else:
                    displacement_vector[idx] = np.zeros(2)

            step_size = 0.1 * (0.995 ** iter)  # Slower decay (0.995 instead of 0.99)
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

        # Update population
        if len(population) < pop_size:
            population.append((current_best_min_area, current_best_points.copy()))
        else:
            # Replace worst if better
            min_idx = np.argmin([p[0] for p in population])
            if current_best_min_area > population[min_idx][0]:
                population[min_idx] = (current_best_min_area, current_best_points.copy())

        # Track global best
        global_best = max([p[0] for p in population]) if population else -1
        if current_best_min_area > global_best:
            no_improve_count = 0
        else:
            no_improve_count += 1

        if no_improve_count >= 20:
            break

    # Return best configuration in population
    population.sort(key=lambda x: x[0], reverse=True)
    return population[0][1]