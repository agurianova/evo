import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import random

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
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
    
    def barycentric_to_cartesian(bary, A, B, C):
        return bary[0] * A + bary[1] * B + bary[2] * C
    
    # Ensure point stays within triangle using barycentric coordinates
    def clamp_to_triangle(p, A, B, C):
        bary = cartesian_to_barycentric(p, A, B, C)
        # Project negative coordinates to zero while maintaining sum=1
        if np.any(bary < 0):
            bary = np.maximum(bary, 0)
            bary = bary / np.sum(bary)
        return barycentric_to_cartesian(bary, A, B, C)

    # Diverse initialization strategies to avoid predictable patterns
    def symmetric_initialization(A, B, C):
        points = np.zeros((11, 2))
        edge_length = np.linalg.norm(B - A)
        
        # Near vertices (2 per vertex)
        vertex_offset = 0.12 * edge_length
        points[0] = A + np.array([vertex_offset, 0])
        points[1] = A + np.array([0, vertex_offset])
        points[2] = B - np.array([vertex_offset, 0])
        points[3] = B + np.array([0, vertex_offset])
        points[4] = C - np.array([0, vertex_offset])
        points[5] = C + np.array([vertex_offset, 0]) - np.array([edge_length/2, 0])
        
        # Along edges (1 per edge)
        edge_offset = 0.15 * edge_length
        points[6] = 0.4 * A + 0.6 * B + np.array([0, edge_offset])
        points[7] = 0.3 * A + 0.7 * C + np.array([edge_offset, 0])
        points[8] = 0.6 * B + 0.4 * C + np.array([-edge_offset, 0])
        
        # Interior points
        points[9] = (A + B + C) / 3.0
        points[10] = 0.25 * A + 0.35 * B + 0.4 * C
        
        return points

    def asymmetric_initialization(A, B, C):
        points = np.zeros((11, 2))
        
        # Near vertices (asymmetric distribution)
        points[0] = A + 0.1 * (B - A) + 0.05 * (C - A)
        points[1] = A + 0.07 * (B - A) + 0.12 * (C - A)
        points[2] = B + 0.13 * (A - B) + 0.08 * (C - B)
        points[3] = B + 0.05 * (A - B) + 0.15 * (C - B)
        points[4] = C + 0.09 * (A - C) + 0.11 * (B - C)
        points[5] = C + 0.15 * (A - C) + 0.06 * (B - C)
        
        # Along edges with varying offsets
        points[6] = 0.35 * A + 0.65 * B + 0.18 * (C - (A+B)/2)
        points[7] = 0.25 * A + 0.75 * C + 0.22 * (B - (A+C)/2)
        points[8] = 0.55 * B + 0.45 * C + 0.16 * (A - (B+C)/2)
        
        # Interior points with deliberate asymmetry
        points[9] = 0.32 * A + 0.33 * B + 0.35 * C
        points[10] = 0.28 * A + 0.37 * B + 0.35 * C
        
        return points

    def grid_based_initialization(A, B, C):
        points = np.zeros((11, 2))
        
        # Create a triangular grid pattern
        n = 4  # Grid resolution
        grid_points = []
        for i in range(n):
            for j in range(n - i):
                # Barycentric coordinates
                u = i / (n - 1)
                v = j / (n - 1)
                w = 1 - u - v
                if w >= 0:
                    grid_points.append(barycentric_to_cartesian([u, v, w], A, B, C))
        
        # Select 11 points from grid (prioritizing symmetry but with some variation)
        if len(grid_points) >= 11:
            indices = np.linspace(0, len(grid_points)-1, 11, dtype=int)
            for i, idx in enumerate(indices):
                points[i] = grid_points[idx]
        else:
            # Fallback to asymmetric if grid too sparse
            return asymmetric_initialization(A, B, C)
            
        return points

    def randomized_initialization(A, B, C):
        points = np.zeros((11, 2))
        
        # Generate points with controlled randomness
        for i in range(11):
            # Use beta distribution to bias toward center but allow edge proximity
            u = np.random.beta(1.5, 1.5)
            v = np.random.beta(1.5, 1.5) * (1 - u)
            w = 1 - u - v
            points[i] = u * A + v * B + w * C
            
        return points

    # Randomly select initialization strategy to avoid predictability
    strategies = [
        symmetric_initialization,
        asymmetric_initialization,
        grid_based_initialization,
        randomized_initialization
    ]
    points = random.choice(strategies)(A, B, C)

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
    stagnation_threshold = 50
    stagnation_counter = 0
    best_min_area = get_smallest_triangle_area(points)
    
    current_points = points.copy()
    current_min_area = best_min_area
    best_points = current_points.copy()
    
    temp = initial_temp
    cooling_rate = base_cooling_rate
    
    while temp > min_temp:
        improved = False
        for _ in range(iterations_per_temp):
            candidate = current_points.copy()
            
            # Make phase transition threshold adaptive based on current best
            phase_transition_threshold = best_min_area * 0.8
            
            # Determine perturbation scope based on current optimization phase
            if current_min_area < phase_transition_threshold:
                # Early phase: broader exploration
                triangle_count = 6
                global_perturbation_prob = 0.15
            else:
                # Later phase: more focused refinement
                triangle_count = 4
                global_perturbation_prob = 0.05

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
                
                # Scale displacement based on density and current min_area - DYNAMIC SCALING
                displacement_scale = temp * 0.4 * (best_min_area * 1.2 / (current_min_area + 1e-10))

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
                
            # Evaluate candidate
            candidate_min_area = get_smallest_triangle_area(candidate)
            
            # Acceptance probability
            delta = candidate_min_area - current_min_area
            if delta >= 0 or random.random() < np.exp(delta / temp):
                current_points = candidate
                current_min_area = candidate_min_area
                improved = True
                
                # Track best solution
                if candidate_min_area > best_min_area:
                    best_points = candidate.copy()
                    best_min_area = candidate_min_area
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

    # Basin exploration phase to verify local optimum depth
    def verify_local_optimum(points, min_area):
        """Systematically test if this is a true local optimum"""
        improved = False
        improved_points = points.copy()
        
        for i in range(11):
            for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
                direction = np.array([np.cos(angle), np.sin(angle)])
                candidate = points.copy()
                candidate[i] += direction * 0.005  # Small perturbation
                candidate[i] = clamp_to_triangle(candidate[i], A, B, C)
                
                # Check validity
                if not is_inside_triangle(candidate, A, B, C):
                    continue
                    
                candidate_min_area = get_smallest_triangle_area(candidate)
                if candidate_min_area > min_area:
                    improved = True
                    improved_points = candidate
                    min_area = candidate_min_area
                    
        return improved, improved_points, min_area

    # Perform basin exploration until no further improvements found
    max_basin_iterations = 3
    for _ in range(max_basin_iterations):
        improved, basin_points, basin_min_area = verify_local_optimum(best_points, best_min_area)
        if improved:
            best_points = basin_points
            best_min_area = basin_min_area
        else:
            break

    return best_points