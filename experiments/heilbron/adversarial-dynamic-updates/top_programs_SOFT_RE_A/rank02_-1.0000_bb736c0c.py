import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

class MoveMemory:
    def __init__(self, decay_rate=0.05):
        self.moves = []  # Will store (timestamp, improvement_delta, idx, move)
        self.decay_rate = decay_rate
        self.current_time = 0

    def add(self, improvement_delta, idx, move):
        self.moves.append((self.current_time, improvement_delta, idx, move.copy()))
        self.current_time += 1

    def get_weighted_moves(self, max_moves=50):
        """Return moves sorted by decayed importance (exp(-decay*age) * improvement_delta)"""
        if not self.moves:
            return []
        
        # Calculate current importance with exponential decay
        current_importance = [
            (np.exp(-self.decay_rate * (self.current_time - timestamp)) * improvement_delta, 
             idx, move)
            for timestamp, improvement_delta, idx, move in self.moves
        ]
        
        # Sort by importance descending
        current_importance.sort(key=lambda x: x[0], reverse=True)
        return current_importance[:max_moves]

def project_to_triangle(point, A, B, C):
    """Project a point to the nearest point inside the triangle."""
    # Convert to barycentric coordinates
    v0 = B - A
    v1 = C - A
    v2 = point - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    
    if abs(denom) < 1e-10:
        return point
        
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w

    # Clamp barycentric coordinates to ensure point is inside triangle
    if u < 0:
        # Project to edge BC
        total = v + w
        if total > 0:
            v, w = v / total, w / total
        u = 0
    if v < 0:
        # Project to edge AC
        total = u + w
        if total > 0:
            u, w = u / total, w / total
        v = 0
    if w < 0:
        # Project to edge AB
        total = u + v
        if total > 0:
            u, v = u / total, v / total
        w = 0

    # Ensure coordinates sum to 1
    total = u + v + w
    if total > 0:
        u, v, w = u/total, v/total, w/total
    
    return u * A + v * B + w * C
def calculate_central_difference_gradient(point_idx, config, A, B, C, current_score):
    """Calculate central difference gradient with adaptive epsilon for more accurate estimation."""
    # Adaptive epsilon with minimum bound
    epsilon = max(1e-5, min(0.01, 0.1 * np.sqrt(current_score)))
    
    # Central differences: sample both positive and negative directions
    dx_pos = np.zeros(2)
    dx_neg = np.zeros(2)
    dx_pos[0] = epsilon
    dx_neg[0] = -epsilon
    
    dy_pos = np.zeros(2)
    dy_neg = np.zeros(2)
    dy_pos[1] = epsilon
    dy_neg[1] = -epsilon

    # Positive x direction
    config_x_pos = config.copy()
    config_x_pos[point_idx] += dx_pos
    if not is_inside_triangle(config_x_pos[point_idx], A, B, C):
        config_x_pos[point_idx] = project_to_triangle(config_x_pos[point_idx], A, B, C)
    score_x_pos = get_smallest_triangle_area(config_x_pos)

    # Negative x direction
    config_x_neg = config.copy()
    config_x_neg[point_idx] += dx_neg
    if not is_inside_triangle(config_x_neg[point_idx], A, B, C):
        config_x_neg[point_idx] = project_to_triangle(config_x_neg[point_idx], A, B, C)
    score_x_neg = get_smallest_triangle_area(config_x_neg)

    # Positive y direction
    config_y_pos = config.copy()
    config_y_pos[point_idx] += dy_pos
    if not is_inside_triangle(config_y_pos[point_idx], A, B, C):
        config_y_pos[point_idx] = project_to_triangle(config_y_pos[point_idx], A, B, C)
    score_y_pos = get_smallest_triangle_area(config_y_pos)

    # Negative y direction
    config_y_neg = config.copy()
    config_y_neg[point_idx] += dy_neg
    if not is_inside_triangle(config_y_neg[point_idx], A, B, C):
        config_y_neg[point_idx] = project_to_triangle(config_y_neg[point_idx], A, B, C)
    score_y_neg = get_smallest_triangle_area(config_y_neg)

    # Central difference calculation (second-order accurate)
    grad_x = (score_x_pos - score_x_neg) / (2 * epsilon)
    grad_y = (score_y_pos - score_y_neg) / (2 * epsilon)
    
    return np.array([grad_x, grad_y])

