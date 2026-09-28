import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    best_points = None
    best_min_area = -1

    # Expanded candidate row structures based on literature for 11 points
    candidate_row_structures = [
        [3, 3, 3, 2],  # Proven optimal
        [4, 3, 2, 2],  # Alternative high-quality
        [3, 2, 4, 2],  # Literature variant
        [2, 3, 4, 2],  # Literature variant
        [3, 4, 2, 2]   # Literature variant
    ]

    for run in range(10):
        np.random.seed(42 + run)
        random.seed(42 + run)

        # Dynamically select row structure per run
        row_counts = random.choice(candidate_row_structures)
        rows = len(row_counts)
        points = []
        for row_idx, num_points in enumerate(row_counts):
            v = (row_idx + 0.5) / rows
            for i in range(num_points):
                u = (i + 0.5) / num_points * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                # Scale perturbation by row length (1-v) for geometric consistency
                magnitude = 0.05 * (1 - v)
                perturbation = np.random.uniform(-magnitude, magnitude, size=2)
                P = P + perturbation
                points.append(P)

        current_points = np.array(points)
        current_min_area = get_smallest_triangle_area(current_points)

        # Adaptive local search parameters
        step = 0.1
        step_decay = 0.95  # Slower decay for deeper exploration
        max_iter = 1000     # Increased iterations for thorough optimization
        stagnation_counter = 0
        stagnation_threshold = 2  # Earlier special move triggering

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

            # Special moves when stuck (earlier triggering)
            if stagnation_counter >= stagnation_threshold:
                # Identify minimal-area triangles (within tolerance)
                n = 11
                min_triangles = []
                for i in range(n):
                    for j in range(i + 1, n):
                        for k in range(j + 1, n):
                            a, b, c = current_points[i], current_points[j], current_points[k]
                            area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                            if abs(area - current_min_area) < 1e-5:
                                min_triangles.append((i, j, k))
                
                # Try up to 3 minimal triangles with coordinated three-point move
                for _ in range(3):
                    if not min_triangles:
                        break
                    tri = random.choice(min_triangles)
                    i, j, k = tri
                    apex_idx = random.choice([i, j, k])
                    
                    # Determine base points
                    if apex_idx == i:
                        base1, base2 = j, k
                    elif apex_idx == j:
                        base1, base2 = i, k
                    else:
                        base1, base2 = i, j
                    
                    base_vec = current_points[base2] - current_points[base1]
                    base_norm = np.linalg.norm(base_vec)
                    if base_norm < 1e-8:
                        continue
                    
                    # Perpendicular direction for apex movement
                    perp = np.array([-base_vec[1], base_vec[0]])
                    perp_norm = np.linalg.norm(perp)
                    if perp_norm < 1e-8:
                        continue
                    perp = perp / perp_norm
                    
                    apex_vec = current_points[apex_idx] - current_points[base1]
                    proj = np.dot(apex_vec, perp)
                    direction_apex = perp * np.sign(proj)
                    
                    # Base spreading directions
                    base_dir = base_vec / base_norm
                    direction_base1 = base_dir * 0.5
                    direction_base2 = -base_dir * 0.5
                    
                    # Proposed moves with step scaling
                    new_apex = current_points[apex_idx] + direction_apex * (step * 1.5)
                    new_base1 = current_points[base1] + direction_base1 * (step * 0.5)
                    new_base2 = current_points[base2] + direction_base2 * (step * 0.5)
                    
                    # Boundary check for all three points
                    if not (is_inside_triangle(new_apex, A, B, C) and 
                            is_inside_triangle(new_base1, A, B, C) and 
                            is_inside_triangle(new_base2, A, B, C)):
                        continue
                    
                    candidate = current_points.copy()
                    candidate[apex_idx] = new_apex
                    candidate[base1] = new_base1
                    candidate[base2] = new_base2
                    new_min_area = get_smallest_triangle_area(candidate)
                    
                    if new_min_area > current_min_area:
                        current_points = candidate
                        current_min_area = new_min_area
                        improved = True
                        stagnation_counter = 0
                        step = 0.1  # Reset step after successful special move
                        break  # Exit after first successful three-point move

            if not improved:
                step *= step_decay
                stagnation_counter = 0
                if step < 1e-5:
                    break

        # Track best configuration across runs
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_points = current_points.copy()

    return best_points