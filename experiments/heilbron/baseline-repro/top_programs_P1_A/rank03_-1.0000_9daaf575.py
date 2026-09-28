import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.stats import qmc

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    M = (A + B) / 2.0

    # Track historical axis positions for adaptive initialization
    historical_axis_positions = []
    
    n_starts = 100
    best_config = None
    best_min_area = -1.0

    for start in range(n_starts):
        # Generate 5 points anywhere in the triangle using barycentric coordinates
        sobol = qmc.Sobol(d=2, seed=42 + start)
        points_left = []
        while len(points_left) < 5:
            sample = sobol.random(1)[0]
            u, v = sample
            if u + v > 1:
                u = 1 - u
                v = 1 - v
            P = A + u * (B - A) + v * (C - A)
            points_left.append(P)

        # Adaptive axis point initialization based on historical data
        if historical_axis_positions and random.random() < 0.7:
            # Sample from historical best positions with some noise
            axis_point = random.choice(historical_axis_positions) + \
                         np.random.normal(0, 0.05, 2)
            # Ensure it's inside the triangle
            if not is_inside_triangle(axis_point, A, B, C):
                t = np.random.uniform(0.5, 0.7)
                axis_point = C + t * (M - C)
        else:
            t = np.random.uniform(0.5, 0.7)
            axis_point = C + t * (M - C)

        # Move success tracking for adaptive selection
        move_success = {'critical': 0.1, 'traditional': 0.1}
        move_attempts = {'critical': 1, 'traditional': 1}
        
        # Build initial configuration
        full_points = []
        for p in points_left:
            full_points.append(p)
        full_points.append(axis_point)
        
        # Parameterized symmetry with decaying probability
        symmetry_prob = max(0.95 - start * 0.005, 0.3)
        
        # Generate right-side points with adaptive symmetry
        for i, p in enumerate(points_left):
            if random.random() < symmetry_prob:
                # Mirror symmetrically
                full_points.append(np.array([2 * M[0] - p[0], p[1]]))
            else:
                # Generate independent point near mirror position
                mirror_pos = np.array([2 * M[0] - p[0], p[1]])
                # Add some random perturbation within triangle
                while True:
                    perturbation = np.random.normal(0, 0.05, 2)
                    candidate = mirror_pos + perturbation
