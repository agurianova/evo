import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def get_smallest_triangle_indices(points, top_n=3):
    n = points.shape[0]
    min_areas = []
    min_indices = []
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                 (points[k,0]-points[i,0])*(points[j,1]-points[i,1]))
                if len(min_areas) < top_n or area < max(min_areas):
                    if len(min_areas) == top_n:
                        idx = min_areas.index(max(min_areas))
                        min_areas[idx] = area
                        min_indices[idx] = (i, j, k)
                    else:
                        min_areas.append(area)
                        min_indices.append((i, j, k))
    
    # Sort by area (smallest first)
    sorted_indices = [x for _, x in sorted(zip(min_areas, min_indices))]
    return sorted_indices

def optimize_configuration(seed):
    np.random.seed(seed)
    A, B, C = get_unit_triangle()
    
    # Initialize with 11 interior points only (no vertices) using [3,3,2,2,1] pattern
    points = []
    
    # Generate points in 5 rows with adaptive counts
    rows = 5
    points_per_row = [3, 3, 2, 2, 1]  # More balanced distribution
    total_points = sum(points_per_row)
    assert total_points == 11

    for i, n in enumerate(points_per_row):
        v = (i + 1) / (rows + 1)  # Better spacing from edge
        for j in range(n):
            u = (j + 0.5) / n * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            # Add larger perturbation to break symmetry (±0.01 instead of ±0.001)
            P += np.random.uniform(-0.01, 0.01, size=2)
            points.append(P)
    
    current_points = np.array(points)
    current_min_area = get_smallest_triangle_area(current_points)

    # PHASE 1: Global exploration with higher temperature and step size
    step_size = 0.05  # Increased from 0.01
    temperature = 0.01  # Increased from 0.0005

    for _ in range(500):
        i = np.random.randint(0, 11)
        dx = step_size * np.random.normal(0, 1)
        dy = step_size * np.random.normal(0, 1)
        
        new_points = current_points.copy()
        new_points[i] += [dx, dy]
        
        if is_inside_triangle(new_points[i], A, B, C):
            new_min_area = get_smallest_triangle_area(new_points)
            delta = new_min_area - current_min_area
            
            # Simulated annealing acceptance with higher temperature
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current_points = new_points
                current_min_area = new_min_area

        # Adaptive cooling
        temperature *= 0.995
        if temperature < 1e-6:
            temperature = 1e-6

    # PHASE 2: Focused optimization on smallest triangles
    best_points = current_points.copy()
    best_min_area = current_min_area
    step_size = 0.02
    temperature = 0.002
    no_improve_count = 0
    
    for iteration in range(1500):
        # Get top 3 smallest triangles instead of just one
        smallest_triangles = get_smallest_triangle_indices(current_points, top_n=3)
        
        candidate = current_points.copy()
        
        # Perturb points from top 3 smallest triangles with weighted influence
        all_indices = set()
        for idx, triangle in enumerate(smallest_triangles):
            weight = 1.0 - (idx * 0.2)  # Decreasing weight for less small triangles
            for point_idx in triangle:
                all_indices.add(point_idx)
                # Apply perturbation with weight based on triangle rank
                candidate[point_idx] += weight * step_size * np.random.normal(0, 1, 2)

        if is_inside_triangle(candidate, A, B, C):
            new_min_area = get_smallest_triangle_area(candidate)
            delta = new_min_area - current_min_area
            
            if new_min_area > best_min_area:
                best_points = candidate.copy()
                best_min_area = new_min_area
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Simulated annealing acceptance
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current_points = candidate
                current_min_area = new_min_area

        # Adaptive cooling and step size
        temperature *= 0.997
        if no_improve_count > 500:  # Increased from 200
            step_size *= 0.97
            no_improve_count = 0
            
        if step_size < 1e-5:
            break

    return best_points, best_min_area

def entrypoint() -> np.ndarray:
    # Run multiple independent optimizations and select the best
    best_configuration = None
    best_min_area = -1
    
    for seed in range(5):  # 5 independent runs
        config, min_area = optimize_configuration(seed)
        if min_area > best_min_area:
            best_configuration = config
            best_min_area = min_area
    
    return best_configuration