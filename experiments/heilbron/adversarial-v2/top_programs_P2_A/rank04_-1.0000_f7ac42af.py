import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

# Helper function to compute gradient for triangle area improvement
def compute_triangle_gradient(p0, p1, p2):
    # Compute signed area
    s_val = 0.5 * ((p1[0]-p0[0])*(p2[1]-p0[1]) - (p1[1]-p0[1])*(p2[0]-p0[0]))
    
    # Compute gradient directions for each point
    dir0 = np.array([p1[1]-p2[1], p2[0]-p1[0]])
    if s_val < 0:
        dir0 = -dir0
    
    dir1 = np.array([p2[1]-p0[1], p0[0]-p2[0]])
    if s_val < 0:
        dir1 = -dir1
    
    dir2 = np.array([p0[1]-p1[1], p1[0]-p0[0]])
    if s_val < 0:
        dir2 = -dir2
    
    # Normalize directions
    for i, d in enumerate([dir0, dir1, dir2]):
        norm = np.linalg.norm(d)
        if norm > 1e-8:
            if i == 0:
                dir0 = d / norm
            elif i == 1:
                dir1 = d / norm
            else:
                dir2 = d / norm
        else:
            if i == 0:
                dir0 = np.array([0.0, 0.0])
            elif i == 1:
                dir1 = np.array([0.0, 0.0])
            else:
                dir2 = np.array([0.0, 0.0])
                
    return dir0, dir1, dir2, abs(s_val)

def find_critical_triplet(points):
    n = len(points)
    min_area = float('inf')
    critical_triplet = None
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                p0, p1, p2 = points[i], points[j], points[k]
                area_val = 0.5 * abs((p1[0]-p0[0])*(p2[1]-p0[1]) - (p1[1]-p0[1])*(p2[0]-p0[0]))
                if area_val < min_area and area_val > 1e-10:
                    min_area = area_val
                    critical_triplet = (i, j, k)
                    
    return critical_triplet, min_area

def generate_symmetric_configuration(A, B, C):
    # Generate symmetric configuration based on known good patterns for equilateral triangles
    # We'll create points along symmetry axes and use reflection
    
    # Calculate triangle center and axes
    center = (A + B + C) / 3
    mid_AB = (A + B) / 2
    mid_BC = (B + C) / 2
    mid_CA = (C + A) / 2
    
    # Symmetry axes
    axis_A = (A + mid_BC) / 2
    axis_B = (B + mid_CA) / 2
    axis_C = (C + mid_AB) / 2
    
    # Create symmetric pattern with 11 points
    points = []
    
    # Center point
    points.append(center)
    
    # Points along symmetry axes at different radii
    radii = [0.15, 0.3, 0.45]
    
    # Points on axis A
    for r in radii:
        p = A + r * (center - A)
        points.append(p)
    
    # Points on axis B (reflected from axis A)
    for r in radii:
        # Reflect point across altitude from B
        p = B + r * (center - B)
        points.append(p)
    
    # Points on axis C (reflected from axis A)
    for r in radii:
        # Reflect point across altitude from C
        p = C + r * (center - C)
        points.append(p)
    
    # We have 10 points, need one more - add a point slightly offset from center
    points.append(center + np.array([0.05, 0.02]))
    
    # Ensure all points are inside the triangle
    valid_points = []
    for p in points:
        if is_inside_triangle(p, A, B, C):
            valid_points.append(p)
        else:
            # Project back inside if necessary
            valid_points.append(project_to_triangle(p, A, B, C))
    
    return np.array(valid_points[:11])

def project_to_triangle(point, A, B, C):
    # Simple projection: find closest point on triangle boundary if outside
    if is_inside_triangle(point, A, B, C):
        return point
    
    # Check each edge
    min_dist = float('inf')
    closest_point = point
    
    # AB edge
    ab = B - A
    ap = point - A
    t = np.dot(ap, ab) / np.dot(ab, ab)
    t = max(0, min(1, t))
    proj = A + t * ab
n    dist = np.linalg.norm(point - proj)
    if dist < min_dist:
        min_dist = dist
        closest_point = proj
    
    # BC edge
    bc = C - B
    bp = point - B
    t = np.dot(bp, bc) / np.dot(bc, bc)
    t = max(0, min(1, t))
    proj = B + t * bc
    dist = np.linalg.norm(point - proj)
    if dist < min_dist:
        min_dist = dist
        closest_point = proj
    
    # CA edge
    ca = A - C
    cp = point - C
    t = np.dot(cp, ca) / np.dot(ca, ca)
    t = max(0, min(1, t))
    proj = C + t * ca
    dist = np.linalg.norm(point - proj)
    if dist < min_dist:
        min_dist = dist
        closest_point = proj
    
    return closest_point

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Generate initial symmetric configuration
    points = generate_symmetric_configuration(A, B, C)
    
    # Simulated annealing parameters
    initial_temp = 0.1
    temp = initial_temp
    cooling_rate = 0.995  # Slower cooling than opponent to maintain exploration
    min_temp = 1e-5
    base_step = 0.05
    max_no_improve = 50
    max_iter = 1000
    
    no_improve_count = 0
    iter_count = 0
    best_points = points.copy()
    best_score = get_smallest_triangle_area(best_points)
    
    while temp > min_temp and no_improve_count < max_no_improve and iter_count < max_iter:
        iter_count += 1

        # Find critical triplet (smallest triangle)
        critical_triplet, min_area = find_critical_triplet(points)
        if critical_triplet is None:
            temp *= cooling_rate
            continue

        i0, i1, i2 = critical_triplet
        p0, p1, p2 = points[i0], points[i1], points[i2]

        # Compute gradient directions
        dir0, dir1, dir2, _ = compute_triangle_gradient(p0, p1, p2)

        # Adaptive step size based on temperature
        step = base_step * (temp / initial_temp)

        # Create candidate by moving points along gradient directions
        candidate = points.copy()
        candidate[i0] += step * dir0
        candidate[i1] += step * dir1
        candidate[i2] += step * dir2

        # Check constraints
        if not is_inside_triangle(candidate, A, B, C):
            # Try a smaller step
            step *= 0.5
            candidate = points.copy()
            candidate[i0] += step * dir0
            candidate[i1] += step * dir1
            candidate[i2] += step * dir2
            
            if not is_inside_triangle(candidate, A, B, C):
                temp *= cooling_rate
                continue

        score = get_smallest_triangle_area(candidate)
        if score <= 0:  # Collinear triplet
            temp *= cooling_rate
            continue

        # Simulated annealing acceptance
        current_score = get_smallest_triangle_area(points)
        if score > best_score:
            best_points = candidate.copy()
            best_score = score
            no_improve_count = 0
        
        if score > current_score:
            points = candidate
            no_improve_count = 0
        else:
            delta = current_score - score
            if np.random.rand() < np.exp(-delta / temp):
                points = candidate
                no_improve_count = 0
            else:
                no_improve_count += 1

        temp *= cooling_rate

    return best_points