import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import random

np.random.seed(42)
random.seed(42)

def clamp_to_triangle(point, A, B, C):
    # Check if point is already inside
    if is_inside_triangle(point, A, B, C):
        return point

    # Calculate edge normals pointing inward
    AB = B - A
    BC = C - B
    CA = A - C
    
    # Normalize edge vectors
    AB_norm = AB / np.linalg.norm(AB)
    BC_norm = BC / np.linalg.norm(BC)
    CA_norm = CA / np.linalg.norm(CA)

    # Calculate inward normals (90-degree counterclockwise rotation)
    n_AB = np.array([-AB_norm[1], AB_norm[0]])
    n_BC = np.array([-BC_norm[1], BC_norm[0]])
    n_CA = np.array([-CA_norm[1], CA_norm[0]])

    # Project onto closest edge
    def distance_to_edge(p, v1, v2, normal):
        return np.dot(p - v1, normal)

    d_AB = distance_to_edge(point, A, B, n_AB)
    d_BC = distance_to_edge(point, B, C, n_BC)
    d_CA = distance_to_edge(point, C, A, n_CA)

    # Find most violated constraint (largest negative distance)
    min_d = min(d_AB, d_BC, d_CA)

    if min_d >= 0:
        return point  # Already inside

    # Project onto the edge with the largest violation
    if d_AB == min_d:
        # Project onto AB
        t = np.dot(point - A, AB) / np.dot(AB, AB)
        t = max(0, min(1, t))
        return A + t * AB
    elif d_BC == min_d:
        # Project onto BC
        t = np.dot(point - B, BC) / np.dot(BC, BC)
        t = max(0, min(1, t))
        return B + t * BC
    else:
        # Project onto CA
        t = np.dot(point - C, CA) / np.dot(CA, CA)
        t = max(0, min(1, t))
        return C + t * CA

