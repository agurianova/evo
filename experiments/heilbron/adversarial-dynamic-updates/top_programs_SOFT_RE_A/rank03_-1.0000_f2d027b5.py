import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

# Known effective row patterns for n=11 points with historical resistance weights
ROW_PATTERNS = [
    ([1, 2, 3, 3, 2], 0.3),  # Base pattern
    ([1, 3, 3, 2, 2], 0.25),  # Alternative with more points in middle rows
    ([2, 2, 3, 3, 1], 0.2),   # Mirror of base pattern
    ([1, 2, 4, 2, 2], 0.15),  # Pattern with a denser middle row
    ([1, 3, 2, 3, 2], 0.1)    # More distributed pattern
]

# Priority-based move memory configuration
DECAY_FACTOR = 0.98
MAX_MEMORY_SIZE = 300


def to_barycentric(point, A, B, C):
    """Convert Cartesian coordinates to barycentric coordinates."""
    v0 = B - A
    v1 = C - A
    v2 = point - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    return np.array([u, v, w])

def to_cartesian(bary, A, B, C):
    """Convert barycentric coordinates to Cartesian coordinates."""
    u, v, w = bary
    return u * A + v * B + w * C

def clamp_barycentric(bary):
    """Clamp barycentric coordinates to ensure point is inside triangle."""
    u, v, w = bary
    # If any coordinate is negative, project to the nearest edge
    if u < 0:
        # Project to edge BC
        total = v + w
        v, w = v / total, w / total
        u = 0
    if v < 0:
        # Project to edge AC
        total = u + w
        u, w = u / total, w / total
        v = 0
    if w < 0:
        # Project to edge AB
        total = u + v
        u, v = u / total, v / total
        w = 0
    # Ensure coordinates sum to 1
    total = u + v + w
    return np.array([u, v, w]) / total

def project_to_triangle(point, A, B, C, min_area=None, preserve_edges=False):
    """Project a point to the nearest point inside the triangle with adaptive boundary repulsion."""
    bary = to_barycentric(point, A, B, C)
    clamped = clamp_barycentric(bary)
    
    # Calculate distances to edges
    def distance_to_edge(p, a, b):
        ba = b - a
        pa = p - a
        h = np.abs(np.cross(ba, pa)) / np.linalg.norm(ba)
        return h
    
    dist_ab = distance_to_edge(point, A, B)
    dist_bc = distance_to_edge(point, B, C)
    dist_ca = distance_to_edge(point, C, A)
    min_dist = min(dist_ab, dist_bc, dist_ca)
    
    # Adaptive repulsion strength based on current min_area (reduced by 50%)
    base_repulsion = 0.01  # Reduced from 0.02 as per boundary_harmful insight
    if min_area is not None:
        # Scale repulsion with quality (less repulsion when quality is high)
        repulsion_strength = base_repulsion * (min_area / 0.0365)
    else:
        repulsion_strength = base_repulsion
    
    # Only apply when close to boundary and not preserving edges
    if not preserve_edges and min_dist < 0.1:
        # Get normal vector pointing inward
        if min_dist == dist_ab:
            normal = np.array([-(B[1]-A[1]), B[0]-A[0]])
        elif min_dist == dist_bc:
            normal = np.array([-(C[1]-B[1]), C[0]-B[0]])
        else:
            normal = np.array([-(A[1]-C[1]), A[0]-C[0]])
        normal = normal / np.linalg.norm(normal)
        point = point + repulsion_strength * normal
        
    # Re-project if still outside
    bary = to_barycentric(point, A, B, C)
    clamped = clamp_barycentric(bary)
    return to_cartesian(clamped, A, B, C)

def get_smallest_triangle_indices(points, n=3):
    """Return indices of the n smallest triangles."""
    n_points = len(points)
    triangle_areas = []
    
    for i in range(n_points):
        for j in range(i+1, n_points):
            for k in range(j+1, n_points):
                # Create triangle with these three points
                triangle = np.array([points[i], points[j], points[k]])
                # Calculate area using cross product
                area = 0.5 * abs(
                    (triangle[1,0] - triangle[0,0]) * (triangle[2,1] - triangle[0,1]) -
                    (triangle[2,0] - triangle[0,0]) * (triangle[1,1] - triangle[0,1])
                )
                triangle_areas.append((area, (i, j, k)))
    
    # Sort by area and return top n
    triangle_areas.sort(key=lambda x: x[0])
    return [indices for _, indices in triangle_areas[:n]]

