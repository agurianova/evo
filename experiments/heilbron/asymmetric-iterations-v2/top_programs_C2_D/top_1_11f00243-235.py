from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import math


def entrypoint():
    A, B, C = get_unit_triangle()
    triangle_height = np.linalg.norm((A + B) / 2 - C)
    
    # Precompute all triangle indices once for incremental updates
    all_triangles = [(i, j, k) for i in range(11) for j in range(i+1, 11) for k in range(j+1, 11)]
    
    # Adaptive parameters for improvement strategy
    restart_min = 0.35
    restart_scale = 0.45  # Increased from 0.25 for deeper basin escapes
    exploration_base = 0.25
    exploration_dynamic = 0.7
    basin_step_scale = 0.75
    basin_step_denom = 9.0
    k_val_min = 2
    k_val_scale = 7.5
    initial_weights = [0.35, 0.35, 0.3]  # rebalanced to better handle shallow basins
    basin_depth_factor_scale = 0.45  # Reduced from 0.9 to maintain single-point move viability
    basin_depth_factor_denom = 10.0

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        
        # Initialize triangle area cache
        triangle_areas = np.zeros(len(all_triangles))
        
        def tri_area(a, b, c):
            return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))

        # Precompute initial triangle areas
        for idx, (i, j, k) in enumerate(all_triangles):
            triangle_areas[idx] = tri_area(best[i], best[j], best[k])
        best_score = np.min(triangle_areas)

        # Incremental update of triangle areas after a move
        def update_triangle_areas(affected_indices):
            for idx, (i, j, k) in enumerate(all_triangles):
                if i in affected_indices or j in affected_indices or k in affected_indices:
                    triangle_areas[idx] = tri_area(best[i], best[j], best[k])

        # Weighted basin depth calculation prioritizing critical triangles
        def calculate_basin_depth(min_area):
            total_weight = 0
            threshold = min(0.05, max(0.02, 0.035 * (1 + total_weight/30.0)))
            for area in triangle_areas:
                if area <= min_area * (1 + threshold):
                    # Weight by how critical the triangle is (closer to minimum = more critical)
                    weight = threshold - (area/min_area - 1)
                    total_weight += weight
            return total_weight

        # Simplified boundary projection that allows points to stay on boundaries
        def project_to_triangle(point):
            if is_inside_triangle(point, A, B, C):
                return point
            
            # Project to the closest edge
            edges = [(A, B), (B, C), (C, A)]
            closest_point = None
            min_dist = float('inf')
            
            for (p1, p2) in edges:
                v = p2 - p1
                w = point - p1
                
                c1 = np.dot(w, v)
                c2 = np.dot(v, v)
                
                if c2 < 1e-10:  # Nearly zero length edge
                    proj = p1
                else:
                    b = max(0.0, min(1.0, c1 / c2))
                    proj = p1 + b * v
                
                dist = np.linalg.norm(point - proj)
                if dist < min_dist:
                    min_dist = dist
                    closest_point = proj
            
            return closest_point

        # Simulated annealing parameters
        T0 = 0.01
        T = T0
        max_iter = 500
        max_no_improve = 50
        no_improve_count = 0
        # Adaptive cooling
        initial_cooling_factor = 0.98
        final_cooling_factor = 0.99
        cooling_transition_iter = 100
        cooling_factor = initial_cooling_factor
        cooling_stagnation_threshold = 20
        cooling_stagnation_count = 0
        restarts = 0
        max_restarts = 2

        # Calculate initial basin depth
        current_basin_depth = calculate_basin_depth(best_score)

        # Move type success tracking with balanced initial weights
        move_type_success = initial_weights.copy()
        move_type_attempts = [1, 1, 1]

        for iter_idx in range(max_iter):
            # Dynamic basin depth threshold
            basin_depth_threshold = min(0.05, max(0.02, 0.035 * (1 + current_basin_depth/30.0)))
            
            # Find smallest triangles and get union of points
            min_indices_set = set()
            min_area_val = best_score
            
            # Only check triangles within threshold of minimum
            for idx, (i, j, k) in enumerate(all_triangles):
                if triangle_areas[idx] <= min_area_val * (1 + basin_depth_threshold):
                    min_indices_set.add(i)
                    min_indices_set.add(j)
                    min_indices_set.add(k)
            
            # ADAPTIVE k_val based on basin depth
            k_val = max(k_val_min, int(k_val_scale * math.sqrt(current_basin_depth)))
            min_indices = list(min_indices_set)

            # DYNAMIC MOVE TYPE SELECTION BASED ON BASIN DEPTH
            basin_depth_factor = 1.0 + basin_depth_factor_scale * (math.exp(current_basin_depth / basin_depth_factor_denom) - 1)
            move_type_weights = [
                move_type_success[0],
                move_type_success[1] * basin_depth_factor,
                move_type_success[2] * basin_depth_factor
            ]
            move_type_weights = [w/sum(move_type_weights) for w in move_type_weights]
            selected_move_type = np.random.choice([0, 1, 2], p=move_type_weights)

            # ADAPTIVE ANGLE RESOLUTION: finer steps at low temperatures
            angle_step_single = 12 if T > 0.005 else 4
            angle_step_multi = 20 if T > 0.005 else 8

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

            # ADAPTIVE non-involved exploration based on basin depth
            non_involved_rate = 0.15 + 0.08 * (current_basin_depth / 20.0)  # Reduced coefficient from 0.2 to 0.08
            if np.random.rand() < non_involved_rate and len(min_indices) < 11:
                non_involved = [i for i in range(11) if i not in min_indices]
                if non_involved:
                    idx = np.random.choice(non_involved)
                    angle = np.random.randint(0, 360)
                    moves.append((idx, angle))

            # SCALED step size by triangle_height with basin depth adaptation
            basin_step_factor = 1.0 + basin_step_scale * (current_basin_depth / basin_step_denom)
            exploration_factor = exploration_base + exploration_dynamic * (1 - T/T0)
            step_size = math.sqrt(T) * triangle_height * exploration_factor * basin_step_factor
            
            best_candidate = None
            best_candidate_score = -1.0
            
            # Try moves of the selected type
            for move in moves:
                candidate = best.copy()
                affected_indices = set()
                
                if len(move) == 2:  # Single-point move
                    idx, angle = move
                    affected_indices.add(idx)
                    dx = step_size * math.cos(math.radians(angle))
                    dy = step_size * math.sin(math.radians(angle))
                    candidate[idx] += [dx, dy]
                elif len(move) == 4:  # Two-point move
                    i, a1, j, a2 = move
                    affected_indices.update([i, j])
                    dx1 = step_size * math.cos(math.radians(a1))
                    dy1 = step_size * math.sin(math.radians(a1))
                    dx2 = step_size * math.cos(math.radians(a2))
                    dy2 = step_size * math.sin(math.radians(a2))
                    candidate[i] += [dx1, dy1]
                    candidate[j] += [dx2, dy2]
                else:  # Three-point move
                    i, a1, j, a2, k, a3 = move
                    affected_indices.update([i, j, k])
                    dx1 = step_size * math.cos(math.radians(a1))
                    dy1 = step_size * math.sin(math.radians(a1))
                    dx2 = step_size * math.cos(math.radians(a2))
                    dy2 = step_size * math.sin(math.radians(a2))
                    dx3 = step_size * math.cos(math.radians(a3))
                    dy3 = step_size * math.sin(math.radians(a3))
                    candidate[i] += [dx1, dy1]
                    candidate[j] += [dx2, dy2]
                    candidate[k] += [dx3, dy3]

                # Project all points to boundary
                for idx in range(11):
                    candidate[idx] = project_to_triangle(candidate[idx])

                # Calculate score using only affected triangles for efficiency
                candidate_areas = triangle_areas.copy()
                for idx, (i, j, k) in enumerate(all_triangles):
                    if i in affected_indices or j in affected_indices or k in affected_indices:
                        candidate_areas[idx] = tri_area(candidate[i], candidate[j], candidate[k])
                score = np.min(candidate_areas)
                
                if score < 1e-10:
                    continue

                if score > best_candidate_score:
                    best_candidate = candidate
                    best_candidate_score = score
                    best_candidate_areas = candidate_areas

            # IMPROVED ACCEPTANCE: Proper simulated annealing with probabilistic acceptance
            improved = False
            if best_candidate is not None:
                delta = best_candidate_score - best_score
                # Always accept improvements, sometimes accept worse solutions
                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    best = best_candidate
                    triangle_areas = best_candidate_areas
                    best_score = best_candidate_score
                    no_improve_count = 0
                    improved = True
                    
                    # Update move type success tracking
                    move_type_success[selected_move_type] += 1
                    
                    # Recalculate basin depth after improvement
                    current_basin_depth = calculate_basin_depth(best_score)
                else:
                    no_improve_count += 1
                    
                # Update move type attempts
                move_type_attempts[selected_move_type] += 1

            # ADAPTIVE COOLING: Smooth transition based on iteration progress
            if iter_idx < max_iter:
                # Smooth transition: cooling_factor = initial + (final-initial)*(iter/max_iter)**2
                progress = iter_idx / max_iter
                cooling_factor = initial_cooling_factor + (final_cooling_factor - initial_cooling_factor) * (progress ** 2)
            else:
                cooling_factor = final_cooling_factor

            T *= cooling_factor

            # STRATEGIC RESTART MECHANISM: Larger perturbations when basin depth is high
            if no_improve_count >= max_no_improve:
                if restarts < max_restarts:
                    # Restart with basin depth-aware perturbation
                    restart_candidate = best.copy()
                    
                    # BASED ON BASIN DEPTH: deeper basins need larger perturbations
                    basin_perturb_factor = max(restart_min, restart_scale * (1 + current_basin_depth/15.0))
                    restart_step = basin_perturb_factor * triangle_height
                    
                    for i in range(11):
                        angle = np.random.uniform(0, 360)
                        dx = restart_step * math.cos(math.radians(angle))
                        dy = restart_step * math.sin(math.radians(angle))
                        restart_candidate[i] += [dx, dy]
                        restart_candidate[i] = project_to_triangle(restart_candidate[i])
                    
                    # Update triangle areas for restart candidate
                    restart_areas = np.zeros(len(all_triangles))
                    for idx, (i, j, k) in enumerate(all_triangles):
                        restart_areas[idx] = tri_area(restart_candidate[i], restart_candidate[j], restart_candidate[k])
                    restart_score = np.min(restart_areas)
                    
                    if restart_score > 1e-10:
                        best = restart_candidate
                        triangle_areas = restart_areas
                        best_score = restart_score
                        
                        # Update basin depth after restart
                        current_basin_depth = calculate_basin_depth(best_score)
                    
                    restarts += 1
                    no_improve_count = 0
                    T = T0  # Reset temperature
                    # Reset cooling parameters
                    cooling_stagnation_count = 0
                else:
                    break

        return best

    return improve