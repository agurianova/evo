import random

from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def project_to_boundary(point, A, B, C):
    """Project a point to the nearest boundary of the unit triangle with boundary repulsion"""
    # Check if point is already inside
    if is_inside_triangle(point, A, B, C):
        return point
    
    # Function to project point to line segment
    def project_to_segment(p, a, b):
        ap = p - a
        ab = b - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)  # Avoid division by zero
        t = max(0, min(1, t))
        return a + t * ab
    
    # Project to each edge
    p_ab = project_to_segment(point, A, B)
    p_bc = project_to_segment(point, B, C)
    p_ca = project_to_segment(point, C, A)
    
    # Find closest projection
    d_ab = np.linalg.norm(point - p_ab)
    d_bc = np.linalg.norm(point - p_bc)
    d_ca = np.linalg.norm(point - p_ca)
    
    if d_ab <= d_bc and d_ab <= d_ca:
        boundary_point = p_ab
        edge = (A, B)
    elif d_bc <= d_ab and d_bc <= d_ca:
        boundary_point = p_bc
        edge = (B, C)
    else:
        boundary_point = p_ca
        edge = (C, A)

    # Apply boundary repulsion to prevent clustering
    edge_vector = edge[1] - edge[0]
    edge_length = np.linalg.norm(edge_vector)
    if edge_length > 1e-5:
        edge_dir = edge_vector / edge_length
        
        # Check nearby boundary points for repulsion
        repulsion_force = np.zeros(2)
        for i in range(len(current_points)):
            p = current_points[i]
            if is_inside_triangle(p, A, B, C):
                continue
            
            # Project this point to the same edge
            p_edge = project_to_segment(p, edge[0], edge[1])
            dist_along_edge = np.dot(p_edge - edge[0], edge_dir)
            
            # Only consider points on the same edge
            if 0 <= dist_along_edge <= edge_length:
                current_dist_along_edge = np.dot(boundary_point - edge[0], edge_dir)
                dist = abs(current_dist_along_edge - dist_along_edge)
                
                # Apply repulsion if points are close along the edge
                if dist < 0.1 * edge_length:
                    direction = 1 if current_dist_along_edge > dist_along_edge else -1
                    repulsion_force += direction * edge_dir / max(dist, 1e-5)

        # Apply repulsion (scaled by distance to original point)
        if np.linalg.norm(repulsion_force) > 1e-5:
            repulsion_force = repulsion_force / np.linalg.norm(repulsion_force)
            boundary_point += 0.02 * edge_length * repulsion_force
            
            # Re-project if needed
            if not is_inside_triangle(boundary_point, A, B, C):
                boundary_point = project_to_segment(boundary_point, edge[0], edge[1])

    return boundary_point

def find_smallest_triangle_indices(points):
    n = points.shape[0]
    min_area = float('inf')
    best_indices = None
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Create a temporary array with just these 3 points
                tri_points = np.array([points[i], points[j], points[k]])
                area = get_smallest_triangle_area(tri_points)
                if area < min_area:
                    min_area = area
                    best_indices = (i, j, k)
    
    return best_indices

def calculate_repulsion_energy(points):
    """Calculate soft repulsion energy based on point distances"""
    n = points.shape[0]
    energy = 0.0
    for i in range(n):
        for j in range(i+1, n):
            dist = np.linalg.norm(points[i] - points[j])
            # Inverse distance repulsion (soft constraint)
            energy += 1.0 / max(dist, 1e-5)
    return energy

