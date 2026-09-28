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
    
    # Best configuration tracking across restarts
    best_points = None
    best_min_area = -1
    
    # Increased restarts with diverse patterns
    num_restarts = 10
    for restart in range(num_restarts):
        # Randomly select row pattern
        row_points = random.choice(candidate_patterns)
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
                
                # Reduced perturbation magnitude to maintain validity
                perturbation = np.random.uniform(-0.05, 0.05, size=2)
                P = P + perturbation
                
                # Ensure point is inside the triangle
                if is_inside_triangle(P, *tri):
                    points.append(P)
                else:
                    # Project back to triangle if outside
                    v_adj = min(v, 1.0 - 1e-5)
                    u_adj = min(u, (1 - v_adj) * (1 - 1e-5))
                    P = (1 - u_adj - v_adj) * A + u_adj * B + v_adj * C
                    points.append(P)
        
        current_points = np.array(points)
        
        # Enhanced simulated annealing parameters
        initial_temperature = 0.1
        cooling_rate = 0.995  # Slower cooling
        min_temperature = 1e-5
        max_iter = 5000  # More iterations
        
        temperature = initial_temperature
        current_min_area = get_smallest_triangle_area(current_points)
        
        # Track best within this restart
        local_best_points = current_points.copy()
        local_best_min_area = current_min_area
        
        for it in range(max_iter):
            # Adaptive tolerance based on current temperature
            tolerance = max(1e-6, 1e-3 * (temperature / initial_temperature))
            
            # Find all critical triangles within tolerance
            min_area = float('inf')
            critical_triangles = []  # (i, j, k, area)
            
            for i in range(11):
                for j in range(i + 1, 11):
                    for k in range(j + 1, 11):
                        area = triangle_area(current_points[i], 
                                            current_points[j], 
                                            current_points[k])
                        if area < min_area - 1e-10:
                            min_area = area
                            critical_triangles = [(i, j, k, area)]
                        elif abs(area - min_area) <= tolerance:
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
                    
                    # Weight by criticality (more critical = higher weight)
                    weight = 1.0 / (area - min_area + 1e-8)
                    grad += weight * direction
                    total_weight += weight

                if total_weight > 0:
                    gradients[idx] = grad / total_weight

            # Decide between single-point or multi-point move
            if np.random.random() < 0.3 and len(critical_triangles) > 0:
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
                        # Adaptive projection for boundary recovery
                        for scale in [0.75, 0.5, 0.25, 0.1]:
                            candidate_pt = current_points[pt] + move_vec * scale
                            if is_inside_triangle(candidate_pt, *tri):
                                new_pt = candidate_pt
                                break
                        else:
                            valid_move = False
                            break
                    candidate[pt] = new_pt
                
                if not valid_move:
                    temperature *= cooling_rate
                    continue
                
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
                    for scale in [0.75, 0.5, 0.25, 0.1]:
                        candidate[point_idx] = current_points[point_idx] + move * scale
                        if is_inside_triangle(candidate[point_idx], *tri):
                            break
                    else:
                        temperature *= cooling_rate
                        continue

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
    
    return best_points