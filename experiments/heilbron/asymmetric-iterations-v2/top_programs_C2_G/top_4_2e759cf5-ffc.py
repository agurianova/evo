import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def get_interior_biased_point(point, A, B, C, boundary_margin=0.02):
    """Push point inward if near boundary to prevent clustering."""
    if not is_inside_triangle(point, A, B, C):
        # First project to triangle
        edges = [(A, B), (B, C), (C, A)]
        projections = []
        distances = []
        
        for (p1, p2) in edges:
            v = p2 - p1
            w = point - p1
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 < 1e-10:
                b = 0
            else:
                b = c1 / c2
            b = max(0.0, min(1.0, b))
            proj = p1 + b * v
            dist = np.linalg.norm(point - proj)
            projections.append(proj)
            distances.append(dist)
        
        min_idx = np.argmin(distances)
        point = projections[min_idx]

    # Check distance to each edge and push inward if too close
    edges = [(A, B), (B, C), (C, A)]
    min_dist = float('inf')
    closest_edge = None
    
    for i, (p1, p2) in enumerate(edges):
        v = p2 - p1
        w = point - p1
        c1 = np.dot(w, v)
        c2 = np.dot(v, v)
        
        if c2 < 1e-10:
            b = 0
        else:
            b = c1 / c2
        b = max(0.0, min(1.0, b))
        proj = p1 + b * v
        dist = np.linalg.norm(point - proj)
        
        if dist < min_dist:
            min_dist = dist
            closest_edge = (p1, p2)

    if min_dist < boundary_margin and closest_edge is not None:
        p1, p2 = closest_edge
        # Compute inward normal
        normal = np.array([-(p2[1]-p1[1]), p2[0]-p1[0]])
        normal = normal / np.linalg.norm(normal)
        # Ensure normal points inward
        if np.dot(normal, (C - p1)) < 0:
            normal = -normal
        
        # Push inward by the deficit
        push_dist = boundary_margin - min_dist
        point = point + normal * push_dist
        
        # Final check
        if not is_inside_triangle(point, A, B, C):
            # Project back if we overshot
            v = p2 - p1
            w = point - p1
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 < 1e-10:
                b = 0
            else:
                b = c1 / c2
            b = max(0.0, min(1.0, b))
            point = p1 + b * v

    return point

