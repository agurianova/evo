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

def generate_initial_points(pattern, A, B, C):
    points = []
    
    if pattern == "hexagonal":
        # Hexagonal lattice initialization for n=11
        n = 11
        rows = 4  # Optimal for n=11
        points_per_row = [3, 3, 3, 2]  # Total 11 points
        
        for row in range(rows):
            num_points = points_per_row[row]
            v = (row + 0.5) / rows
            
            # Hexagonal offset (alternating rows)
            hex_offset = 0.5 if row % 2 == 1 else 0.0
            
            for i in range(num_points):
                u = (i + hex_offset) / (num_points - 1 + 0.5) * (1 - v) if num_points > 1 else 0.5 * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                
                # Symmetry-breaking noise with boundary safety
                noise = np.random.uniform(-0.005, 0.005, size=2)
                P_noisy = P + noise
                P_clipped = clip_to_triangle(P_noisy, A, B, C)
                points.append(P_clipped)
    else:
        total_rows = len(pattern)
        for row in range(total_rows):
            num_points = pattern[row]
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

        # Compute gradients for minimal-area triangles
        critical_gradients = []
        min_area = float('inf')
        tolerance = 1e-4
        
        # First find the actual minimum area
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = 0.5 * abs(
                        (current_points[j,0] - current_points[i,0]) * (current_points[k,1] - current_points[i,1]) -
                        (current_points[k,0] - current_points[i,0]) * (current_points[j,1] - current_points[i,1])
                    )
                    if area < min_area:
                        min_area = area
        
        # Now identify triangles within tolerance of minimum and compute gradients
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = 0.5 * abs(
                        (current_points[j,0] - current_points[i,0]) * (current_points[k,1] - current_points[i,1]) -
                        (current_points[k,0] - current_points[i,0]) * (current_points[j,1] - current_points[i,1])
                    )
                    if area < min_area * (1 + tolerance):
                        # Compute gradient for area with respect to each point
                        A_pt = current_points[i]
                        B_pt = current_points[j]
                        C_pt = current_points[k]
                        
                        grad_A = np.array([-(B_pt[1] - C_pt[1]), C_pt[0] - B_pt[0]]) * 0.5
                        grad_B = np.array([C_pt[1] - A_pt[1], -(C_pt[0] - A_pt[0])]) * 0.5
                        grad_C = np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]]) * 0.5
                        
                        # Normalize gradients
                        if np.linalg.norm(grad_A) > 1e-10:
                            grad_A = grad_A / np.linalg.norm(grad_A)
                        if np.linalg.norm(grad_B) > 1e-10:
                            grad_B = grad_B / np.linalg.norm(grad_B)
                        if np.linalg.norm(grad_C) > 1e-10:
                            grad_C = grad_C / np.linalg.norm(grad_C)
                        
                        critical_gradients.append((i, j, k, grad_A, grad_B, grad_C))

        # Multi-point perturbation (15% chance)
        if np.random.rand() < 0.15:
            num_moves = np.random.choice([2, 3])
            # Prioritize critical points for multi-move
            if critical_gradients:
                # Get top 3 critical triangles
                top_triangles = critical_gradients[:3]
                critical_points = set()
                for (i, j, k, _, _, _) in top_triangles:
                    critical_points.update([i, j, k])
                
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
            if critical_gradients:
                # Get a random point from top critical triangles
                top_triangles = critical_gradients[:3]
                critical_points = set()
                for (i, j, k, _, _, _) in top_triangles:
                    critical_points.update([i, j, k])
                if critical_points:
                    idx = np.random.choice(list(critical_points))
                else:
                    idx = np.random.randint(0, 11)
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
            if critical_gradients:
                top_triangles = critical_gradients[:3]
                critical_points = set()
                for (i, j, k, _, _, _) in top_triangles:
                    critical_points.update([i, j, k])
                if critical_points:
                    idx = np.random.choice(list(critical_points))
                else:
                    idx = np.random.randint(0, 11)
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

        # Constraint-driven diversification phase when stuck
        if stagnation_count > max_stagnation:
            # Enter diversification phase
            if len(critical_gradients) > 0:
                # Apply constraint-driven perturbations
                diversification_magnitude = step_size * 2.0

                # Create a set of points to perturb (focus on critical points)
                points_to_perturb = set()
                for (i, j, k, _, _, _) in critical_gradients[:3]:
                    points_to_perturb.update([i, j, k])
                
                # If we don't have many critical points, add some random ones
                if len(points_to_perturb) < 5:
                    remaining = [i for i in range(11) if i not in points_to_perturb]
                    np.random.shuffle(remaining)
                    points_to_perturb.update(remaining[:5-len(points_to_perturb)])
                
                # Compute aggregate gradient for each point
                point_gradients = {i: np.zeros(2) for i in points_to_perturb}
                for (i, j, k, grad_A, grad_B, grad_C) in critical_gradients[:3]:
                    if i in points_to_perturb:
                        point_gradients[i] += grad_A
                    if j in points_to_perturb:
                        point_gradients[j] += grad_B
                    if k in points_to_perturb:
                        point_gradients[k] += grad_C
                
                # Apply perturbations in gradient directions
                candidate = current_points.copy()
                for idx in points_to_perturb:
                    # Normalize and scale the gradient
                    grad = point_gradients[idx]
                    if np.linalg.norm(grad) > 1e-10:
                        grad = grad / np.linalg.norm(grad) * diversification_magnitude
                    else:
                        # Random direction if gradient is zero
                        angle = np.random.uniform(0, 2*np.pi)
                        grad = diversification_magnitude * np.array([np.cos(angle), np.sin(angle)])
                    
                    candidate[idx] += grad
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
                
                if not duplicate:
                    # Evaluate the diversification candidate
                    new_min_area = get_smallest_triangle_area(candidate)
                    if new_min_area > current_min_area:
                        # Accept the diversification if it improves
                        current_points = candidate
                        current_min_area = new_min_area
                        acceptance_count += 1
                        stagnation_count = 0
                        continue
                    elif new_min_area > current_min_area * 0.95:
                        # Sometimes accept slightly worse to escape deeper local optima
                        if np.random.rand() < 0.3:
                            current_points = candidate
                            current_min_area = new_min_area
                            acceptance_count += 1
                            stagnation_count = 0
                            continue

            # If diversification didn't help or wasn't possible, reset with reduced temperature
            temp = initial_temp * 0.3
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
        [3, 4, 4],     # Alternative row distribution
        [2, 3, 4, 2],  # Literature-inspired pattern for n=11
        "hexagonal"    # Hexagonal lattice pattern
    ]
    
    for pattern in initialization_patterns:
        points = generate_initial_points(pattern, A, B, C)
        optimized_points, min_area = optimize_configuration(points, A, B, C)
        
        if min_area > best_min_area:
            best_points = optimized_points
            best_min_area = min_area

    return best_points