def find_optimal_ring_parameters(A, B, C, center):
    """Find optimal ring radii through parameter sweep"""
    best_score = -1
    best_params = (0.3, 0.6, 0.85)
    
    # Parameter ranges to search
    r1_range = np.linspace(0.25, 0.45, 5)
    r2_range = np.linspace(0.55, 0.75, 5)
    r3_range = np.linspace(0.80, 0.95, 5)
    
    for r1 in r1_range:
        for r2 in r2_range:
            for r3 in r3_range:
                # Create configuration with these parameters
                points = np.zeros((11, 2))
                points[0] = center
                
                # Inner ring (3 points)
                for i in range(3):
                    angle = 2 * np.pi * i / 3 + np.pi/6
                    dx = r1 * np.cos(angle)
                    dy = r1 * np.sin(angle)
                    points[i+1] = center + np.array([dx, dy])

                # Middle ring (3 points)
                for i in range(3):
                    angle = 2 * np.pi * i / 3 + np.pi/6
                    dx = r2 * np.cos(angle)
                    dy = r2 * np.sin(angle)
                    points[i+4] = center + np.array([dx, dy])

                # Outer ring (4 points)
                for i in range(4):
                    angle = 2 * np.pi * i / 4 + np.pi/8
                    dx = r3 * np.cos(angle)
                    dy = r3 * np.sin(angle)
                    points[i+7] = center + np.array([dx, dy])

                # Ensure all points are inside triangle
                for i in range(11):
                    points[i] = clamp_to_triangle(points[i], A, B, C)
                
                # Evaluate
                score = get_smallest_triangle_area(points)
                if score > best_score:
                    best_score = score
                    best_params = (r1, r2, r3)

    return best_params

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Calculate triangle center (centroid)
    center = (A + B + C) / 3.0
    
    # Find optimal ring parameters through early optimization
    r1, r2, r3 = find_optimal_ring_parameters(A, B, C, center)

    # Initialize points directly in Cartesian space
    points = np.zeros((11, 2))
    
    # Center point
    points[0] = center
    
    # Inner ring (3 points)
    for i in range(3):
        angle = 2 * np.pi * i / 3 + np.pi/6
        dx = r1 * np.cos(angle)
        dy = r1 * np.sin(angle)
        points[i+1] = center + np.array([dx, dy])
    
    # Middle ring (3 points)
    for i in range(3):
        angle = 2 * np.pi * i / 3 + np.pi/6
        dx = r2 * np.cos(angle)
        dy = r2 * np.sin(angle)
        points[i+4] = center + np.array([dx, dy])
    
    # Outer ring (4 points)
    for i in range(4):
        angle = 2 * np.pi * i / 4 + np.pi/8
        dx = r3 * np.cos(angle)
        dy = r3 * np.sin(angle)
        points[i+7] = center + np.array([dx, dy])
    
    # Ensure all points are properly inside the triangle
    for i in range(11):
        points[i] = clamp_to_triangle(points[i], A, B, C)
    
    # Enhanced simulated annealing with adaptive parameters
    initial_temp = 0.1
    min_temp = 1e-6
    iterations_per_temp = 75
    
    # Adaptive cooling parameters
    adaptive_cooling = True
    improvement_threshold = 0.0001
    recent_improvements = []
    max_history = 100
    
    # Stagnation tracking
    max_no_improve = int(0.25 * iterations_per_temp)
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
            
            # Find smallest triangles (top 3 smallest)
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
            
            # Sort by area and take top 3 smallest triangles
            sorted_indices = np.argsort(min_areas)
            relevant_triangles = [min_triangles[i] for i in sorted_indices[:min(3, len(min_areas))]]
            
            # Collect points involved in these triangles
            relevant_points = set()
            for tri in relevant_triangles:
                relevant_points.update(tri)
            relevant_points = list(relevant_points)
            
            # Select points to perturb based on involvement in small triangles
            points_to_perturb = []
            for idx in relevant_points:
                # Count how many small triangles this point is in
                count = sum(1 for tri in relevant_triangles if idx in tri)
                # Higher count means more likely to be perturbed
                if random.random() < count / 3.0:
                    points_to_perturb.append(idx)
            
            # If none selected, pick at least one
            if not points_to_perturb:
                points_to_perturb = [random.choice(relevant_points)]

            # Apply perturbations with log-based adaptive scaling
            for idx in points_to_perturb:
                # Find all triangles involving this point
                triangles_with_idx = [tri for tri in relevant_triangles if idx in tri]
                
                if triangles_with_idx:
                    # Compute average outward direction
                    total_direction = np.zeros(2)
                    total_weight = 0
                    
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
                        # Use log-based scaling for stable weights
                        weight = 1.0 / (np.log(1.0 / (area + 1e-10)) + 1e-5)
                        total_direction += weight * direction
                        total_weight += weight
                    
                    if total_weight > 1e-10:
                        total_direction = total_direction / total_weight
                        
                        # Scale displacement using log-based adaptive factor
                        min_area_involving_point = min([min_areas[i] for i in range(len(min_triangles)) 
                                                      if idx in min_triangles[i]])
                        # Log-based adaptive factor for stable step sizes
                        adaptive_factor = np.log(1.0 / (min_area_involving_point + 1e-10))
                        adaptive_factor = min(3.0, max(0.5, adaptive_factor))  # Constrain to reasonable range
                        
                        # Apply displacement with adaptive factor
                        displacement = total_direction * temp * adaptive_factor
                        # Add small random exploration component
                        random_component = np.random.normal(0, temp * 0.15, size=2)
                        candidate[idx] += displacement + random_component

            # Ensure points stay inside triangle
            for i in range(11):
                candidate[i] = clamp_to_triangle(candidate[i], A, B, C)

            # Evaluate candidate
            candidate_min_area = get_smallest_triangle_area(candidate)
            
            # Acceptance probability
            delta = candidate_min_area - current_min_area
            if delta >= 0 or random.random() < np.exp(delta / temp):
                current_points = candidate
                current_min_area = candidate_min_area
                
                # Track recent improvements for adaptive cooling
                if delta > improvement_threshold:
                    recent_improvements.append(delta)
                    
                # Track best solution
                if candidate_min_area > best_min_area:
                    best_points = candidate.copy()
                    best_min_area = candidate_min_area
                    no_improve_count = 0
                else:
                    no_improve_count += 1
            else:
                no_improve_count += 1

            # Maintain history size
            if len(recent_improvements) > max_history:
                recent_improvements.pop(0)

            # Restart mechanism if stuck in local minimum
            if no_improve_count >= max_no_improve:
                # Apply larger perturbation based on stagnation depth
                perturb_count = max(2, min(5, int(no_improve_count / (max_no_improve * 0.5))))
                current_points = best_points.copy()
                current_min_area = best_min_area
                
                # Apply perturbation to multiple points
                for _ in range(perturb_count):
                    idx = random.randint(0, 10)
                    # Larger steps when deeply stuck
                    step_size = 0.8 * temp * (1 + no_improve_count / max_no_improve)
                    current_points[idx] += np.random.normal(0, step_size, size=2)
                    current_points[idx] = clamp_to_triangle(current_points[idx], A, B, C)
                
                current_min_area = get_smallest_triangle_area(current_points)
                no_improve_count = 0

        # Adaptive cooling based on recent improvements
        if adaptive_cooling and len(recent_improvements) > 0:
            avg_improvement = np.mean(recent_improvements)
            if avg_improvement > 0.0005:  # Good progress
                cooling_rate = 0.98
            elif avg_improvement > 0.0001:  # Moderate progress
                cooling_rate = 0.99
            else:  # Slow progress
                cooling_rate = 0.995
        else:
            cooling_rate = 0.99

        # Cool down
        temp *= cooling_rate

    # Final local search phase considering top-k smallest triangles
    local_search_steps = 150
    local_step_size = 0.003

    final_points = best_points.copy()
    final_min_area = best_min_area

    for _ in range(local_search_steps):
        # Find top 3 smallest triangles
        n = 11
        min_areas = []
        min_triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs((final_points[j,0]-final_points[i,0])*(final_points[k,1]-final_points[i,1]) - 
                                   (final_points[k,0]-final_points[i,0])*(final_points[j,1]-final_points[i,1]))
                    min_areas.append(area)
                    min_triangles.append((i, j, k))
        
        # Sort and take top 3 smallest
        sorted_indices = np.argsort(min_areas)
        relevant_triangles = [min_triangles[i] for i in sorted_indices[:min(3, len(min_areas))]]

        # For each triangle, try to improve
        improved = False
        for triangle in relevant_triangles:
            i, j, k = triangle
            min_area = min_areas[min_triangles.index(triangle)]
            
            # Skip if already large enough
            if min_area > final_min_area * 0.9:
                continue

            # Compute gradient for each point in the triangle
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
                    improved = True

        if not improved:
            break

    return final_points