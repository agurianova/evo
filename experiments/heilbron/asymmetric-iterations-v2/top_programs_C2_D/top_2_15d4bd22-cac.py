from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import math


def entrypoint():
    A, B, C = get_unit_triangle()
    triangle_height = np.linalg.norm((A + B) / 2 - C)
    triangle_base = np.linalg.norm(B - A)

    # NEW: CONFIGURATION ANALYSIS FUNCTION
    def analyze_configuration(points):
        # Calculate current min area
        current_min_area = get_smallest_triangle_area(points)
        
        # Calculate point density (average distance to nearest neighbor)
        distances = []
        for i in range(11):
            min_dist = float('inf')
            for j in range(11):
                if i != j:
                    dist = np.linalg.norm(points[i] - points[j])
                    min_dist = min(min_dist, dist)
            distances.append(min_dist)
        avg_nn_dist = np.mean(distances)
        point_density = 1.0 / (avg_nn_dist + 1e-10)
        
        # Calculate boundary proximity
        edges = [(A, B), (B, C), (C, A)]
        boundary_distances = []
        for point in points:
            min_dist = float('inf')
            for (p1, p2) in edges:
                v = p2 - p1
                w = point - p1
                c1 = np.dot(w, v)
                c2 = np.dot(v, v)
                b = 0 if c2 == 0 else c1 / c2
                b = max(0.0, min(1.0, b))
                proj = p1 + b * v
                dist = np.linalg.norm(point - proj)
                min_dist = min(min_dist, dist)
            boundary_distances.append(min_dist)
        avg_boundary_dist = np.mean(boundary_distances)
        boundary_proximity = avg_boundary_dist / (0.5 * triangle_height)
        
        return {
            'current_min_area': current_min_area,
            'point_density': point_density,
            'boundary_proximity': boundary_proximity,
            'avg_nn_dist': avg_nn_dist
        }

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

        # CONFIG ANALYSIS FOR ADAPTIVE INITIALIZATION
        config_analysis = analyze_configuration(points)
        current_min_area = config_analysis['current_min_area']
        point_density = config_analysis['point_density']
        boundary_proximity = config_analysis['boundary_proximity']
        avg_nn_dist = config_analysis['avg_nn_dist']

        # ADAPTIVE PARAMETER INITIALIZATION BASED ON CONFIG ANALYSIS
        # T0 scales with current min_area (smaller min_area = higher initial temp for more exploration)
        T0 = max(0.008, 0.02 * (current_min_area / 0.0365) ** 0.5)
        T = T0
        
        # k_val parameters adapt to point density
        k_base = max(8, min(20, 15 * (1.0 + 0.5 * (point_density / 10.0))))
        k_exponent = max(0.3, min(0.8, 0.5 * (1.0 + 0.5 * boundary_proximity)))

        max_iter = 500
        max_no_improve = 50
        no_improve_count = 0
        restarts = 0
        max_restarts = 2

        # ADAPTIVE MOVE TYPE SELECTION WITH EMA AND MINIMUM EXPLORATION
        # Initialize move type weights based on point distribution
        if point_density > 8.0:
            # Dense configurations benefit more from multi-point moves
            move_type_ema = [0.2, 0.4, 0.4]
        else:
            # More uniform distributions can use more single-point moves
            move_type_ema = [0.4, 0.3, 0.3]
        
        ema_alpha = 0.2  # EMA smoothing factor
        min_explore_rate = 0.1  # Ensure at least 10% exploration for each move type

        # Track recent directions for restart diversity
        recent_directions = {}
        direction_decay = 0.9

        for iter_idx in range(max_iter):
            # DYNAMIC BOUNDARY MARGIN BASED ON TEMPERATURE AND BOUNDARY PROXIMITY
            # Coefficients now adapt to configuration
            margin_base = 0.001 * triangle_height * (1.0 + 0.5 * boundary_proximity)
            margin_scale = 0.019 * triangle_height * (1.0 + 0.3 * (1.0 - boundary_proximity))
            boundary_margin = margin_base + margin_scale * (T / T0)

            # Find smallest triangles and get union of points
            min_areas = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = tri_area(best[i], best[j], best[k])
                        min_areas.append((area, (i, j, k)))
            min_areas.sort(key=lambda x: x[0])
            
            # ADAPTIVE k_val CALCULATION BASED ON CONFIG ANALYSIS
            k_val = max(3, int(k_base * (T / T0) ** k_exponent))
            min_indices_set = set()
            for idx in range(min(k_val, len(min_areas))):
                i, j, k_idx = min_areas[idx][1]
                min_indices_set.add(i)
                min_indices_set.add(j)
                min_indices_set.add(k_idx)
            min_indices = list(min_indices_set)

            # ADAPTIVE MOVE TYPE SELECTION WITH EMA
            total_ema = sum(move_type_ema)
            if total_ema > 0:
                move_type_weights = [(w / total_ema) * (1 - 3 * min_explore_rate) + min_explore_rate for w in move_type_ema]
            else:
                move_type_weights = [1/3, 1/3, 1/3]
            
            selected_move_type = np.random.choice([0, 1, 2], p=move_type_weights)

            # CONTINUOUS ANGLE RESOLUTION BASED ON TEMPERATURE
            # Replaced binary threshold with continuous function
            angle_progress = T / T0
            base_angle_step = 30 * (0.5 + 0.5 * angle_progress)  # Smoother transition
            progress_factor = 1.0 + (max_no_improve - no_improve_count) / max_no_improve
            angle_step_single = max(5, int(base_angle_step / progress_factor))
            angle_step_multi = max(10, int(2 * base_angle_step / progress_factor))

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

            # DYNAMIC non-involved exploration rate
            non_involved_rate = 0.05 + 0.2 * (T / T0) * (no_improve_count / max_no_improve)
            if np.random.rand() < non_involved_rate and len(min_indices) < 11:
                non_involved = [i for i in range(11) if i not in min_indices]
                if non_involved:
                    idx = np.random.choice(non_involved)
                    angle = np.random.randint(0, 360)
                    moves.append((idx, angle))

            # ADAPTIVE step size based on recent success
            step_size_factor = 0.4 * (1.0 + 0.5 * (max_no_improve - no_improve_count) / max_no_improve)
            step_size = math.sqrt(T) * triangle_height * step_size_factor
            
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
                    # Track direction for restart diversity
                    if idx not in recent_directions:
                        recent_directions[idx] = angle
                    else:
                        recent_directions[idx] = direction_decay * recent_directions[idx] + (1 - direction_decay) * angle
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
                    
                    # Update EMA with success
                    move_type_ema[selected_move_type] = ema_alpha * 1.0 + (1 - ema_alpha) * move_type_ema[selected_move_type]
                else:
                    no_improve_count += 1
                    # Update EMA with failure (less impact)
                    move_type_ema[selected_move_type] = ema_alpha * 0.0 + (1 - ema_alpha) * move_type_ema[selected_move_type]

            # ADAPTIVE COOLING: Based on actual improvement rate
            cooling_factor = 0.95 if no_improve_count < max_no_improve / 2 else 0.99
            T *= cooling_factor

            # ENHANCED RESTART MECHANISM WITH STAGNATION-AWARE PERTURBATION
            if no_improve_count >= max_no_improve:
                if restarts < max_restarts:
                    # NEW: Adaptive restart step based on plateau metrics
                    plateau_length = no_improve_count - max_no_improve
                    improvement_history = max(0.01, best_score / (current_min_area + 1e-10))
                    # Calculate restart coefficient based on plateau metrics
                    restart_coefficient = 0.3 * (1.0 + 0.5 * plateau_length / 20.0) * (2.0 - improvement_history)
                    
                    # Restart with perturbation based on stagnation level
                    restart_candidate = best.copy()
                    stagnation_factor = 1.0 + (no_improve_count - max_no_improve) / 10.0
                    restart_step = restart_coefficient * stagnation_factor * triangle_height
                    
                    for i in range(11):
                        angle = np.random.uniform(0, 360)
                        # Add directional component to push away from recent moves
                        if i in recent_directions:
                            angle = (angle + 180 + recent_directions[i]) % 360
                        
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
                    T = T0 * (1.1 ** restarts)  # Slightly higher temperature for subsequent restarts
                    # Reset EMA for move types after restart
                    if point_density > 8.0:
                        move_type_ema = [0.2, 0.4, 0.4]
                    else:
                        move_type_ema = [0.4, 0.3, 0.3]
                    recent_directions = {}
                else:
                    break

        return best

    return improve