import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.spatial import Delaunay
import matplotlib.pyplot as plt

np.random.seed(42)

def delaunay_area_initialization(triangle, n_points):
    A, B, C = triangle
    
    # Start with random barycentric points
    points = random_barycentric_points(triangle, n_points)
    
    # Iterative refinement based on triangle areas
    for _ in range(30):
        # Compute Delaunay triangulation
        try:
            tri = Delaunay(points)
        except:
            # Fall back to random if Delaunay fails
            return random_barycentric_points(triangle, n_points)
        
        # Calculate area for each triangle in the triangulation
        areas = []
        for simplex in tri.simplices:
            a, b, c = points[simplex]
            area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
            areas.append(area)
        
        # If we have no valid triangles, break
        if not areas or min(areas) < 1e-10:
            break
        
        # Find the smallest triangle area
        min_area_idx = np.argmin(areas)
        min_area = areas[min_area_idx]
        worst_simplex = tri.simplices[min_area_idx]
        
        # Calculate centroid of the worst triangle
        centroid = np.mean(points[worst_simplex], axis=0)
        
        # Find the point in the worst triangle that contributes most to small area
        # (the one closest to the opposite edge)
        worst_point_idx = None
        max_dist_to_edge = -1
        
        for i, idx in enumerate(worst_simplex):
            # Get the other two points forming the edge
            edge_points = [points[worst_simplex[j]] for j in range(3) if j != i]
            p1, p2 = edge_points
            
            # Calculate distance from point to edge
            edge_vec = p2 - p1
            point_vec = points[idx] - p1
            edge_len = np.linalg.norm(edge_vec)
            if edge_len > 1e-10:
                # Project point_vec onto edge_vec
                proj = np.dot(point_vec, edge_vec) / edge_len
                # Calculate perpendicular distance
                dist = np.sqrt(np.linalg.norm(point_vec)**2 - proj**2)
                if dist > max_dist_to_edge:
                    max_dist_to_edge = dist
                    worst_point_idx = idx

        # If we couldn't identify a worst point, skip this iteration
        if worst_point_idx is None:
            continue
        
        # Move the worst point toward the centroid of the worst triangle
        direction = centroid - points[worst_point_idx]
        step = 0.3 * np.linalg.norm(direction)
        if np.linalg.norm(direction) > 1e-5:
            new_point = points[worst_point_idx] + 0.3 * direction
n            # Ensure the new point is inside the triangle
            if is_inside_triangle(new_point, A, B, C):
                points[worst_point_idx] = new_point

    return points

def random_barycentric_points(triangle, n_points):
    A, B, C = triangle
    points = []
    for _ in range(n_points):
        u, v = np.random.random(), np.random.random()
        if u + v > 1:
            u, v = 1 - u, 1 - v
        w = 1 - u - v
        P = w * A + u * B + v * C
        points.append(P)
    return np.array(points)

def compute_gradient_directions(points, triplet):
    i, j, k = triplet
    a, b, c = points[i], points[j], points[k]
    
    # Compute area and sign
    area_val = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
    s_val = 1 if area_val > 0 else -1
    
    # Compute gradient directions for each point
    dir_i = np.array([b[1]-c[1], c[0]-b[0]])
    dir_j = np.array([c[1]-a[1], a[0]-c[0]])
    dir_k = np.array([a[1]-b[1], b[0]-a[0]])
    
    if s_val < 0:
        dir_i, dir_j, dir_k = -dir_i, -dir_j, -dir_k
    
    # Normalize
    norm_i = np.linalg.norm(dir_i)
    norm_j = np.linalg.norm(dir_j)
    norm_k = np.linalg.norm(dir_k)
    
    if norm_i > 1e-8:
        dir_i = dir_i / norm_i
    if norm_j > 1e-8:
        dir_j = dir_j / norm_j
    if norm_k > 1e-8:
        dir_k = dir_k / norm_k
    
    return i, j, k, dir_i, dir_j, dir_k

def find_critical_triplets(points, k=5):
    n = len(points)
    areas = []
    triplets = []
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                a, b, c = points[i], points[j], points[k]
                area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                areas.append(area_val)
                triplets.append((i, j, k))
    
    # Sort by area (ascending)
    sorted_indices = np.argsort(areas)
    critical_triplets = [triplets[i] for i in sorted_indices[:k]]
    min_area = areas[sorted_indices[0]]
    
    return critical_triplets, min_area

