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
    """Project a point to the nearest point inside the triangle with boundary repulsion."""
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
    
    # Apply gentle repulsion from boundary
    repulsion_strength = 0.025 * (1 - min_dist / 0.5)  # Parameterized for optimization
    if min_dist < 0.1:  # Only apply when close to boundary
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

def get_bottleneck_points(points):
    """Identify points that form the smallest triangles."""
    n = len(points)
    min_area = float('inf')
    bottleneck_indices = set()
    
    # Find the minimum area triangle(s)
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Calculate area of triangle i,j,k
                area = 0.5 * abs(
                    (points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                    (points[k,0]-points[i,0])*(points[j,1]-points[i,1])
                )
                
                # If this is the smallest area seen so far, reset bottleneck indices
                if area < min_area - 1e-10:
                    min_area = area
                    bottleneck_indices = {i, j, k}
                # If this matches the current minimum area, add these points
                elif abs(area - min_area) < 1e-10:
                    bottleneck_indices.update([i, j, k])
    
    return list(bottleneck_indices), min_area

def physics_initialization(n, A, B, C):
    """Initialize points using adaptive row configuration to approximate known Heilbronn solution."""
    # Create hexagonal grid pattern with 5 rows [2,2,3,3,1] points (improved from [1,2,3,3,2])
    row_points = [2, 2, 3, 3, 1]
    
    # Adaptive height calculation based on triangle geometry
    base_height = 0.05
    row_heights = [
        1.0 - base_height,
        0.75 - base_height,
        0.55 - base_height,
        0.35 - base_height,
        0.15 - base_height
    ]
    
    points = []
    for i, (num_points, height) in enumerate(zip(row_points, row_heights)):
        for j in range(num_points):
            # Position within row (centered)
            pos = (j + 0.5 - num_points/2) / (num_points + 1)
            
            # Barycentric coordinates
            w = height  # Height from base
            u = 0.5 + pos * (1 - height)  # Horizontal position
            v = 1 - u - w
            
            # Convert to Cartesian
            P = u * A + v * B + w * C
            
            # Add small perturbation to break symmetry
            perturbation = np.random.normal(0, 0.001, size=2)
            P = P + perturbation
            
            # Ensure inside triangle with boundary repulsion
            P = project_to_triangle(P, A, B, C)
            points.append(P)
    
    # Convert to numpy array
    points = np.array(points)
    
    # Apply area-based repulsion for better spacing
    for _ in range(100):
        forces = np.zeros_like(points)
        # Repulsion based on triangle area (target small triangles)
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    # Calculate triangle area
                    area = 0.5 * abs(
                        (points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                        (points[k,0]-points[i,0])*(points[j,1]-points[i,1])
                    )
                    # Inverse area weighting (smaller area = stronger repulsion)
                    weight = 1.0 / (area + 1e-5)
                    
                    # Repulsion between all pairs in the triangle
                    diff_ij = points[i] - points[j]
                    dist_ij = max(np.linalg.norm(diff_ij), 1e-5)
                    direction_ij = diff_ij / dist_ij
n                    diff_ik = points[i] - points[k]
                    dist_ik = max(np.linalg.norm(diff_ik), 1e-5)
                    direction_ik = diff_ik / dist_ik
                    
                    # Apply weighted repulsion
                    forces[i] += weight * (direction_ij / dist_ij + direction_ik / dist_ik)
                    forces[j] -= weight * direction_ij / dist_ij
                    forces[k] -= weight * direction_ik / dist_ik
        
        # Update positions with boundary projection
        points += 0.005 * forces
        for i in range(n):
            points[i] = project_to_triangle(points[i], A, B, C)
    
    return points

def optimize_configuration(points, A, B, C, restarts=5):
    """Optimize configuration with bottleneck-targeted simulated annealing."""
    best_points = points.copy()
    best_score = get_smallest_triangle_area(points)
    
    for _ in range(restarts):
        current_points = points.copy()
        current_score = best_score
        
        # Enhanced simulated annealing parameters
        T = 0.1
        cooling_rate = 0.99
        iterations = 600  # Increased from 500 for better convergence

        for i in range(iterations):
            # Generate candidate by perturbing points with bottleneck targeting
            candidate = current_points.copy()
            
            # Identify bottleneck points (smallest triangles)
            bottleneck_indices, _ = get_bottleneck_points(current_points)
            
            # Adaptive perturbation strategy
            if np.random.rand() < 0.6:  # 60% chance to target bottlenecks
                # Weighted selection: bottleneck points have higher probability
                weights = np.zeros(11)
                weights[bottleneck_indices] = 0.8 / len(bottleneck_indices)
                weights[np.setdiff1d(np.arange(11), bottleneck_indices)] = 0.2 / (11 - len(bottleneck_indices))
                
                # Biased probability for number of points
                num_perturb = np.random.choice([1, 2, 3, 4, 5], p=[0.5, 0.3, 0.15, 0.03, 0.02])
                indices = np.random.choice(11, size=num_perturb, replace=False, p=weights)
            else:
                # Biased probability for number of points (non-bottleneck)
                num_perturb = np.random.choice([1, 2, 3, 4, 5], p=[0.5, 0.3, 0.15, 0.03, 0.02])
                indices = np.random.choice(11, size=num_perturb, replace=False)

            # Adaptive step size scaled to triangle dimensions
            step_size = 0.08 * (T / 0.1) ** 0.5
            
            for idx in indices:
                # Gaussian perturbation
                perturbation = np.random.normal(0, step_size, size=2)
                candidate[idx] += perturbation
                
                # Ensure point stays inside triangle with boundary repulsion
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
            
            # Calculate score
            min_area = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            delta = min_area - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current_points = candidate
                current_score = min_area
                
                if min_area > best_score:
                    best_points = candidate.copy()
                    best_score = min_area
            
            # Cool down
            T *= cooling_rate
    
    return best_points

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Initialize with physics-based method approximating known good configuration
    points = physics_initialization(11, A, B, C)
    
    # Local optimization with enhanced parameters
    optimized_points = optimize_configuration(points, A, B, C, restarts=5)
    
    # Final validation
    if not is_inside_triangle(optimized_points, A, B, C):
        return points
    
    return optimized_points