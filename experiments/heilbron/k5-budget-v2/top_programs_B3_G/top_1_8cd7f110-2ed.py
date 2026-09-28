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

def clamp_to_triangle(point, A, B, C):
    # Convert to barycentric coordinates
    bary = cartesian_to_barycentric(point, A, B, C)
    # Clamp to [0,1] and renormalize
    bary = np.clip(bary, 0, 1)
    bary = bary / np.sum(bary)
    # Convert back to Cartesian
    return barycentric_to_cartesian(bary, A, B, C)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Center of triangle (barycentric)
    center = (A + B + C) / 3.0
    
    # Adaptive ring initialization based on known Heilbronn configurations
    # 1 center + 3 inner ring + 3 middle ring + 4 outer ring points
    points = np.zeros((11, 2))
    
    # Center point
    points[0] = center
    
    # Inner ring (3 points) - at r1=0.4 from center
    r1 = 0.4
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
    
    # Middle ring (3 points) - at r2=0.55 from center
    r2 = 0.55
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
    
    # Outer ring (4 points) - at r3=0.85 from center
    r3 = 0.85
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
    
    # Ensure all points are properly inside the triangle using barycentric clamping
    for i in range(11):
        points[i] = clamp_to_triangle(points[i], A, B, C)
    
    # Enhanced simulated annealing optimization
    initial_temp = 0.1
    cooling_rate = 0.99
    min_temp = 1e-6
    iterations_per_temp = 50
    
    # Stagnation tracking
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
            
            # Find smallest triangles (top 10 instead of top 3)
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
            
            # Sort by area and take top 10 smallest triangles
            sorted_indices = np.argsort(min_areas)
            relevant_triangles = [min_triangles[i] for i in sorted_indices[:10]]
            
            # Collect points involved in these triangles
            relevant_points = set()
            for tri in relevant_triangles:
                relevant_points.update(tri)
            relevant_points = list(relevant_points)
            
            # Select 4-6 points to perturb (instead of 1-3)
            num_to_perturb = min(6, max(4, len(relevant_points) // 2))
            points_to_perturb = random.sample(relevant_points, num_to_perturb)

            # Enhanced geometrically-informed perturbations with random exploration
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
                        
                        # Apply displacement with larger factor (1.0 instead of 0.5) and add random component
                        displacement = total_direction * temp * 1.0
                        # Add random exploration component (temperature-scaled)
                        random_component = np.random.normal(0, temp * 0.3, size=2)
                        candidate[idx] += displacement + random_component

            # Ensure points stay inside triangle using barycentric clamping
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
                current_points = best_points.copy()
                current_min_area = best_min_area
                no_improve_count = 0

        # Cool down
        temp *= cooling_rate

    return best_points