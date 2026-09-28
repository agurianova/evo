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

def calculate_centroid(A, B, C):
    """Calculate centroid of the triangle."""
    return (A + B + C) / 3.0

def create_rotation_matrix(angle):
    """Create 2D rotation matrix for given angle in radians."""
    return np.array([
        [np.cos(angle), -np.sin(angle)],
        [np.sin(angle), np.cos(angle)]
    ])

def apply_rotation(point, center, angle):
    """Rotate point around center by given angle."""
    rot_matrix = create_rotation_matrix(angle)
    return center + np.dot(rot_matrix, point - center)

def get_boundary_distance(point, A, B, C):
    """Calculate minimum distance from point to any triangle edge."""
    def distance_to_line(p, a, b):
        # Vector AB
        ab = b - a
        # Vector AP
        ap = p - a
        # Length of AB
        length_ab = np.linalg.norm(ab)
        # Normalize AB
        if length_ab < 1e-10:
            return np.linalg.norm(ap)
        ab_norm = ab / length_ab
        # Projection of AP onto AB
        proj = np.dot(ap, ab_norm)
        # Clamp projection to segment
        proj = max(0, min(length_ab, proj))
        # Closest point on segment
        closest = a + proj * ab_norm
n        return np.linalg.norm(p - closest)
    
    d1 = distance_to_line(point, A, B)
    d2 = distance_to_line(point, B, C)
    d3 = distance_to_line(point, C, A)
    return min(d1, d2, d3)

def project_to_triangle(point, A, B, C, safety_margin=0.0):
    """Project a point to the nearest point inside the triangle with safety margin."""
    # First get barycentric coordinates
    bary = to_barycentric(point, A, B, C)
    u, v, w = bary
    
    # If any coordinate is negative, project to the nearest edge
    if u < 0 or v < 0 or w < 0:
        # Standard projection to boundary
        if u < 0:
            total = v + w
            v, w = v / total, w / total
            u = 0
        if v < 0:
            total = u + w
            u, w = u / total, w / total
            v = 0
        if w < 0:
            total = u + v
            u, v = u / total, v / total
            w = 0
        
        # Convert back to Cartesian
        boundary_point = to_cartesian([u, v, w], A, B, C)
        
        # Now calculate direction away from boundary
        edge_normal = None
        if u < 1e-10:  # Close to BC edge
            edge_normal = A - boundary_point
        elif v < 1e-10:  # Close to AC edge
            edge_normal = B - boundary_point
        else:  # Close to AB edge
            edge_normal = C - boundary_point
            
        if edge_normal is not None:
            edge_normal = edge_normal / np.linalg.norm(edge_normal)
            # Move inward by safety margin
            point = boundary_point + edge_normal * safety_margin
        else:
            point = boundary_point
    
    # Ensure point is inside triangle after adjustment
    bary = to_barycentric(point, A, B, C)
    u, v, w = np.maximum(bary, 0)
    total = u + v + w
    if total > 0:
        u, v, w = u/total, v/total, w/total
    
    return to_cartesian([u, v, w], A, B, C)

def create_symmetric_configuration(A, B, C):
    """Create symmetric point configuration using 3-fold rotational symmetry."""
    centroid = calculate_centroid(A, B, C)
    
    # Calculate triangle height for reference
    height = np.linalg.norm(C - A) * np.sqrt(3)/2
    
    # Base configuration (4 points that will be rotated)
    base_points = []
    
    # Center point (centroid with small perturbation)
    center_offset = np.array([0.01, 0.01])
    base_points.append(centroid + center_offset)
    
    # Inner ring points (3 points forming small equilateral triangle)
    inner_radius = height * 0.1
    for i in range(3):
        angle = 2 * np.pi * i / 3
        offset = np.array([inner_radius * np.cos(angle), inner_radius * np.sin(angle)])
        base_points.append(centroid + offset)
    
    # Generate full symmetric configuration through rotation
    all_points = []
    
    # Add the center point (only one)
    all_points.append(base_points[0])
    
    # Add the inner ring points and their rotations
    for i in range(1, 4):
        point = base_points[i]
        for j in range(3):  # 0°, 120°, 240° rotations
            angle = 2 * np.pi * j / 3
            rotated = apply_rotation(point, centroid, angle)
            all_points.append(rotated)
    
    # We now have 1 + 9 = 10 points, need 11th point
    # Add a strategic point near the middle of an edge but with safety margin
    edge_midpoint = (A + B) / 2
    direction = centroid - edge_midpoint
    direction = direction / np.linalg.norm(direction)
    strategic_point = edge_midpoint + direction * height * 0.15
    all_points.append(strategic_point)
    
    # Convert to numpy array
    points = np.array(all_points)
    
    # Add small random perturbations to break perfect symmetry (helps avoid degenerate cases)
    for i in range(len(points)):
        points[i] += np.random.normal(0, 0.005, size=2)
    
    return points

def optimize_configuration(points, A, B, C, restarts=5):
    """Optimize the configuration using simulated annealing with multiple restarts."""
    best_points = points.copy()
    best_score = get_smallest_triangle_area(points)
    
    for _ in range(restarts):
        current_points = points.copy()
        current_score = best_score
        
        # Significantly increased parameters to escape shallow local optima
        T = 0.1  # Increased from 0.01
        cooling_rate = 0.98
        iterations = 500  # Increased from 50
        
        for i in range(iterations):
            # Generate candidate by perturbing 1-5 random points (more exploration)
            candidate = current_points.copy()
            num_perturb = np.random.choice([1, 2, 3, 4, 5], p=[0.2, 0.3, 0.25, 0.15, 0.1])
            indices = np.random.choice(11, size=num_perturb, replace=False)
            
            # Adaptive step size with larger initial steps
            step_size = 0.05 * (T / 0.1) ** 0.5
            
            for idx in indices:
                # Gaussian perturbation
                perturbation = np.random.normal(0, step_size, size=2)
                candidate[idx] += perturbation
                
                # Dynamic safety margin based on optimization progress
                safety_margin = 0.01 * (1 - i/iterations)
                
                # Ensure point stays inside triangle with boundary repulsion
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C, safety_margin)
            
            # Calculate score (removed collinearity threshold filter)
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
    
    # Create symmetric configuration with 3-fold rotational symmetry
    points = create_symmetric_configuration(A, B, C)
    
    # Local optimization with enhanced parameters
    optimized_points = optimize_configuration(points, A, B, C, restarts=5)
    
    # Final validation check
    if not is_inside_triangle(optimized_points, A, B, C):
        return points
    
    return optimized_points