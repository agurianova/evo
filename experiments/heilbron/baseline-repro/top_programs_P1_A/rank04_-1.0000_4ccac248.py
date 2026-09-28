import random
import numpy as np
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    L = np.linalg.norm(B - A)
    triangle_center_x = (A[0] + B[0] + C[0]) / 3
    symmetry_axis = 0.7598  # x-coordinate of altitude midpoint
    
    n_starts = 30
    best_config = None
    best_min_area = -1

    for start in range(n_starts):
        # Fixed boundary points: 8 total (5 additional beyond vertices)
        total_boundary = 8
        additional = 5  # fixed count based on literature
        a = [0, 0, 0]  # additional points per side
        
        # Distribute 5 additional points with bias toward vertices
        # Using power-law distribution (t^2.5) to cluster near vertices
        for _ in range(additional):
            side = random.choices([0, 1, 2], weights=[1.5, 1.5, 1.5])[0]
            a[side] += 1
        
        boundary_points = [A.copy(), B.copy(), C.copy()]
        sides = [(A, B), (B, C), (C, A)]
        for idx in range(3):
            num_interior = a[idx]
            if num_interior == 0:
                continue
            X, Y = sides[idx]
            # Power-law distribution (t^p where p=2.5) to cluster near vertices
            t = [((i / (num_interior + 1)) ** 2.5) for i in range(1, num_interior + 1)]
            for frac in t:
                P = X + frac * (Y - X)
                boundary_points.append(P)

        # Generate inner points with symmetry constraint (5 symmetric pairs + 1 on axis)
        inner_count = 11 - total_boundary  # 3 inner points
        inner_points = []
        
        # Generate 1 point on symmetry axis and 1 off-axis (will be mirrored)
        # Using hexagonal lattice pattern adapted to triangle geometry
        target_min_area = 0.0365
        # Approximate spacing based on target area
        spacing = math.sqrt(4 * target_min_area / math.sqrt(3))
        
        # Point on symmetry axis
        r1, r2 = 0.5, 0.5  # barycentric coords for center-ish
        r3 = 1 - r1 - r2
        P_center = r1 * A + r2 * B + r3 * C
        P_center[0] = symmetry_axis  # enforce on symmetry axis
        inner_points.append(P_center)
        
        # One asymmetric point (will be mirrored)
        r1, r2 = 0.6, 0.3  # barycentric coords
        r3 = 1 - r1 - r2
        P_asym = r1 * A + r2 * B + r3 * C
        # Ensure it's on the left side of symmetry axis
        if P_asym[0] >= symmetry_axis:
            P_asym[0] = symmetry_axis - (P_asym[0] - symmetry_axis)
        inner_points.append(P_asym)
        
        # Mirror the asymmetric point
        P_mirror = P_asym.copy()
