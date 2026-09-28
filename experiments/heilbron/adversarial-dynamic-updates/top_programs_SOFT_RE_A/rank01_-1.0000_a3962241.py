import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.spatial import Voronoi

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

def get_bottleneck_points(config):
    """Identify points that form the smallest triangles."""
    n = len(config)
    min_area = float('inf')
    bottleneck_indices = set()
    
    # Find the minimum area triangle(s)
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Calculate area of triangle i,j,k
                area = 0.5 * abs(
                    (config[j,0]-config[i,0])*(config[k,1]-config[i,1]) - 
                    (config[k,0]-config[i,0])*(config[j,1]-config[i,1])
                )
                
                # If this is the smallest area seen so far, reset bottleneck indices
                if area < min_area - 1e-10:
                    min_area = area
                    bottleneck_indices = {i, j, k}
                # If this matches the current minimum area, add these points
                elif abs(area - min_area) < 1e-10:
                    bottleneck_indices.update([i, j, k])
    
    return list(bottleneck_indices), min_area

def estimate_gradient(point_idx, config, current_min_area):
    """Estimate gradient of minimum triangle area at a specific point using central differences."""
    # Adaptive epsilon based on current min_area for numerical stability
    epsilon = max(1e-7, 0.03 * current_min_area)
    
    original_score = get_smallest_triangle_area(config)
    
    # Try small perturbations in x and y directions (central difference)
    dx = np.zeros(2)
    dy = np.zeros(2)
    dx[0] = epsilon
    dy[1] = epsilon
    
    config_x_plus = config.copy()
    config_x_plus[point_idx] += dx
    score_x_plus = get_smallest_triangle_area(config_x_plus)
    
    config_x_minus = config.copy()
    config_x_minus[point_idx] -= dx
    score_x_minus = get_smallest_triangle_area(config_x_minus)
    
    config_y_plus = config.copy()
    config_y_plus[point_idx] += dy
    score_y_plus = get_smallest_triangle_area(config_y_plus)
    
    config_y_minus = config.copy()
    config_y_minus[point_idx] -= dy
    score_y_minus = get_smallest_triangle_area(config_y_minus)
    
    # Calculate gradients using central difference (more accurate)
    grad_x = (score_x_plus - score_x_minus) / (2 * epsilon)
    grad_y = (score_y_plus - score_y_minus) / (2 * epsilon)
    
    return np.array([grad_x, grad_y])

def find_largest_empty_regions(points, A, B, C, n_regions=3):
    """Find largest empty regions in the triangle using Voronoi analysis."""
    # Create boundary points to constrain Voronoi to the triangle
    boundary_points = np.array([A, B, C])
    all_points = np.vstack([points, boundary_points])
    
    # Compute Voronoi diagram
    vor = Voronoi(all_points)
    
    # Find regions completely inside the triangle
    valid_regions = []
    for i, region in enumerate(vor.regions):
        if not region or -1 in region:
            continue
        
        # Check if region is inside the triangle
        region_points = vor.vertices[region]
        if all(is_inside_triangle(p, A, B, C) for p in region_points):
            # Calculate area of the Voronoi region
            area = 0
            for j in range(len(region_points)):
                k = (j + 1) % len(region_points)
                area += region_points[j, 0] * region_points[k, 1]
                area -= region_points[k, 0] * region_points[j, 1]
            area = abs(area) / 2
            valid_regions.append((i, area))
    
    # Sort by area (largest first)
    valid_regions.sort(key=lambda x: x[1], reverse=True)
    
    # Get the center points of the largest regions
    centers = []
    for i, _ in valid_regions[:n_regions]:
        region = vor.regions[vor.point_region[len(points) + i]]
        region_points = vor.vertices[region]
        center = np.mean(region_points, axis=0)
        centers.append(center)
    
    return np.array(centers)

