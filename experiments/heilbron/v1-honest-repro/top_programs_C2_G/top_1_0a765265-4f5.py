import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

# Fixed seed for reproducibility
np.random.seed(42)
random.seed(42)

def triangle_area(a, b, c):
    """Calculate area of triangle given three points."""
    return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

def triangle_aspect_ratio(a, b, c):
    """Calculate aspect ratio of triangle (1.0 for equilateral, lower for flatter triangles)."""
    # Calculate sides
    ab = np.linalg.norm(b - a)
    bc = np.linalg.norm(c - b)
    ca = np.linalg.norm(a - c)
    
    # Semi-perimeter
    s = (ab + bc + ca) / 2
    
    # Area (using Heron's formula)
    area = np.sqrt(max(0, s * (s - ab) * (s - bc) * (s - ca)))
    
    if area < 1e-10:
        return 0.0
    
    # Circumradius
    R = (ab * bc * ca) / (4 * area)
    
    # Aspect ratio: 4*area/(3*sqrt(3)*R^2) for equilateral = 1
    aspect_ratio = 4 * area / (3 * np.sqrt(3) * R * R)
    return aspect_ratio

def project_to_boundary(point, A, B, C):
    """Project point to nearest location on triangle boundary."""
    # Check distance to each edge
    def point_to_line_distance(p, a, b):
        ap = p - a
        ab = b - a
        t = np.dot(ap, ab) / np.dot(ab, ab)
        t = max(0, min(1, t))
        projection = a + t * ab
        return projection, np.linalg.norm(ap - (t * ab))
    
    # Get projections to all three edges
    proj_AB, dist_AB = point_to_line_distance(point, A, B)
    proj_BC, dist_BC = point_to_line_distance(point, B, C)
    proj_CA, dist_CA = point_to_line_distance(point, C, A)
    
    # Choose closest projection
    if dist_AB <= dist_BC and dist_AB <= dist_CA:
        return proj_AB
    elif dist_BC <= dist_AB and dist_BC <= dist_CA:
        return proj_BC
    else:
        return proj_CA

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Candidate row patterns for n=11 points
    candidate_patterns = [
        [4, 3, 2, 2],  # 4+3+2+2=11
        [4, 4, 2, 1],  # 4+4+2+1=11
        [3, 3, 3, 2],  # 3+3+3+2=11
        [5, 3, 2, 1]   # 5+3+2+1=11
    ]
    
    # Pattern success tracking
    pattern_success = {str(pattern): 0 for pattern in candidate_patterns}
    pattern_attempts = {str(pattern): 0 for pattern in candidate_patterns}

    # Best configuration tracking across restarts
    best_points = None
    best_min_area = -1
    
    # Increased restarts with diverse patterns
    num_restarts = 15
    for restart in range(num_restarts):
        # Select pattern with weighted probability based on success rate
        weights = []
        for pattern in candidate_patterns:
            pattern_str = str(pattern)
            success_rate = pattern_success[pattern_str] / max(1, pattern_attempts[pattern_str])
            weights.append(success_rate + 0.1)  # Add small constant to avoid zero weights

        # Normalize weights
        total = sum(weights)
        if total > 0:
            weights = [w/total for w in weights]
            row_points = random.choices(candidate_patterns, weights=weights, k=1)[0]
        else:
            row_points = random.choice(candidate_patterns)
            
        pattern_attempts[str(row_points)] += 1
        rows = len(row_points)
        
        points = []
        # Calculate row heights to distribute points evenly in the triangle
        for row in range(rows):
            num = row_points[row]
            # Height parameter v: 0 at base, 1 at apex
            v = (row + 0.5) / rows
            
            for i in range(num):
                # Horizontal parameter u: 0 at left edge, 1-v at right edge
                u = (i + 0.5) / num * (1 - v)
                
                # Convert barycentric to Cartesian coordinates
                P = (1 - u - v) * A + u * B + v * C
                
                # Apply symmetry breaking (50% chance)
                if random.random() < 0.5:
                    asymmetry = np.random.uniform(-0.01, 0.01, size=2)
                    # Position-dependent asymmetry
                    asym_factor = (row + i) * 0.1
                    P = P + asymmetry * asym_factor
                
                # Adaptive perturbation magnitude based on row position
                perturbation_magnitude = 0.03 * (1 - v)  # Smaller perturbations near apex
                perturbation = np.random.uniform(-perturbation_magnitude, perturbation_magnitude, size=2)
                P = P + perturbation
                
                # Ensure point is inside the triangle
                if is_inside_triangle(P, *tri):
                    points.append(P)
                else:
                    # Smarter boundary projection
                    P = project_to_boundary(P, A, B, C)
                    points.append(P)
        
        current_points = np.array(points)
        
        # Enhanced simulated annealing parameters
        initial_temperature = 0.1
        cooling_rate = 0.995  # Slower cooling
        min_temperature = 1e-5
        max_iter = 6000  # More iterations
        
        temperature = initial_temperature
        current_min_area = get_smallest_triangle_area(current_points)
        
        # Track best within this restart
        local_best_points = current_points.copy()
        local_best_min_area = current_min_area
        
        # Track symmetry metrics
        symmetry_break_count = 0
        
        for it in range(max_iter):
            # Collect all triangle areas for dynamic tolerance
            all_areas = []
            for i in range(11):
                for j in range(i + 1, 11):
                    for k in range(j + 1, 11):
                        area = triangle_area(current_points[i], 
                                            current_points[j], 
                                            current_points[k])
                        all_areas.append(area)

            all_areas.sort()
            min_area = all_areas[0]
            # Include triangles within top 5% of critical values
            critical_percentile = min(5, len(all_areas) - 1)
            tolerance = max(1e-6, 0.05 * (all_areas[critical_percentile] - min_area))

            # Find all critical triangles within tolerance
            critical_triangles = []  # (i, j, k, area)
            for i in range(11):
                for j in range(i + 1, 11):
                    for k in range(j + 1, 11):
                        area = triangle_area(current_points[i], 
                                            current_points[j], 
                                            current_points[k])
                        if abs(area - min_area) <= tolerance:
                            critical_triangles.append((i, j, k, area))
            
            # If no critical triangles found, skip (shouldn't happen)
            if not critical_triangles:
                temperature *= cooling_rate
                continue

            # Compute gradient directions for all points
            gradients = np.zeros((11, 2))
            for idx in range(11):
                total_weight = 0.0
                grad = np.zeros(2)
                
                # Check all critical triangles containing this point
                for (i, j, k, area) in critical_triangles:
                    if idx not in (i, j, k):
                        continue
                    
                    # Determine the base points for this triangle
                    if idx == i:
                        base_p1, base_p2 = current_points[j], current_points[k]
                    elif idx == j:
                        base_p1, base_p2 = current_points[i], current_points[k]
                    else:  # idx == k
                        base_p1, base_p2 = current_points[i], current_points[j]
                    
                    # Compute perpendicular direction to increase area
                    base_vec = base_p2 - base_p1
                    perp_vec = np.array([-base_vec[1], base_vec[0]])
                    norm = np.linalg.norm(perp_vec)
                    if norm < 1e-8:
                        continue
                    perp_vec = perp_vec / norm
                    
                    apex = current_points[idx]
                    to_apex = apex - base_p1
                    height = np.dot(to_apex, perp_vec)
                    direction = perp_vec * np.sign(height)
                    
                    # Geometry-aware weighting: prioritize flatter triangles
                    aspect_ratio = triangle_aspect_ratio(base_p1, base_p2, apex)
                    # Higher weight for flatter triangles (lower aspect ratio)
                    geometry_weight = 1.0 - min(1.0, aspect_ratio)
                    # Weight by criticality (more critical = higher weight)
                    critical_weight = 1.0 / (area - min_area + 1e-8)
                    weight = critical_weight * (1.0 + 2.0 * geometry_weight)
                    
                    grad += weight * direction
                    total_weight += weight

                if total_weight > 0:
                    gradients[idx] = grad / total_weight

            # Dynamic multi-point move probability based on critical triangles and symmetry
            critical_count = len(critical_triangles)
            # Scale from 0.3 to 0.9 based on critical triangle count
            multi_point_prob = min(0.9, 0.3 + 0.6 * (critical_count / 15.0))
            # Increase probability if symmetry detected
            if symmetry_break_count < 2:
                multi_point_prob = min(0.95, multi_point_prob * 1.2)

            if np.random.random() < multi_point_prob and critical_count > 0:
                # Multi-point move: select random critical triangle
                i, j, k, _ = critical_triangles[np.random.randint(0, len(critical_triangles))]
                points_to_move = [i, j, k]
                step_per_point = temperature * 0.5 / np.sqrt(3)  # Scale for 3 points
                
                candidate = current_points.copy()
                valid_move = True
                
                for pt in points_to_move:
                    # Compute move vector with gradient and random component
                    move_vec = gradients[pt] * step_per_point
                    random_comp = np.random.normal(0, 0.1, size=2)
                    move_vec += random_comp * (step_per_point * 0.2)
                    
                    new_pt = current_points[pt] + move_vec
                    if not is_inside_triangle(new_pt, *tri):
                        # Smarter boundary projection
                        new_pt = project_to_boundary(new_pt, A, B, C)
                        
                        # Check if we're creating symmetry
                        if symmetry_break_count < 2:
                            # Add small asymmetric perturbation
                            asymmetry = np.random.uniform(-0.001, 0.001, size=2)
                            new_pt = new_pt + asymmetry
                            symmetry_break_count += 1

                    candidate[pt] = new_pt
                
            else:
                # Single-point move: select random point with non-zero gradient
                candidate_points = [p for p in range(11) 
                                  if np.linalg.norm(gradients[p]) > 1e-8]
                if not candidate_points:
                    temperature *= cooling_rate
                    continue
                
                point_idx = random.choice(candidate_points)
                direction = gradients[point_idx]
                norm_dir = np.linalg.norm(direction)
                if norm_dir < 1e-8:
                    temperature *= cooling_rate
                    continue
                direction = direction / norm_dir  # Normalize
                
                step = temperature * 0.5
                move = direction * step
                random_comp = np.random.normal(0, 0.1, size=2)
                move += random_comp * (step * 0.2)
                
                candidate = current_points.copy()
                candidate[point_idx] += move
                
                if not is_inside_triangle(candidate[point_idx], *tri):
                    # Smarter boundary projection
                    candidate[point_idx] = project_to_boundary(candidate[point_idx], A, B, C)
                    
                    # Check if we're creating symmetry
                    if symmetry_break_count < 2:
                        # Add small asymmetric perturbation
                        asymmetry = np.random.uniform(-0.001, 0.001, size=2)
                        candidate[point_idx] = candidate[point_idx] + asymmetry
                        symmetry_break_count += 1

            # Calculate new minimum area
            new_min_area = get_smallest_triangle_area(candidate)
            
            # Acceptance probability
            if new_min_area > current_min_area:
                accept = True
                delta = new_min_area - current_min_area
            else:
                delta = new_min_area - current_min_area
                if temperature > min_temperature:
                    accept_prob = math.exp(delta / temperature)
                    accept = random.random() < accept_prob
                else:
                    accept = False
            
            if accept:
                current_points = candidate
                current_min_area = new_min_area
                
                if new_min_area > local_best_min_area:
                    local_best_points = candidate.copy()
                    local_best_min_area = new_min_area
            
            # Cool down
            temperature *= cooling_rate
            
            # Early termination
            if temperature < min_temperature:
                break
        
        # Update global best across restarts
        if local_best_min_area > best_min_area:
            best_points = local_best_points.copy()
            best_min_area = local_best_min_area
            pattern_success[str(row_points)] += 1
    
    return best_points