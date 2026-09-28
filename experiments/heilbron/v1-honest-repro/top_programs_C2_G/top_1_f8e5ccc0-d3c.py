import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    best_points = None
    best_min_area = -1

    for run in range(10):
        np.random.seed(42 + run)
        random.seed(42 + run)

        # Symmetric row configuration [4,3,3,1] for 4 rows
        row_counts = [4, 3, 3, 1]
        rows = len(row_counts)
        points = []
        for row_idx, num_points in enumerate(row_counts):
            v = (row_idx + 0.5) / rows
            for i in range(num_points):
                u = (i + 0.5) / num_points * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                # Uniform perturbation (0.05 magnitude across all rows)
                magnitude = 0.05
                perturbation = np.random.uniform(-magnitude, magnitude, size=2)
                P = P + perturbation
                points.append(P)

        current_points = np.array(points)
        current_min_area = get_smallest_triangle_area(current_points)

        # Local search parameters
        step = 0.05
        max_iter = 500
        stagnation_counter = 0
        stagnation_threshold = 5

        for _ in range(max_iter):
            improved = False

            # Standard moves: 10 random directions per point
            for i in range(11):
                old_point = current_points[i].copy()
                # Generate 10 random unit directions scaled by step
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

            # Special move when stuck: target smallest triangle
            if stagnation_counter >= stagnation_threshold:
                # Identify all minimal-area triangles (within tolerance)
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
                    tri = random.choice(min_triangles)
                    i, j, k = tri
                    point_idx = random.choice([i, j, k])
                    
                    # Determine base points (the other two in the triangle)
                    if point_idx == i:
                        base1, base2 = j, k
                    elif point_idx == j:
                        base1, base2 = i, k
                    else:
                        base1, base2 = i, j
                    
                    base_vec = current_points[base2] - current_points[base1]
                    perp = np.array([-base_vec[1], base_vec[0]])
                    norm = np.linalg.norm(perp)
                    if norm > 1e-8:
                        perp = perp / norm
                        apex_vec = current_points[point_idx] - current_points[base1]
                        proj = np.dot(apex_vec, perp)
                        direction = perp * np.sign(proj)
                        
                        new_point = current_points[point_idx] + direction * (step * 1.5)
                        if is_inside_triangle(new_point, A, B, C):
                            candidate = current_points.copy()
                            candidate[point_idx] = new_point
                            new_min_area = get_smallest_triangle_area(candidate)
                            if new_min_area > current_min_area:
                                current_points = candidate
                                current_min_area = new_min_area
                                improved = True
                                stagnation_counter = 0

            if not improved:
                step *= 0.9
                stagnation_counter = 0
                if step < 1e-5:
                    break

        # Track best configuration across runs
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_points = current_points.copy()

    return best_points