def create_multi_scale_configuration(A, B, C):
    """Create configuration using multi-scale approach: optimize 5 points, add 3, then add 3 more."""
    # Step 1: Create optimal 5-point configuration
    # Known good configuration for n=5 in equilateral triangle
    base_points = np.array([
        [0.5, 0.2],
        [0.3, 0.5],
        [0.7, 0.5],
        [0.2, 0.1],
        [0.8, 0.1]
    ])
    
    # Convert to Cartesian in our triangle
    height = np.sqrt(3)/2 * 1.5197  # Height of unit-area equilateral triangle
    scale_x = 1.5197
    scale_y = height
    base_points[:, 0] *= scale_x
    base_points[:, 1] *= scale_y
    
    # Project to ensure inside triangle
    for i in range(5):
        base_points[i] = project_to_triangle(base_points[i], A, B, C)
    
    # Optimize the 5-point configuration
    optimized_5 = optimize_sub_configuration(base_points, A, B, C, target_n=5, iterations=300)
    
    # Step 2: Add 3 points in largest empty regions
    empty_centers = find_largest_empty_regions(optimized_5, A, B, C, n_regions=3)
    candidate_8 = np.vstack([optimized_5, empty_centers])
    
    # Optimize the 8-point configuration
    optimized_8 = optimize_sub_configuration(candidate_8, A, B, C, target_n=8, iterations=200)
    
    # Step 3: Add 3 more points with boundary awareness
    # Find regions near boundaries that can improve min_area
    boundary_points = []
    for _ in range(3):
        # Try random points with bias toward boundaries
        bary = np.random.dirichlet([0.8, 0.8, 0.8])
        # Slightly bias toward boundaries
        if np.random.rand() < 0.6:
            idx = np.random.randint(0, 3)
            bary[idx] = max(0.05, bary[idx] * 0.5)
        point = to_cartesian(bary, A, B, C)
        boundary_points.append(point)
    
    candidate_11 = np.vstack([optimized_8, boundary_points])
    
    # Final optimization
    optimized_11 = optimize_sub_configuration(candidate_11, A, B, C, target_n=11, iterations=150)
    
    return optimized_11

def optimize_sub_configuration(points, A, B, C, target_n, iterations=200):
    """Optimize a subset configuration with adaptive parameters."""
    best_points = points.copy()
    best_score = get_smallest_triangle_area(points)
    
    current_points = points.copy()
    current_score = best_score
    
    # Adaptive temperature schedule
    T = 0.08 * (target_n / 11.0)  # Scale temperature based on target size
    cooling_rate = 0.92
    
    for i in range(iterations):
        # Adaptive boundary repulsion margin based on current quality
        margin = 0.03 + 0.05 * (current_score / 0.0365)
        
        # Adaptive score weighting based on optimization phase
        weight_factor = 0.03 + 0.12 * (i / iterations)
        
        # Generate candidate by perturbing points
        candidate = current_points.copy()
        
        # Determine how many points to perturb (adaptive based on stagnation)
        num_perturb = np.random.choice([1, 2, 3, 4], p=[0.25, 0.3, 0.25, 0.2])
        indices = np.random.choice(target_n, size=num_perturb, replace=False)
        
        # Adaptive step size
        step_size = 0.04 * (T / 0.08) ** 0.5
        
        # Get bottleneck points for targeted optimization
        bottleneck_indices, current_min_area = get_bottleneck_points(candidate)
        
        for idx in indices:
            # Higher probability to perturb bottleneck points
            if idx in bottleneck_indices and np.random.rand() < 0.7:
                # Estimate gradient for directional improvement
                grad = estimate_gradient(idx, candidate, current_min_area)
                grad_norm = np.linalg.norm(grad)
                
                if grad_norm > 1e-5:
                    # Normalize and scale gradient
                    grad = grad / grad_norm * step_size * 1.5
n                    candidate[idx] += grad
                else:
                    # Random perturbation if gradient is unreliable
                    candidate[idx] += np.random.normal(0, step_size, size=2)
            else:
                # Random perturbation for non-bottleneck points
                candidate[idx] += np.random.normal(0, step_size, size=2)

            # Ensure point stays inside triangle
            candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

        # Calculate boundary distances
        boundary_distances = [to_barycentric(p, A, B, C).min() for p in candidate]
        boundary_score = np.mean(boundary_distances)
        
        # Combined score with adaptive weighting
        min_area = get_smallest_triangle_area(candidate)
        combined_score = min_area + weight_factor * boundary_score
        
        # Simulated annealing acceptance
        current_boundary_score = np.mean([to_barycentric(p, A, B, C).min() for p in current_points])
        current_combined = current_score + weight_factor * current_boundary_score
        
        delta = combined_score - current_combined
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            current_points = candidate
            current_score = min_area
            
            if min_area > best_score:
                best_points = candidate.copy()
                best_score = min_area
        
        # Adaptive cooling: slow down if making good progress
        if delta > 0:
            cooling_rate = 0.95
        else:
            cooling_rate = 0.92
        
        # Cool down
        T *= cooling_rate
        
    return best_points