n                    if is_inside_triangle(candidate, A, B, C):
                        full_points.append(candidate)
                        break
                    # Try smaller perturbation if outside
                    if np.linalg.norm(perturbation) < 0.01:
                        full_points.append(mirror_pos)  # Fallback to symmetric
                        break

        full_points = np.array(full_points)
        current_min_area = get_smallest_triangle_area(full_points)

        step_size = 0.05
        no_improve_count = 0
        max_no_improve = 500
        max_steps = 10000
        step = 0
        restarts_within_run = 0
        max_restarts_within_run = 5  # Increased for deeper exploration

        while (no_improve_count < max_no_improve or restarts_within_run < max_restarts_within_run) and step < max_steps:
            step += 1
            improved = False

            # Adaptive move selection based on historical success
            critical_success_rate = move_success['critical'] / move_attempts['critical']
            traditional_success_rate = move_success['traditional'] / move_attempts['traditional']
            
            # Bias selection toward more successful strategy
            p_critical = 0.5 + 0.4 * (critical_success_rate - traditional_success_rate)
            p_critical = max(0.1, min(0.9, p_critical))  # Clamp between 0.1 and 0.9
            
            if random.random() < p_critical:
                move_type = 'critical'
                move_attempts['critical'] += 1
                # Build current full configuration
                full_points_current = []
                for p in points_left:
                    full_points_current.append(p)
                full_points_current.append(axis_point)
                for i, p in enumerate(points_left):
                    if random.random() < symmetry_prob:
                        full_points_current.append(np.array([2 * M[0] - p[0], p[1]]))
                    else:
                        mirror_pos = np.array([2 * M[0] - p[0], p[1]])
                        perturbation = np.random.normal(0, 0.02, 2)
                        candidate = mirror_pos + perturbation
                        if is_inside_triangle(candidate, A, B, C):
                            full_points_current.append(candidate)
                        else:
                            full_points_current.append(mirror_pos)
                
                full_points_current = np.array(full_points_current)

                # Find critical triangle (smallest area)
                min_area_val = float('inf')
                critical_indices = None
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            p1, p2, p3 = full_points_current[i], full_points_current[j], full_points_current[k]
                            area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p2[1]-p1[1])*(p3[0]-p1[0]))
                            if area < min_area_val:
                                min_area_val = area
                                critical_indices = (i, j, k)

                if critical_indices is None:
                    continue

                # Determine involved left_points and axis
                involved_left = set()
                axis_involved = False
                for idx in critical_indices:
                    if idx == 5:
                        axis_involved = True
                    elif idx < 5:
                        involved_left.add(idx)
                    else:  # Mirror points (6-10)
                        involved_left.add(idx - 6)
                n_dof = len(involved_left) + (1 if axis_involved else 0)
                
                # Calculate curvature-based weights for each point in critical triangle
                weights = np.zeros(3)
                points_tri = [full_points_current[i] for i in critical_indices]
                for idx_in_tri, point_index in enumerate(critical_indices):
                    # Other two points in triangle
                    j = (idx_in_tri + 1) % 3
                    k = (idx_in_tri + 2) % 3
                    A_tri = points_tri[idx_in_tri]
                    B_tri = points_tri[j]
                    C_tri = points_tri[k]
                    
                    # Calculate area contribution (curvature approximation)
                    base_area = 0.5 * abs((B_tri[0]-A_tri[0])*(C_tri[1]-A_tri[1]) - 
                                       (B_tri[1]-A_tri[1])*(C_tri[0]-A_tri[0]))
                    
                    # Perturb this point and see area change
                    perturbation = np.array([0.01, 0.01])
                    A_tri_pert = A_tri + perturbation
                    pert_area = 0.5 * abs((B_tri[0]-A_tri_pert[0])*(C_tri[1]-A_tri_pert[1]) - 
                                      (B_tri[1]-A_tri_pert[1])*(C_tri[0]-A_tri_pert[0]))
                    
                    # Weight proportional to sensitivity
                    weights[idx_in_tri] = max(0.1, min(1.0, abs(pert_area - base_area) / (base_area + 1e-10)))

                # Normalize weights
                weights = weights / np.sum(weights)

                # Prepare move vectors for underlying representation
                left_moves = np.zeros((5, 2))
                axis_move = np.array([0.0, 0.0])

                # Points in critical triangle
                points_tri = [full_points_current[i] for i in critical_indices]
                for idx_in_tri, point_index in enumerate(critical_indices):
                    # Weighted step size based on contribution
                    weighted_step = step_size * weights[idx_in_tri]
                    
                    # Other two points in triangle
                    j = (idx_in_tri + 1) % 3
                    k = (idx_in_tri + 2) % 3
                    A_tri = points_tri[idx_in_tri]
                    B_tri = points_tri[j]
                    C_tri = points_tri[k]

                    # Compute outward normal for A_tri
                    v = C_tri - B_tri
                    n_vec = np.array([v[1], -v[0]])
                    n_norm = np.linalg.norm(n_vec)
                    if n_norm < 1e-10:
                        n_unit = np.array([0.0, 0.0])
                    else:
                        n_vec = n_vec / n_norm
                        w = A_tri - B_tri
                        if np.dot(w, n_vec) < 0:
                            n_vec = -n_vec
                        n_unit = n_vec

                    move_free = n_unit * weighted_step

                    # Convert to underlying representation move
                    if point_index == 5:  # axis point
                        axis_move += move_free
                    elif point_index < 5:  # left_point
                        i = point_index
                        left_moves[i] += move_free
                    else:  # mirror point (6-10)
                        i = point_index - 6
                        left_moves[i] += np.array([-move_free[0], move_free[1]])

                # Save current state
                old_left_points = [p.copy() for p in points_left]
                old_axis_point = axis_point.copy()

                # Apply moves to left_points
                valid_move = True
                for i in range(5):
                    if np.any(left_moves[i] != 0):
                        new_left = old_left_points[i] + left_moves[i]
                        if not is_inside_triangle(new_left, A, B, C):
                            valid_move = False
                            break
                        points_left[i] = new_left

                # Apply move to axis point if involved
                if valid_move and axis_involved:
                    new_axis = old_axis_point + axis_move
                    if not is_inside_triangle(new_axis, A, B, C):
                        valid_move = False
                    else:
                        axis_point = new_axis

                if not valid_move:
                    # Revert
                    points_left = [p.copy() for p in old_left_points]
                    axis_point = old_axis_point.copy()
                else:
                    # Build and evaluate new configuration
                    config = []
                    for p in points_left:
                        config.append(p)
                    config.append(axis_point)
                    for i, p in enumerate(points_left):
                        if random.random() < symmetry_prob:
                            config.append(np.array([2 * M[0] - p[0], p[1]]))
                        else:
                            mirror_pos = np.array([2 * M[0] - p[0], p[1]])
                            perturbation = np.random.normal(0, 0.02, 2)
                            candidate = mirror_pos + perturbation
                            if is_inside_triangle(candidate, A, B, C):
                                config.append(candidate)
                            else:
                                config.append(mirror_pos)
                    config = np.array(config)
                    new_min_area = get_smallest_triangle_area(config)

                    if new_min_area > current_min_area:
                        current_min_area = new_min_area
                        improved = True
                        no_improve_count = 0
                        move_success['critical'] += 1
                    else:
                        # Revert if no improvement
                        points_left = [p.copy() for p in old_left_points]
                        axis_point = old_axis_point.copy()

            # Traditional single-point moves
            else:
                move_type = 'traditional'
                move_attempts['traditional'] += 1
                indices = list(range(6))
                random.shuffle(indices)

                for idx in indices:
                    if idx == 5:  # Axis point move
                        k = 1
                        step_size_actual = step_size / np.sqrt(k)
                        old_axis = axis_point.copy()
                        direction = np.random.uniform(-1, 1, 2)
                        norm_dir = np.linalg.norm(direction)
                        if norm_dir < 1e-10:
                            continue
                        direction = direction / norm_dir * step_size_actual
                        new_axis = old_axis + direction

                        if not is_inside_triangle(new_axis, A, B, C):
                            continue

                        # Build config with new axis point
                        config = []
                        for p in points_left:
                            config.append(p)
                        config.append(new_axis)
                        for i, p in enumerate(points_left):
                            if random.random() < symmetry_prob:
                                config.append(np.array([2 * M[0] - p[0], p[1]]))
                            else:
                                mirror_pos = np.array([2 * M[0] - p[0], p[1]])
                                perturbation = np.random.normal(0, 0.02, 2)
                                candidate = mirror_pos + perturbation
                                if is_inside_triangle(candidate, A, B, C):
                                    config.append(candidate)
                                else:
                                    config.append(mirror_pos)
                        config = np.array(config)
                        new_min_area = get_smallest_triangle_area(config)

                        if new_min_area > current_min_area:
                            axis_point = new_axis
                            current_min_area = new_min_area
                            improved = True
                            no_improve_count = 0
                            move_success['traditional'] += 1

                    else:  # Symmetric pair move
                        i = idx
                        k = 2
                        step_size_actual = step_size / np.sqrt(k)
                        old_left = points_left[i].copy()
                        direction = np.random.uniform(-1, 1, 2)
                        norm_dir = np.linalg.norm(direction)
                        if norm_dir < 1e-10:
                            continue
                        direction = direction / norm_dir * step_size_actual
                        new_left = old_left + direction

                        if not is_inside_triangle(new_left, A, B, C):
                            continue

                        new_left_points = points_left.copy()
                        new_left_points[i] = new_left
                        config = []
                        for p in new_left_points:
                            config.append(p)
                        config.append(axis_point)
                        for i, p in enumerate(new_left_points):
                            if random.random() < symmetry_prob:
                                config.append(np.array([2 * M[0] - p[0], p[1]]))
                            else:
                                mirror_pos = np.array([2 * M[0] - p[0], p[1]])
                                perturbation = np.random.normal(0, 0.02, 2)
                                candidate = mirror_pos + perturbation
                                if is_inside_triangle(candidate, A, B, C):
                                    config.append(candidate)
                                else:
                                    config.append(mirror_pos)
                        config = np.array(config)
                        new_min_area = get_smallest_triangle_area(config)

                        if new_min_area > current_min_area:
                            points_left[i] = new_left
                            current_min_area = new_min_area
                            improved = True
                            no_improve_count = 0
                            move_success['traditional'] += 1

            # Handle non-improving steps and restarts
            if not improved:
                no_improve_count += 1
                if no_improve_count >= max_no_improve:
                    if restarts_within_run < max_restarts_within_run:
                        step_size = 0.05
                        no_improve_count = 0
                        restarts_within_run += 1
                else:
                    # Adaptive step size reduction based on improvement rate
                    improvement_rate = 1.0 / (no_improve_count + 1)
                    step_size = max(1e-7, step_size * (0.9 + 0.1 * improvement_rate))

        # Build final configuration for this start
        final_points = []
        for p in points_left:
            final_points.append(p)
        final_points.append(axis_point)
        for i, p in enumerate(points_left):
            if random.random() < symmetry_prob:
                final_points.append(np.array([2 * M[0] - p[0], p[1]]))
            else:
                mirror_pos = np.array([2 * M[0] - p[0], p[1]])
                perturbation = np.random.normal(0, 0.02, 2)
                candidate = mirror_pos + perturbation
                if is_inside_triangle(candidate, A, B, C):
                    final_points.append(candidate)
                else:
                    final_points.append(mirror_pos)
        final_points = np.array(final_points)
        
        # Update historical axis positions if this is a good configuration
        if current_min_area > best_min_area * 0.95:  # Store promising axis positions
            historical_axis_positions.append(axis_point.copy())
            if len(historical_axis_positions) > 20:
                historical_axis_positions.pop(0)
        
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = final_points.copy()

    return best_config