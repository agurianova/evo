import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import random

np.random.seed(42)
random.seed(42)

def barycentric_to_cartesian(bary, A, B, C):
    return bary[0] * A + bary[1] * B + bary[2] * C

def cartesian_to_barycentric(point, A, B, C):
    # Compute barycentric coordinates for point in triangle ABC
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

def distance_to_edge(p, v1, v2):
    edge = v2 - v1
    normal = np.array([-edge[1], edge[0]])
    if np.linalg.norm(normal) < 1e-10:
        return 0.0
    normal = normal / np.linalg.norm(normal)
    return abs(np.dot(p - v1, normal))

def clamp_to_triangle(point, A, B, C):
    # First check if already inside
    if is_inside_triangle(point, A, B, C):
        return point
    
    # Compute distances to each edge
    d_AB = distance_to_edge(point, A, B)
    d_AC = distance_to_edge(point, A, C)
    d_BC = distance_to_edge(point, B, C)
    
    # Find closest edge
    min_d = min(d_AB, d_AC, d_BC)
    
    # Project onto closest edge
    if min_d == d_AB:
        # Project onto AB
        edge = B - A
        if np.linalg.norm(edge) < 1e-10:
            return A
        t = np.dot(point - A, edge) / np.dot(edge, edge)
        t = max(0, min(1, t))
        return A + t * edge
    elif min_d == d_AC:
        # Project onto AC
        edge = C - A
        if np.linalg.norm(edge) < 1e-10:
            return A
        t = np.dot(point - A, edge) / np.dot(edge, edge)
        t = max(0, min(1, t))
        return A + t * edge
    else:
        # Project onto BC
        edge = C - B
        if np.linalg.norm(edge) < 1e-10:
            return B
        t = np.dot(point - B, edge) / np.dot(edge, edge)
        t = max(0, min(1, t))
        return B + t * edge

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Center of triangle (barycentric)
    center = (A + B + C) / 3.0
    
    # Adaptive ring initialization based on known Heilbronn configurations
    # 1 center + 3 inner ring + 3 middle ring + 4 outer ring points
    points = np.zeros((11, 2))
    
    # Center point
    points[0] = center
    
    # Inner ring (3 points) - optimized radius
    r1 = 0.38
    for i in range(3):
        angle = 2 * np.pi * i / 3 + np.pi/6
        dx = r1 * np.cos(angle)
        dy = r1 * np.sin(angle)
        # Convert to barycentric for proper triangle mapping
        bary_center = cartesian_to_barycentric(center, A, B, C)
        # Move in barycentric space (preserves triangle constraints)
        bary_offset = np.array([0, dx, dy])
        bary_offset = bary_offset / np.sum(bary_offset)
        bary_point = bary_center + 0.5 * bary_offset
        bary_point = bary_point / np.sum(bary_point)
        points[i+1] = barycentric_to_cartesian(bary_point, A, B, C)
    
    # Middle ring (3 points) - optimized radius
    r2 = 0.62
    for i in range(3):
        angle = 2 * np.pi * i / 3 + np.pi/6
        dx = r2 * np.cos(angle)
        dy = r2 * np.sin(angle)
        bary_center = cartesian_to_barycentric(center, A, B, C)
        bary_offset = np.array([0, dx, dy])
        bary_offset = bary_offset / np.sum(bary_offset)
        bary_point = bary_center + 0.5 * bary_offset
        bary_point = bary_point / np.sum(bary_point)
        points[i+4] = barycentric_to_cartesian(bary_point, A, B, C)
    
    # Outer ring (4 points) - optimized radius
    r3 = 0.88
    for i in range(4):
        angle = 2 * np.pi * i / 4 + np.pi/8
        dx = r3 * np.cos(angle)
        dy = r3 * np.sin(angle)
        bary_center = cartesian_to_barycentric(center, A, B, C)
        bary_offset = np.array([0, dx, dy])
        bary_offset = bary_offset / np.sum(bary_offset)
        bary_point = bary_center + 0.5 * bary_offset
        bary_point = bary_point / np.sum(bary_point)
        points[i+7] = barycentric_to_cartesian(bary_point, A, B, C)
    
    # Ensure all points are properly inside the triangle using edge projection
    for i in range(11):
        points[i] = clamp_to_triangle(points[i], A, B, C)
    
    # Enhanced simulated annealing optimization
    initial_temp = 0.1
    cooling_rate = 0.99
    min_temp = 1e-6
    iterations_per_temp = 50
    
    # Stagnation tracking with dynamic threshold
    max_no_improve = int(0.2 * iterations_per_temp)
    no_improve_count = 0
    
    current_points = points.copy()
    current_min_area = get_smallest_triangle_area(current_points)
    best_points = current_points.copy()
    best_min_area = current_min_area
    
    temp = initial_temp
    while temp > min_temp:
        for _ in range(iterations_per_temp):
            # Create candidate by perturbing points
            candidate = current_points.copy()
            
            # Find smallest triangles (top 1-3 instead of top 10)
            min_areas = []
            min_triangles = []
            n = 11
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = current_points[i]
                        x2, y2 = current_points[j]
                        x3, y3 = current_points[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        min_areas.append(area)
                        min_triangles.append((i, j, k))
            
            # Sort by area and take top 1-3 smallest triangles
            sorted_indices = np.argsort(min_areas)
            relevant_triangles = [min_triangles[i] for i in sorted_indices[:max(1, min(3, len(min_areas)))]]
            
            # Collect points involved in these triangles
            relevant_points = set()
            for tri in relevant_triangles:
                relevant_points.update(tri)
            relevant_points = list(relevant_points)
            
            # Select only 1-2 points to perturb (instead of 4-6)
            num_to_perturb = min(2, len(relevant_points))
            points_to_perturb = random.sample(relevant_points, num_to_perturb)

            # Enhanced geometrically-informed perturbations with adaptive scaling
            for idx in points_to_perturb:
                # Find all triangles involving this point
                triangles_with_idx = [tri for tri in relevant_triangles if idx in tri]
                
                if triangles_with_idx:
                    # Compute average outward direction
                    total_direction = np.zeros(2)
                    for tri in triangles_with_idx:
                        # Get the other two points in the triangle
                        others = [p for p in tri if p != idx]
                        p1, p2 = current_points[others[0]], current_points[others[1]]
                        
                        # Compute edge vector and normal
                        edge = p2 - p1
                        normal = np.array([-edge[1], edge[0]])
                        norm = np.linalg.norm(normal)
                        if norm > 1e-10:
                            normal /= norm
                        
                        # Determine outward direction
                        to_point = current_points[idx] - p1
                        direction = normal if np.dot(to_point, normal) > 0 else -normal
                        
                        # Weight by triangle area (smaller triangles get more weight)
                        area = 0.5 * abs(edge[0]*to_point[1] - edge[1]*to_point[0])
                        weight = 1.0 / (area + 1e-10)
                        total_direction += weight * direction
                    
                    if np.linalg.norm(total_direction) > 1e-10:
                        total_direction = total_direction / np.linalg.norm(total_direction)
                        
                        # Scale displacement by inverse of smallest triangle area involving this point
                        min_area_involving_point = min([min_areas[i] for i in range(len(min_triangles)) 
                                                      if idx in min_triangles[i]])
                        adaptive_factor = 0.5 / (min_area_involving_point + 1e-10)
                        adaptive_factor = min(2.0, adaptive_factor)  # Cap to prevent excessive steps
                        
                        # Apply displacement with adaptive factor and add small random component
                        displacement = total_direction * temp * adaptive_factor
                        # Add small random exploration component (temperature-scaled)
                        random_component = np.random.normal(0, temp * 0.1, size=2)
                        candidate[idx] += displacement + random_component

            # Ensure points stay inside triangle using edge projection
            for i in range(11):
                candidate[i] = clamp_to_triangle(candidate[i], A, B, C)

            # Evaluate candidate
            candidate_min_area = get_smallest_triangle_area(candidate)
            
            # Acceptance probability
            delta = candidate_min_area - current_min_area
            if delta >= 0 or random.random() < np.exp(delta / temp):
                current_points = candidate
                current_min_area = candidate_min_area
                
                # Track best solution
                if candidate_min_area > best_min_area:
                    best_points = candidate.copy()
                    best_min_area = candidate_min_area
                    no_improve_count = 0
                else:
                    no_improve_count += 1
            else:
                no_improve_count += 1

            # Restart mechanism if stuck in local minimum
            if no_improve_count >= max_no_improve:
                # Instead of just resetting to best, add a controlled perturbation
                current_points = best_points.copy()
                current_min_area = best_min_area
                
                # Apply small perturbation to escape local minima
                perturb_count = max(1, int(0.1 * 11))
                for _ in range(perturb_count):
                    idx = random.randint(0, 10)
                    step_size = 0.5 * temp
                    current_points[idx] += np.random.normal(0, step_size, size=2)
                    current_points[idx] = clamp_to_triangle(current_points[idx], A, B, C)
                
                current_min_area = get_smallest_triangle_area(current_points)
                no_improve_count = 0

        # Cool down
        temp *= cooling_rate

    # Final local search phase for gradient-based refinement
    local_search_steps = 100
    local_step_size = 0.005

    final_points = best_points.copy()
    final_min_area = best_min_area

    for _ in range(local_search_steps):
        # Find the smallest triangle
        n = 11
        min_area = float('inf')
        min_triangle = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs((final_points[j,0]-final_points[i,0])*(final_points[k,1]-final_points[i,1]) - 
                                   (final_points[k,0]-final_points[i,0])*(final_points[j,1]-final_points[i,1]))
                    if area < min_area:
                        min_area = area
                        min_triangle = (i, j, k)
        
        if min_triangle is None or min_area <= 1e-10:
            break
        
        i, j, k = min_triangle
        # Compute gradient for each point in the smallest triangle
        for idx in [i, j, k]:
            # Direction that increases area of this triangle
            other_indices = [x for x in [i, j, k] if x != idx]
            a, b, c = final_points[idx], final_points[other_indices[0]], final_points[other_indices[1]]
            
            # Vector along the base
            base = c - b
            # Normal vector perpendicular to base
            normal = np.array([-base[1], base[0]])
            normal_norm = np.linalg.norm(normal)
            if normal_norm < 1e-10:
                continue
            normal = normal / normal_norm
            
            # Direction to move: outward from the triangle
            d = np.dot(a - b, normal)
            move_direction = normal if d > 0 else -normal
            
            # Try moving in this direction
            candidate = final_points.copy()
            candidate[idx] += local_step_size * move_direction
            
            # Check if inside triangle
            candidate[idx] = clamp_to_triangle(candidate[idx], A, B, C)
            
            candidate_min_area = get_smallest_triangle_area(candidate)
            if candidate_min_area > final_min_area:
                final_points = candidate
                final_min_area = candidate_min_area

    return final_points