def calculate_central_difference_gradient(point_idx, config, A, B, C, current_score):
    """Calculate central difference gradient for more accurate estimation with adaptive epsilon."""
    # Adaptive epsilon scaling with current min_area for numerical stability
    epsilon = max(1e-7, 0.01 * current_score)
    
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
    if not is_inside_triangle(config_x_pos[point_idx].reshape(1, 2), A, B, C):
        config_x_pos[point_idx] = project_to_triangle(config_x_pos[point_idx], A, B, C, current_score)
    score_x_pos = get_smallest_triangle_area(config_x_pos)

    # Negative x direction
    config_x_neg = config.copy()
    config_x_neg[point_idx] += dx_neg
    if not is_inside_triangle(config_x_neg[point_idx].reshape(1, 2), A, B, C):
        config_x_neg[point_idx] = project_to_triangle(config_x_neg[point_idx], A, B, C, current_score)
    score_x_neg = get_smallest_triangle_area(config_x_neg)

    # Positive y direction
    config_y_pos = config.copy()
    config_y_pos[point_idx] += dy_pos
    if not is_inside_triangle(config_y_pos[point_idx].reshape(1, 2), A, B, C):
        config_y_pos[point_idx] = project_to_triangle(config_y_pos[point_idx], A, B, C, current_score)
    score_y_pos = get_smallest_triangle_area(config_y_pos)

    # Negative y direction
    config_y_neg = config.copy()
    config_y_neg[point_idx] += dy_neg
    if not is_inside_triangle(config_y_neg[point_idx].reshape(1, 2), A, B, C):
        config_y_neg[point_idx] = project_to_triangle(config_y_neg[point_idx], A, B, C, current_score)
    score_y_neg = get_smallest_triangle_area(config_y_neg)

    # Central difference calculation (second-order accurate)
    grad_x = (score_x_pos - score_x_neg) / (2 * epsilon)
    grad_y = (score_y_pos - score_y_neg) / (2 * epsilon)
    
    return np.array([grad_x, grad_y])

def calculate_gradient(point_idx, config, A, B, C, min_area=None):
    """Calculate gradient using central difference with plateau handling."""
    if min_area is None:
        min_area = get_smallest_triangle_area(config)
    
    # First try central difference for better accuracy
    grad = calculate_central_difference_gradient(point_idx, config, A, B, C, min_area)
    
    # Handle plateau regions where gradient norm is near zero
    grad_norm = np.linalg.norm(grad)
    if grad_norm < 1e-5:
        # Use direct search method for plateau regions
        directions = [
            np.array([1, 0]), np.array([-1, 0]), 
            np.array([0, 1]), np.array([0, -1]),
            np.array([1, 1]), np.array([-1, -1])
        ]
        best_improvement = 0
        best_direction = np.zeros(2)
        
        for direction in directions:
            candidate = config.copy()
            # Normalize and scale direction
            direction = direction / np.linalg.norm(direction) * 0.01
            candidate[point_idx] += direction
            
            # Project to triangle if needed
            if not is_inside_triangle(candidate[point_idx].reshape(1, 2), A, B, C):
                candidate[point_idx] = project_to_triangle(candidate[point_idx], A, B, C, min_area)
            
            # Calculate improvement
            score = get_smallest_triangle_area(candidate)
            improvement = score - min_area
            
            if improvement > best_improvement:
                best_improvement = improvement
                best_direction = direction
        
        return best_direction if best_improvement > 0 else np.zeros(2)
    
    return grad

