import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.stats import qmc

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    M = (A + B) / 2.0

    n_starts = 100
    best_config = None
    best_min_area = -1.0

    for start in range(n_starts):
        # Generate symmetric initial configuration
        sobol = qmc.Sobol(d=2, seed=42 + start)
        left_points = []
        while len(left_points) < 5:
            sample = sobol.random(1)[0]
            u, v = sample
            if u + v > 1:
                u = 1 - u
                v = 1 - v
            P = A + u * (C - A) + v * (M - A)
            # Nudge off axis to prevent mirroring duplicates
            if abs(P[0] - M[0]) < 1e-10:
                P[0] = M[0] - 1e-10
            left_points.append(P)

        t = np.random.uniform(0.2, 0.8)
        axis_point = C + t * (M - C)

        # Build initial symmetric configuration (11 points)
        initial_points = []
        for p in left_points:
            initial_points.append(p)
        initial_points.append(axis_point)
        for p in left_points:
            initial_points.append(np.array([2 * M[0] - p[0], p[1]]))
        points = np.array(initial_points)

        # Add initial asymmetry to break perfect symmetry
        for i in range(11):
            if random.random() < 0.5:
                offset = np.random.uniform(-0.05, 0.05, 2)
                new_pos = points[i] + offset
                if is_inside_triangle(new_pos, A, B, C):
                    points[i] = new_pos

        current_min_area = get_smallest_triangle_area(points)

        step_size = 0.05
        no_improve_count = 0
        max_no_improve = 500
        max_steps = 10000
        step = 0

        # Track best quality for dynamic phase threshold
        dynamic_best = current_min_area
