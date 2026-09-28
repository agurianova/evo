import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

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

def project_to_triangle(point, A, B, C):
    """Project a point to the nearest point inside the triangle."""
    bary = to_barycentric(point, A, B, C)
    clamped = clamp_barycentric(bary)
    return to_cartesian(clamped, A, B, C)

def get_bottleneck_points(config, A, B, C, threshold=0.05):
    """Identify points participating in triangles near the minimum area."""
    n = len(config)
    min_area = get_smallest_triangle_area(config)
    bottleneck_indices = set()
    
    # Find all triangles within threshold of minimum area
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Create triangle with these three points
                triangle = np.array([config[i], config[j], config[k]])
                # Calculate area using cross product
                area = 0.5 * abs(
                    (triangle[1,0] - triangle[0,0]) * (triangle[2,1] - triangle[0,1]) -
                    (triangle[2,0] - triangle[0,0]) * (triangle[1,1] - triangle[0,1])
                )
                # If area is close to the minimum, mark these points as bottlenecks
                if area <= min_area * (1 + threshold):
                    bottleneck_indices.update([i, j, k])
    
    return list(bottleneck_indices), min_area

def calculate_gradient(point_idx, config, A, B, C, current_min_area=None):
    """Calculate finite-difference gradient for improving min triangle area."""
    if current_min_area is None:
        current_min_area = get_smallest_triangle_area(config)
    
    # Adaptive epsilon based on current min_area for numerical stability
    epsilon = max(1e-7, 0.01 * current_min_area)
    
    original_score = get_smallest_triangle_area(config)
    
    # Try small perturbations in x and y directions
    dx = np.zeros(2)
    dy = np.zeros(2)
    dx[0] = epsilon
    dy[1] = epsilon
    
    config_x = config.copy()
    config_x[point_idx] += dx
    if not is_inside_triangle(config_x[point_idx].reshape(1, 2), A, B, C):
        config_x[point_idx] = project_to_triangle(config_x[point_idx], A, B, C)
    score_x = get_smallest_triangle_area(config_x)
    
    config_y = config.copy()
    config_y[point_idx] += dy
    if not is_inside_triangle(config_y[point_idx].reshape(1, 2), A, B, C):
        config_y[point_idx] = project_to_triangle(config_y[point_idx], A, B, C)
    score_y = get_smallest_triangle_area(config_y)
    
    # Calculate gradients
    grad_x = (score_x - original_score) / epsilon
    grad_y = (score_y - original_score) / epsilon
    
    return np.array([grad_x, grad_y])

def create_radial_configuration(A, B, C, n_points=11):
    """Create a radial configuration optimized for Heilbronn problem."""
    # Calculate centroid of the triangle
    centroid = (A + B + C) / 3
    
    # Get triangle height for boundary calculations
    height = np.linalg.norm(C - (A + B) / 2)
    
    # Define radial pattern based on known Heilbronn solutions
    points = []
    
    # First point at centroid
    points.append(centroid)
    
    # Concentric circles with optimized spacing
    num_circles = 3
    points_per_circle = [1, 3, 6]  # Total 10 points + centroid = 11
    
    # Radii proportional to sqrt(k/num_circles) for better spacing
    radii = [0.15 * height, 0.35 * height, 0.6 * height]
    
    for circle_idx in range(num_circles):
        radius = radii[circle_idx]
        num_points = points_per_circle[circle_idx]
        
        # Angular offsets with small randomization to break symmetry
        base_angle = np.random.uniform(0, 2*np.pi/num_points)
        angles = [base_angle + 2*np.pi*i/num_points + np.random.uniform(-0.1, 0.1) 
                 for i in range(num_points)]
        
        for angle in angles:
            # Convert polar to cartesian
            dx = radius * np.cos(angle)
            dy = radius * np.sin(angle)
            
            # Project to triangle
            candidate = centroid + np.array([dx, dy])
            point = project_to_triangle(candidate, A, B, C)
            points.append(point)
    
    # Ensure we have exactly n_points
    return np.array(points[:n_points])

def adaptive_boundary_repulsion(points, A, B, C, current_min_area=None, target_min=0.0365):
    """Apply boundary repulsion with margin adaptive to current optimization state."""
    new_points = points.copy()
    
    # Calculate adaptive margin: allows boundary points when min_area is low,
    # but enforces stronger interior placement as we approach target
    if current_min_area is None:
        current_min_area = get_smallest_triangle_area(points)
    
    # Margin formula: 0.02 + 0.08 * (current_min/target_min)^2
    margin = 0.02 + 0.08 * min(1.0, (current_min_area / target_min) ** 2)
    
    for i, point in enumerate(points):
        bary = to_barycentric(point, A, B, C)
        min_coord = min(bary)
        
        if min_coord < margin:
            # Calculate repulsion vector
            repulsion = np.array([max(0, margin - b) for b in bary])
            repulsion = repulsion / np.sum(repulsion) if np.sum(repulsion) > 0 else np.array([1/3, 1/3, 1/3])
            
            # Move toward repulsion target
            new_bary = bary + 0.5 * repulsion
            new_bary = new_bary / np.sum(new_bary)
            new_points[i] = to_cartesian(new_bary, A, B, C)
            
    return new_points