P_mirror[0] = symmetry_axis + (symmetry_axis - P_asym[0])
        inner_points.append(P_mirror)

        # Combine points
        points = np.array(boundary_points + inner_points)

        # Force-directed repulsion with adaptive parameters
        for repel_iter in range(50):
            forces = np.zeros((11, 2))
            for i in range(11):
                for j in range(11):
                    if i == j:
                        continue
                    vec = points[i] - points[j]
                    dist = np.linalg.norm(vec)
                    if dist < 1e-5:
                        continue
                    force_vec = vec / (dist * dist)
                    forces[i] += force_vec

            # Adaptive scaling: decreases as 1/(iteration_count^0.5)
            adaptive_factor = 1.0 / math.sqrt(repel_iter + 1)
            max_force = np.max(np.linalg.norm(forces, axis=1))
            step_size_repel = 0.02 * adaptive_factor / max_force if max_force > 1e-10 else 0.0
            displacement = forces * step_size_repel

            new_points = points + displacement
            for i in range(11):
                if not is_inside_triangle(new_points[i], A, B, C):
                    new_points[i] = points[i]
            points = new_points

            # Enforce symmetry after each repulsion step
            for i in range(11):
                if abs(points[i, 0] - symmetry_axis) > 1e-5:
                    # Mirror points to maintain symmetry
                    dist = abs(points[i, 0] - symmetry_axis)
                    side = 1 if points[i, 0] > symmetry_axis else -1
                    points[i, 0] = symmetry_axis + side * dist

        current_min_area = get_smallest_triangle_area(points)
        step_size = 0.02 * L
        no_improve_count = 0
        max_no_improve = 50
        max_steps = 5000
        step = 0
        
        # Track recent success rate for adaptive optimization
        success_history = []
        success_window = 100

        while no_improve_count < max_no_improve and step < max_steps:
            step += 1
            improved = False

            # Dynamic optimization balance based on success rate
            success_rate = sum(success_history[-success_window:]) / max(1, len(success_history[-success_window:]))
            focus_ratio = 0.9 - 0.6 * success_rate  # 0.3-0.9 depending on success

            if random.random() < focus_ratio:  # Focus on vulnerable triangles
                # Dynamic threshold proportional to (current/target) ratio
                target_ratio = current_min_area / 0.0365
                threshold = current_min_area * (0.05 + 0.15 * target_ratio)
                threshold = max(1.05 * current_min_area, min(1.2 * current_min_area, threshold))
                
                triangles = []
                for i in range(11):
                    for j in range(i + 1, 11):
                        for k in range(j + 1, 11):
                            x1, y1 = points[i]
                            x2, y2 = points[j]
                            x3, y3 = points[k]
                            area = 0.5 * abs((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1))
                            if area <= threshold:
                                triangles.append((area, i, j, k))
                
                if not triangles:
                    # Fallback to top-3 if none found
                    triangles_all = []
                    for i in range(11):
                        for j in range(i + 1, 11):
                            for k in range(j + 1, 11):
                                x1, y1 = points[i]
                                x2, y2 = points[j]
                                x3, y3 = points[k]
                                area = 0.5 * abs((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1))
                                triangles_all.append((area, i, j, k))
                    triangles_all.sort(key=lambda x: x[0])
                    triangles = triangles_all[:3]

                candidate_points = set()
                for (_, i, j, k) in triangles:
                    candidate_points.update([i, j, k])
                candidate_points = list(candidate_points)

                best_global_min_area = current_min_area
                best_move = None

                for idx in candidate_points:
                    dir_vec_total = np.zeros(2)
                    total_weight = 0.0
                    for (area_val, i, j, k) in triangles:
                        if idx not in (i, j, k):
                            continue
                        if idx == i:
                            P, Q, R = points[i], points[j], points[k]
                        elif idx == j:
                            P, Q, R = points[j], points[i], points[k]
                        else:
                            P, Q, R = points[k], points[i], points[j]

                        v = R - Q
                        cross_val = v[0]*(P[1]-Q[1]) - v[1]*(P[0]-Q[1])
                        if abs(cross_val) < 1e-10:
                            continue
                        dir_vec = np.array([Q[1]-R[1], R[0]-Q[0]])
                        norm_dir = np.linalg.norm(dir_vec)
                        if norm_dir < 1e-10:
                            continue
                        dir_vec = dir_vec / norm_dir
                        if cross_val < 0:
                            dir_vec = -dir_vec
                        
                        weight = 1.0 / (area_val + 1e-5)
                        dir_vec_total += weight * dir_vec
                        total_weight += weight

                    if total_weight < 1e-5:
                        continue
                    dir_vec_avg = dir_vec_total / total_weight
                    norm_dir_avg = np.linalg.norm(dir_vec_avg)
                    if norm_dir_avg < 1e-5:
                        continue
                    dir_vec_avg = dir_vec_avg / norm_dir_avg

                    new_point = points[idx] + step_size * dir_vec_avg
                    if not is_inside_triangle(new_point, A, B, C):
                        continue

                    # Enforce symmetry for new point
                    if abs(new_point[0] - symmetry_axis) > 1e-5:
                        dist = abs(new_point[0] - symmetry_axis)
                        side = 1 if new_point[0] > symmetry_axis else -1
                        new_point[0] = symmetry_axis + side * dist

                    temp_points = points.copy()
                    temp_points[idx] = new_point
                    new_min_area = get_smallest_triangle_area(temp_points)

                    if new_min_area > best_global_min_area:
                        best_global_min_area = new_min_area
                        best_move = (idx, new_point, points[idx].copy())

                if best_global_min_area > current_min_area:
                    idx, new_point, _ = best_move
                    points[idx] = new_point
                    current_min_area = best_global_min_area
                    improved = True
                    no_improve_count = 0
                    success_history.append(1)
                else:
                    success_history.append(0)

            else:  # Random perturbation
                idx = random.randint(0, 10)
                old_point = points[idx].copy()
                direction = np.random.uniform(-1, 1, 2)
                norm_dir = np.linalg.norm(direction)
                direction = direction / norm_dir if norm_dir > 1e-5 else np.array([1.0, 0.0])
                new_point = old_point + step_size * direction

                if is_inside_triangle(new_point, A, B, C):
                    # Enforce symmetry
                    if abs(new_point[0] - symmetry_axis) > 1e-5:
                        dist = abs(new_point[0] - symmetry_axis)
                        side = 1 if new_point[0] > symmetry_axis else -1
                        new_point[0] = symmetry_axis + side * dist

                    points[idx] = new_point
                    new_min_area = get_smallest_triangle_area(points)
                    if new_min_area > current_min_area:
                        current_min_area = new_min_area
                        improved = True
                        no_improve_count = 0
                        success_history.append(1)
                    else:
                        points[idx] = old_point
                        success_history.append(0)

            # Adaptive step size based on success
            if improved:
                step_size = min(step_size * 1.05, 0.05 * L)
            else:
                no_improve_count += 1
                if no_improve_count > 25:
                    step_size = max(step_size * 0.92, 0.001 * L)
                
            # Aggressive restart when stuck
            if no_improve_count > max_no_improve:
                no_improve_count = 0
                step_size = 0.03 * L * (0.8 + 0.4 * random.random())
                # Add larger random perturbation to escape local optimum
                for idx in range(11):
                    if random.random() < 0.3:  # 30% chance to perturb each point
                        direction = np.random.uniform(-1, 1, 2)
                        norm_dir = np.linalg.norm(direction)
                        direction = direction / norm_dir if norm_dir > 1e-5 else np.array([1.0, 0.0])
                        magnitude = 0.02 * L * random.random()
                        new_point = points[idx] + magnitude * direction
                        if is_inside_triangle(new_point, A, B, C):
                            # Enforce symmetry
                            if abs(new_point[0] - symmetry_axis) > 1e-5:
                                dist = abs(new_point[0] - symmetry_axis)
                                side = 1 if new_point[0] > symmetry_axis else -1
                                new_point[0] = symmetry_axis + side * dist
                            points[idx] = new_point

            # Keep success history bounded
            if len(success_history) > success_window * 2:
                success_history = success_history[-success_window:]

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config