def optimize_configuration(points, A, B, C, restarts=3):
    """Optimize the configuration with bottleneck targeting and adaptive parameters."""
    best_points = points.copy()
    best_score = get_smallest_triangle_area(points)
    
    # Get initial bottleneck points and min_area
    _, current_min_area = get_bottleneck_points(points)
    
    for _ in range(restarts):
        current_points = points.copy()
        current_score = best_score
        
        # Adaptive temperature schedule based on current quality
        T = 0.05 * (0.0365 / max(current_min_area, 0.001))
        cooling_rate = 0.90
        iterations = 400
        
        # Track historical gradients for stagnation recovery
        gradient_history = {i: np.array([0.0, 0.0]) for i in range(11)}
        no_improve_count = 0
        
        for i in range(iterations):
            # Adaptive boundary repulsion margin
            margin = 0.03 + 0.05 * (current_score / 0.0365)
            
            # Adaptive score weighting
            weight_factor = 0.03 + 0.12 * (current_score / 0.0365)
            
            # Get bottleneck points for targeted optimization
            bottleneck_indices, current_min_area = get_bottleneck_points(current_points)
            
            # Generate candidate by perturbing points
            candidate = current_points.copy()
            
            # Adaptive perturbation scope based on stagnation
            if no_improve_count > 30:
                num_perturb = np.random.choice([3, 4, 5, 6], p=[0.2, 0.3, 0.3, 0.2])
            else:
                num_perturb = np.random.choice([1, 2, 3, 4], p=[0.25, 0.3, 0.25, 0.2])
            
            # Weighted selection: higher probability for bottleneck points
            weights = np.zeros(11)
            weights[bottleneck_indices] = 0.7 / len(bottleneck_indices)
            weights[np.setdiff1d(np.arange(11), bottleneck_indices)] = 0.3 / (11 - len(bottleneck_indices))
            indices = np.random.choice(11, size=num_perturb, replace=False, p=weights)
            
            # Adaptive step size
            step_size = 0.04 * (T / 0.05) ** 0.5
            
            for idx in indices:
                # Try gradient-guided perturbation first
                grad = estimate_gradient(idx, candidate, current_min_area)
                grad_norm = np.linalg.norm(grad)
                
                if grad_norm > 1e-5:
                    # Normalize and scale gradient
                    grad = grad / grad_norm * step_size * 1.2
                    candidate[idx] += grad
                    gradient_history[idx] = grad  # Update history
                else:
                    # Use historical gradient if available
                    hist_grad = gradient_history[idx]
                    hist_norm = np.linalg.norm(hist_grad)
                    if hist_norm > 1e-5:
                        hist_grad = hist_grad / hist_norm * step_size
                        candidate[idx] += hist_grad
                    else:
                        # Random perturbation
                        candidate[idx] += np.random.normal(0, step_size, size=2)

                # Ensure point stays inside triangle
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

            # Calculate boundary distances
            boundary_distances = [to_barycentric(p, A, B, C).min() for p in candidate]
            boundary_score = np.mean(boundary_distances)
            
            # Combined score with adaptive weighting
            min_area = get_smallest_triangle_area(candidate)
            combined_score = min_area + weight_factor * boundary_score
            
            # Simulated annealing acceptance
            current_boundary_score = np.mean([to_barycentric(p, A, B, C).min() for p in current_points])
            current_combined = current_score + weight_factor * current_boundary_score
            
            delta = combined_score - current_combined
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current_points = candidate
                current_score = min_area
                no_improve_count = 0
                
                if min_area > best_score:
                    best_points = candidate.copy()
                    best_score = min_area
            else:
                no_improve_count += 1

            # Adaptive cooling: slow down if making good progress
            if delta > 0:
                cooling_rate = max(0.90, cooling_rate + 0.01)
            else:
                cooling_rate = max(0.90, cooling_rate - 0.01)
            
            # Stagnation recovery
            if no_improve_count > 50:
                # Use historical gradients for targeted restart
                for idx in range(11):
                    hist_grad = gradient_history[idx]
                    hist_norm = np.linalg.norm(hist_grad)
                    if hist_norm > 1e-5:
                        hist_grad = hist_grad / hist_norm * step_size * 2.0
                        current_points[idx] += hist_grad
                    else:
                        # Larger random perturbation
                        current_points[idx] += np.random.normal(0, step_size * 2.5, size=2)
                    
                    # Ensure point stays inside triangle
                    current_points[idx] = project_to_triangle(current_points[idx], A, B, C)
                
                current_score = get_smallest_triangle_area(current_points)
                no_improve_count = 0

            # Cool down
            T *= cooling_rate
            
    return best_points

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Create configuration using multi-scale approach
    points = create_multi_scale_configuration(A, B, C)
    
    # Local optimization with bottleneck targeting
    optimized_points = optimize_configuration(points, A, B, C, restarts=3)
    
    # Final validation check
    if not is_inside_triangle(optimized_points, A, B, C):
        return points
    
    return optimized_points