def adaptive_row_configuration(n, A, B, C, resistance_feedback=None):
    """Generate adaptive row configuration with pattern selection based on resistance feedback."""
    # Select row pattern based on historical resistance performance
    if resistance_feedback is None:
        # Use weighted probability based on known effective patterns
        patterns, weights = zip(*ROW_PATTERNS)
        row_points = patterns[np.random.choice(len(patterns), p=weights)]
    else:
        # TODO: In future, adapt weights based on resistance feedback
        patterns, weights = zip(*ROW_PATTERNS)
        row_points = patterns[np.random.choice(len(patterns), p=weights)]

    # Adaptive height variation based on optimization context
    base_heights = np.array([0.05, 0.25, 0.45, 0.65, 0.85])
    # Expanded from ±0.015 to ±0.05 as per exploration_rigid insight
    adaptive_shift = np.random.uniform(-0.05, 0.05, size=5)
    row_heights = base_heights + adaptive_shift
    row_heights = np.clip(row_heights, 0.02, 0.98)
    
    points = []
    for i, (num_points, height) in enumerate(zip(row_points, row_heights)):
        for j in range(num_points):
            # Position within row (centered)
            pos = (j + 0.5 - num_points/2) / num_points
            
            # Quadratic horizontal spread function for better approximation of optimal patterns
            horizontal_spread = 0.85 - 0.25 * height * (1 - height)  # Quadratic nonlinearity
            u = 0.5 + pos * horizontal_spread
            v = 1 - u - height
            
            # Convert to Cartesian
            P = u * A + v * B + height * C
            
            # Adaptive symmetry-breaking perturbation
            # Start with larger perturbation for exploration, decay over optimization
            perturbation = np.random.normal(0, 0.025, size=2)
            P = P + perturbation
            
            # Ensure inside triangle with boundary-aware projection
            P = project_to_triangle(P, A, B, C, min_area=None, preserve_edges=True)
            points.append(P)
    
    # Convert to numpy array
    points = np.array(points)
    
    return points

def optimize_configuration(points, A, B, C, restarts=5):
    """Optimize configuration with memory-guided simulated annealing."""
    best_points = points.copy()
    best_score = get_smallest_triangle_area(points)
    
    # Initialize move memory for tracking successful perturbations
    move_memory = []
    current_timestamp = 0
    
    for _ in range(restarts):
        current_points = points.copy()
        current_score = best_score
        
        # Improved simulated annealing parameters
        T = 0.3
        cooling_rate = 0.995
        iterations = 1500  # Increased from 800 for more thorough exploration
        
        for i in range(iterations):
            current_timestamp += 1
            # Generate candidate by perturbing points
            candidate = current_points.copy()
            
            # Diversified triangle-focused perturbation strategy
            if np.random.random() < 0.8:
                # Get top k smallest triangles based on relative gap
                all_triangles = []
                n = len(current_points)
                for idx1 in range(n):
                    for idx2 in range(idx1+1, n):
                        for idx3 in range(idx2+1, n):
                            triangle = np.array([current_points[idx1], current_points[idx2], current_points[idx3]])
                            area = 0.5 * abs(
                                (triangle[1,0] - triangle[0,0]) * (triangle[2,1] - triangle[0,1]) -
                                (triangle[2,0] - triangle[0,0]) * (triangle[1,1] - triangle[0,1])
                            )
                            all_triangles.append((area, (idx1, idx2, idx3)))
                
                # Sort triangles by area
                all_triangles.sort(key=lambda x: x[0])
                min_area = all_triangles[0][0]
                
                # Adaptive k selection based on relative gap between triangles
                k = 1
                for j in range(1, min(10, len(all_triangles))):
                    gap = (all_triangles[j][0] - min_area) / min_area
                    if gap < 0.05:  # Consider triangles within 5% of min_area
                        k += 1
                    else:
                        break
                
                # Get top-k smallest triangles
                top_k_indices = [indices for _, indices in all_triangles[:k]]
                
                # Flatten and get unique point indices from top-k triangles
                bottleneck_points = set()
                for indices in top_k_indices:
                    bottleneck_points.update(indices)
                bottleneck_points = list(bottleneck_points)

                # Choose 1-3 points from bottleneck points
                num_points = np.random.choice([1, 2, 3], p=[0.6, 0.3, 0.1])
                indices = np.random.choice(bottleneck_points, size=min(num_points, len(bottleneck_points)), replace=False)
            else:
                # Biased probability for number of points to perturb
                num_perturb = np.random.choice([1, 2, 3, 4, 5], p=[0.5, 0.3, 0.15, 0.03, 0.02])
                indices = np.random.choice(11, size=num_perturb, replace=False)
            
            # Gradient-guided perturbation
            use_gradient = np.random.random() < 0.65
            if use_gradient:
                for idx in indices:
                    grad = calculate_gradient(idx, candidate, A, B, C, current_score)
                    grad_norm = np.linalg.norm(grad)
                    if grad_norm > 1e-5:
                        # Normalize and scale by adaptive step size
                        grad = grad / grad_norm
                        # Increased base step size as per step_size_rigid insight
                        step_size = 0.1 * (T / 0.3)
                        candidate[idx] += grad * step_size
                    else:
                        # Fall back to random perturbation if gradient is unreliable
                        step_size = 0.1 * (T / 0.3) ** 0.5
                        perturbation = np.random.normal(0, step_size, size=2)
                        candidate[idx] += perturbation
            else:
                # Adaptive step size scaled to triangle dimensions
                step_size = 0.1 * (T / 0.3) ** 0.5
                for idx in indices:
                    perturbation = np.random.normal(0, step_size, size=2)
                    candidate[idx] += perturbation
            
            # Ensure points stay inside triangle with boundary-aware projection
            for i in range(len(candidate)):
                if not is_inside_triangle(candidate[i].reshape(1, 2), A, B, C):
                    candidate[i] = project_to_triangle(candidate[i], A, B, C, current_score, preserve_edges=True)
            
            # Calculate score
            min_area = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            delta = min_area - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current_points = candidate
                current_score = min_area
                
                # Track successful moves for memory-guided restarts
                if delta > 0:
                    for idx in indices:
                        move = candidate[idx] - current_points[idx]
                        if np.linalg.norm(move) > 1e-5:
                            # Store as (timestamp, improvement, idx, move)
                            move_memory.append((current_timestamp, delta, idx, move.copy()))

                if min_area > best_score:
                    best_points = candidate.copy()
                    best_score = min_area
            
            # Cool down
            T *= cooling_rate

        # Memory-guided restart if we're stuck
        if best_score - get_smallest_triangle_area(points) < 1e-5:
            # Use move memory to guide restart
            if len(move_memory) > 20:
                # Calculate weighted importance of each move