def identify_critical_bottleneck_points(points, min_area_threshold=0.05):
    """Identify points participating in triangles where area gap to next-largest triangle exceeds threshold."""
    n = len(points)
    min_area = get_smallest_triangle_area(points)
    
    # Calculate all triangle areas
    triangle_areas = []
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = 0.5 * abs(
                    (points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                    (points[k,0]-points[i,0])*(points[j,1]-points[i,1])
                )
                triangle_areas.append((area, i, j, k))
    
    # Sort by area
    triangle_areas.sort(key=lambda x: x[0])
    
    # Find critical gaps - where the difference to next triangle is significant
    critical_gaps = []
    for i in range(1, len(triangle_areas)):
        current_area = triangle_areas[i][0]
        prev_area = triangle_areas[i-1][0]
        gap = current_area - prev_area
        
        # Consider it a critical gap if it's significant relative to current min_area
        if gap > min_area_threshold * min_area:
            critical_gaps.append(i)
    
    # If no critical gaps found, use the smallest few triangles
    if not critical_gaps:
        critical_gaps = [1, 2, 3]  # Take a few smallest triangles
    
    # Get the earliest critical gap index
    critical_index = min(critical_gaps)
    
    # Collect all points in triangles up to the critical gap
    bottleneck_points = set()
    for i in range(critical_index):
        _, p1, p2, p3 = triangle_areas[i]
        bottleneck_points.update([p1, p2, p3])
    
    return list(bottleneck_points)

def calculate_triangle_participation(points, current_score, progress_ratio):
    """Calculate how many small triangles each point participates in with adaptive threshold."""
    n = len(points)
    participation_counts = np.zeros(n)
    
    # Adaptive threshold based on progress toward optimum
    adaptive_threshold = current_score * (1.0 + 0.1 * (1 - progress_ratio))
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Calculate area of triangle i,j,k
                area = 0.5 * abs(
                    (points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                    (points[k,0]-points[i,0])*(points[j,1]-points[i,1])
                )
                # Include triangles within adaptive threshold of min_area
                if area < adaptive_threshold:
                    participation_counts[i] += 1
                    participation_counts[j] += 1
                    participation_counts[k] += 1
    
    return participation_counts

def random_direction_search(current, current_score, A, B, C, step_size, num_directions=15, move_memory=None):
    """Sample multiple random directions with directional bias to escape flat regions."""
    best_candidate = current.copy()
    best_score = current_score
    
    # First try directions from historical successful moves
    if move_memory and len(move_memory.moves) > 10:
        weighted_moves = move_memory.get_weighted_moves(max_moves=10)
        for _, idx, move in weighted_moves:
            candidate = current.copy()
            # Scale the historical move to current step size
            if np.linalg.norm(move) > 1e-5:
                direction = move / np.linalg.norm(move)
                candidate[idx] += direction * step_size * 1.5
                
                # Project if needed
                if not is_inside_triangle(candidate[idx], A, B, C):
                    candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
                
                candidate_score = get_smallest_triangle_area(candidate)
                if candidate_score > best_score:
                    best_candidate = candidate
                    best_score = candidate_score

    # Then try additional random directions
    for _ in range(num_directions):
        # Generate a random direction
        direction = np.random.normal(0, 1, size=(11, 2))
        direction_norm = np.linalg.norm(direction, axis=1, keepdims=True)
        direction_norm[direction_norm == 0] = 1
        direction = direction / direction_norm
        
        # Scale by adaptive step size
        step = direction * step_size
        
        # Create candidate
        candidate = current + step
        
        # Project any points that moved outside the triangle
        for i in range(11):
            if not is_inside_triangle(candidate[i], A, B, C):
                candidate[i] = project_to_triangle(candidate[i], A, B, C)
        
        # Calculate score
        candidate_score = get_smallest_triangle_area(candidate)
        
        # Track best candidate
        if candidate_score > best_score:
            best_candidate = candidate
            best_score = candidate_score

    return best_candidate, best_score

def repair_collinear_points(candidate, A, B, C, min_area_threshold=1e-5):
    """Identify and repair collinear points using gradient-based approach with stabilized step sizing."""
    n = len(candidate)
    min_area = get_smallest_triangle_area(candidate)
    
    if min_area >= min_area_threshold:
        return candidate, min_area
    
    # Find problematic triangles
    problematic_points = set()
    problematic_triangles = []
    min_triangle_area = float('inf')
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Calculate area of triangle i,j,k
                area = 0.5 * abs((candidate[j,0]-candidate[i,0])*(candidate[k,1]-candidate[i,1]) - 
                               (candidate[k,0]-candidate[i,0])*(candidate[j,1]-candidate[i,1]))
                if area < min_area_threshold:
                    problematic_points.update([i, j, k])
                    problematic_triangles.append((i, j, k, area))
                    if area < min_triangle_area:
                        min_triangle_area = area
    
    if not problematic_points:
        return candidate, min_area
    
    # Compute gradient for problematic points
    gradient = np.zeros_like(candidate)
    for idx in problematic_points:
        grad = calculate_central_difference_gradient(idx, candidate, A, B, C, min_area)
        gradient[idx] = grad
    
    # Adaptive step size with capping for numerical stability
    step_size = min(0.05, 0.008 * np.sqrt(max(min_triangle_area, 1e-6)))
    
    repaired = candidate.copy()
    for idx in problematic_points:
        # Move along gradient direction with stabilized step size
        if np.linalg.norm(gradient[idx]) > 1e-8:
            step = gradient[idx] / np.linalg.norm(gradient[idx]) * step_size
            repaired[idx] += step
            
            # Ensure point stays inside triangle
            if not is_inside_triangle(repaired[idx], A, B, C):
                repaired[idx] = project_to_triangle(repaired[idx], A, B, C)
    
    # Check if repair was successful
    repaired_min_area = get_smallest_triangle_area(repaired)
    if repaired_min_area < min_area:
        return candidate, min_area  # Keep original if repair made things worse
    
    return repaired, repaired_min_area

def generate_density_adaptive_configuration(A, B, C, n_points=11):
    """Generate configuration using density-adaptive hexagonal lattice with edge adjustment."""
    # Hexagonal lattice parameters
    max_attempts = 1000
    points = []
    
    # Edge density adjustment factor (higher near boundaries)
    edge_density_factor = 1.2
    
    # Target minimum distance between points (theoretical estimate)
    min_dist = 0.25 / np.sqrt(n_points)
    
    # Generate candidate points using hexagonal lattice with jitter
n    for attempt in range(max_attempts):
        if len(points) >= n_points:
            break
            
        # Hexagonal lattice pattern with adaptive density
        row = int(np.sqrt(len(points)))
        col = len(points) % (row + 1)
        
        # Adaptive horizontal spacing based on row
        u = (col + 0.5) / (row + 1)
        # Adaptive vertical spacing with edge density adjustment
        v = 0.05 + 0.9 * (row / max(1, n_points//3)) ** 1.1
        
        # Add edge density adjustment (more points near boundaries)
        if v < 0.2 or v > 0.8:
            u = u ** edge_density_factor if v < 0.2 else (1 - (1 - u) ** edge_density_factor)
        
        # Convert to Cartesian coordinates
        P = (1 - u - v) * A + u * B + v * C
        
        # Add small jitter for diversity
        jitter = np.random.normal(0, 0.02 * min_dist, size=2)
        P = P + jitter
        
        # Check if point is inside triangle
        if not is_inside_triangle(P, A, B, C):
            continue
            
        # Check minimum distance to existing points
        too_close = False
        for p in points:
            if np.linalg.norm(P - p) < min_dist * 0.8:
                too_close = True
                break
        
        if not too_close:
            points.append(P)

    # If we didn't get enough points, fill with random points inside triangle
    while len(points) < n_points:
        # Random barycentric coordinates
        u, v = np.random.rand(), np.random.rand()
        if u + v > 1:
            u, v = 1 - u, 1 - v
        w = 1 - u - v
        P = w * A + u * B + v * C
        
        # Check minimum distance
        too_close = False
        for p in points:
            if np.linalg.norm(P - p) < min_dist * 0.7:
                too_close = True
                break
        
        if not too_close:
            points.append(P)

    return np.array(points)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate density-adaptive initial configuration
    points = generate_density_adaptive_configuration(A, B, C, n_points=11)
    
    # Validate initial configuration
    if not is_inside_triangle(points, A, B, C):
        points = generate_density_adaptive_configuration(A, B, C, n_points=11)
    
    # Simulated annealing for robust local optimization
    initial_temp = 0.05
    final_temp = 1e-5
    n_steps = 500
    best_points = points.copy()
    best_score = get_smallest_triangle_area(points)
    
    # Memory buffer for successful move directions with exponential decay
    move_memory = MoveMemory(decay_rate=0.03)  # Reduced decay rate to retain memory longer
    
    # Track optimization progress for adaptive parameters
    progress_ratio = best_score / 0.0365
    no_improve_count = 0
    stagnation_depth = 0
    recent_improvements = []
    
    for step in range(n_steps):
        # Temperature decay with exponent 0.25 for better exploration/exploitation balance
        temp = initial_temp * (1 - step / n_steps) ** 0.25
        
        # Step size decay extended to 0.005 at end
        step_size = 0.05 * (0.005 / 0.05) ** (step / n_steps)
        
        # Update progress ratio for adaptive parameters
        current_score = get_smallest_triangle_area(points)
        progress_ratio = current_score / 0.0365
        
        # Adaptive bottleneck threshold: tighter focus on critical constraints
        adaptive_threshold = 0.02 + 0.1 * (1 - progress_ratio)
        
        # Identify bottleneck points with gap analysis instead of fixed threshold
        bottleneck_points = identify_critical_bottleneck_points(points, min_area_threshold=adaptive_threshold)
        
        # Calculate triangle participation for gradient weighting
        participation_counts = calculate_triangle_participation(points, current_score, progress_ratio)
        
        # Select points to perturb - focus on bottlenecks with adaptive probability
        if len(bottleneck_points) > 0 and np.random.random() < 0.8:
            num_points = np.random.choice([1, 2, 3], p=[0.6, 0.3, 0.1])
            indices = np.random.choice(
                bottleneck_points, 
                size=min(num_points, len(bottleneck_points)), 
                replace=False
            )
        else:
            num_points = np.random.choice([1, 2, 3, 4, 5], p=[0.5, 0.3, 0.15, 0.03, 0.02])
            indices = np.random.choice(11, size=num_points, replace=False)
        
        # Create candidate solution
        candidate = points.copy()
        gradient_success = False
        
        # Try gradient-informed perturbation first (90% probability throughout optimization)
        if np.random.random() < 0.9:
            for idx in indices:
                # Use central differences for more accurate gradient
                grad = calculate_central_difference_gradient(idx, candidate, A, B, C, current_score)
                
                if np.linalg.norm(grad) > 1e-3:
                    # Weight gradient by 1/log(1 + number of small triangles it participates in)
                    weight = 1.0 / np.log(1 + max(1, participation_counts[idx]))
                    # Normalize and scale by adaptive step size
                    grad = grad / np.linalg.norm(grad) * step_size * 2.0 * weight
                    candidate[idx] += grad
                    gradient_success = True
                    
                    # Store successful moves for future reference
                    move = candidate[idx] - points[idx]
                    if np.linalg.norm(move) > 1e-5:
                        improvement_delta = get_smallest_triangle_area(candidate) - current_score
                        move_memory.add(improvement_delta, idx, move)
        else:
            # Pure random perturbation
            for idx in indices:
                candidate[idx] += np.random.normal(0, step_size, size=2)
        
        # Project to triangle if needed
        for idx in indices:
            if not is_inside_triangle(candidate[idx], A, B, C):
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
        
        # Repair collinear points if needed
        candidate, candidate_score = repair_collinear_points(candidate, A, B, C)
        
        # Calculate acceptance probability
        delta = candidate_score - current_score
        
        # Simulated annealing acceptance
        if delta > 0 or (temp > 1e-5 and np.random.random() < np.exp(delta / temp)):
            points = candidate
            current_score = candidate_score
            
            # Track best solution
            if candidate_score > best_score:
                best_points = candidate.copy()
                best_score = candidate_score
                no_improve_count = 0
                # Record improvement for adaptive step sizing
                if len(recent_improvements) >= 5:
                    recent_improvements.pop(0)
                recent_improvements.append(delta)
            else:
                no_improve_count += 1
        else:
            no_improve_count += 1

        # Multi-direction sampling when stuck in flat region
        if no_improve_count > 20:  # Reduced threshold to react faster
            # Check if gradient is small (flat region)
            total_grad = 0
            for idx in range(11):
                grad = calculate_central_difference_gradient(idx, points, A, B, C, current_score)
                total_grad += np.linalg.norm(grad)
            
            if total_grad < 1e-4:
                # Sample multiple random directions with directional bias
                flat_candidate, flat_score = random_direction_search(
                    points, current_score, A, B, C, step_size * 2.0, num_directions=15, move_memory=move_memory
                )
                
                if flat_score > best_score:
                    best_points = flat_candidate.copy()
                    best_score = flat_score
                    points = flat_candidate
                    current_score = flat_score
                    no_improve_count = 0

        # Memory-guided restart when improvement stalls
        if no_improve_count > 40 and len(move_memory.moves) > 10:
            # Try to apply historically successful moves
            weighted_moves = move_memory.get_weighted_moves(max_moves=30)
            for _ in range(min(3, len(indices))):
                idx = np.random.choice(indices)
                # Find moves for this index in memory
                relevant_moves = [(imp, move) for imp, i, move in weighted_moves if i == idx]
                if relevant_moves:
                    # Weight moves by their calculated importance
                    total_imp = sum(imp for imp, _ in relevant_moves)
                    if total_imp > 0:
                        weights = [imp/total_imp for imp, _ in relevant_moves]
                        # Select a move proportional to its importance
                        selected_idx = np.random.choice(len(relevant_moves), p=weights)
                        move = relevant_moves[selected_idx][1]
                        # Normalize and scale
                        if np.linalg.norm(move) > 1e-5:
                            # Adaptive scaling based on recent improvements
                            adaptive_scale = 1.0
                            if recent_improvements:
                                avg_improvement = np.mean(recent_improvements)
                                adaptive_scale = max(1.0, 2.0 * avg_improvement / step_size)
                            
                            move = move / np.linalg.norm(move) * step_size * 3.0 * adaptive_scale
                            candidate[idx] = points[idx] + move
                            if is_inside_triangle(candidate[idx], A, B, C):
                                candidate, candidate_score = repair_collinear_points(candidate, A, B, C)
                                if candidate_score > best_score:
                                    best_points = candidate.copy()
                                    best_score = candidate_score
                                    points = candidate
                                    current_score = candidate_score
                                    no_improve_count = 0

    return best_points