def entrypoint() -> np.ndarray:
    triangle = get_unit_triangle()
    A, B, C = triangle
    n_points = 11

    # Initialize with Delaunay area-based approach
    initial_config = delaunay_area_initialization(triangle, n_points)
    current_config = initial_config.copy()
    current_min_area = get_smallest_triangle_area(current_config)

    # Simulated annealing parameters
    initial_temp = 0.2
    temp = initial_temp
    cooling_rate = 0.995
    min_temp = 1e-6
    base_step = 0.03
    max_iter = 2500
    no_improve_limit = 200
    
    no_improve_count = 0
    iter_count = 0
    
    # Track historical min_area for adaptive step sizing
    historical_min_area = [current_min_area]

    while temp > min_temp and no_improve_count < no_improve_limit and iter_count < max_iter:
        iter_count += 1
        
        # Dynamically adjust k based on progress
        k = max(3, min(5, 3 + int(no_improve_count / 50)))
        
        # Find top-k critical triplets (smallest triangles)
        critical_triplets, min_area_val = find_critical_triplets(current_config, k=k)
        if not critical_triplets:
            temp *= cooling_rate
            continue
        
        # Adaptive step size based on current min_area and historical progress
        area_scale = np.sqrt(min_area_val / 0.0365) if min_area_val > 0 else 1.0
        historical_trend = np.mean(historical_min_area[-min(10, len(historical_min_area)):])
        progress_rate = (min_area_val - historical_trend) / (historical_trend + 1e-8)
        step_scale = 0.8 + 0.4 * min(1.0, max(0.0, -progress_rate * 5))
        
        # Track all points that need movement
        point_movements = {i: np.zeros(2) for i in range(n_points)}
        point_weights = {i: 0.0 for i in range(n_points)}
        
        # Process each critical triplet
        for triplet in critical_triplets:
            i, j, k, dir_i, dir_j, dir_k = compute_gradient_directions(current_config, triplet)
            
            # Weight by how critical this triplet is (inverse of area difference)
            area_val = 0.5 * abs((current_config[j,0]-current_config[i,0])*(current_config[k,1]-current_config[i,1]) - 
                               (current_config[j,1]-current_config[i,1])*(current_config[k,0]-current_config[i,0]))
            weight = 1.0 / (area_val - min_area_val + 1e-8)
            
            # Apply weighted movements
            point_movements[i] += weight * dir_i
            point_movements[j] += weight * dir_j
            point_movements[k] += weight * dir_k
            point_weights[i] += weight
            point_weights[j] += weight
            point_weights[k] += weight

        # Normalize and apply movements
        candidates = []
        
        # Create candidate by moving critical points
        new_config = current_config.copy()
        for idx in range(n_points):
            if point_weights[idx] > 0:
                direction = point_movements[idx] / point_weights[idx]
                norm = np.linalg.norm(direction)
                if norm > 1e-5:
                    direction = direction / norm
                    
                    # Adaptive step size
                    step = base_step * area_scale * step_scale * (temp / initial_temp)
                    
                    # Asymmetric step (preserve beneficial pattern)
                    new_point = new_config[idx] + 1.0 * step * direction
                    if is_inside_triangle(new_point, A, B, C):
                        new_config[idx] = new_point

        # Calculate new min_area
        new_min_area = get_smallest_triangle_area(new_config)
        candidates.append((new_config, new_min_area))

        # Periodic full exploration phase (address fragile diversity mechanism)
        if iter_count % 50 == 0 or (no_improve_count > 100 and np.random.rand() < 0.3):
            exploration_config = current_config.copy()
            exploration_scale = 0.05 * (1.0 + 2.0 * (1.0 - min_area_val / 0.0365))
            
            for idx in range(n_points):
                angle = np.random.uniform(0, 2*np.pi)
                direction = np.array([np.cos(angle), np.sin(angle)])
                step = exploration_scale * np.random.uniform(0.5, 1.5)
                new_point = exploration_config[idx] + step * direction
                
                if is_inside_triangle(new_point, A, B, C):
                    exploration_config[idx] = new_point

            exploration_min_area = get_smallest_triangle_area(exploration_config)
            candidates.append((exploration_config, exploration_min_area))

        # Evaluate all candidates and select best
        if candidates:
            # Sort by min_area (descending)
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_candidate, best_min_area = candidates[0]
            
            # Simulated annealing acceptance
            if best_min_area > current_min_area:
                current_config, current_min_area = best_candidate, best_min_area
                historical_min_area.append(current_min_area)
                no_improve_count = 0
            else:
                delta = current_min_area - best_min_area
                if np.random.rand() < np.exp(-delta / temp):
                    current_config, current_min_area = best_candidate, best_min_area
                    historical_min_area.append(current_min_area)
                    no_improve_count = 0
                else:
                    no_improve_count += 1
        else:
            no_improve_count += 1

        # Adaptive cooling
        if no_improve_count > 20:
            cooling_rate = min(0.999, cooling_rate + 0.0005)
        else:
            cooling_rate = max(0.99, cooling_rate - 0.0005)
            
        temp *= cooling_rate

    return current_config