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

    population = []  # List of (points, min_area)

    for restart in range(50):
        # Determine generation method: dynamic crossover probability
        if len(population) < 5:
            crossover_prob = 0.0
        else:
            # Calculate population diversity (simplified as variance in min areas)
            min_areas = [p[1] for p in population]
            diversity = np.std(min_areas) / (0.0365 + 1e-10)  # Normalize by target
            # REVERTED: crossover_prob = 0.3 * diversity -> 0.3 * (1 - diversity)
            crossover_prob = 0.3 * (1.0 - min(diversity, 1.0))

        if len(population) < 5 or np.random.rand() > crossover_prob:
            # Generate new configuration with symmetry option
            use_symmetry = np.random.rand() < 0.18  # Reduced from 30% to 18% for better quality exploration
            
            if use_symmetry:
                # Create symmetric configuration with 3-fold symmetry
                center = (A + B + C) / 3
                points = [center]
                
                # Generate base points in one sector and mirror
                num_per_sector = (n - 2) // 3
                remaining = (n - 2) % 3
                
                # Add center point (already added)
                # Add centroid as second center point with modified weights
                if n > 1:
                    # MODIFIED: Changed weights from [0.7, 0.1, 0.1, 0.1] to [0.6, 0.133, 0.133, 0.133]
                    points.append(center * 0.6 + A * 0.133 + B * 0.133 + C * 0.133)

                for i in range(num_per_sector + remaining):
                    # Generate in first sector (near AB edge)
                    u = 0.1 + 0.8 * np.random.rand()
                    v = 0.1 * np.random.rand()
                    P = A + u * (B - A) + v * (C - A)
                    if is_inside_triangle(P.reshape(1, 2), A, B, C):
                        points.append(P)
                        # Mirror to other sectors
                        # Rotation matrix for 120 degrees
                        R1 = np.array([[-0.5, -np.sqrt(3)/2], [np.sqrt(3)/2, -0.5]])
                        R2 = np.array([[-0.5, np.sqrt(3)/2], [-np.sqrt(3)/2, -0.5]])
                        
                        # Translate to origin, rotate, translate back
                        P_centered = P - center
                        P1 = center + R1 @ P_centered
                        P2 = center + R2 @ P_centered
                        
                        if is_inside_triangle(P1.reshape(1, 2), A, B, C):
                            points.append(P1)
                        if is_inside_triangle(P2.reshape(1, 2), A, B, C):
                            points.append(P2)

                # Fill remaining points if needed
                while len(points) < n:
                    u = np.random.rand()
                    v = np.random.rand()
                    if u + v > 1:
                        u = 1 - u
                        v = 1 - v
                    P = A + u * (B - A) + v * (C - A)
                    if is_inside_triangle(P.reshape(1, 2), A, B, C):
                        points.append(P)
                
                points = np.array(points[:n])
            else:
                # Standard random generation with adaptive density
                current_best_min_area = 0.0
                if population:
                    current_best_min_area = max([p[1] for p in population])
                # MODIFIED: density_factor = 0.8 + 0.5 * (min_area/0.0365) -> 0.65 + 0.35 * (min_area/0.0365)
                density_factor = 0.65 + 0.35 * (current_best_min_area / 0.0365)
                min_dist = density_factor * np.sqrt(1.0 / n)
                max_attempts = 10000
                attempts = 0
                points = []
                
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

                # Apply reduced jitter
                jitter = 0.01 * (2 * np.random.rand(n, 2) - 1)
                for i in range(n):
                    new_point = points[i] + jitter[i]
                    if is_inside_triangle(new_point.reshape(1, 2), A, B, C):
                        points[i] = new_point

        else:
            # Crossover: tournament selection of two parents
            idxs1 = np.random.choice(len(population), 2, replace=False)
            p1, p2 = population[idxs1[0]], population[idxs1[1]]
            parent1 = p1[0] if p1[1] > p2[1] else p2[0]
            
            idxs2 = np.random.choice(len(population), 2, replace=False)
            p1, p2 = population[idxs2[0]], population[idxs2[1]]
            parent2 = p1[0] if p1[1] > p2[1] else p2[0]

            # Create child by averaging
            points = (parent1 + parent2) * 0.5
            # Project boundary violations
            for i in range(n):
                if not is_inside_triangle(points[i].reshape(1, 2), A, B, C):
                    points[i] = project_to_boundary(points[i], A, B, C)

        # Local optimization
        current_best_points = points.copy()
        current_best_min_area = get_smallest_triangle_area(points)
        n_points = len(points)
        max_iter = 1000
        stagnation_counter = 0
        # Adaptive stagnation threshold based on current quality
        stagnation_threshold = 30 + 20 * (current_best_min_area / 0.0365)

        # INCREASED k_max base value and adjusted scaling factor to broaden optimization focus
        k_max = max(5, min(20, int(8 + 12 * (current_best_min_area/0.0365))))
        
        # Adaptive step decay based on progress
        step_decay = 0.99 + 0.005 * (current_best_min_area / 0.0365)

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

            triangles.sort(key=lambda x: x[0])

            min_area_val = triangles[0][0]
            k = 0
            for i in range(len(triangles)):
                if triangles[i][0] <= min_area_val * 1.1:
                    k = i + 1
                else:
                    break
            k = min(k, k_max)
            top_triangles = triangles[:k]

            displacement_vector = [np.zeros(2) for _ in range(n_points)]

            # Weight displacements by triangle severity (inverse relative area to power 1.5 instead of 2)
            for (area, i, j, k_idx) in top_triangles:
                # Weight calculation - prioritize smaller triangles but less aggressively
                weight = (min_area_val / max(area, 1e-10)) ** 1.5
                
                base_jk = points[k_idx] - points[j]
                normal_jk = np.array([-base_jk[1], base_jk[0]])
                norm_jk = np.linalg.norm(normal_jk)
                if norm_jk > 1e-10:
                    normal_jk = normal_jk / norm_jk
                    d_i = np.dot(points[i] - points[j], normal_jk)
                    dir_i = np.sign(d_i) * normal_jk * weight
                else:
                    dir_i = np.zeros(2)

                base_ik = points[k_idx] - points[i]
                normal_ik = np.array([-base_ik[1], base_ik[0]])
                norm_ik = np.linalg.norm(normal_ik)
                if norm_ik > 1e-10:
                    normal_ik = normal_ik / norm_ik
                    d_j = np.dot(points[j] - points[i], normal_ik)
                    dir_j = np.sign(d_j) * normal_ik * weight
                else:
                    dir_j = np.zeros(2)

                base_ij = points[j] - points[i]
                normal_ij = np.array([-base_ij[1], base_ij[0]])
                norm_ij = np.linalg.norm(normal_ij)
                if norm_ij > 1e-10:
                    normal_ij = normal_ij / norm_ij
                    d_k = np.dot(points[k_idx] - points[i], normal_ij)
                    dir_k = np.sign(d_k) * normal_ij * weight
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

            # ADDED: Stagnation detection and response
            previous_best = current_best_min_area
            step_size = 0.1 * (step_decay ** iter)
            if stagnation_counter > stagnation_threshold:
                # Apply larger perturbations to escape local optimum
                step_size = 0.3  # Larger step to break free
                # Reset stagnation counter after applying escape maneuver
                stagnation_counter = 0

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
                stagnation_counter = 0  # Reset counter on improvement
            else:
                stagnation_counter += 1  # Increment counter when no improvement

        # Add to population - INCREASED from 5 to 8 candidates
        candidate = (current_best_points, current_best_min_area)
        if len(population) < 8:
            population.append(candidate)
        else:
            min_idx = np.argmin([p[1] for p in population])
            if candidate[1] > population[min_idx][1]:
                population[min_idx] = candidate

    # Return best configuration
    best_idx = np.argmax([p[1] for p in population])
    return population[best_idx][0]