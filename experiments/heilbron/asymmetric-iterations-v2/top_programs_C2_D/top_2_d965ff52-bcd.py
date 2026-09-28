from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import math


def entrypoint():
    A, B, C = get_unit_triangle()
    triangle_height = np.linalg.norm((A + B) / 2 - C)
    
    # Adaptive parameters for improvement strategy
    restart_min = 0.35
    restart_scale = 0.25
    exploration_base = 0.25
    exploration_dynamic = 0.7
    basin_step_scale = 0.75
    basin_step_denom = 9.0
    k_val_min = 2
    k_val_scale = 7.5
    initial_weights = [0.35, 0.35, 0.3]  # rebalanced to emphasize single and two-point moves
    basin_depth_factor_scale = 0.9
    basin_depth_factor_denom = 10.0
    basin_depth_threshold = 0.035

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)

        def tri_area(a, b, c):
            return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))

        # Track triangles incrementally to avoid O(n^3) recomputation
        triangle_cache = {}
        min_triangle_indices = []
        
        # Initialize triangle cache with all triangle areas
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = tri_area(points[i], points[j], points[k])
                    triangle_cache[(i, j, k)] = area
                    
        # Get current minimum area
        min_area = min(triangle_cache.values())
        min_triangle_indices = [key for key, val in triangle_cache.items() if abs(val - min_area) < 1e-10]

        # Update triangle cache after a move
        def update_triangle_cache(moved_indices):
            nonlocal min_area, min_triangle_indices
            affected_triangles = set()
            
            # Find all triangles containing any moved index
            for idx in moved_indices:
                for i in range(11):
                    for j in range(i+1, 11):
                        if i == idx or j == idx:
                            affected_triangles.add(tuple(sorted([i, j, idx])))
                        elif i < idx < j:
                            affected_triangles.add((i, idx, j))

            # Recompute areas for affected triangles
            new_min_area = float('inf')
            for tri in affected_triangles:
                i, j, k = tri
                area = tri_area(best[i], best[j], best[k])
                triangle_cache[tri] = area
                if area < new_min_area:
                    new_min_area = area

            # Update min_area and min_triangle_indices if needed
            if new_min_area < min_area:
                min_area = new_min_area
                min_triangle_indices = [key for key, val in triangle_cache.items() 
                                     if abs(val - min_area) < 1e-10]
            elif abs(new_min_area - min_area) < 1e-10:
                # Check if we have new minimum triangles
                new_min_tris = [key for key, val in triangle_cache.items() 
                               if abs(val - min_area) < 1e-10]
                min_triangle_indices = new_min_tris

        # Basin depth calculation using the cache
        def calculate_basin_depth(min_area_val, threshold=basin_depth_threshold):
            count = 0
            for area in triangle_cache.values():
                if area <= min_area_val * (1 + threshold):
                    count += 1
            return count

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

        # Simulated annealing parameters
        T0 = 0.01
        T = T0
        max_iter = 500
        max_no_improve = 50
        no_improve_count = 0
        # Adaptive cooling
        initial_cooling_factor = 0.98  # Slower initial cooling for better exploration
        final_cooling_factor = 0.99
        cooling_transition_iter = 100
        cooling_factor = initial_cooling_factor
        cooling_stagnation_threshold = 20
        cooling_stagnation_count = 0
        restarts = 0
        max_restarts = 2

        # Calculate initial basin depth
        current_basin_depth = calculate_basin_depth(min_area, basin_depth_threshold)

        # Move type success tracking with balanced initial weights
        move_type_success = initial_weights.copy()
        move_type_attempts = [1, 1, 1]

        # Row detection and disruption logic
        def detect_rows(points, y_threshold=0.02):
            """Detect rows of points with similar y-coordinates."""
            # Sort points by y-coordinate
            y_coords = points[:, 1]
            sorted_indices = np.argsort(y_coords)
            sorted_ys = y_coords[sorted_indices]
            
            # Find clusters of y-coordinates
            rows = []
            current_row = [sorted_indices[0]]
            
            for i in range(1, len(sorted_ys)):
                if sorted_ys[i] - sorted_ys[i-1] < y_threshold:
                    current_row.append(sorted_indices[i])
                else:
                    if len(current_row) > 1:  # Only consider rows with multiple points
                        rows.append(current_row)
                    current_row = [sorted_indices[i]]
            
            if len(current_row) > 1:
                rows.append(current_row)
            
            return rows

        def add_row_disruption_moves(moves, rows):
            """Add specialized moves to disrupt detected rows."""
            for row in rows:
                # For each row, create moves that push points away from the row line
                if len(row) >= 2:
                    # Calculate the average y of the row
                    avg_y = np.mean([best[i, 1] for i in row])
                    
                    # Create moves that push points up or down from the row
                    for i in row:
                        # Vertical disruption
                        angle_up = 90
                        angle_down = 270
                        moves.append((i, angle_up))
                        moves.append((i, angle_down))
                        
                        # Diagonal disruption for end points
                        if i == row[0] or i == row[-1]:
                            moves.append((i, 45))
                            moves.append((i, 135))
                            moves.append((i, 225))
                            moves.append((i, 315))
            return moves

        for iter_idx in range(max_iter):
            # Update boundary margin based on current basin depth
            boundary_margin = 0.01 * triangle_height * (1 + 0.8 * (current_basin_depth / 20.0))
            
            # Detect rows for potential disruption
            rows = detect_rows(best)
            
            # Find smallest triangles and get union of points
            min_indices_set = set()
            for tri in min_triangle_indices:
                i, j, k = tri
                min_indices_set.add(i)
                min_indices_set.add(j)
                min_indices_set.add(k)
            min_indices = list(min_indices_set)

            # ADAPTIVE k_val based on basin depth
            # When basin depth is high (deep local optimum), examine more triangles
            k_val = max(k_val_min, int(k_val_scale * math.sqrt(current_basin_depth)))
            
            # DYNAMIC MOVE TYPE SELECTION BASED ON BASIN DEPTH
            # When basin depth is high, emphasize multi-point moves to break the basin
            basin_depth_factor = 1.0 + basin_depth_factor_scale * (math.exp(current_basin_depth / basin_depth_factor_denom) - 1)
            move_type_weights = [
                move_type_success[0],
                move_type_success[1] * basin_depth_factor,
                move_type_success[2] * basin_depth_factor
            ]
            move_type_weights = [w/sum(move_type_weights) for w in move_type_weights]
            selected_move_type = np.random.choice([0, 1, 2], p=move_type_weights)

            # ADAPTIVE ANGLE RESOLUTION: finer steps at low temperatures
            angle_step_single = 20 if T > 0.005 else 10  # Increased resolution
            angle_step_multi = 40 if T > 0.005 else 20    # Increased resolution

            # Generate moves based on selected type
            moves = []
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

            # ADAPTIVE non-involved exploration based on basin depth
            # When basin depth is high, explore more non-involved points
            non_involved_rate = 0.15 + 0.2 * (current_basin_depth / 20.0)  # Increased base rate
            if np.random.rand() < non_involved_rate and len(min_indices) < 11:
                non_involved = [i for i in range(11) if i not in min_indices]
                if non_involved:
                    idx = np.random.choice(non_involved)
                    angle = np.random.randint(0, 360)
                    moves.append((idx, angle))

            # Add row disruption moves if rows are detected
            if rows:
                moves = add_row_disruption_moves(moves, rows)

            # SCALED step size by triangle_height with basin depth adaptation
            # Larger steps when basin depth is high
            basin_step_factor = 1.0 + basin_step_scale * (current_basin_depth / basin_step_denom)
            # Adaptive exploration: larger initial moves that gradually become more focused
            exploration_factor = exploration_base + exploration_dynamic * (1 - T/T0)
            step_size = math.sqrt(T) * triangle_height * exploration_factor * basin_step_factor
            
            best_candidate = None
            best_candidate_score = -1.0
            
            # Try moves of the selected type
            for move in moves:
                candidate = best.copy()
                moved_indices = []
                
                if len(move) == 2:  # Single-point move
                    idx, angle = move
                    dx = step_size * math.cos(math.radians(angle))
                    dy = step_size * math.sin(math.radians(angle))
                    candidate[idx] += [dx, dy]
                    moved_indices = [idx]
                elif len(move) == 4:  # Two-point move
                    i, a1, j, a2 = move
                    dx1 = step_size * math.cos(math.radians(a1))
                    dy1 = step_size * math.sin(math.radians(a1))
                    dx2 = step_size * math.cos(math.radians(a2))
                    dy2 = step_size * math.sin(math.radians(a2))
                    candidate[i] += [dx1, dy1]
                    candidate[j] += [dx2, dy2]
                    moved_indices = [i, j]
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
                    moved_indices = [i, j, k]

                # Project all points to boundary with interior bias
                for idx in range(11):
                    candidate[idx] = project_to_triangle(candidate[idx])

                # Check validity before expensive area calculation
                valid = True
                for i in range(11):
                    if not is_inside_triangle(candidate[i], A, B, C):
                        valid = False
                        break
                if not valid:
                    continue

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
                    
                    # Update triangle cache with the new configuration
                    update_triangle_cache(moved_indices)
                    
                    # Update move type success tracking
                    move_type_success[selected_move_type] += 1
                    
                    # Recalculate basin depth after improvement
                    current_basin_depth = calculate_basin_depth(min_area, basin_depth_threshold)
                else:
                    no_improve_count += 1
                    
                # Update move type attempts
                move_type_attempts[selected_move_type] += 1

            # ADAPTIVE COOLING: Switch to slower cooling after initial exploration
            if improved:
                cooling_stagnation_count = 0
            else:
                cooling_stagnation_count += 1
                
            if iter_idx < cooling_transition_iter or cooling_stagnation_count < cooling_stagnation_threshold:
                cooling_factor = initial_cooling_factor
            else:
                cooling_factor = final_cooling_factor

            T *= cooling_factor

            # STRATEGIC RESTART MECHANISM: Larger perturbations when basin depth is high
            if no_improve_count >= max_no_improve:
                if restarts < max_restarts:
                    # Restart with basin depth-aware perturbation
                    restart_candidate = best.copy()
                    
                    # BASED ON BASIN DEPTH: deeper basins need larger perturbations
                    basin_perturb_factor = max(restart_min, restart_scale * math.sqrt(current_basin_depth))
                    restart_step = basin_perturb_factor * triangle_height
                    
                    for i in range(11):
                        angle = np.random.uniform(0, 360)
                        dx = restart_step * math.cos(math.radians(angle))
                        dy = restart_step * math.sin(math.radians(angle))
                        restart_candidate[i] += [dx, dy]
                        restart_candidate[i] = project_to_triangle(restart_candidate[i])
                    
                    restart_score = get_smallest_triangle_area(restart_candidate)
                    if restart_score > 1e-10:
                        best = restart_candidate
                        best_score = restart_score
                        
                        # Update triangle cache after restart
                        for i in range(11):
                            for j in range(i+1, 11):
                                for k in range(j+1, 11):
                                    area = tri_area(best[i], best[j], best[k])
                                    triangle_cache[(i, j, k)] = area
                        
                        # Update min_area and min_triangle_indices
                        min_area = min(triangle_cache.values())
                        min_triangle_indices = [key for key, val in triangle_cache.items() 
                                             if abs(val - min_area) < 1e-10]
                        
                        # Update basin depth after restart
                        current_basin_depth = calculate_basin_depth(min_area, basin_depth_threshold)
                    
                    restarts += 1
                    no_improve_count = 0
                    T = T0  # Reset temperature
                    # Reset cooling parameters
                    cooling_factor = initial_cooling_factor
                    cooling_stagnation_count = 0
                else:
                    break

        return best

    return improve