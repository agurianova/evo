import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle


def clip_to_triangle(point, A, B, C):
    """Clip a point to the triangle boundary if it's outside."""
    if is_inside_triangle(point, A, B, C):
        return point
    
    # Check each edge and find closest point on boundary
    edges = [(A, B), (B, C), (C, A)]
    min_dist = float('inf')
    closest_point = point
    
    for (p1, p2) in edges:
        # Vector from p1 to p2
        edge_vec = p2 - p1
        # Vector from p1 to point
        point_vec = point - p1
        
        # Project point_vec onto edge_vec
        edge_len_sq = np.dot(edge_vec, edge_vec)
        if edge_len_sq < 1e-10:  # Skip near-zero length edges
            continue
            
        t = max(0, min(1, np.dot(point_vec, edge_vec) / edge_len_sq))
        projection = p1 + t * edge_vec
        
        # Calculate distance squared
        dist_sq = np.sum((point - projection)**2)
        if dist_sq < min_dist:
            min_dist = dist_sq
            closest_point = projection
    
    return closest_point

def calculate_area_gradient(point_idx, triangle_idx, points):
    """Calculate gradient of triangle area with respect to point position"""
    i, j, k = triangle_idx
    if point_idx == i:
        # Gradient with respect to point i
        return np.array([
            0.5 * (points[k, 1] - points[j, 1]),
            0.5 * (points[j, 0] - points[k, 0])
        ])
    elif point_idx == j:
        # Gradient with respect to point j
        return np.array([
            0.5 * (points[i, 1] - points[k, 1]),
            0.5 * (points[k, 0] - points[i, 0])
        ])
    else:  # point_idx == k
        # Gradient with respect to point k
        return np.array([
            0.5 * (points[j, 1] - points[i, 1]),
            0.5 * (points[i, 0] - points[j, 0])
        ])

def generate_initial_points(row_counts, A, B, C):
    points = []
    total_rows = len(row_counts)
    for row in range(total_rows):
        num_points = row_counts[row]
        v = (row + 0.5) / total_rows
        for i in range(num_points):
            u = (i + 0.5) / num_points * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            
            # Symmetry-breaking noise with boundary safety
            noise = np.random.uniform(-0.01, 0.01, size=2)
            P_noisy = P + noise
            P_clipped = clip_to_triangle(P_noisy, A, B, C)
            points.append(P_clipped)

    return np.array(points)