def multi_scale_optimization(A, B, C, n_points=11, initial_points=5):
    """Build configuration through multi-scale optimization."""
    # Start with fewer points
    points = create_radial_configuration(A, B, C, initial_points)
    
    # Initial optimization with fewer points
    points = optimize_configuration(points, A, B, C, restarts=3, max_iterations=300)
    
    # Add points strategically near bottleneck regions
    for _ in range(initial_points, n_points):
        # Identify bottleneck regions
        bottleneck_indices, _ = get_bottleneck_points(points, A, B, C, threshold=0.1)
        
        # Select a bottleneck triangle
        triangle_indices = []
        min_area = float('inf')
        for i in range(len(points)):
            for j in range(i+1, len(points)):
                for k in range(j+1, len(points)):
                    triangle = np.array([points[i], points[j], points[k]])
                    area = 0.5 * abs(
                        (triangle[1,0] - triangle[0,0]) * (triangle[2,1] - triangle[0,1]) -
                        (triangle[2,0] - triangle[0,0]) * (triangle[1,1] - triangle[0,1])
                    )
                    if area < min_area:
                        min_area = area
                        triangle_indices = [i, j, k]

        # Add a new point at the centroid of the smallest triangle
        new_point = np.mean([points[i] for i in triangle_indices], axis=0)
        
        # Slightly perturb to avoid exact centroid
        new_point += np.random.normal(0, 0.02, size=2)
        new_point = project_to_triangle(new_point, A, B, C)
        
        # Add to configuration
        points = np.vstack([points, new_point])
        
        # Re-optimize with new point
        points = optimize_configuration(points, A, B, C, restarts=2, max_iterations=200)
    
    return points

def optimize_configuration(points, A, B, C, restarts=5, max_iterations=500):
    """Optimize configuration with bottleneck-focused simulated annealing."""
    best_points = points.copy()
    best_score = get_smallest_triangle_area(points)
    target_min = 0.0365
    
    for _ in range(restarts):
        current_points = points.copy()
        current_score = best_score
        
        # Simulated annealing parameters
        T = 0.08  # Starting temperature
        cooling_rate = 0.95
        
        for i in range(max_iterations):
            # Adaptive step size
            step_size = 0.04 * (T / 0.08) ** 0.5
            
            # BOTTLENECK-FOCUSED PERTURBATION (70% probability)
            bottleneck_indices, _ = get_bottleneck_points(current_points, A, B, C, threshold=0.05)
            
            if len(bottleneck_indices) == 0:
                bottleneck_indices = list(range(len(current_points)))
            
            if np.random.rand() < 0.7 and bottleneck_indices:
                # Focus on bottleneck points with higher probability
                weights = np.zeros(len(current_points))
                weights[bottleneck_indices] = 1.0 / len(bottleneck_indices)
                
                # Choose 1-3 points from bottleneck regions
                num_perturb = np.random.choice([1, 2, 3], p=[0.5, 0.35, 0.15])
                indices = np.random.choice(
                    len(current_points), 
                    size=num_perturb, 
                    replace=False,
                    p=weights/np.sum(weights)
                )
            else:
                # Biased probability for number of points to perturb
                num_perturb = np.random.choice([1, 2, 3, 4, 5], p=[0.4, 0.3, 0.15, 0.1, 0.05])
                indices = np.random.choice(len(current_points), size=num_perturb, replace=False)

            candidate = current_points.copy()
            
            # Try gradient-informed perturbation first (60% probability)
            if np.random.rand() < 0.6:
                for idx in indices:
                    grad = calculate_gradient(idx, candidate, A, B, C, current_score)
                    if np.linalg.norm(grad) > 1e-4:
                        # Normalize and scale by adaptive step size
                        grad = grad / np.linalg.norm(grad) * step_size * 1.5
                        candidate[idx] += grad
                    else:
                        # Fall back to random perturbation
                        candidate[idx] += np.random.normal(0, step_size, size=2)
            else:
                # Random perturbation
                for idx in indices:
                    candidate[idx] += np.random.normal(0, step_size, size=2)

            # Project to triangle
            for idx in indices:
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

            # Apply adaptive boundary repulsion
            candidate = adaptive_boundary_repulsion(candidate, A, B, C, current_min_area=current_score)

            # Calculate new score
            min_area = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            delta = min_area - current_score
n            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current_points = candidate
                current_score = min_area
                
                if min_area > best_score:
                    best_points = candidate.copy()
                    best_score = min_area

            # Cool down
            T *= cooling_rate

    # Final boundary repulsion with current best score
    best_points = adaptive_boundary_repulsion(best_points, A, B, C, current_min_area=best_score)
    
    return best_points

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Create configuration through multi-scale optimization
    points = multi_scale_optimization(A, B, C, n_points=11, initial_points=5)
    
    # Final validation check
    if not is_inside_triangle(points, A, B, C):
        # Fallback to radial configuration if multi-scale failed
        points = create_radial_configuration(A, B, C, 11)
    
    return points