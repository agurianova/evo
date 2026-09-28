import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random
import scipy.spatial
import math

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Helper function for boundary optimization
    def optimize_boundary_position(point, all_points, idx):
        """Optimize position along boundary to maximize min triangle area"""
        original = point.copy()
        
        # Check which edge the point is closest to
        edges = [(A, B), (B, C), (C, A)]
        min_dist = float('inf')
        closest_edge = 0
        
        for i, (p1, p2) in enumerate(edges):
            # Distance from point to edge
            edge_vec = p2 - p1
            point_vec = original - p1
            proj = np.dot(point_vec, edge_vec) / (np.dot(edge_vec, edge_vec) + 1e-10)
            proj = max(0, min(1, proj))
            closest_point = p1 + proj * edge_vec
            dist = np.linalg.norm(original - closest_point)
            if dist < min_dist:
                min_dist = dist
                closest_edge = i

        # Sample points along the closest edge
        p1, p2 = edges[closest_edge]
        best_position = original
        best_min_area = get_smallest_triangle_area(all_points)
        
        for t in np.linspace(0, 1, 20):
            candidate = p1 * (1 - t) + p2 * t
            
            # Calculate min area with this candidate position
            test_points = all_points.copy()
            test_points[idx] = candidate
            min_area = get_smallest_triangle_area(test_points)
            
            if min_area > best_min_area:
                best_min_area = min_area
                best_position = candidate

        return best_position

    # Create initial points based on known high-quality configurations for 11 points
    def create_initial_points():
        # Known good configuration for 11 points in equilateral triangle
        # Scaled to our unit-area triangle
        # Source: Adapted from known Heilbronn problem solutions
        
        # Base coordinates in barycentric for a standard equilateral triangle
        barycentric_points = [
            (0.5, 0.25, 0.25),
            (0.25, 0.5, 0.25),
            (0.25, 0.25, 0.5),
            (0.7, 0.15, 0.15),
            (0.15, 0.7, 0.15),
            (0.15, 0.15, 0.7),
            (0.4, 0.4, 0.2),
            (0.4, 0.2, 0.4),
            (0.2, 0.4, 0.4),
            (0.6, 0.3, 0.1),
            (0.3, 0.6, 0.1)
        ]
        
        # Convert to Cartesian coordinates
        cartesian_points = []
        for (u, v, w) in barycentric_points:
            # Ensure non-negative and sum to 1
            total = u + v + w
            u, v, w = u/total, v/total, w/total
            point = u * A + v * B + w * C
            cartesian_points.append(point)
        
        return np.array(cartesian_points)
    
    points = create_initial_points()
    
    # Simulated annealing parameters
    initial_temp = 0.025
    cooling_rate = 0.995
    max_iter = 10000
    base_step = 0.04
    acceptance_target = 0.44
    
    current = points.copy()
    current_score = get_smallest_triangle_area(current)
    best = current.copy()
    best_score = current_score
    
    # Track resistance history for adaptive behavior
    resistance_history = [0.5] * 10  # Start with neutral resistance
    
    # Adaptive step size parameters
    step_size = base_step
    successful = 0
    attempts = 0
    
    for iter in range(max_iter):
        temp = initial_temp * (cooling_rate ** iter)
        
        # Calculate current resistance estimate
        current_resistance = np.mean(resistance_history)
        
        # Find triangles that need attention
        triangles = []
        n = 11
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    # Compute area
                    area = 0.5 * abs(
                        (current[j,0] - current[i,0]) * (current[k,1] - current[i,1]) -
                        (current[j,1] - current[i,1]) * (current[k,0] - current[i,0])
                    )
                    triangles.append((area, i, j, k))
        
        # Sort by area (smallest first)
        triangles.sort()
        
        # Adaptive triangle selection based on resistance
        # When resistance is low (< 0.5), consider more triangles to address broader issues
        num_triangles_to_consider = max(5, min(20, int(15 * (1 - current_resistance))))
        
        # Count how many times each point appears in the smallest triangles
        point_counts = [0] * 11
        for idx, (_, i, j, k) in enumerate(triangles[:num_triangles_to_consider]):
            point_counts[i] += 1
            point_counts[j] += 1
            point_counts[k] += 1
        
        # Convert to probabilities for selection
        total = sum(point_counts)
        if total > 0:
            probabilities = [count/total for count in point_counts]
        else:
            probabilities = [1/11] * 11
        
        # Select point to perturb based on probability
        point_idx = np.random.choice(11, p=probabilities)
        
        # Create candidate by perturbing the selected point
        candidate = current.copy()
        displacement = np.random.normal(0, step_size, 2)
        candidate[point_idx] += displacement
        
        # Boundary handling with edge-specific optimization
        if not is_inside_triangle(candidate, A, B, C):
            # Project back to triangle
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
            
            # Further optimize boundary position
            candidate[point_idx] = optimize_boundary_position(
                candidate[point_idx], candidate, point_idx)
        
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
            if acceptance_rate > acceptance_target:
                step_size *= 1.15
            else:
                step_size *= 0.85
            
            successful = 0
            attempts = 0

        # Voronoi-based exploration to proactively optimize spacing (like opponent does)
        if iter > 0 and iter % 500 == 0:
            try:
                # Compute Voronoi tessellation
                padding = 0.1
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
                
                # Move points to balance density
                if region_sizes:
                    target_regions = [rs[1] for rs in region_sizes[:min(3, len(region_sizes))]]
                    
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
                            if region_sizes and region_area < region_sizes[0][0] * 0.3:
                                # Move to centroid of a large region
                                target_region_idx = target_regions[0]
                                target_region = vor.regions[target_region_idx]
                                if target_region:
                                    target_points = [vor.vertices[i] for i in target_region]
                                    target_centroid = np.mean(target_points, axis=0)
                                    
                                    # Project to triangle if needed
                                    if is_inside_triangle(target_centroid, A, B, C):
                                        # Optimize boundary position if on edge
                                        if not is_inside_triangle(target_centroid + 1e-5, A, B, C):
                                            candidate_point = optimize_boundary_position(target_centroid, current, point_idx)
                                        else:
                                            candidate_point = target_centroid
                                    else:
                                        # Project to triangle
                                        p = target_centroid
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
                                        
                                        candidate_point = A + bary_u * v0 + bary_v * v1
                                        candidate_point = optimize_boundary_position(candidate_point, current, point_idx)
                                    
                                    # Evaluate candidate move
                                    test_points = current.copy()
                                    test_points[point_idx] = candidate_point
                                    test_score = get_smallest_triangle_area(test_points)
                                    
                                    if test_score > current_score * 0.995:  # Allow small decreases for exploration
                                        current[point_idx] = candidate_point
                                        if test_score > best_score:
                                            best = test_points
                                            best_score = test_score
                                        points_moved += 1
                                        
                                    if points_moved >= 2:
                                        break
            except Exception as e:
                # Fail gracefully if Voronoi computation fails
                pass

    # Final deepening phase to create a deeper local optimum
    deepening_steps = 1500
    deepening_temp = 0.0007

    for _ in range(deepening_steps):
        point_idx = random.randint(0, 10)
        candidate = best.copy()
        displacement = np.random.normal(0, step_size * 0.1, 2)
        candidate[point_idx] += displacement

        if not is_inside_triangle(candidate, A, B, C):
            # Project back to triangle
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
            
            if bary_u < 0: bary_u = 0
            if bary_v < 0: bary_v = 0
            if bary_u + bary_v > 1:
                scale = 1 / (bary_u + bary_v)
                bary_u *= scale
                bary_v *= scale
            
            candidate[point_idx] = A + bary_u * v0 + bary_v * v1
            
            # Further optimize boundary position
            candidate[point_idx] = optimize_boundary_position(
                candidate[point_idx], candidate, point_idx)

        candidate_score = get_smallest_triangle_area(candidate)
        delta = candidate_score - best_score

        # Only accept if it doesn't decrease the minimum area (very conservative deepening)
        if delta >= -1e-10 or random.random() < np.exp(delta / deepening_temp):
            best = candidate
            best_score = candidate_score

    return best