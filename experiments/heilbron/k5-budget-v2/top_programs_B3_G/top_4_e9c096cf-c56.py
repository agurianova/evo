import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import random

np.random.seed(42)
random.seed(42)

# Golden angle in radians (137.5 degrees) for optimal dispersion
GOLDEN_ANGLE = 2 * np.pi * (3 - np.sqrt(5))

# Target Heilbron minimum area for n=11
TARGET_MIN_AREA = 0.0365

# Adaptive radius ranges will be calculated based on progress toward target
# Optimal ring structure for n=11: 1 center + 3 inner + 3 middle + 4 outer


def clamp_to_triangle(point, A, B, C):
    # Convert to barycentric coordinates
    v0 = B - A
    v1 = C - A
    v2 = point - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-10:
        return (A + B + C) / 3.0
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    
    # Renormalize to ensure inside triangle
    if u < 0:
        u, v, w = 0, v/(v+w), w/(v+w)
    elif v < 0:
        u, v, w = u/(u+w), 0, w/(u+w)
    elif w < 0:
        u, v, w = u/(u+v), v/(u+v), 0
    
    # Convert back to Cartesian
    return u * A + v * B + w * C

def shannon_entropy(areas):
    """Calculate Shannon entropy of area distribution"""
    areas = np.array(areas)
    areas = areas[areas > 0]  # Remove zeros
    if len(areas) == 0:
        return 0
    probs = areas / np.sum(areas)
    return -np.sum(probs * np.log2(probs + 1e-10))

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Center of triangle (Cartesian)
    center = (A + B + C) / 3.0
    
    # Initial random configuration with literature-supported 1+3+3+4 ring structure
    points = np.zeros((11, 2))
    
    # Center point
    points[0] = center
    
    # Generate initial configuration with adaptive parameters
    current_min_area = 0.0
    progress = current_min_area / TARGET_MIN_AREA
    
    # Adaptive radius ranges based on progress
    R1_RANGE = (0.20 * (1 + progress), 0.30 * (1 + progress))  # Inner ring
    R2_RANGE = (0.45 * (1 + progress), 0.60 * (1 + progress))  # Middle ring
    R3_RANGE = (0.70 * (1 + progress), 0.85 * (1 + progress))  # Outer ring

    # Inner ring (3 points) - using golden angle for optimal dispersion
    for i in range(3):
        angle = GOLDEN_ANGLE * i + random.uniform(0, np.pi/6)
        r = random.uniform(*R1_RANGE)
        dx = r * np.cos(angle)
        dy = r * np.sin(angle)
        candidate = center + np.array([dx, dy])
        points[i+1] = clamp_to_triangle(candidate, A, B, C)
    
    # Middle ring (3 points)
    for i in range(3):
        angle = 2 * np.pi * i * np.sqrt(2) + random.uniform(0, np.pi/8)
        r = random.uniform(*R2_RANGE)
        dx = r * np.cos(angle)
        dy = r * np.sin(angle)
        candidate = center + np.array([dx, dy])
        points[i+4] = clamp_to_triangle(candidate, A, B, C)
    
    # Outer ring (4 points) - note increased count to 4
    for i in range(4):
        angle = 2 * np.pi * i * np.sqrt(3) + random.uniform(0, np.pi/12)
        r = random.uniform(*R3_RANGE)
        dx = r * np.cos(angle)
        dy = r * np.sin(angle)
        candidate = center + np.array([dx, dy])
        points[i+7] = clamp_to_triangle(candidate, A, B, C)
    
    # Enhanced simulated annealing optimization with adaptive parameters
    initial_temp = 0.1
    min_temp = 1e-6
    iterations_per_temp = 150
    
    # Track absolute best solution to prevent regression
    best_overall = points.copy()
    best_overall_min_area = get_smallest_triangle_area(best_overall)
    
    current_points = points.copy()
    current_min_area = best_overall_min_area
    best_points = current_points.copy()
    best_min_area = current_min_area
    
    temp = initial_temp
    while temp > min_temp:
        # Recalculate progress for adaptive parameters
        progress = current_min_area / TARGET_MIN_AREA
        
        # Adaptive cooling rate - slow down as we approach optimum
        cooling_rate = 0.92 + 0.06 * (1 - progress)
        
        # Adaptive buffer for boundary proximity
        buffer = 0.01 * (1 - progress)
        
        # Adaptive displacement factor
        displacement_factor = 1.2 + 0.8 * (1 - progress)
        
        for _ in range(iterations_per_temp):
            # Create candidate by perturbing points
            candidate = current_points.copy()
            
            # Find all triangle areas
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
            
            # Calculate entropy to determine focus areas
            areas_entropy = shannon_entropy(min_areas)
            # Focus more on problematic regions when entropy is low (more uniform small triangles)
            adaptive_k = max(10, int(30 * (1 - areas_entropy)))
            
            # Sort by area and take top adaptive_k smallest triangles
            sorted_indices = np.argsort(min_areas)
            top_indices = sorted_indices[:adaptive_k]
            
            # Randomly select 10 from these for spatial diversity
            selected_indices = np.random.choice(top_indices, size=min(10, len(top_indices)), replace=False)
            relevant_triangles = [min_triangles[i] for i in selected_indices]
            
            # Collect points involved in these triangles
            relevant_points = set()
            for tri in relevant_triangles:
                relevant_points.update(tri)
            relevant_points = list(relevant_points)
            
            # Select 4-6 points to perturb
            num_to_perturb = min(6, max(4, len(relevant_points) // 2))
            points_to_perturb = random.sample(relevant_points, num_to_perturb)

            # Geometrically-informed perturbations with adaptive magnitude
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
                        weight = 1.0 / (area + max(1e-10, 0.01*current_min_area))
                        total_direction += weight * direction
                    
                    if np.linalg.norm(total_direction) > 1e-10:
                        total_direction = total_direction / np.linalg.norm(total_direction)
                        
                        # Apply displacement with adaptive factor
                        displacement = total_direction * temp * displacement_factor
                        # Add random exploration component with non-linear schedule
                        random_component = np.random.normal(0, temp**0.7 * 0.8, size=2)
                        candidate[idx] += displacement + random_component

            # Ensure points stay inside triangle
            for i in range(11):
                candidate[i] = clamp_to_triangle(candidate[i], A, B, C)

            # Evaluate candidate
            candidate_min_area = get_smallest_triangle_area(candidate)
            
            # Track absolute best solution
            if candidate_min_area > best_overall_min_area:
                best_overall = candidate.copy()
                best_overall_min_area = candidate_min_area

            # Acceptance probability
            delta = candidate_min_area - current_min_area
            if delta >= 0 or random.random() < np.exp(delta / temp):
                current_points = candidate
                current_min_area = candidate_min_area
                
                # Track best solution at current temperature
                if candidate_min_area > best_min_area:
                    best_points = candidate.copy()
                    best_min_area = candidate_min_area

        # Cool down with adaptive rate
        temp *= cooling_rate

    return best_overall