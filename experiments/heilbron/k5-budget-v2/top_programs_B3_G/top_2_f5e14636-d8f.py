import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import random

np.random.seed(42)
random.seed(42)

# Global constants for Heilbronn problem
HEILBRONN_TARGET = 0.0365

# Soft boundary constraint penalty function
def boundary_penalty(point, A, B, C):
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
        return 0.0
        
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    
    # Calculate distance to nearest boundary
    distances = [u, v, w]
    min_distance = min(distances)
    
    # Apply penalty when too close to boundary
    if min_distance < 0.05:
        return (0.05 - min_distance) * 0.1
    return 0.0

# Evaluate configuration with boundary penalty
def evaluate_with_penalty(points, A, B, C):
    base_score = get_smallest_triangle_area(points)
    total_penalty = 0.0
    
    for i in range(len(points)):
        total_penalty += boundary_penalty(points[i], A, B, C)
    
    # Apply penalty to score (smaller penalty = better)
    return max(0, base_score - total_penalty)

# Simulate basic opponent attack to test resistance
def test_resistance(points, A, B, C, num_tests=5):
    original_score = get_smallest_triangle_area(points)
    current = points.copy()
    improved = False
    
    for _ in range(num_tests):
        # Find smallest triangle
        n = 11
        min_area = float('inf')
        best_triangle = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs((points[j,0]-points[i,0]) * 
                                   (points[k,1]-points[i,1]) - 
                                   (points[k,0]-points[i,0]) * 
                                   (points[j,1]-points[i,1]))
                    if area < min_area:
                        min_area = area
                        best_triangle = (i, j, k)
        
        if best_triangle is None:
            continue
        
        i, j, k = best_triangle
        
        # Try to expand the smallest triangle
        candidate = current.copy()
        direction = np.array([0, 0])
        
        # Compute outward normal for each point
        for idx in [i, j, k]:
            others = [p for p in [i, j, k] if p != idx]
            p1, p2 = points[others[0]], points[others[1]]
            
            edge = p2 - p1
            normal = np.array([-edge[1], edge[0]])
            norm = np.linalg.norm(normal)
            if norm > 1e-10:
                normal /= norm
            
            to_point = points[idx] - p1
            direction = normal if np.dot(to_point, normal) > 0 else -normal
            
            # Apply small displacement
            candidate[idx] = points[idx] + direction * 0.005

        # Check if valid and improves score
        if is_inside_triangle(candidate, A, B, C):
            candidate_score = get_smallest_triangle_area(candidate)
            if candidate_score > original_score:
                improved = True
                break

    return not improved  # True if resistant (no improvement found)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Vertex-biased asymmetric initialization matching known Heilbronn optima
    # 2 points near each vertex, 1 point along each edge, 2 interior points
    points = np.zeros((11, 2))
    
    # Helper for barycentric coordinate conversion
    def cartesian_to_barycentric(p, A, B, C):
        v0 = B - A
        v1 = C - A
        v2 = p - A
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
    
    # Ensure point stays within triangle using soft boundary constraints
    def clamp_to_triangle(p, A, B, C):
        bary = cartesian_to_barycentric(p, A, B, C)
        # Soft constraint: allow points near boundary but with penalty
        if np.any(bary < 0):
            bary = np.maximum(bary, 0)
            bary = bary / np.sum(bary)
        return barycentric_to_cartesian(bary, A, B, C)

    def barycentric_to_cartesian(bary, A, B, C):
        return bary[0] * A + bary[1] * B + bary[2] * C

    # Place points near vertices (2 per vertex)
    vertex_offset = 0.15  # Will be optimized during annealing
    edge_length = np.linalg.norm(B - A)
    
    # Near vertex A
    points[0] = A + vertex_offset * (B - A) + vertex_offset * (C - A)
    points[1] = A + 0.7 * vertex_offset * (B - A) + 0.3 * vertex_offset * (C - A)
    
    # Near vertex B
    points[2] = B + vertex_offset * (A - B) + vertex_offset * (C - B)
    points[3] = B + 0.4 * vertex_offset * (A - B) + 0.6 * vertex_offset * (C - B)
    
    # Near vertex C
    points[4] = C + vertex_offset * (A - C) + vertex_offset * (B - C)
    points[5] = C + 0.6 * vertex_offset * (A - C) + 0.4 * vertex_offset * (B - C)
    
    # Place points along edges (1 per edge)
    edge_offset = 0.2  # Offset from edge toward interior
    points[6] = 0.3 * A + 0.7 * B + edge_offset * (C - (A+B)/2)  # AB edge
    points[7] = 0.2 * A + 0.8 * C + edge_offset * (B - (A+C)/2)  # AC edge
    points[8] = 0.6 * B + 0.4 * C + edge_offset * (A - (B+C)/2)  # BC edge
    
    # Place interior points with controlled asymmetry
    points[9] = (A + B + C) / 3.0 + np.array([0.05, -0.03])  # Center with asymmetry
    points[10] = 0.25 * A + 0.35 * B + 0.4 * C + np.array([-0.02, 0.04])  # Asymmetric interior

    # Ensure all points are properly inside the triangle
    for i in range(11):
        points[i] = clamp_to_triangle(points[i], A, B, C)
    
    # Adaptive simulated annealing optimization
    initial_temp = 0.03
    min_temp = 1e-6
    iterations_per_temp = 75
    
    # Adaptive cooling parameters
    base_cooling_rate = 0.99
    min_cooling_rate = 0.98
    max_cooling_rate = 0.999
    stagnation_threshold = 25  # Reduced from 50
    stagnation_counter = 0
    best_min_area = get_smallest_triangle_area(points)
    
    current_points = points.copy()
    current_min_area = best_min_area
    best_points = current_points.copy()
    
    temp = initial_temp
    cooling_rate = base_cooling_rate
    
    # Track resistance of best configuration
    best_resistant = test_resistance(best_points, A, B, C)
    
    while temp > min_temp:
        improved = False
        for _ in range(iterations_per_temp):
            candidate = current_points.copy()
            
            # Determine perturbation scope based on current optimization phase
            if current_min_area < 0.03:  # Increased from 0.02
                # Early phase: broader exploration
                triangle_count = 3  # Reduced from 6
                global_perturbation_prob = 0.15
            else:
                # Later phase: more focused refinement
                triangle_count = 2  # Reduced from 4
                global_perturbation_prob = 0.015  # Reduced from 0.05

            # Global perturbation with small probability
            if random.random() < global_perturbation_prob:
                # Apply small random perturbations to all points
                for i in range(11):
                    candidate[i] += np.random.normal(0, temp * 0.3, size=2)
            else:
                # Targeted perturbation based on smallest triangles
                n = 11
                min_areas = []
                min_triangles = []
                
                for i in range(n):
                    for j in range(i+1, n):
                        for k in range(j+1, n):
                            area = 0.5 * abs((current_points[j,0]-current_points[i,0]) * 
                                           (current_points[k,1]-current_points[i,1]) - 
                                           (current_points[k,0]-current_points[i,0]) * 
                                           (current_points[j,1]-current_points[i,1]))
                            min_areas.append(area)
                            min_triangles.append((i, j, k))
                
                # Sort by area and take top triangles
                sorted_indices = np.argsort(min_areas)
                relevant_triangles = [min_triangles[i] for i in sorted_indices[:triangle_count]]
                
                # Weighted selection: smaller triangles have higher probability
                weights = [1.0/(min_areas[i] + 1e-10) for i in sorted_indices[:triangle_count]]
                weights = np.array(weights) / sum(weights)
                selected_tri = relevant_triangles[np.random.choice(len(relevant_triangles), p=weights)]
                
                # Collect points involved and determine outward directions
                relevant_points = list(selected_tri)
                
                # Compute adaptive displacement magnitude based on local geometry
                local_density = 0
                for p in relevant_points:
                    distances = np.linalg.norm(current_points - current_points[p], axis=1)
                    distances = np.sort(distances)
                    local_density += 1.0 / (distances[1] + 1e-10)  # Use nearest neighbor distance
                local_density /= len(relevant_points)
                
                # Scale displacement based on density and current min_area (using target value)
                displacement_scale = temp * 0.4 * (HEILBRONN_TARGET / max(current_min_area, HEILBRONN_TARGET))

                # Compute outward directions for each point in the triangle
                for idx in relevant_points:
                    # Get the other two points in the triangle
                    others = [p for p in relevant_points if p != idx]
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
                    
                    # Apply displacement with adaptive magnitude
                    displacement = direction * displacement_scale
                    candidate[idx] += displacement

            # Ensure all points remain inside triangle using barycentric constraints
            valid = True
            for i in range(11):
                candidate[i] = clamp_to_triangle(candidate[i], A, B, C)
                
            # Evaluate candidate with boundary penalty
            candidate_min_area = evaluate_with_penalty(candidate, A, B, C)
            
            # Acceptance probability
            delta = candidate_min_area - current_min_area
            if delta >= 0 or random.random() < np.exp(delta / temp):
                current_points = candidate
                current_min_area = candidate_min_area
                improved = True
                
                # Track best solution
                raw_candidate_min_area = get_smallest_triangle_area(candidate)
                if raw_candidate_min_area > best_min_area:
                    # Only accept if resistant to basic perturbations
                    if test_resistance(candidate, A, B, C):
                        best_points = candidate.copy()
                        best_min_area = raw_candidate_min_area
                        best_resistant = True
                        stagnation_counter = 0
                    elif not best_resistant:  # If current best isn't resistant, accept better score
                        best_points = candidate.copy()
                        best_min_area = raw_candidate_min_area
                        best_resistant = False
                        stagnation_counter = 0

        # Adaptive cooling schedule
        if improved:
            # Slow cooling when making progress
            cooling_rate = min(max_cooling_rate, cooling_rate * 1.005)
            stagnation_counter = 0
        else:
            stagnation_counter += 1
            # Faster cooling when stuck
            cooling_rate = max(min_cooling_rate, cooling_rate * 0.995)
            
            # Reheat if stuck for too long
            if stagnation_counter > stagnation_threshold:
                temp = initial_temp * 0.7
                stagnation_counter = 0
                cooling_rate = base_cooling_rate

        # Cool down
        temp *= cooling_rate

    return best_points