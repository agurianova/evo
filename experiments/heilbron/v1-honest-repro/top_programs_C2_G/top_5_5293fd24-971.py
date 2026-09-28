import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def optimize_configuration(points, A, B, C, max_iter=500, step_init=0.1, step_decay=0.95, stagnation_threshold=2):
    current_points = points.copy()
    current_min_area = get_smallest_triangle_area(current_points)
    step = step_init
    stagnation_counter = 0

    for _ in range(max_iter):
        improved = False

        # Standard moves: 10 random directions per point
        for i in range(11):
            old_point = current_points[i].copy()
            angles = np.random.uniform(0, 2 * np.pi, 10)
            directions = np.column_stack((np.cos(angles), np.sin(angles))) * step

            best_new_point = old_point
            best_new_min_area = current_min_area

            for d in directions:
                new_point = old_point + d
                if not is_inside_triangle(new_point, A, B, C):
                    continue
                
                candidate = current_points.copy()
                candidate[i] = new_point
                new_min_area = get_smallest_triangle_area(candidate)
                
                if new_min_area > best_new_min_area:
                    best_new_min_area = new_min_area
                    best_new_point = new_point

            if best_new_min_area > current_min_area:
                current_points[i] = best_new_point
                current_min_area = best_new_min_area
                improved = True

        if improved:
            stagnation_counter = 0
            continue

        stagnation_counter += 1

        if stagnation_counter >= stagnation_threshold:
            # Find minimal triangles
            n = 11
            min_triangles = []
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = current_points[i], current_points[j], current_points[k]
                        area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                        if abs(area - current_min_area) < 1e-5:
                            min_triangles.append((i, j, k))
            
            if min_triangles:
                selected_tris = random.sample(min_triangles, min(3, len(min_triangles)))
                
                # Try 3-point moves on selected triangles
                for tri in selected_tris:
                    i, j, k = tri
                    p_i, p_j, p_k = current_points[i], current_points[j], current_points[k]
                    
                    # Compute side lengths
                    d_ij = np.linalg.norm(p_j - p_i)
                    d_jk = np.linalg.norm(p_k - p_j)
                    d_ki = np.linalg.norm(p_i - p_k)
                    
                    # Identify longest side
                    if d_ij >= d_jk and d_ij >= d_ki:
                        base1, base2, apex = i, j, k
                        base_vec = p_j - p_i
                    elif d_jk >= d_ij and d_jk >= d_ki:
                        base1, base2, apex = j, k, i
                        base_vec = p_k - p_j
                    else:
                        base1, base2, apex = k, i, j
                        base_vec = p_i - p_k

                    base_length = np.linalg.norm(base_vec)
                    if base_length < 1e-8:
                        continue
                    
                    perp = np.array([-base_vec[1], base_vec[0]])
                    perp = perp / base_length
                    
                    apex_vec = current_points[apex] - current_points[base1]
                    proj = np.dot(apex_vec, perp)
                    direction_apex = perp * np.sign(proj)
                    
                    d_base = step * 0.5
                    d_apex = step * 1.0
                    base_dir = base_vec / base_length
                    
                    new_base1 = current_points[base1] - base_dir * d_base
                    new_base2 = current_points[base2] + base_dir * d_base
                    new_apex = current_points[apex] + direction_apex * d_apex

                    if (is_inside_triangle(new_base1, A, B, C) and 
                        is_inside_triangle(new_base2, A, B, C) and 
                        is_inside_triangle(new_apex, A, B, C)):
                        
                        candidate_points = current_points.copy()
                        candidate_points[base1] = new_base1
                        candidate_points[base2] = new_base2
                        candidate_points[apex] = new_apex
                        new_min_area = get_smallest_triangle_area(candidate_points)
                        
                        if new_min_area > current_min_area + 1e-10:
                            current_points = candidate_points
                            current_min_area = new_min_area
                            improved = True
                            stagnation_counter = 0
                            step = step_init
                            break

                if improved:
                    continue

                # Fallback: single apex push
                tri = random.choice(min_triangles)
                i, j, k = tri
                point_idx = random.choice([i, j, k])
                
                if point_idx == i:
                    base1, base2 = j, k
                elif point_idx == j:
                    base1, base2 = i, k
                else:
                    base1, base2 = i, j

                base_vec = current_points[base2] - current_points[base1]
                norm_base = np.linalg.norm(base_vec)
                if norm_base > 1e-8:
                    perp = np.array([-base_vec[1], base_vec[0]]) / norm_base
                    apex_vec = current_points[point_idx] - current_points[base1]
                    proj = np.dot(apex_vec, perp)
                    direction = perp * np.sign(proj)
                    
                    new_point = current_points[point_idx] + direction * (step * 1.5)
                    if is_inside_triangle(new_point, A, B, C):
                        candidate = current_points.copy()
                        candidate[point_idx] = new_point
                        new_min_area = get_smallest_triangle_area(candidate)
                        if new_min_area > current_min_area + 1e-10:
                            current_points = candidate
                            current_min_area = new_min_area
                            improved = True
                            stagnation_counter = 0
                            step = step_init

            if improved:
                continue

            # Decay step when stuck
            step *= step_decay
            stagnation_counter = 0
            if step < 1e-5:
                break

    return current_points, current_min_area

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    best_points = None
    best_fitness = -1

    # Expanded row structures based on literature
    candidate_row_structures = [
        [3, 3, 3, 2],
        [4, 3, 2, 2],
        [3, 2, 4, 2],
        [2, 3, 4, 2],
        [3, 4, 2, 2],
        [4, 2, 3, 2],
        [2, 4, 3, 2]
    ]

    for run in range(10):
        np.random.seed(42 + run)
        random.seed(42 + run)

        # Generate initial configuration
        row_counts = random.choice(candidate_row_structures)
        rows = len(row_counts)
        points = []
        for row_idx, num_points in enumerate(row_counts):
            v = (row_idx + 0.5) / rows
            for i in range(num_points):
                u = (i + 0.5) / num_points * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                magnitude = 0.05 * (1 - v)
                perturbation = np.random.uniform(-magnitude, magnitude, size=2)
                P = P + perturbation
                points.append(P)

        initial_points = np.array(points)
        
        # Optimize configuration
        current_points, current_min_area = optimize_configuration(
            initial_points, A, B, C,
            max_iter=500,
            step_init=0.1,
            step_decay=0.95,
            stagnation_threshold=2
        )

        # Adversarial resistance test with multiple strategies
        adversary_step_inits = [0.05, 0.1, 0.2]
        resistance_count = 0
        for step_init in adversary_step_inits:
            _, adv_min_area = optimize_configuration(
                current_points, A, B, C,
                max_iter=500,
                step_init=step_init,
                step_decay=0.95,
                stagnation_threshold=2
            )
            if adv_min_area <= current_min_area + 1e-10:
                resistance_count += 1
        
        resistance = resistance_count / len(adversary_step_inits)
        quality = min(current_min_area / 0.0365, 1.0)
        fitness_val = 0.5 * quality + 0.5 * resistance

        # Track best configuration by combined fitness
        if fitness_val > best_fitness:
            best_fitness = fitness_val
            best_points = current_points.copy()

    return best_points