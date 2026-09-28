from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import math
import scipy.spatial


def entrypoint():
    A, B, C = get_unit_triangle()
    triangle_height = np.linalg.norm((A + B) / 2 - C)
    boundary_margin = 0.01 * triangle_height

    def find_candidate_small_triangles(points):
        """Use Delaunay triangulation to efficiently identify candidate small triangles."""
        try:
            tri = scipy.spatial.Delaunay(points)
            min_triangles = []
            
            for simplex in tri.simplices:
                i, j, k = simplex
                area = 0.5 * abs(
                    points[i][0]*(points[j][1]-points[k][1]) +
                    points[j][0]*(points[k][1]-points[i][1]) +
                    points[k][0]*(points[i][1]-points[j][1])
                )
                min_triangles.append((area, (i, j, k)))
            
            # Sort by area and return indices of smallest triangles
            min_triangles.sort(key=lambda x: x[0])
            return min_triangles
        except:
            # Fallback to brute force if Delaunay fails
            min_areas = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = 0.5 * abs(points[i][0]*(points[j][1]-points[k][1]) + 
                                       points[j][0]*(points[k][1]-points[i][1]) + 
                                       points[k][0]*(points[i][1]-points[j][1]))
                        min_areas.append((area, (i, j, k)))
            min_areas.sort(key=lambda x: x[0])
            return min_areas

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)

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
        restarts = 0
        max_restarts = 3

        # Adaptive move type selection with dynamic bias
        move_type_success = [1, 1, 1]  # Start neutral
        move_type_attempts = [1, 1, 1]
        single_point_stagnation = 0
        single_point_threshold = 20  # After this many iterations without single-point improvement, shift bias

        # Track recent improvements to guide restarts
        improvement_history = []
        max_history = 100

        for iter_idx in range(max_iter):
            # Use Delaunay triangulation to find smallest triangles efficiently
            min_triangles = find_candidate_small_triangles(best)
            
            # NON-LINEAR k_val function with sigmoid scaling
            # Focuses on more triangles during critical mid-temperature phase
            k_val = max(3, min(15, int(12 / (1 + np.exp(5*(T/T0 - 0.4))))))
            min_indices_set = set()
            for idx in range(min(k_val, len(min_triangles))):
                i, j, k_idx = min_triangles[idx][1]
                min_indices_set.add(i)
                min_indices_set.add(j)
                min_indices_set.add(k_idx)
            min_indices = list(min_indices_set)

            # DYNAMIC MOVE TYPE SELECTION WITH ADAPTIVE BIAS TOWARD MULTI-POINT MOVES
            # Shift bias when single-point moves stop working
            if single_point_stagnation > single_point_threshold:
                # Gradually increase multi-point move probability
                bias_factor = 1 + 0.05 * (single_point_stagnation - single_point_threshold)
                move_type_weights = [1.0, bias_factor * 1.5, bias_factor * 2.0]
            else:
                move_type_weights = [1.0, 1.0, 1.0]
            
            # Normalize weights
            total = sum(move_type_weights)
            move_type_weights = [w/total for w in move_type_weights]
            
            # Select move type with adaptive bias
            selected_move_type = np.random.choice([0, 1, 2], p=move_type_weights)

            # ADAPTIVE ANGLE RESOLUTION based on temperature and progress
            progress_factor = 1.0 - min(0.9, no_improve_count / (max_no_improve * 0.5))
            angle_step_single = max(5, int(30 * progress_factor))
            angle_step_multi = max(10, int(60 * progress_factor))

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

            # SCALED step size by triangle_height for proper dimensionality
            step_size = math.sqrt(T) * triangle_height * 0.5
            
            # Add directional perturbations toward promising regions
            if improvement_history and np.random.rand() < 0.2:
                # Analyze recent improvements to find promising directions
                avg_improvement = np.mean(improvement_history[-min(10, len(improvement_history)):])
                if avg_improvement > 0:
                    # Create directional moves based on recent success patterns
                    for _ in range(min(3, len(min_indices))):
                        idx = np.random.choice(min_indices)
                        # Direction based on recent improvements
                        angle = np.random.randint(0, 360)
                        moves.append((idx, angle))

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

            # IMPROVED ACCEPTANCE
            improved = False
            if best_candidate is not None:
                delta = best_candidate_score - best_score
                # Always accept improvements, sometimes accept worse solutions
                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    best = best_candidate
                    best_score = best_candidate_score
                    no_improve_count = 0
                    improved = True
                    
                    # Record improvement for restart guidance
                    improvement_history.append(delta)
                    if len(improvement_history) > max_history:
                        improvement_history.pop(0)
                    
                    # Reset single-point stagnation counter on improvement
                    if selected_move_type == 0:
                        single_point_stagnation = 0
                else:
                    no_improve_count += 1
                    if selected_move_type == 0:
                        single_point_stagnation += 1

            # ADAPTIVE COOLING
            cooling_factor = 0.95 if T > T0 * 0.2 else 0.99
            T *= cooling_factor

            # ENHANCED RESTART MECHANISM WITH RECORD-TO-RECORD TRAVEL PRINCIPLES
            if no_improve_count >= max_no_improve:
                if restarts < max_restarts:
                    # Calculate plateau depth to scale perturbation
                    plateau_depth = 0
                    if improvement_history:
                        recent_improvements = improvement_history[-min(20, len(improvement_history))]
                        if recent_improvements:
                            plateau_depth = max(0, best_score - min(recent_improvements))
                    
                    # Scale perturbation based on plateau depth
                    base_perturbation = 0.3 * (1 + plateau_depth / max(1e-6, best_score))
                    
                    # Add directional perturbations based on improvement history
                    restart_candidate = best.copy()
                    for i in range(11):
                        # Base random perturbation
                        angle = np.random.uniform(0, 360)
                        magnitude = base_perturbation * (1 + 0.5 * np.random.rand())
                        dx = magnitude * math.cos(math.radians(angle))
                        dy = magnitude * math.sin(math.radians(angle))
                        
                        # Add directional bias if we have improvement history
                        if improvement_history and np.random.rand() < 0.3:
                            # Try to move in directions that previously led to improvements
                            recent_angles = []
                            for hist in improvement_history[-min(10, len(improvement_history)):]:
                                if hist > 0:
                                    recent_angles.append(np.random.uniform(0, 360))
                            
                            if recent_angles:
                                bias_angle = np.mean(recent_angles)
                                dx += 0.5 * base_perturbation * math.cos(math.radians(bias_angle))
                                dy += 0.5 * base_perturbation * math.sin(math.radians(bias_angle))

                        restart_candidate[i] += [dx, dy]
                        restart_candidate[i] = project_to_triangle(restart_candidate[i])
                    
                    restart_score = get_smallest_triangle_area(restart_candidate)
                    if restart_score > 1e-10:
                        best = restart_candidate
                        best_score = restart_score
                        # Record this as an improvement to guide future restarts
                        improvement_history.append(restart_score - best_score)
                        if len(improvement_history) > max_history:
                            improvement_history.pop(0)
                        
                    restarts += 1
                    no_improve_count = 0
                    # Reset single-point stagnation
                    single_point_stagnation = 0
                    # Reset temperature but not completely to avoid too much exploration
                    T = T0 * 0.7
                else:
                    break

        return best

    return improve