n        while no_improve_count < max_no_improve and step < max_steps:
            step += 1
            improved = False

            # Dynamic quality phase threshold (50% of current best)
            quality_phase_threshold = max(0.028, 0.5 * dynamic_best)
            quality_phase = 'exploration' if current_min_area < quality_phase_threshold else 'exploitation'

            # Phase-adaptive move strategy ratio (60% gradient in exploration, 85% in exploitation)
            move_ratio = 0.4 if quality_phase == 'exploration' else 0.85

            # Minimum asymmetry factor of 0.05 during exploration
            asymmetry_factor = max(0.05, 0.1 * (current_min_area / 0.0365))

            if random.random() < move_ratio:
                # Find top 7 smallest triangles (was top 3)
                min_areas = []
                critical_indices_list = []
                
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            p1, p2, p3 = points[i], points[j], points[k]
                            area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p2[1]-p1[1])*(p3[0]-p1[0]))
                            if len(min_areas) < 7 or area < max(min_areas):
                                if len(min_areas) == 7:
                                    idx = min_areas.index(max(min_areas))
                                    min_areas[idx] = area
                                    critical_indices_list[idx] = (i, j, k)
                                else:
                                    min_areas.append(area)
                                    critical_indices_list.append((i, j, k))

                # Sort by area (smallest first)
                sorted_indices = np.argsort(min_areas)
                min_areas = [min_areas[i] for i in sorted_indices]
                critical_indices_list = [critical_indices_list[i] for i in sorted_indices]

                # Compute composite gradient with weights for up to 7 triangles (was 3)
                weights = [0.4, 0.2, 0.15, 0.1, 0.07, 0.05, 0.03][:len(min_areas)]
                if sum(weights) > 0:
                    weights = [w / sum(weights) for w in weights]
                
                composite_grads = {i: np.zeros(2) for i in range(11)}
                
                for weight, critical_indices in zip(weights, critical_indices_list):
                    i, j, k = critical_indices
                    p1, p2, p3 = points[i], points[j], points[k]
                    
                    # Compute signed area and orientation factor
                    s = 0.5 * ((p2[0]-p1[0])*(p3[1]-p1[1]) - (p2[1]-p1[1])*(p3[0]-p1[0]))
                    factor = 1.0 if s >= 0 else -1.0
                    
                    # Compute gradients for area increase
                    grad_p1 = factor * np.array([-(p2[1]-p3[1]), (p2[0]-p3[0])])
                    grad_p2 = factor * np.array([(p3[1]-p1[1]), -(p3[0]-p1[0])])
                    grad_p3 = factor * np.array([(p1[1]-p2[1]), -(p1[0]-p2[0])])

                    # Accumulate weighted gradients
                    composite_grads[i] += weight * grad_p1
                    composite_grads[j] += weight * grad_p2
                    composite_grads[k] += weight * grad_p3

                # Determine points involved in critical triangles
                critical_points = set()
                for critical_indices in critical_indices_list:
                    for idx in critical_indices:
                        critical_points.add(idx)

                # 20% chance to include non-critical point
                include_extra = random.random() < 0.2
                extra_idx = None
                if include_extra:
                    non_critical = [i for i in range(11) if i not in critical_points]
                    if non_critical:
                        extra_idx = random.choice(non_critical)

                total_points_moved = len(critical_points) + (1 if include_extra else 0)
                step_size_actual = step_size / total_points_moved

                # Save current state
                old_points = points.copy()

                valid_move = True
                
                # Move critical points using composite gradient direction
                for idx in range(11):
                    if idx not in critical_points and (not include_extra or idx != extra_idx):
                        continue
                    
                    grad_norm = np.linalg.norm(composite_grads[idx])
                    if grad_norm < 1e-10:
                        continue
                    
                    direction = composite_grads[idx] / grad_norm
                    
                    if include_extra and idx == extra_idx:
                        # For extra point, use random direction with gradient magnitude bias
                        random_dir = np.random.uniform(-1, 1, 2)
                        random_dir = random_dir / np.linalg.norm(random_dir)
                        direction = 0.7 * direction + 0.3 * random_dir
                        direction = direction / np.linalg.norm(direction)

                    new_pos = old_points[idx] + step_size_actual * direction
                    
                    if not is_inside_triangle(new_pos, A, B, C):
                        valid_move = False
                        break
                    
                    points[idx] = new_pos

                if valid_move:
                    new_min_area = get_smallest_triangle_area(points)

                    # Update dynamic best for phase threshold
                    if new_min_area > dynamic_best:
                        dynamic_best = new_min_area

                    # Simulated annealing acceptance with slower cooling
                    if new_min_area > current_min_area:
                        current_min_area = new_min_area
                        improved = True
                        no_improve_count = 0
                    else:
                        p_accept = 0.3 * (1 - step / max_steps)**0.5
                        if random.random() < p_accept:
                            current_min_area = new_min_area
                            improved = True
                            no_improve_count = 0
                        else:
                            # Revert if not accepted
                            points = old_points.copy()
                else:
                    # Revert invalid move
                    points = old_points.copy()

            # Traditional single-point moves
            else:
                idx = random.randint(0, 10)
                k = 1
                step_size_actual = step_size / np.sqrt(k)
                old_point = points[idx].copy()
                direction = np.random.uniform(-1, 1, 2)
                norm_dir = np.linalg.norm(direction)
                if norm_dir < 1e-10:
                    continue
                direction = direction / norm_dir * step_size_actual
                new_point = old_point + direction

                if not is_inside_triangle(new_point, A, B, C):
                    continue

                # Apply new point
                points[idx] = new_point
                new_min_area = get_smallest_triangle_area(points)

                # Update dynamic best for phase threshold
                if new_min_area > dynamic_best:
                    dynamic_best = new_min_area

                # Simulated annealing acceptance with slower cooling
                if new_min_area > current_min_area:
                    current_min_area = new_min_area
                    improved = True
                    no_improve_count = 0
                else:
                    p_accept = 0.3 * (1 - step / max_steps)**0.5
                    if random.random() < p_accept:
                        current_min_area = new_min_area
                        improved = True
                        no_improve_count = 0
                    else:
                        # Revert if not accepted
                        points[idx] = old_point

            # More aggressive step size adaptation when stuck
            if not improved:
                no_improve_count += 1
                # Faster reduction when improvements stall
                if no_improve_count > 20 and no_improve_count % 5 == 0 and step_size > 1e-7:
                    step_size *= 0.5
            else:
                # Reset no_improve_count on success
                no_improve_count = 0

        # Update best configuration
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config