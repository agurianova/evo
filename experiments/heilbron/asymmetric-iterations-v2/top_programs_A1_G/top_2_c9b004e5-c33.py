import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def project_to_triangle(point, A, B, C):
    """Project a point outside the triangle onto the nearest edge."""
    # Check if point is already inside
    if is_inside_triangle(point, A, B, C):
        return point
    
    # Calculate distances to each edge and project to nearest
    edges = [(A, B), (B, C), (C, A)]
    min_dist = float('inf')
    nearest_projection = None
    
    for (P1, P2) in edges:
        # Vector along the edge
        edge_vec = P2 - P1
        edge_len_sq = np.sum(edge_vec**2)
        
        # Vector from P1 to point
        point_vec = point - P1
        
        # Projection scalar
        t = np.dot(point_vec, edge_vec) / edge_len_sq
        t = max(0, min(1, t))  # Clamp to edge segment
        
        # Projected point
        projection = P1 + t * edge_vec
        
        # Distance squared from point to projection
        dist_sq = np.sum((point - projection)**2)
        
        if dist_sq < min_dist:
            min_dist = dist_sq
            nearest_projection = projection
    
    return nearest_projection

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    centroid = (A + B + C) / 3

    # Generate balanced hexagonal lattice (2+3+3+3 points)
    points = []
    edge_buffer = 0.05  # Prevent boundary degeneracies
    
    # Row 0: 2 points
    for col in range(2):
        u = edge_buffer + (0.9 - 2*edge_buffer) * (0 / 3)
        v = edge_buffer + (0.9 - 2*edge_buffer) * (col / 1) * (1 - u)
        w = 1 - u - v
        P = w * A + u * B + v * C
        points.append(P)
    
    # Row 1: 3 points
    for col in range(3):
        u = edge_buffer + (0.9 - 2*edge_buffer) * (1 / 3)
        v = edge_buffer + (0.9 - 2*edge_buffer) * (col / 2) * (1 - u)
        w = 1 - u - v
        P = w * A + u * B + v * C
        points.append(P)

    # Row 2: 3 points
    for col in range(3):
        u = edge_buffer + (0.9 - 2*edge_buffer) * (2 / 3)
        v = edge_buffer + (0.9 - 2*edge_buffer) * (col / 2) * (1 - u)
        w = 1 - u - v
        P = w * A + u * B + v * C
        points.append(P)

    # Row 3: 3 points
    for col in range(3):
        u = edge_buffer + (0.9 - 2*edge_buffer) * (3 / 3)
        v = edge_buffer + (0.9 - 2*edge_buffer) * (col / 2) * (1 - u)
        w = 1 - u - v
        P = w * A + u * B + v * C
        points.append(P)

    # Ensure exactly 11 points
    points = points[:11]
    points = np.array(points)

    # Apply 2 iterations of Lloyd's relaxation (repulsion)
    for _ in range(2):
        new_points = []
        for i in range(11):
            P = points[i]
            repel = np.zeros(2)
            for j in range(11):
                if i == j:
                    continue
                diff = P - points[j]
                dist_sq = np.sum(diff**2)
                if dist_sq < 1e-10:
                    repel += np.random.uniform(-0.1, 0.1, 2)
                else:
                    repel += diff / dist_sq
            new_P = P + 0.05 * repel
            if not is_inside_triangle(new_P, A, B, C):
                new_P = project_to_triangle(new_P, A, B, C)
            new_points.append(new_P)
        points = np.array(new_points)

    current_points = points
    current_min = get_smallest_triangle_area(current_points)

    # Adaptive simulated annealing parameters
    T0 = 0.1
    cooling_rate = 0.999
    step_size = 0.2
    max_iter = 15000
    T = T0

    # Adaptive control variables
    no_improve_count = 0
    plateau_threshold = 300
    step_size_decay = 0.9995
    min_step_size_decay = 0.99
    
    # Track recent improvement success rate for adaptation
    improvement_history = []
    history_window = 500

    def evaluate_direction(point_idx, direction, step):
        """Evaluate a candidate direction for improvement"""
        new_pos = current_points[point_idx] + step * direction
        if not is_inside_triangle(new_pos, A, B, C):
            new_pos = project_to_triangle(new_pos, A, B, C)
        
        new_points = current_points.copy()
        new_points[point_idx] = new_pos
        
        # Check distinctness only for affected points
        for j in range(11):
            if j == point_idx:
                continue
            if np.linalg.norm(new_points[point_idx] - new_points[j]) < 1e-5:
                return -np.inf
        
        return get_smallest_triangle_area(new_points)

    for iter_count in range(max_iter):
        # Calculate recent improvement rate
        if len(improvement_history) > 0:
            improvement_rate = sum(improvement_history) / len(improvement_history)
        else:
            improvement_rate = 0.5
        
        # Determine move type (single or two-point)
        two_point_freq = max(0.1, min(0.4, 0.25 + 0.15 * improvement_rate))
        use_two_points = random.random() < two_point_freq

        # Identify bottleneck triangles using dynamic threshold
        all_areas = []
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = 0.5 * abs(
                        (current_points[j,0]-current_points[i,0])*(current_points[k,1]-current_points[i,1]) - 
                        (current_points[j,1]-current_points[i,1])*(current_points[k,0]-current_points[i,0])
                    )
                    all_areas.append(area)
        
        # Use 0.5th percentile as bottleneck threshold (more selective than fixed threshold)
        bottleneck_threshold = np.percentile(all_areas, 0.5)
        
        smallest_triangles = []
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = 0.5 * abs(
                        (current_points[j,0]-current_points[i,0])*(current_points[k,1]-current_points[i,1]) - 
                        (current_points[j,1]-current_points[i,1])*(current_points[k,0]-current_points[i,0])
                    )
                    if area <= bottleneck_threshold:
                        smallest_triangles.append((i, j, k))
        
        candidate_points = set()
        for tri in smallest_triangles:
            candidate_points.update(tri)
        candidate_points = list(candidate_points)

        # Select points to move
        if use_two_points and len(candidate_points) >= 2:
            idx1, idx2 = random.sample(candidate_points, 2)
        else:
            idx1 = random.choice(candidate_points) if candidate_points else random.randint(0, 10)
            idx2 = None

        # Compute optimal movement directions using sampling
        directions = []
        for idx in [idx1, idx2]:
            if idx is None:
                continue
            
            # Get base direction from triangles
            base_direction = np.zeros(2)
            tri_count = 0
            
            for tri in smallest_triangles:
                if idx in tri:
                    other_indices = [i for i in tri if i != idx]
                    q, r = other_indices
                    Q, R = current_points[q], current_points[r]
                    v = R - Q
                    n_vec = np.array([-v[1], v[0]])
                    n_norm = np.linalg.norm(n_vec)
                    if n_norm > 1e-10:
                        n_vec = n_vec / n_norm
                        w = current_points[idx] - Q
                        signed_dist = np.dot(w, n_vec)
                        if abs(signed_dist) > 1e-10:
                            base_direction += n_vec * np.sign(signed_dist)
                            tri_count += 1
            
            if tri_count > 0:
                base_direction = base_direction / tri_count
            else:
                base_direction = np.random.uniform(-1, 1, 2)
                base_direction /= np.linalg.norm(base_direction)

            # Sample directions around base direction
            best_dir = None
            best_value = -np.inf
            
            # Adaptive direction sampling density
            n_directions = max(5, min(9, int(7 - 2 * improvement_rate)))
            direction_angles = np.linspace(-np.pi/4, np.pi/4, n_directions)
            
            for angle in direction_angles:
                # Rotate base direction
                rot_matrix = np.array([
                    [np.cos(angle), -np.sin(angle)],
                    [np.sin(angle), np.cos(angle)]
                ])
                candidate_dir = rot_matrix @ base_direction
                
                # Evaluate this direction
                value = evaluate_direction(idx, candidate_dir, step_size)
                if value > best_value:
                    best_value = value
                    best_dir = candidate_dir

            directions.append(best_dir if best_dir is not None else base_direction)
        
        # Generate new candidate positions
        new_positions = []
        for i, idx in enumerate([idx1, idx2]):
            if idx is None:
                continue
            new_pos = current_points[idx] + step_size * directions[i]
            if not is_inside_triangle(new_pos, A, B, C):
                new_pos = project_to_triangle(new_pos, A, B, C)
            new_positions.append((idx, new_pos))

        # Validate new configuration
        new_points = current_points.copy()
        for idx, new_pos in new_positions:
            new_points[idx] = new_pos

        # Evaluate new configuration
        new_min = get_smallest_triangle_area(new_points)
        delta = new_min - current_min

        # Simulated annealing acceptance
        accepted = False
        if delta > 0 or (T > 1e-5 and random.random() < np.exp(delta / T)):
            current_points = new_points
            current_min = new_min
            no_improve_count = 0
            accepted = True
        else:
            no_improve_count += 1

        # Update improvement history
        improvement_history.append(1 if delta > 0 else 0)
        if len(improvement_history) > history_window:
            improvement_history.pop(0)

        # Adaptive step size decay
        if no_improve_count > plateau_threshold:
            step_size_decay = max(min_step_size_decay, step_size_decay * 0.995)
            plateau_threshold = min(1000, plateau_threshold * 1.1)

        # Update parameters
        T *= cooling_rate
        step_size *= step_size_decay
        
        # Reset plateau counter if we make progress
        if delta > 0:
            no_improve_count = 0
            plateau_threshold = max(300, plateau_threshold * 0.95)

        # Early termination if step size too small
        if step_size < 1e-6 or T < 1e-6:
            break

    return current_points