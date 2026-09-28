from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import math


def entrypoint():
    A, B, C = get_unit_triangle()
    triangle_height = np.linalg.norm((A + B) / 2 - C)

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        initial_min_area = get_smallest_triangle_area(best)
        best_score = initial_min_area

        def tri_area(a, b, c):
            return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))

        # Helper functions for boundary projection with interior bias
        def project_point_to_line(point, a, b):
            ab = b - a
            ap = point - a
            denom = np.dot(ab, ab)
            if denom < 1e-10:
                return a
            t = np.dot(ap, ab) / denom
            t = max(0.0, min(1.0, t))
            return a + t * ab

        def project_to_triangle(point):
            if is_inside_triangle(point, A, B, C):
                # Check if point is too close to boundary and apply repulsion
                edges = [(A, B), (B, C), (C, A)]
                min_dist = float('inf')
                
                for (p1, p2) in edges:
                    v = p2 - p1
                    w = point - p1
                    
                    c1 = np.dot(w, v)
                    c2 = np.dot(v, v)
                    
                    if c2 == 0:
                        b = 0
                    else:
                        b = c1 / c2
                    
                    if b < 0:
                        proj = p1
                    elif b > 1:
                        proj = p2
                    else:
                        proj = p1 + b * v
                    
                    dist = np.linalg.norm(point - proj)
                    if dist < min_dist:
                        min_dist = dist
                
                # ADAPTIVE boundary margin based on current solution quality
                boundary_margin = max(0.001, 0.05 * best_score) * triangle_height
                
                # If too close to boundary, push inward
                if min_dist < boundary_margin:
                    direction = np.zeros(2)
                    for (p1, p2) in edges:
                        v = p2 - p1
                        w = point - p1
                        c1 = np.dot(w, v)
                        c2 = np.dot(v, v)
                        b = 0 if c2 == 0 else c1 / c2
                        b = max(0.0, min(1.0, b))
                        proj = p1 + b * v
                        normal = np.array([-(p2[1]-p1[1]), p2[0]-p1[0]])
                        normal = normal / np.linalg.norm(normal)
                        if np.dot(normal, C - p1) < 0:
                            normal = -normal
                        direction += normal
                    
                    if np.linalg.norm(direction) > 0:
                        direction = direction / np.linalg.norm(direction)
                        point = point + direction * (boundary_margin - min_dist)
                        
                # Final boundary check
                if is_inside_triangle(point, A, B, C):
                    return point

            # Standard projection if still outside
            p1 = project_point_to_line(point, A, B)
            p2 = project_point_to_line(point, B, C)
            p3 = project_point_to_line(point, C, A)
            d1 = np.linalg.norm(point - p1)
            d2 = np.linalg.norm(point - p2)
            d3 = np.linalg.norm(point - p3)
            if d1 <= d2 and d1 <= d3:
                return p1
            elif d2 <= d3:
                return p2
            else:
                return p3

        # ADAPTIVE temperature initialization based on problem difficulty
        TARGET_MAX_MIN_AREA = 0.0365
        T0 = max(0.005, 0.5 * (TARGET_MAX_MIN_AREA - initial_min_area))
        T = T0
        max_iter = 500
        max_no_improve = 50
        no_improve_count = 0
        # Adaptive cooling
        initial_cooling_factor = 0.95
        final_cooling_factor = 0.99
        cooling_stagnation_threshold = 20
        cooling_stagnation_count = 0
        restarts = 0
        max_restarts = 2

        # Move type success tracking with equal initial weights and min exploration
        move_type_success = [1.0, 1.0, 1.0]  # Equal initial weights instead of [0.6, 0.3, 0.1]
        move_type_attempts = [1, 1, 1]
        
        # Track recent move directions for directional diversity in restarts
        recent_moves = []
        max_recent_moves = 10

        for iter_idx in range(max_iter):
            # PROGRESSIVE EXPLORATION RATE DECAY
            min_exploration_rate = max(0.05, 0.1 * (1 - iter_idx/max_iter))

            # Find smallest triangles and get union of points
            min_areas = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = tri_area(best[i], best[j], best[k])
                        min_areas.append((area, (i, j, k)))
            min_areas.sort(key=lambda x: x[0])
            
            # CHANGED: Square-root relationship instead of linear
            k_val = max(3, int(15 * math.sqrt(T / T0)))
            min_indices_set = set()
            for idx in range(min(k_val, len(min_areas))):
                i, j, k_idx = min_areas[idx][1]
                min_indices_set.add(i)
                min_indices_set.add(j)
                min_indices_set.add(k_idx)
            min_indices = list(min_indices_set)

            # DYNAMIC MOVE TYPE SELECTION WITH MINIMUM EXPLORATION GUARANTEE
            move_type_weights = [success/attempts for success, attempts in zip(move_type_success, move_type_attempts)]
            total = sum(move_type_weights)
            if total > 0:
                move_type_weights = [w/total for w in move_type_weights]
            else:
                move_type_weights = [1/3, 1/3, 1/3]
            
            # Ensure minimum exploration rate for each move type
            for i in range(3):
                if move_type_weights[i] < min_exploration_rate / (3 - min_exploration_rate):
                    move_type_weights[i] = min_exploration_rate / (3 - min_exploration_rate)
            total = sum(move_type_weights)
            move_type_weights = [w/total for w in move_type_weights]
            
            selected_move_type = np.random.choice([0, 1, 2], p=move_type_weights)

            # PROGRESS-DEPENDENT ANGLE RESOLUTION: coarser when progressing, finer when stagnating
            angle_step_single = 30 if no_improve_count < 10 else 10
            angle_step_multi = 60 if no_improve_count < 10 else 20

            # Generate moves based on selected type
            if selected_move_type == 0:  # Single-point moves
                moves = [(idx, angle) for idx in min_indices for angle in range(0, 360, angle_step_single)]
            elif selected_move_type == 1:  # Two-point moves
                moves = [(min_indices[i], angle, min_indices[j], (angle + 180) % 360) 
                         for i in range(len(min_indices)) for j in range(i+1, len(min_indices)) 
                         for angle in range(0, 360, angle_step_multi)]
            else:  # Three-point moves
                moves = [(min_indices[i], angle, min_indices[j], (angle + 120) % 360, min_indices[k], (angle + 240) % 360)
                         for i in range(len(min_indices)) for j in range(i+1, len(min_indices)) 
                         for k in range(j+1, len(min_indices)) for angle in range(0, 360, angle_step_multi)]

            # ADDED occasional random moves for non-involved points (10% of moves)
            if np.random.rand() < 0.1 and len(min_indices) < 11:
                non_involved = [i for i in range(11) if i not in min_indices]
                if non_involved:
                    idx = np.random.choice(non_involved)
                    angle = np.random.randint(0, 360)
                    moves.append((idx, angle))

            # SCALED step size by triangle_height for proper dimensionality
            step_size = math.sqrt(T) * triangle_height * 0.5
            
            best_candidate = None
            best_candidate_score = -1.0
            
            # Try moves of the selected type
            for move in moves:
                candidate = best.copy()
                move_direction = np.zeros(2)
                
                if len(move) == 2:  # Single-point move
                    idx, angle = move
                    dx = step_size * math.cos(math.radians(angle))
                    dy = step_size * math.sin(math.radians(angle))
                    candidate[idx] += [dx, dy]
                    move_direction = np.array([dx, dy])
                elif len(move) == 4:  # Two-point move
                    i, a1, j, a2 = move
                    dx1 = step_size * math.cos(math.radians(a1))
                    dy1 = step_size * math.sin(math.radians(a1))
                    dx2 = step_size * math.cos(math.radians(a2))
                    dy2 = step_size * math.sin(math.radians(a2))
                    candidate[i] += [dx1, dy1]
                    candidate[j] += [dx2, dy2]
                    move_direction = np.array([dx1+dx2, dy1+dy2])
                else:  # Three-point move
                    i, a1, j, a2, k, a3 = move
                    dx1 = step_size * math.cos(math.radians(a1))
                    dy1 = step_size * math.sin(math.radians(a1))
                    dx2 = step_size * math.cos(math.radians(a2))
                    dy2 = step_size * math.sin(math.radians(a2))
                    dx3 = step_size * math.cos(math.radians(a3))
                    dy3 = step_size * math.sin(math.radians(a3))
                    candidate[i] += [dx1, dy1]
                    candidate[j] += [dx2, dy2]
                    candidate[k] += [dx3, dy3]
                    move_direction = np.array([dx1+dx2+dx3, dy1+dy2+dy3])

                # Track recent move directions for restart diversity
                if np.linalg.norm(move_direction) > 0:
                    move_direction = move_direction / np.linalg.norm(move_direction)
                    recent_moves.append(move_direction)
                    if len(recent_moves) > max_recent_moves:
                        recent_moves.pop(0)

                # Project all points to boundary with interior bias
                for idx in range(11):
                    candidate[idx] = project_to_triangle(candidate[idx])

                score = get_smallest_triangle_area(candidate)
                if score < 1e-10:
                    continue

                if score > best_candidate_score:
                    best_candidate = candidate
                    best_candidate_score = score

            # IMPROVED ACCEPTANCE: Proper simulated annealing with probabilistic acceptance
            improved = False
            if best_candidate is not None:
                delta = best_candidate_score - best_score
                # Always accept improvements, sometimes accept worse solutions
                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    best = best_candidate
                    best_score = best_candidate_score
                    no_improve_count = 0
                    improved = True
                    
                    # Update move type success tracking
                    move_type_success[selected_move_type] += 1
                else:
                    no_improve_count += 1
                    
                # Update move type attempts
                move_type_attempts[selected_move_type] += 1

            # ADAPTIVE COOLING: Based on stagnation rather than fixed iteration count
            if improved:
                cooling_stagnation_count = 0
            else:
                cooling_stagnation_count += 1
                
            if cooling_stagnation_count < cooling_stagnation_threshold:
                cooling_factor = initial_cooling_factor
            else:
                cooling_factor = final_cooling_factor

            T *= cooling_factor

            # IMPROVED RESTART MECHANISM: Stagnation-aware with directional diversity
            if no_improve_count >= max_no_improve:
                if restarts < max_restarts:
                    # Restart with stagnation-aware perturbation
                    restart_candidate = best.copy()
                    # CHANGED: Stagnation-aware scaling instead of T0/T
                    restart_step = 0.1 * (1 + 0.5 * (no_improve_count / max_no_improve))
                    
                    for i in range(11):
                        # Add directional diversity: push opposite to recent moves
                        avg_opposite_dir = np.zeros(2)
                        if len(recent_moves) > 0:
                            avg_dir = np.mean(recent_moves, axis=0)
                            avg_opposite_dir = -avg_dir
                            if np.linalg.norm(avg_opposite_dir) > 0:
                                avg_opposite_dir = avg_opposite_dir / np.linalg.norm(avg_opposite_dir)
                        
                        if np.linalg.norm(avg_opposite_dir) > 0:
                            # Use directional diversity
                            dx = restart_step * avg_opposite_dir[0]
                            dy = restart_step * avg_opposite_dir[1]
                        else:
                            # Fall back to random direction
                            angle = np.random.uniform(0, 360)
                            dx = restart_step * math.cos(math.radians(angle))
                            dy = restart_step * math.sin(math.radians(angle))
                        
                        restart_candidate[i] += [dx, dy]
                        restart_candidate[i] = project_to_triangle(restart_candidate[i])
                    
                    restart_score = get_smallest_triangle_area(restart_candidate)
                    if restart_score > 1e-10:
                        best = restart_candidate
                        best_score = restart_score
                    restarts += 1
                    no_improve_count = 0
                    T = T0  # Reset temperature
                    # Reset cooling parameters
                    cooling_factor = initial_cooling_factor
                    cooling_stagnation_count = 0
                    # Clear recent moves for fresh start
                    recent_moves = []
                else:
                    break

        return best

    return improve