def entrypoint() -> np.ndarray:
    global current_points
    A, B, C = get_unit_triangle()
    
    # Balanced row distributions that sum to 11
    # Removed extreme asymmetric distributions like [5,3,2,1] and [5,2,2,2]
    row_distributions = [
        [4, 3, 2, 2],
        [4, 4, 2, 1],
        [3, 3, 3, 2],
        [3, 4, 2, 2],
        [4, 3, 3, 1]
    ]
    
    # Add small random variation to distribution for more diversity
    if random.random() < 0.3:
        dist = random.choice(row_distributions)
        idx1, idx2 = random.sample(range(len(dist)), 2)
        if dist[idx1] > 1 and idx2 != 0:  # Ensure we don't make first row too small
            dist[idx1] -= 1
            dist[idx2] += 1
        row_points = dist
    else:
        row_points = random.choice(row_distributions)
    
    points = []
    rows = len(row_points)

    # Construct grid
    for i in range(rows):
        v = (i + 0.5) / rows
        num_in_row = row_points[i]
        
        for j in range(num_in_row):
            # Distribute points across the row
            u = (j + 0.5) / num_in_row * (1 - v)
            
            # Barycentric coordinates
            P = (1 - u - v) * A + u * B + v * C
            points.append(P)

    current = np.array(points)
    current_points = current  # For boundary repulsion
    current_score = get_smallest_triangle_area(current)
    current_repulsion = calculate_repulsion_energy(current)

    # Enhanced simulated annealing parameters
    initial_temp = 0.01
    cooling_rate = 0.99
    n_iterations = 5000
    temp = initial_temp
    
    # Track best solution found
    best = current.copy()
    best_score = current_score
    best_repulsion = current_repulsion

    for _ in range(n_iterations):
        # Adaptive targeting probability (slower decay from 0.7 to 0.5)
        target_smallest_prob = 0.7 * (temp / initial_temp) + 0.5 * (1 - temp / initial_temp)

        # Determine which points to perturb
        if random.random() < target_smallest_prob:
            i, j, k = find_smallest_triangle_indices(current)
            
            # 25% chance for coordinated 3-point move
            if random.random() < 0.25:
                # Calculate geometrically coordinated movement
                a, b, c = current[i], current[j], current[k]
                
                # Calculate triangle center
                center = (a + b + c) / 3
                
                # Move each point away from center
                candidate = current.copy()
                for idx, p in zip([i, j, k], [a, b, c]):
                    direction = p - center
n                    if np.linalg.norm(direction) > 1e-5:
                        direction = direction / np.linalg.norm(direction)
                        step_size = 0.01 * (temp / initial_temp)
                        candidate[idx] += direction * step_size
                
                # Check if valid
                valid = True
                for idx in [i, j, k]:
                    candidate[idx] = project_to_boundary(candidate[idx], A, B, C)
                    if not is_inside_triangle(candidate[idx], A, B, C):
                        valid = False
                        break
                
                if valid:
                    current = candidate
                    current_score = get_smallest_triangle_area(current)
                    current_repulsion = calculate_repulsion_energy(current)
                    
                    # Update best solution if improved
                    if current_score > best_score:
                        best = candidate.copy()
                        best_score = current_score
                        best_repulsion = current_repulsion
                    
                    # Cool down and continue to next iteration
                    temp *= cooling_rate
                    continue
            
            # Regular single-point targeting
            idx = random.choice([i, j, k])
        else:
            idx = np.random.randint(0, 11)

        # Improved step size adaptation using reciprocal scaling for top regions
        v_pos = current[idx][1] / C[1]  # Normalize y-coordinate to [0,1]
        step_size = 0.015 * (1 / (1 - v_pos + 0.1)) * (temp / initial_temp)
        
        step = np.random.normal(0, step_size, size=2)
        candidate = current.copy()

        # Apply move to the selected point
        candidate[idx] += step

        # Project out-of-bound points to boundary with repulsion
        current_points = candidate  # Update for boundary repulsion
        candidate[idx] = project_to_boundary(candidate[idx], A, B, C)

        # Calculate repulsion energy (soft constraint)
        candidate_repulsion = calculate_repulsion_energy(candidate)
        
        # Combined score: triangle area minus repulsion penalty (100x stronger)
        repulsion_penalty = 0.05 * temp * candidate_repulsion
        score = get_smallest_triangle_area(candidate) - repulsion_penalty
        
        # Current state with repulsion penalty
        current_total = current_score - 0.05 * temp * current_repulsion
        
        # Calculate acceptance probability
        delta = score - current_total
        if delta > 0 or random.random() < np.exp(delta / temp):
            current = candidate
            current_score = get_smallest_triangle_area(current)
            current_repulsion = candidate_repulsion
            
            # Update best solution if improved (using raw area, not penalized score)
            if current_score > best_score:
                best = candidate.copy()
                best_score = current_score
                best_repulsion = current_repulsion

        # Cool down
        temp *= cooling_rate

    return best