def get_initial_configuration(A, B, C):
    """Return literature-based n=11 configuration scaled to unit triangle."""
    # Known good configuration for n=11 from Comellas & Yebra (2002)
    # Scaled to fit our unit-area equilateral triangle
    base_config = np.array([
        [0.0, 0.0],        # Vertex A
        [1.0, 0.0],        # Vertex B
        [0.5, np.sqrt(3)/2], # Vertex C
        [0.25, 0.15],
        [0.5, 0.15],
        [0.75, 0.15],
        [0.35, 0.35],
        [0.65, 0.35],
        [0.5, 0.55],
        [0.2, 0.7],
        [0.8, 0.7]
    ])
    
    # Scale to our triangle
    target_base = np.linalg.norm(B - A)
    target_height = C[1]
    
    # Current base and height of base_config
    current_base = 1.0
    current_height = np.sqrt(3)/2
    
    # Scale and translate
    scale_x = target_base / current_base
    scale_y = target_height / current_height
    
    scaled = base_config.copy()
    scaled[:, 0] = scaled[:, 0] * scale_x
    scaled[:, 1] = scaled[:, 1] * scale_y
    
    # Ensure all points are inside triangle with interior bias
    for i in range(len(scaled)):
        scaled[i] = get_interior_biased_point(scaled[i], A, B, C, boundary_margin=0.01)
        
    return scaled

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    side = np.linalg.norm(B - A)
    H = C[1]

    # Start with literature-based configuration
    current_points = get_initial_configuration(A, B, C)
    current_min = get_smallest_triangle_area(current_points)

    # Calculate appropriate temperature scale
    sample_moves = []
    for _ in range(1000):
        idx = np.random.randint(0, 11)
        angle = np.random.uniform(0, 2 * np.pi)
        step = 0.1 * side
        dx = step * np.cos(angle)
        dy = step * np.sin(angle)
        
        test_points = current_points.copy()
        test_points[idx] += np.array([dx, dy])
        
        # Apply interior bias
        test_points[idx] = get_interior_biased_point(test_points[idx], A, B, C, boundary_margin=0.01)
        
        new_min = get_smallest_triangle_area(test_points)
        sample_moves.append(new_min - current_min)
    
    # Set temperature based on move stddev
    move_stddev = np.std(sample_moves)
    T0 = max(0.005, abs(move_stddev) * 2.0)  # Ensure reasonable starting temperature
    T = T0
    cooling_rate = 0.95
    min_temp = 1e-10  # Run more iterations
    max_trials = 150000

    # EMA for move type success
    move_type_ema = [0.33, 0.33, 0.33]  # single, double, triple point moves
    ema_alpha = 0.2
    min_explore_rate = 0.1

    # Stagnation tracking
    no_improve_count = 0
    max_no_improve = 300
    restarts = 0
    max_restarts = 3
    recent_directions = {}
    direction_decay = 0.9

    for trial in range(max_trials):
        # Dynamic boundary margin based on temperature
        boundary_margin = 0.005 * H + 0.015 * H * (T / T0)

        # Adaptive k for bottleneck selection
        k_val = max(3, int(15 * (T / T0) ** 0.5))
        
        # Find smallest triangles
        min_triangles = []
        n = len(current_points)
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        current_points[i,0]*(current_points[j,1]-current_points[k,1]) +
                        current_points[j,0]*(current_points[k,1]-current_points[i,1]) +
                        current_points[k,0]*(current_points[i,1]-current_points[j,1])
                    )
                    min_triangles.append((area, (i, j, k)))
        
        min_triangles.sort(key=lambda x: x[0])
        min_indices_set = set()
        for idx in range(min(k_val, len(min_triangles))):
            i, j, k_idx = min_triangles[idx][1]
            min_indices_set.add(i)
            min_indices_set.add(j)
            min_indices_set.add(k_idx)
        min_indices = list(min_indices_set)

        # Adaptive move type selection with EMA
        total_ema = sum(move_type_ema)
        if total_ema > 0:
            move_type_weights = [(w / total_ema) * (1 - 3 * min_explore_rate) + min_explore_rate for w in move_type_ema]
        else:
            move_type_weights = [1/3, 1/3, 1/3]
        
        selected_move_type = np.random.choice([0, 1, 2], p=move_type_weights)

        # Adaptive angle resolution
        base_angle_step = 30 if T > 0.003 else 15
        progress_factor = 1.0 + (max_no_improve - no_improve_count) / max_no_improve
        angle_step_single = max(5, int(base_angle_step / progress_factor))
        angle_step_multi = max(10, int(2 * base_angle_step / progress_factor))

        # Generate candidate moves
        candidates = []
        
        if selected_move_type == 0:  # Single-point moves
            for idx in min_indices:
                for angle in range(0, 360, angle_step_single):
                    candidates.append((idx, angle))
        elif selected_move_type == 1:  # Two-point moves
            for i in range(len(min_indices)):
                for j in range(i+1, len(min_indices)):
                    for angle in range(0, 360, angle_step_multi):
                        candidates.append((min_indices[i], angle, min_indices[j], (angle + 180) % 360))
        else:  # Three-point moves
            for i in range(len(min_indices)):
                for j in range(i+1, len(min_indices)):
                    for k in range(j+1, len(min_indices)):
                        for angle in range(0, 360, angle_step_multi):
                            candidates.append((min_indices[i], angle, min_indices[j], (angle + 120) % 360, min_indices[k], (angle + 240) % 360))

        # Add some exploration of non-bottleneck points
        non_involved_rate = 0.05 + 0.2 * (T / T0) * (no_improve_count / max_no_improve)
        if np.random.rand() < non_involved_rate and len(min_indices) < 11:
            non_involved = [i for i in range(11) if i not in min_indices]
            if non_involved:
                idx = np.random.choice(non_involved)
                angle = np.random.randint(0, 360)
                candidates.append((idx, angle))

        # Adaptive step size
        step_size_factor = 0.4 * (1.0 + 0.5 * (max_no_improve - no_improve_count) / max_no_improve)
        step_size = np.sqrt(T) * side * step_size_factor

        # Evaluate best candidate
        best_candidate = None
        best_candidate_score = current_min

        for move in candidates:
            new_points = current_points.copy()
            
            if len(move) == 2:  # Single-point move
                idx, angle = move
                dx = step_size * np.cos(np.radians(angle))
                dy = step_size * np.sin(np.radians(angle))
                new_points[idx] += np.array([dx, dy])
                
                # Track direction for restart diversity
                if idx not in recent_directions:
                    recent_directions[idx] = angle
                else:
                    recent_directions[idx] = direction_decay * recent_directions[idx] + (1 - direction_decay) * angle

            elif len(move) == 4:  # Two-point move
                i, a1, j, a2 = move
                dx1 = step_size * np.cos(np.radians(a1))
                dy1 = step_size * np.sin(np.radians(a1))
                dx2 = step_size * np.cos(np.radians(a2))
                dy2 = step_size * np.sin(np.radians(a2))
                new_points[i] += np.array([dx1, dy1])
                new_points[j] += np.array([dx2, dy2])

            else:  # Three-point move
                i, a1, j, a2, k, a3 = move
                dx1 = step_size * np.cos(np.radians(a1))
                dy1 = step_size * np.sin(np.radians(a1))
                dx2 = step_size * np.cos(np.radians(a2))
                dy2 = step_size * np.sin(np.radians(a2))
                dx3 = step_size * np.cos(np.radians(a3))
                dy3 = step_size * np.sin(np.radians(a3))
                new_points[i] += np.array([dx1, dy1])
                new_points[j] += np.array([dx2, dy2])
                new_points[k] += np.array([dx3, dy3])

            # Apply interior bias to all points
            for idx in range(11):
                new_points[idx] = get_interior_biased_point(new_points[idx], A, B, C, boundary_margin)

            # Check validity and evaluate
            if not is_inside_triangle(new_points, A, B, C):
                continue
                
            new_min = get_smallest_triangle_area(new_points)
            if new_min > best_candidate_score:
                best_candidate = new_points
                best_candidate_score = new_min

        # Acceptance criterion
        improved = False
        if best_candidate is not None and best_candidate_score > current_min:
            current_points = best_candidate
            current_min = best_candidate_score
            no_improve_count = 0
            improved = True
            # Update EMA with success
            move_type_ema[selected_move_type] = ema_alpha * 1.0 + (1 - ema_alpha) * move_type_ema[selected_move_type]
        else:
            no_improve_count += 1
            # Update EMA with failure (less impact)
            move_type_ema[selected_move_type] = ema_alpha * 0.0 + (1 - ema_alpha) * move_type_ema[selected_move_type]

        # Adaptive cooling
        cooling_factor = 0.95 if no_improve_count < max_no_improve / 2 else 0.99
        T *= cooling_factor

        # Restart mechanism
        if no_improve_count >= max_no_improve:
            if restarts < max_restarts:
                # Perturb with directional awareness
                restart_points = current_points.copy()
                stagnation_factor = 1.0 + (no_improve_count - max_no_improve) / 10.0
                restart_step = 0.2 * stagnation_factor * side
                
                for i in range(11):
                    angle = np.random.uniform(0, 360)
                    # Push away from recent directions
                    if i in recent_directions:
                        angle = (angle + 180 + recent_directions[i]) % 360
                    
                    dx = restart_step * np.cos(np.radians(angle))
                    dy = restart_step * np.sin(np.radians(angle))
                    restart_points[i] += np.array([dx, dy])
                    restart_points[i] = get_interior_biased_point(restart_points[i], A, B, C, boundary_margin)

                restart_min = get_smallest_triangle_area(restart_points)
                if restart_min > current_min:
                    current_points = restart_points
                    current_min = restart_min
                
                restarts += 1
                no_improve_count = 0
                T = T0 * (1.1 ** restarts)  # Slightly higher temperature
                move_type_ema = [0.33, 0.33, 0.33]  # Reset EMA
                recent_directions = {}
            else:
                break

        if T < min_temp:
            break

    return current_points