n                weighted_moves = []
                for timestamp, improvement, idx, move in move_memory:
                    # Exponential decay based on recency
                    time_factor = DECAY_FACTOR ** (current_timestamp - timestamp)
                    # Weight by improvement magnitude
                    total_weight = improvement * time_factor
                    if total_weight > 0:
                        weighted_moves.append((total_weight, idx, move))
                
                # Sort by weight descending
                weighted_moves.sort(key=lambda x: x[0], reverse=True)
                
                # Keep only top moves
                top_moves = weighted_moves[:min(MAX_MEMORY_SIZE, len(weighted_moves))]
                
                # Apply top moves to create a better starting point
                restart_points = points.copy()
                applied_indices = set()
                for _, idx, move in top_moves:
                    if idx not in applied_indices and np.linalg.norm(move) > 1e-5:
                        # Scale move by temperature factor for exploration
                        scale = 1.5 * (T / 0.3)
                        restart_points[idx] += move * scale
                        applied_indices.add(idx)
                        if len(applied_indices) >= 3:  # Limit to 3 points for restart
                            break
                
                # Ensure validity
                for i in range(len(restart_points)):
                    if not is_inside_triangle(restart_points[i].reshape(1, 2), A, B, C):
                        restart_points[i] = project_to_triangle(restart_points[i], A, B, C, None, preserve_edges=True)
                
                # Re-run optimization from this better starting point
                points = restart_points
    
    return best_points

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Initialize with adaptive row configuration
    points = adaptive_row_configuration(11, A, B, C)
    
    # Local optimization with gradient-guided simulated annealing
    optimized_points = optimize_configuration(points, A, B, C, restarts=5)
    
    # Final validation
    if not is_inside_triangle(optimized_points, A, B, C):
        return points
    
    return optimized_points