def optimize_configuration(points, A, B, C):
    np.random.seed(42)
    current_points = points.copy()
    current_min_area = get_smallest_triangle_area(current_points)

    # Enhanced simulated annealing parameters
    total_iterations = 30000
    initial_temp = 0.3
    cooling_factor = 0.9995
    min_step = 0.005
    max_step = 0.06
    step_size = max_step
    
    # Adaptive step_size tracking
    acceptance_window = 100
    acceptance_count = 0
    stagnation_count = 0
    max_stagnation = 500

    for iteration in range(total_iterations):
        # Temperature schedule
        temp = initial_temp * (cooling_factor ** iteration)

        # Identify critical points (involved in minimal-area triangles)
        critical_points = set()
        min_area = float('inf')
        min_triangles = []
        
        # First find the actual minimum area and record minimal triangles
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = 0.5 * abs(
                        (current_points[j,0] - current_points[i,0]) * (current_points[k,1] - current_points[i,1]) -
                        (current_points[k,0] - current_points[i,0]) * (current_points[j,1] - current_points[i,1])
                    )
                    if area < min_area:
                        min_area = area
                        min_triangles = [(i, j, k)]
                    elif abs(area - min_area) < 1e-10:
                        min_triangles.append((i, j, k))
        
        # Now identify all points in minimal triangles
        for tri in min_triangles:
            critical_points.update(tri)

        # Large jump mechanism (1% chance to escape local optima)
        if np.random.rand() < 0.01:
            large_jump_size = max_step * 3  # 3x normal max step
            if critical_points:
                idx = np.random.choice(list(critical_points))
            else:
                idx = np.random.randint(0, 11)
            dx = np.random.uniform(-large_jump_size, large_jump_size)
            dy = np.random.uniform(-large_jump_size, large_jump_size)
            candidate = current_points.copy()
            candidate[idx] += [dx, dy]
            candidate[idx] = clip_to_triangle(candidate[idx], A, B, C)
            # Check for duplicates
            duplicate = False
            for i in range(11):
                for j in range(i+1, 11):
                    if np.linalg.norm(candidate[i] - candidate[j]) < 1e-8:
                        duplicate = True
                        break
                if duplicate:
                    break
            if duplicate:
                continue  # Skip this candidate if duplicates created
            
            # Evaluate candidate
            new_min_area = get_smallest_triangle_area(candidate)
            delta = new_min_area - current_min_area

            # Acceptance criterion (simulated annealing)
            accept = False
            if delta > 0:
                accept = True
            elif temp > 0 and np.random.rand() < np.exp(delta / temp):
                accept = True
                
            if accept:
                current_points = candidate
                current_min_area = new_min_area
                acceptance_count += 1
                stagnation_count = 0
            else:
                stagnation_count += 1
            continue

        # Gradient-based move (20% chance for targeted improvement)
        if np.random.rand() < 0.2 and min_triangles:
            # Pick a random minimal triangle
            tri_idx = np.random.choice(len(min_triangles))
            i, j, k = min_triangles[tri_idx]
            
            # Pick a random point in this triangle to move
            point_idx = np.random.choice([i, j, k])
            
            # Calculate gradient
            grad = calculate_area_gradient(point_idx, (i, j, k), current_points)
            
            # Normalize and scale
            grad_norm = np.linalg.norm(grad)
            if grad_norm > 1e-10:
                grad = grad / grad_norm * step_size
                
                # Add some randomness to avoid getting stuck
                random_dir = np.random.uniform(-0.1, 0.1, size=2)
                grad = grad + random_dir
                
                candidate = current_points.copy()
                candidate[point_idx] += grad
                candidate[point_idx] = clip_to_triangle(candidate[point_idx], A, B, C)
                
                # Check for duplicates
                duplicate = False
                for i in range(11):
                    for j in range(i+1, 11):
                        if np.linalg.norm(candidate[i] - candidate[j]) < 1e-8:
                            duplicate = True
                            break
                    if duplicate:
                        break
                if duplicate:
                    continue  # Skip this candidate if duplicates created
                
                # Evaluate candidate
                new_min_area = get_smallest_triangle_area(candidate)
                delta = new_min_area - current_min_area

                # Acceptance criterion (simulated annealing)
                accept = False
                if delta > 0:
                    accept = True
                elif temp > 0 and np.random.rand() < np.exp(delta / temp):
                    accept = True
                    
                if accept:
                    current_points = candidate
                    current_min_area = new_min_area
                    acceptance_count += 1
                    stagnation_count = 0
                else:
                    stagnation_count += 1
                continue

        # Multi-point perturbation (15% chance)
        if np.random.rand() < 0.15:
            num_moves = np.random.choice([2, 3])
            # Prioritize critical points for multi-move
            if critical_points:
                indices = list(critical_points)
                np.random.shuffle(indices)
                selected_indices = indices[:num_moves]
                if len(selected_indices) < num_moves:
                    non_critical = [i for i in range(11) if i not in critical_points]
                    np.random.shuffle(non_critical)
                    selected_indices += non_critical[:num_moves - len(selected_indices)]
            else:
                selected_indices = np.random.choice(11, num_moves, replace=False).tolist()

            candidate = current_points.copy()
            step_scale = 1.0 / num_moves  # Scale step for coordinated moves
            for idx in selected_indices:
                dx = np.random.uniform(-step_size * step_scale, step_size * step_scale)
                dy = np.random.uniform(-step_size * step_scale, step_size * step_scale)
                candidate[idx] += [dx, dy]
                # Clip to boundary instead of rejecting
                candidate[idx] = clip_to_triangle(candidate[idx], A, B, C)
        else:
            # Single-point move (prioritize critical points)
            if critical_points:
                idx = np.random.choice(list(critical_points))
            else:
                idx = np.random.randint(0, 11)

            dx = np.random.uniform(-step_size, step_size)
            dy = np.random.uniform(-step_size, step_size)
            candidate = current_points.copy()
            candidate[idx] += [dx, dy]
            # Clip to boundary instead of rejecting
            candidate[idx] = clip_to_triangle(candidate[idx], A, B, C)

        # Check for duplicates (more efficient)
        duplicate = False
        for i in range(11):
            for j in range(i+1, 11):
                if np.linalg.norm(candidate[i] - candidate[j]) < 1e-8:
                    duplicate = True
                    break
            if duplicate:
                break
        if duplicate:
            # Instead of rejecting, make a small adjustment
            if critical_points:
                idx = np.random.choice(list(critical_points))
            else:
                idx = np.random.randint(0, 11)
            candidate[idx] += np.random.uniform(-1e-5, 1e-5, size=2)
            candidate[idx] = clip_to_triangle(candidate[idx], A, B, C)

        # Evaluate candidate
        new_min_area = get_smallest_triangle_area(candidate)
        delta = new_min_area - current_min_area

        # Acceptance criterion (simulated annealing)
        accept = False
        if delta > 0:
            accept = True
        elif temp > 0 and np.random.rand() < np.exp(delta / temp):
            accept = True
            
        if accept:
            current_points = candidate
            current_min_area = new_min_area
            acceptance_count += 1
            stagnation_count = 0
        else:
            stagnation_count += 1

        # Adaptive step_size adjustment
        if (iteration + 1) % acceptance_window == 0:
            acceptance_rate = acceptance_count / acceptance_window
            acceptance_count = 0
            if acceptance_rate > 0.5:
                step_size = min(step_size * 1.1, max_step)
            elif acceptance_rate < 0.2:
                step_size = max(step_size * 0.9, min_step)

        # Re-heat if stuck for too long
        if stagnation_count > max_stagnation:
            temp = initial_temp * 0.5  # Re-heat to half initial temperature
            stagnation_count = 0

    return current_points, current_min_area

def entrypoint() -> np.ndarray:
    np.random.seed(42)
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Multiple restarts with diverse initialization patterns
    best_points = None
    best_min_area = -1
    
    # Three different initialization patterns based on literature
    initialization_patterns = [
        [3, 3, 3, 2],  # Balanced distribution
        [4, 3, 2, 2],  # Gradual row reduction
        [4, 4, 3],     # Original pattern for comparison
        [3, 3, 2, 2, 1]  # Literature-based pattern for n=11 Heilbronn problem
    ]
    
    for pattern in initialization_patterns:
        points = generate_initial_points(pattern, A, B, C)
        optimized_points, min_area = optimize_configuration(points, A, B, C)
        
        if min_area > best_min_area:
            best_points = optimized_points
            best_min_area = min_area

    return best_points