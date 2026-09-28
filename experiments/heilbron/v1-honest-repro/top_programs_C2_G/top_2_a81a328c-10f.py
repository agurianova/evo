import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    best_points = None
    best_min_area = -1

    # Weighted candidate row structures: [3,3,3,2] gets 3x priority
    candidate_row_structures = [
        [3, 3, 3, 2],  # Proven optimal (weight=3)
        [4, 3, 2, 2],  # Alternative high-quality (weight=1)
        [3, 2, 4, 2],  # Literature variant (weight=1)
        [2, 3, 4, 2],  # Literature variant (weight=1)
        [3, 4, 2, 2]   # Literature variant (weight=1)
    ]
    weights = [3, 1, 1, 1, 1]

    # Helper: project out-of-bound points to boundary then nudge inward
    def project_and_nudge(point):
        if is_inside_triangle(point, A, B, C):
            return point
        
        edges = [(A, B), (B, C), (C, A)]
        min_dist = float('inf')
        best_proj = None

        for (P1, P2) in edges:
            v = P2 - P1
            w = point - P1
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 < 1e-12:
                t = 0
            else:
                t = c1 / c2
            t = max(0.0, min(1.0, t))
            proj = P1 + t * v
            dist = np.linalg.norm(point - proj)
            if dist < min_dist:
                min_dist = dist
                best_proj = proj

        centroid = (A + B + C) / 3.0
        direction = centroid - best_proj
        dir_norm = np.linalg.norm(direction)
        if dir_norm < 1e-12:
            nudge = np.array([0.0, 0.0])
        else:
            nudge = 0.001 * direction / dir_norm

        return best_proj + nudge

    for run in range(25):  # Increased runs for better exploration
        np.random.seed(42 + run)
        random.seed(42 + run)

        # Weighted selection of row structure
        row_counts = random.choices(candidate_row_structures, weights=weights, k=1)[0]
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

        current_points = np.array(points)
        current_min_area = get_smallest_triangle_area(current_points)

        # Adaptive local search parameters
        step = 0.1
        step_decay = 0.95
        max_iter = 1000
        stagnation_counter = 0
        stagnation_threshold = 2

        for _ in range(max_iter):
            improved = False

            # Standard moves with boundary projection
            for i in range(11):
                old_point = current_points[i].copy()
                angles = np.random.uniform(0, 2 * np.pi, 10)
                directions = np.column_stack((np.cos(angles), np.sin(angles))) * step

                best_new_point = old_point
                best_new_min_area = current_min_area

                for d in directions:
                    new_point = old_point + d
                    new_point = project_and_nudge(new_point)  # Boundary handling

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

            # Special moves when stuck
            if stagnation_counter >= stagnation_threshold:
                # Find minimal triangles with priority scoring
                n = 11
                min_triangles = []  # (triangle, priority_score)
                for i in range(n):
                    for j in range(i + 1, n):
                        for k in range(j + 1, n):
                            a, b, c = current_points[i], current_points[j], current_points[k]
                            area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                            if abs(area - current_min_area) < 1e-5:
                                # Compute priority: acuteness + height/base ratio
                                ab = np.linalg.norm(b - a)
                                bc = np.linalg.norm(c - b)
                                ca = np.linalg.norm(a - c)
                                sides = sorted([ab, bc, ca])
                                # Smallest angle (opposite smallest side)
                                cos_angle = (sides[1]**2 + sides[2]**2 - sides[0]**2) / (2 * sides[1] * sides[2])
                                cos_angle = max(-1.0, min(1.0, cos_angle))
                                angle_deg = np.degrees(np.arccos(cos_angle))
                                # Height-to-base ratio (using longest side as base)
                                base_length = sides[2]
                                height_val = 2 * area / base_length
                                ratio = height_val / base_length
                                priority_score = (1 - angle_deg / 90.0) * 0.7 + (1 - ratio) * 0.3
                                min_triangles.append(((i, j, k), priority_score))

                if not min_triangles:
                    stagnation_counter = 0
                    continue

                # Sort by priority descending
                min_triangles.sort(key=lambda x: x[1], reverse=True)
                tri, _ = min_triangles[0]  # Highest priority triangle
                i, j, k = tri

                # Determine base and apex (longest side as base)
                a, b, c = current_points[i], current_points[j], current_points[k]
                ab = np.linalg.norm(b - a)
                bc = np.linalg.norm(c - b)
                ca = np.linalg.norm(a - c)
                sides = [ab, bc, ca]
                max_idx = np.argmax(sides)
                if max_idx == 0:  # ab longest
                    base1, base2, apex_idx = i, j, k
                elif max_idx == 1:  # bc longest
                    base1, base2, apex_idx = j, k, i
                else:  # ca longest
                    base1, base2, apex_idx = k, i, j

                base_vec = current_points[base2] - current_points[base1]
                base_norm = np.linalg.norm(base_vec)
                if base_norm < 1e-8:
                    continue

                # Perpendicular direction
                perp = np.array([-base_vec[1], base_vec[0]])
                perp_norm = np.linalg.norm(perp)
                if perp_norm < 1e-8:
                    continue
                perp = perp / perp_norm

                apex_vec = current_points[apex_idx] - current_points[base1]
                proj = np.dot(apex_vec, perp)
                height_val = abs(proj)

                # Randomly select move type
                move_type = random.randint(0, 2)
                candidate = current_points.copy()
                moved = False

                if move_type == 0:  # Apex move
                    direction_apex = perp * np.sign(proj)
                    move_mag = step * height_val * 1.5
                    new_apex = current_points[apex_idx] + direction_apex * move_mag
                    new_apex = project_and_nudge(new_apex)
                    candidate[apex_idx] = new_apex
                    moved = True

                elif move_type == 1:  # Base spreading
                    base_dir = base_vec / base_norm
                    base_spread = step * base_norm * 0.5
                    new_base1 = current_points[base1] + base_dir * (base_spread / 2)
                    new_base2 = current_points[base2] - base_dir * (base_spread / 2)
                    new_base1 = project_and_nudge(new_base1)
                    new_base2 = project_and_nudge(new_base2)
                    candidate[base1] = new_base1
                    candidate[base2] = new_base2
                    moved = True

                else:  # Combined move
                    direction_apex = perp * np.sign(proj)
                    move_mag_apex = step * height_val * 1.5
                    new_apex = current_points[apex_idx] + direction_apex * move_mag_apex
                    new_apex = project_and_nudge(new_apex)

                    base_dir = base_vec / base_norm
                    base_spread = step * base_norm * 0.5
                    new_base1 = current_points[base1] + base_dir * (base_spread / 2)
                    new_base2 = current_points[base2] - base_dir * (base_spread / 2)
                    new_base1 = project_and_nudge(new_base1)
                    new_base2 = project_and_nudge(new_base2)

                    candidate[apex_idx] = new_apex
                    candidate[base1] = new_base1
                    candidate[base2] = new_base2
                    moved = True

                if moved:
                    new_min_area = get_smallest_triangle_area(candidate)
                    if new_min_area > current_min_area:
                        current_points = candidate
                        current_min_area = new_min_area
                        improved = True
                        stagnation_counter = 0
                        step = 0.1  # Reset step after success
                        break  # Exit after first successful move

            if not improved:
                step *= step_decay
                stagnation_counter = 0
                if step < 1e-5:
                    break

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_points = current_points.copy()

    return best_points