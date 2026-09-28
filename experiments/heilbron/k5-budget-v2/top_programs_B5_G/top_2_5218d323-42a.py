import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import scipy.spatial
import random

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Create initial points using adaptive Fibonacci spiral
    def create_initial_points():
        points = []
        
        # Golden angle for spiral distribution
        golden_angle = np.pi * (3 - np.sqrt(5))
        n_points = 11
        
        # Adaptive radius scaling based on point count
        max_radius = 0.65  # Scaled for unit area triangle
        
        for i in range(n_points):
            # Radius increases with sqrt of index for uniform density
            r = max_radius * np.sqrt(i / n_points)
            
            # Angle increases by golden angle
            theta = i * golden_angle
            
            # Convert to Cartesian in barycentric space
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            
            # Map to barycentric coordinates (centered at centroid)
            bary_x = 1/3 + x
            bary_y = 1/3 + y * np.sqrt(3)/3
            bary_z = 1 - bary_x - bary_y
            
            # Ensure non-negative and inside triangle
            if bary_z < 0:
                excess = -bary_z/2
                bary_x += excess
                bary_y += excess
                bary_z = 0
            if bary_x < 0:
                excess = -bary_x/2
                bary_y += excess
                bary_z += excess
                bary_x = 0
            if bary_y < 0:
                excess = -bary_y/2
                bary_x += excess
                bary_z += excess
                bary_y = 0
            
            # Convert to Cartesian
            point = bary_x * A + bary_y * B + bary_z * C
            points.append(point)
        
        return np.array(points)
    
    points = create_initial_points()
    
    # Simulated annealing parameters
    initial_temp = 0.03
    cooling_rate = 0.994
    max_iter = 10000
    base_step = 0.045
    
    current = points.copy()
    current_score = get_smallest_triangle_area(current)
    best = current.copy()
    best_score = current_score
    
    # Track resistance history for adaptive behavior
    resistance_history = []
    recent_resistance = 0.45  # Starting estimate
    
    # Adaptive step size parameters
    step_size = base_step
    successful = 0
    attempts = 0
    
    for iter in range(max_iter):
        temp = initial_temp * (cooling_rate ** iter)
        
        # Find triangles and sort by area
        triangles = []
        n = 11
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        (current[j,0] - current[i,0]) * (current[k,1] - current[i,1]) -
                        (current[j,1] - current[i,1]) * (current[k,0] - current[i,0])
                    )
                    triangles.append((area, i, j, k))
        
        # Sort by area (smallest first)
        triangles.sort()
        
        # Adaptive triangle selection based on resistance
        # When resistance is low, examine more triangles to escape shallow optima
        # When resistance is high, focus on critical areas
        min_area = triangles[0][0]
        if recent_resistance < 0.5:
            # Low resistance - examine more triangles (up to 25%)
            threshold = min_area * (1 + 0.25 * (0.5 - recent_resistance) / 0.5)
        else:
            # High resistance - focus on critical areas (down to 5%)
            threshold = min_area * (1 + 0.05 * (1 - recent_resistance))
        
        # Select all triangles within threshold
        selected_triangles = [t for t in triangles if t[0] <= threshold]
        
        # Count how many times each point appears in the selected triangles
        point_counts = [0] * 11
        for _, i, j, k in selected_triangles:
            point_counts[i] += 1
            point_counts[j] += 1
            point_counts[k] += 1
        
        # Convert to probabilities for selection
        total = sum(point_counts)
        if total > 0:
            probabilities = [count/total for count in point_counts]
        else:
            probabilities = [1/11] * 11  # Uniform if no small triangles found
        
        # Select point to perturb based on probability
        point_idx = np.random.choice(11, p=probabilities)
        
        # Create candidate by perturbing the selected point
        candidate = current.copy()
        displacement = np.random.normal(0, step_size, 2)
        candidate[point_idx] += displacement
        
        # Boundary handling with edge optimization
        if not is_inside_triangle(candidate, A, B, C):
            p = candidate[point_idx]
            v0 = B - A
            v1 = C - A
            v2 = p - A
            
            d00 = np.dot(v0, v0)
            d01 = np.dot(v0, v1)
            d11 = np.dot(v1, v1)
            d20 = np.dot(v2, v0)
            d21 = np.dot(v2, v1)
            denom = d00 * d11 - d01 * d01
            
            if abs(denom) < 1e-10:
                bary_u = 0.5
                bary_v = 0.5
            else:
                bary_u = (d11 * d20 - d01 * d21) / denom
                bary_v = (d00 * d21 - d01 * d20) / denom
            
            # Clamp to triangle
            if bary_u < 0: bary_u = 0
            if bary_v < 0: bary_v = 0
            if bary_u + bary_v > 1:
                scale = 1 / (bary_u + bary_v)
                bary_u *= scale
                bary_v *= scale
            
            candidate[point_idx] = A + bary_u * v0 + bary_v * v1
            
            # Additional edge optimization
            if bary_u < 1e-5 or bary_v < 1e-5 or (bary_u + bary_v) > 0.999:
                # Near an edge - sample multiple points along the edge for optimization
                edges = [(A, B), (B, C), (C, A)]
                min_dist = float('inf')
                closest_edge = 0
                
                for i, (p1, p2) in enumerate(edges):
                    edge_vec = p2 - p1
                    point_vec = candidate[point_idx] - p1
                    proj = np.dot(point_vec, edge_vec) / np.dot(edge_vec, edge_vec)
                    proj = max(0, min(1, proj))
                    closest_point = p1 + proj * edge_vec
                    dist = np.linalg.norm(candidate[point_idx] - closest_point)
                    if dist < min_dist:
                        min_dist = dist
                        closest_edge = i

                # Sample points along the closest edge
                p1, p2 = edges[closest_edge]
                best_position = candidate[point_idx]
                best_min_area = 0
                
                for t in np.linspace(0, 1, 15):
                    test_candidate = p1 * (1 - t) + p2 * t
                    test_points = candidate.copy()
                    test_points[point_idx] = test_candidate
                    min_area = get_smallest_triangle_area(test_points)
                    
                    if min_area > best_min_area:
                        best_min_area = min_area
                        best_position = test_candidate
                
                candidate[point_idx] = best_position

        # Evaluate candidate
        candidate_score = get_smallest_triangle_area(candidate)
        delta = candidate_score - current_score
        
        # Simulated annealing acceptance
        if delta > 0 or random.random() < np.exp(delta / temp):
            current = candidate
            current_score = candidate_score
            successful += 1
            
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
        
        attempts += 1
        
        # Adaptive step size adjustment
        if iter > 0 and iter % 100 == 0:
            acceptance_rate = successful / attempts
            if acceptance_rate > 0.45:
                step_size *= 1.1
            else:
                step_size *= 0.9
            
            successful = 0
            attempts = 0

        # Voronoi-based diversity mechanism when resistance is low
        if iter % 500 == 0 and recent_resistance < 0.48:
            try:
                # Compute Voronoi tessellation to identify low-density regions
                padding = 0.05
                boundary_points = [
                    [A[0]-padding, A[1]-padding],
                    [B[0]+padding, B[1]-padding],
                    [C[0], C[1]+padding],
                    [(A[0]+B[0])/2, (A[1]+B[1])/2 - padding],
                    [(A[0]+C[0])/2 - padding, (A[1]+C[1])/2 + padding/2],
                    [(B[0]+C[0])/2 + padding, (B[1]+C[1])/2 + padding/2]
                ]
                
                all_points = np.vstack([current, boundary_points])
                vor = scipy.spatial.Voronoi(all_points)
                
                # Find largest Voronoi regions (low-density areas)
                region_sizes = []
                for region_idx, region in enumerate(vor.regions):
                    if not region or -1 in region:
                        continue
                    polygon = [vor.vertices[i] for i in region]
                    if len(polygon) < 3:
                        continue
                    # Compute polygon area
                    area = 0
                    for i in range(len(polygon)):
                        j = (i + 1) % len(polygon)
                        area += polygon[i][0] * polygon[j][1] - polygon[j][0] * polygon[i][1]
                    area = abs(area) / 2
                    region_sizes.append((area, region_idx))
                
                region_sizes.sort(reverse=True)
                
                # Move points from small regions to large regions
                if region_sizes:
                    target_regions = [rs[1] for rs in region_sizes[:min(2, len(region_sizes))]]
                    
                    # Find which Voronoi points correspond to our current points
                    point_to_region = {}
                    for point_idx, region_idx in enumerate(vor.point_region[:len(current)]):
                        if region_idx != -1 and region_idx < len(vor.regions) and vor.regions[region_idx]:
                            point_to_region[point_idx] = region_idx
                    
                    # Move points from small regions to large regions
                    points_moved = 0
                    for point_idx, region_idx in point_to_region.items():
                        if region_idx in target_regions:
                            continue
                        
                        # Find points in small regions to move
                        if len(vor.regions[region_idx]) >= 3:
                            region_area = next((area for area, r_idx in region_sizes if r_idx == region_idx), 0)
                            # If this region is significantly smaller than the largest
                            if region_sizes and region_area < region_sizes[0][0] * 0.4:
                                # Move to centroid of a large region
                                target_region_idx = target_regions[0]
                                target_region = vor.regions[target_region_idx]
                                if target_region:
                                    target_points = [vor.vertices[i] for i in target_region]
                                    target_centroid = np.mean(target_points, axis=0)
                                    
                                    # Project to triangle if needed
                                    if is_inside_triangle(target_centroid, A, B, C):
                                        # Check if on boundary and optimize
                                        if not is_inside_triangle(target_centroid + 1e-5, A, B, C):
                                            edges = [(A, B), (B, C), (C, A)]
                                            min_dist = float('inf')
                                            closest_edge = 0
                                            
                                            for i, (p1, p2) in enumerate(edges):
                                                edge_vec = p2 - p1
                                                point_vec = target_centroid - p1
                                                proj = np.dot(point_vec, edge_vec) / np.dot(edge_vec, edge_vec)
                                                proj = max(0, min(1, proj))
                                                closest_point = p1 + proj * edge_vec
                                                dist = np.linalg.norm(target_centroid - closest_point)
                                                if dist < min_dist:
                                                    min_dist = dist
                                                    closest_edge = i

                                            # Sample points along the closest edge
                                            p1, p2 = edges[closest_edge]
                                            best_position = target_centroid
                                            best_min_area = 0
                                            
                                            for t in np.linspace(0, 1, 15):
                                                test_candidate = p1 * (1 - t) + p2 * t
                                                test_points = current.copy()
                                                test_points[point_idx] = test_candidate
                                                min_area = get_smallest_triangle_area(test_points)
                                                
                                                if min_area > best_min_area:
                                                    best_min_area = min_area
                                                    best_position = test_candidate
                                            
                                            current[point_idx] = best_position
                                        else:
                                            current[point_idx] = target_centroid
                                    else:
                                        # Project to triangle
                                        v0 = B - A
                                        v1 = C - A
                                        v2 = target_centroid - A
                                        
                                        d00 = np.dot(v0, v0)
                                        d01 = np.dot(v0, v1)
                                        d11 = np.dot(v1, v1)
                                        d20 = np.dot(v2, v0)
                                        d21 = np.dot(v2, v1)
                                        denom = d00 * d11 - d01 * d01
                                        
                                        if abs(denom) < 1e-10:
                                            bary_u = 0.5
                                            bary_v = 0.5
                                        else:
                                            bary_u = (d11 * d20 - d01 * d21) / denom
                                            bary_v = (d00 * d21 - d01 * d20) / denom
                                        
                                        if bary_u < 0: bary_u = 0
                                        if bary_v < 0: bary_v = 0
                                        if bary_u + bary_v > 1:
                                            scale = 1 / (bary_u + bary_v)
                                            bary_u *= scale
                                            bary_v *= scale
                                        
                                        current[point_idx] = A + bary_u * v0 + bary_v * v1
                                    
                                    # Update current score after moving
                                    current_score = get_smallest_triangle_area(current)
                                    points_moved += 1
                                    if points_moved >= 2:
                                        break
            except Exception as e:
                pass

        # Update resistance estimate based on improvement potential
        if iter % 200 == 0 and iter > 0:
            # Simulate opponent improvement attempt
            opponent_candidate = current.copy()
            # Perturb points that form smallest triangles
            for _, i, j, k in triangles[:3]:
                idx = np.random.choice([i, j, k])
                displacement = np.random.normal(0, step_size * 0.8, 2)
                opponent_candidate[idx] += displacement
                
                # Boundary handling
                if not is_inside_triangle(opponent_candidate, A, B, C):
                    p = opponent_candidate[idx]
                    v0 = B - A
                    v1 = C - A
                    v2 = p - A
                    
                    d00 = np.dot(v0, v0)
                    d01 = np.dot(v0, v1)
                    d11 = np.dot(v1, v1)
                    d20 = np.dot(v2, v0)
                    d21 = np.dot(v2, v1)
                    denom = d00 * d11 - d01 * d01
                    
                    if abs(denom) < 1e-10:
                        bary_u = 0.5
                        bary_v = 0.5
                    else:
                        bary_u = (d11 * d20 - d01 * d21) / denom
                        bary_v = (d00 * d21 - d01 * d20) / denom
                    
                    if bary_u < 0: bary_u = 0
                    if bary_v < 0: bary_v = 0
                    if bary_u + bary_v > 1:
                        scale = 1 / (bary_u + bary_v)
                        bary_u *= scale
                        bary_v *= scale
                    
                    opponent_candidate[idx] = A + bary_u * v0 + bary_v * v1

            opponent_score = get_smallest_triangle_area(opponent_candidate)
            improvement = opponent_score - current_score
            
            # Update resistance estimate (0-1 scale, 1 = perfectly resistant)
            resistance = 0.5 * (1 - np.tanh(improvement * 1000)) + 0.5
            resistance_history.append(resistance)
            
            # Use moving average for recent resistance
            if len(resistance_history) > 5:
                recent_resistance = np.mean(resistance_history[-5:])

    return best