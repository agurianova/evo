import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def create_hexagonal_lattice(n, A, B, C):
    """Create a hexagonal lattice pattern inside the triangle"""
    # Get triangle dimensions
    base = np.linalg.norm(B - A)
    height = np.sqrt(3)/2 * base
    
    # For 11 points, a 4-row hexagonal pattern works well
    # Row 0: 4 points, Row 1: 3 points, Row 2: 3 points, Row 3: 1 point
    rows = [4, 3, 3, 1]
    
    points = []
    
    for i, n_in_row in enumerate(rows):
        # Horizontal offset for hexagonal pattern
        h_offset = 0.5 * (base / 4) if i % 2 == 1 else 0
        
        for j in range(n_in_row):
            # Relative position in triangle
            u = (h_offset + j * (base / 4)) / base
            v = (i * height / 3) / height
            
            # Convert to Cartesian coordinates
            point = (1 - u - v) * A + u * B + v * C
            
            # Add 5% jitter
            jitter = np.random.uniform(-0.05, 0.05, 2) * np.array([base/4, height/3])
            point = point + jitter
            
            points.append(point)
    
    # If we have fewer than n points, add random ones (shouldn't happen for n=11)
    while len(points) < n:
        u = random.random()
        v = random.random()
        if u + v > 1:
            u = 1 - u
            v = 1 - v
        point = (1 - u - v) * A + u * B + v * C
        points.append(point)
    
    return np.array(points[:n])

def project_to_triangle(point, A, B, C):
    """Project a point back to the triangle if it's outside"""
    if is_inside_triangle(point.reshape(1,2), A, B, C):
        return point
    
    edges = [(A, B), (B, C), (C, A)]
    best_proj = None
    min_dist = float('inf')
    
    for (X, Y) in edges:
        v = Y - X
        w = point - X
        c1 = np.dot(w, v)
        c2 = np.dot(v, v)
        
        if c2 < 1e-10:
            t = 0
        else:
            t = c1 / c2
        t = max(0, min(1, t))
        
        proj = X + t * v
        dist = np.linalg.norm(point - proj)
        
        if dist < min_dist:
            min_dist = dist
            best_proj = proj
    
    return best_proj

def get_critical_triangles(points):
    """Identify triangles near the minimum area and their points"""
    min_area = get_smallest_triangle_area(points)
    n = len(points)
    critical_triangles = []
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                a, b, c = points[i], points[j], points[k]
                area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                # Consider triangles within 5% of the minimum area as critical
                if area <= min_area * 1.05:
                    critical_triangles.append((i, j, k, area))
    
    return critical_triangles

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Improved initialization: hexagonal lattice with 5% jitter
    points = create_hexagonal_lattice(11, A, B, C)
    
    # Simulated annealing parameters
    initial_temp = 0.005
    temp = initial_temp
    cooling_rate = 0.99
    max_iter = 300
    
    # Step size parameters
    step_size = 0.02
    step_decay = 0.99
    min_step = 1e-6
    
    current_min_area = get_smallest_triangle_area(points)
    best_points = points.copy()
    best_min_area = current_min_area
    
    for iter in range(max_iter):
        # Identify critical triangles and points
        critical_triangles = get_critical_triangles(points)
        critical_points = set()
        for i, j, k, _ in critical_triangles:
            critical_points.add(i)
            critical_points.add(j)
            critical_points.add(k)
        
        # Weight selection toward critical points
        weights = np.ones(11) * 0.1
        for idx in critical_points:
            weights[idx] = 1.0
        weights /= weights.sum()
        
        # Choose 2 or 3 points to move
        k = np.random.choice([2, 3])
        indices = np.random.choice(11, size=k, replace=False, p=weights)
        
        # Create candidate by perturbing selected points
        candidate = points.copy()
        std = step_size * (temp / initial_temp)  # Scale perturbation with temperature
        
        for idx in indices:
            # Sample directions that are likely to improve triangle areas
            best_dir_improvement = -np.inf
            best_dir_point = None
            
            # For each critical triangle involving this point, compute a beneficial direction
            for i, j, k, tri_area in critical_triangles:
                if idx not in [i, j, k]:
                    continue
                
                # Get the opposite edge
                if idx == i:
                    p1, p2 = points[j], points[k]
                elif idx == j:
                    p1, p2 = points[i], points[k]
                else:
                    p1, p2 = points[i], points[j]
                
                # Compute perpendicular direction that increases area
                AB = p2 - p1
                AP = points[idx] - p1
                cross = AB[0]*AP[1] - AB[1]*AP[0]
                
                if cross > 0:
                    direction = np.array([-AB[1], AB[0]])
                else:
                    direction = np.array([AB[1], -AB[0]])
                
                if np.linalg.norm(direction) < 1e-10:
                    continue
                direction = direction / np.linalg.norm(direction)
                
                # Try this direction and variations
                for angle_offset in [0, 15, -15]:
                    # Rotate direction
                    angle = np.radians(angle_offset)
                    rotation_matrix = np.array([
                        [np.cos(angle), -np.sin(angle)],
                        [np.sin(angle), np.cos(angle)]
                    ])
                    dir_rotated = rotation_matrix @ direction
                    
                    # Apply step
                    candidate_point = points[idx] + std * dir_rotated
                    
                    # Project back to triangle if needed
                    candidate_point = project_to_triangle(candidate_point, A, B, C)
                    
                    # Check improvement
                    candidate[idx] = candidate_point
                    candidate_min_area = get_smallest_triangle_area(candidate)
                    improvement = candidate_min_area - current_min_area
                    
                    if improvement > best_dir_improvement:
                        best_dir_improvement = improvement
                        best_dir_point = candidate_point.copy()
                    
                    # Restore for next direction test
                    candidate[idx] = points[idx]
            
            if best_dir_point is not None:
                candidate[idx] = best_dir_point
        
        candidate_min_area = get_smallest_triangle_area(candidate)
        delta = candidate_min_area - current_min_area
        
        # Simulated annealing: accept worsening moves with probability exp(delta/temp)
        if delta > 0 or random.random() < np.exp(delta / temp):
            points = candidate
            current_min_area = candidate_min_area
            
            # Track best solution
            if candidate_min_area > best_min_area:
                best_points = points.copy()
                best_min_area = candidate_min_area
            
            # Reset step size on improvement
            step_size = 0.02
        else:
            # Only decay step size if no improvement
            step_size *= step_decay
            if step_size < min_step:
                step_size = min_step
        
        # Cool the temperature
        temp *= cooling_rate
    
    return best_points