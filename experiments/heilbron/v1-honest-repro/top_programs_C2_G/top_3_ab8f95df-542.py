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
    
    # Diverse row patterns for exploration
    row_patterns = [
        [4, 3, 2, 2],  # Pattern 1
        [4, 4, 2, 1],  # Pattern 2
        [3, 3, 3, 2],  # Pattern 3 (original)
    ]
    
    # Best configuration tracking across restarts
    best_points = None
    best_min_area = -1
    
    # Increased restarts with pattern cycling
    num_restarts = 10
    for restart in range(num_restarts):
        # Cycle through row patterns
        pattern_idx = restart % len(row_patterns)
        row_points = row_patterns[pattern_idx]
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
        max_iter = 5000       # Increased iterations
        initial_tolerance = 1e-3

        temperature = initial_temperature
        current_min_area = get_smallest_triangle_area(current_points)
        
        # Track best within this restart
        local_best_points = current_points.copy()
        local_best_min_area = current_min_area
        
        for it in range(max_iter):
            # Adaptive area tolerance (decays from 1e-3 to 1e-6)
            tolerance = initial_tolerance * (cooling_rate ** it)
            tolerance = max(1e-6, tolerance)

            # Find all triangles within tolerance of minimal area
            min_area = float('inf')
            critical_triangles = []  # (i, j, k, area)
            
            for i in range(11):
                for j in range(i + 1, 11):
                    for k in range(j + 1, 11):
                        area = triangle_area(current_points[i], 
                                            current_points[j], 
                                            current_points[k])
                        if area < min_area - tolerance:
                            min_area = area
                            critical_triangles = [(i, j, k, area)]
                        elif abs(area - min_area) <= tolerance:
                            critical_triangles.append((i, j, k, area))
            
            # If no critical triangles found, skip
            if not critical_triangles:
                continue

            # 20% chance of coordinated multi-point move
            if random.random() < 0.2 and len(critical_triangles) > 0:
                # Select one critical triangle
                i, j, k, _ = critical_triangles[np.random.randint(0, len(critical_triangles))]
                triangle_points = [i, j, k]
                candidate = current_points.copy()
                move_success = True

                # Compute moves for all three points
                for idx in triangle_points:
                    # Determine base points (the other two in the triangle)
                    base_indices = [p for p in triangle_points if p != idx]
                    base_p1, base_p2 = current_points[base_indices[0]], current_points[base_indices[1]]

                    # Vector along the base
                    base_vec = base_p2 - base_p1
                    # Perpendicular vector
                    perp_vec = np.array([-base_vec[1], base_vec[0]])

                    # Normalize
                    norm = np.linalg.norm(perp_vec)
                    if norm < 1e-8:
                        direction = np.zeros(2)
                    else:
                        perp_vec = perp_vec / norm
                        
                        # Current position of the point we're moving
                        apex = current_points[idx]
                        # Vector from base_p1 to apex
                        to_apex = apex - base_p1
                        # Height
                        height = np.dot(to_apex, perp_vec)
                        
                        # Direction to move: away from the base line
                        direction = perp_vec * np.sign(height)

                    # Step size proportional to temperature (reduced for multi-point)
                    step = temperature * 0.25

                    # Add random exploration component
                    random_component = np.random.normal(0, 0.1, size=2)
                    move = direction * step + random_component * (step * 0.2)

                    # Apply move to candidate
                    candidate[idx] += move

                    # Check if candidate point is inside the triangle
                    if not is_inside_triangle(candidate[idx], *tri):
                        # Try smaller steps
                        for scale in [0.75, 0.5, 0.25, 0.1]:
                            smaller_move = move * scale
                            candidate[idx] = current_points[idx] + smaller_move
                            if is_inside_triangle(candidate[idx], *tri):
                                break
                        else:
                            move_success = False
                            break

                # Skip if any point couldn't be moved inside
                if not move_success:
                    temperature *= cooling_rate
                    continue

                # Calculate new minimum area
                new_min_area = get_smallest_triangle_area(candidate)

                # Acceptance logic
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

            else:
                # Original single-point move (with adaptive tolerance)
                i, j, k, _ = critical_triangles[np.random.randint(0, len(critical_triangles))]
                
                # Randomly select one vertex from the triangle to move
                point_idx = np.random.choice([i, j, k])
                
                # Compute direction to increase area of this triangle
                if point_idx == i:
                    base_p1, base_p2 = current_points[j], current_points[k]
                elif point_idx == j:
                    base_p1, base_p2 = current_points[i], current_points[k]
                else:
                    base_p1, base_p2 = current_points[i], current_points[j]
                
                # Vector along the base
                base_vec = base_p2 - base_p1
                # Perpendicular vector
                perp_vec = np.array([-base_vec[1], base_vec[0]])
                
                # Normalize
                norm = np.linalg.norm(perp_vec)
                if norm < 1e-8:
                    direction = np.zeros(2)
                else:
                    perp_vec = perp_vec / norm
                    
                    # Current position of the point we're moving
                    apex = current_points[point_idx]
                    # Vector from base_p1 to apex
                    to_apex = apex - base_p1
                    # Projection along perpendicular gives height
                    height = np.dot(to_apex, perp_vec)
                    
                    # Direction to move: away from the base line
                    direction = perp_vec * np.sign(height)
                
                # Step size proportional to temperature
                step = temperature * 0.5
                
                # Add random exploration component
                random_component = np.random.normal(0, 0.1, size=2)
                move = direction * step + random_component * (step * 0.2)
                
                # Create candidate by moving the point
                candidate = current_points.copy()
                candidate[point_idx] += move
                
                # Check if candidate point is inside the triangle
                if not is_inside_triangle(candidate[point_idx], *tri):
                    # Try smaller steps
                    for scale in [0.75, 0.5, 0.25, 0.1]:
                        smaller_move = move * scale
                        candidate[point_idx] = current_points[point_idx] + smaller_move
                        if is_inside_triangle(candidate[point_idx], *tri):
                            break
                    else:
                        # Skip this move
                        temperature *= cooling_rate
                        continue
                
                # Calculate new minimum area
                new_min_area = get_smallest_triangle_area(candidate)
                
                # Acceptance logic
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
            
            # Early termination if temperature too low
            if temperature < min_temperature:
                break
        
        # Update global best across restarts
        if local_best_min_area > best_min_area:
            best_points = local_best_points.copy()
            best_min_area = local_best_min_area
    
    return best_points