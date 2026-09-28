from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import math


def entrypoint():
    A, B, C = get_unit_triangle()
    triangle_height = np.linalg.norm((A + B) / 2 - C)

    def calculate_basin_depth(points, min_area, threshold=0.05):
        """Calculate how many triangles are within threshold of the minimum area."""
        areas = []
        n = len(points)
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        points[i][0]*(points[j][1]-points[k][1]) +
                        points[j][0]*(points[k][1]-points[i][1]) +
                        points[k][0]*(points[i][1]-points[j][1])
                    )
                    areas.append(area)
        areas.sort()
        # Count triangles within threshold of minimum
        count = 0
        for area in areas:
            if area <= min_area * (1 + threshold):
                count += 1
            else:
                break
        return count

    def calculate_local_density(points, idx):
        """Calculate average distance to nearest neighbors for a point."""
        distances = []
        for j in range(len(points)):
            if j != idx:
                dist = np.linalg.norm(points[idx] - points[j])
                distances.append(dist)
        distances.sort()
        # Use average of 3 nearest neighbors
        return np.mean(distances[:3]) if len(distances) >= 3 else distances[0] if distances else 0.1

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)

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
                
                # Adaptive boundary margin based on local density
                # More crowded areas can have points closer to boundaries
                idx = -1
                for i in range(len(best)):
                    if np.allclose(best[i], point, atol=1e-5):
                        idx = i
                        break
                
                density_factor = 0.5
                if idx != -1:
                    density = calculate_local_density(best, idx)
                    # Normalize density to [0.5, 1.5] range
                    density_factor = max(0.5, min(1.5, density / (0.1 * triangle_height)))
                
                # Minimum margin of 0.005*triangle_height to prevent degeneracy
                boundary_margin = max(0.005 * triangle_height, 0.01 * triangle_height * density_factor)
                
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
        # Adaptive cooling: start aggressive then slow down
        initial_cooling_factor = 0.95
        final_cooling_factor = 0.99
        cooling_stagnation_threshold = 20
        cooling_stagnation_count = 0
        restarts = 0
        max_restarts = 2

        # Move type success tracking for dynamic weighting
        # Neutral initialization instead of single-point bias
        move_type_success = [0.33, 0.33, 0.34]  # Changed from [0.6, 0.3, 0.1] to neutral weights
        move_type_attempts = [1, 1, 1]
        
        # Basin depth tracking
        basin_depth = calculate_basin_depth(best, best_score)
        basin_depth_history = [basin_depth]
        
        # ADDED adaptive threshold factor based on current solution quality
        adaptive_threshold_factor = max(0.6, min(1.4, 0.0365 / best_score))
        basin_depth_threshold = 0.05 * adaptive_threshold_factor

        for iter_idx in range(max_iter):
            # Recalculate basin depth periodically
            if iter_idx % 10 == 0:
                # ADDED adaptive threshold based on current solution quality
                adaptive_threshold_factor = max(0.6, min(1.4, 0.0365 / best_score))
                basin_depth_threshold = 0.05 * adaptive_threshold_factor
                basin_depth = calculate_basin_depth(best, best_score, basin_depth_threshold)
                basin_depth_history.append(basin_depth)

            # Find smallest triangles and get union of points
            min_areas = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = tri_area(best[i], best[j], best[k])
                        min_areas.append((area, (i, j, k)))
            min_areas.sort(key=lambda x: x[0])
            
            # Basin depth-adaptive k_val
            # Focus on more triangles when basin is deep
            k_val = max(3, min(15, int(1.5 * basin_depth)))
            
            min_indices_set = set()
            for idx in range(min(k_val, len(min_areas))):
                i, j, k_idx = min_areas[idx][1]
                min_indices_set.add(i)
                min_indices_set.add(j)
                min_indices_set.add(k_idx)
            min_indices = list(min_indices_set)

            # DYNAMIC MOVE TYPE SELECTION BASED ON BASIN DEPTH
            # Increase multi-point move probability when basin depth is high
            basin_depth_factor = max(0.5, min(2.0, basin_depth / 5.0))
            base_weights = [0.33, 0.33, 0.34]
            # When basin is deep, favor multi-point moves
            if basin_depth > 5:
                base_weights = [0.2, 0.35, 0.45]
            elif basin_depth > 3:
                base_weights = [0.25, 0.35, 0.4]
            
            # ADDED proper success rate calculation with time decay
            decay_factor = 0.98
            for i in range(3):
                move_type_success[i] = (move_type_success[i] * decay_factor) + 0.01
                move_type_attempts[i] = (move_type_attempts[i] * decay_factor) + 0.01
            
            # Calculate success rates
            success_rates = [
                move_type_success[0] / max(1e-5, move_type_attempts[0]),
                move_type_success[1] / max(1e-5, move_type_attempts[1]),
                move_type_success[2] / max(1e-5, move_type_attempts[2])
            ]
            
            # Normalize success rates for weighting
            total_success = sum(success_rates)
            if total_success > 0:
                move_type_weights = [sr / total_success for sr in success_rates]
            else:
                move_type_weights = base_weights

            selected_move_type = np.random.choice([0, 1, 2], p=move_type_weights)

            # ADAPTIVE ANGLE RESOLUTION: finer steps at low temperatures
            angle_step_single = 30 if T > 0.005 else 10
            angle_step_multi = 60 if T > 0.005 else 20

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
                
                if len(move) == 2:  # Single-point move
                    idx, angle = move
                    dx = step_size * math.cos(math.radians(angle))
                    dy = step_size * math.sin(math.radians(angle))
                    candidate[idx] += [dx, dy]
                elif len(move) == 4:  # Two-point move
                    i, a1, j, a2 = move
                    dx1 = step_size * math.cos(math.radians(a1))
                    dy1 = step_size * math.sin(math.radians(a1))
                    dx2 = step_size * math.cos(math.radians(a2))
                    dy2 = step_size * math.sin(math.radians(a2))
                    candidate[i] += [dx1, dy1]
                    candidate[j] += [dx2, dy2]
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

            # ADDED continuous cooling factor based on improvement rate
            improvement_window = 20
            if len(basin_depth_history) > improvement_window:
                # Calculate improvement rate over recent history
                recent_improvements = []
                for i in range(len(basin_depth_history)-improvement_window, len(basin_depth_history)-1):
                    # Positive when basin depth is decreasing (improving)
                    improvement = basin_depth_history[i] - basin_depth_history[i+1]
                    recent_improvements.append(improvement)
                
                avg_improvement = sum(recent_improvements) / len(recent_improvements)
                
                # Adjust cooling factor based on improvement rate
                if avg_improvement > 0.1:  # Good improvement
                    cooling_factor = 0.96
                elif avg_improvement > 0:  # Some improvement
                    cooling_factor = 0.97
                else:  # Stagnant
                    cooling_factor = 0.985
            else:
                cooling_factor = initial_cooling_factor

            T *= cooling_factor

            # IMPROVED RESTART MECHANISM: Strategic basin-aware perturbations
            if no_improve_count >= max_no_improve:
                if restarts < max_restarts:
                    # Restart with strategic perturbation based on basin depth
                    restart_candidate = best.copy()
                    
                    # Identify bottleneck points (those in many small triangles)
                    point_usage = [0] * 11
                    for i in range(len(min_areas)):
                        if min_areas[i][0] <= best_score * (1 + basin_depth_threshold):
                            for idx in min_areas[i][1]:
                                point_usage[idx] += 1
                        else:
                            break
                    
                    # Normalize usage counts
                    max_usage = max(point_usage)
                    if max_usage > 0:
                        point_usage = [u / max_usage for u in point_usage]
                    
                    # ADDED basin-depth-dependent restart scaling
                    restart_step_base = 0.3 + 0.4 * min(1.0, basin_depth / 15.0)
                    
                    # Larger perturbations for high-usage points
                    for i in range(11):
                        # Scale perturbation by point usage (bottleneck points get larger moves)
                        perturb_scale = 0.5 + 1.5 * point_usage[i]
                        angle = np.random.uniform(0, 360)
                        dx = restart_step_base * perturb_scale * math.cos(math.radians(angle))
                        dy = restart_step_base * perturb_scale * math.sin(math.radians(angle))
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
                    cooling_stagnation_count = 0
                    
                    # Recalculate basin depth after restart
                    basin_depth = calculate_basin_depth(best, best_score)
                else:
                    break

        return best

    return improve