import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    base_seed = 42
    best_points = None
    best_min_area = -1

    # Precompute base step size for hexagonal lattice
    d0 = np.sqrt(2 / (11 * np.sqrt(3)))
    
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Precompute triangle bounding box
    x_min = min(A[0], B[0], C[0])
    x_max = max(A[0], B[0], C[0])
    y_min = min(A[1], B[1], C[1])
    y_max = max(A[1], B[1], C[1])

    # Helper: get x-range at given y
    def get_x_range_at_y(y):
        vertices = [A, B, C]
        edges = [(0, 1), (1, 2), (2, 0)]
        xs = []
        for i, j in edges:
            p1, p2 = vertices[i], vertices[j]
            if min(p1[1], p2[1]) <= y <= max(p1[1], p2[1]):
                if abs(p1[1] - p2[1]) < 1e-10:
                    x = (p1[0] + p2[0]) / 2
                else:
                    t = (y - p1[1]) / (p2[1] - p1[1])
                    x = p1[0] + t * (p2[0] - p1[0])
                xs.append(x)
        return (min(xs), max(xs)) if len(xs) >= 2 else (None, None)

    # Helper: generate boundary-adapted lattice (without golden ratio)
    def generate_boundary_adapted_lattice(d):
        points = []
        hex_height = (np.sqrt(3) / 2) * d
        y = y_min
        row_index = 0
        
        while y <= y_max:
            left_x, right_x = get_x_range_at_y(y)
            if left_x is None or right_x is None:
                y += hex_height
                row_index += 1
                continue
                
            # Hexagonal offset
            if row_index % 2 == 1:
                x_start = left_x + d / 2
            else:
                x_start = left_x
                
            x = x_start
            while x <= right_x:
                p = np.array([x, y])
                if is_inside_triangle(p.reshape(1, 2), A, B, C):
                    points.append(p)
                x += d
                
            y += hex_height
            row_index += 1
            
        return points

    # Helper: area-aware greedy selection
    def area_aware_sampling(candidates, k):
        n = len(candidates)
        if k >= n:
            return np.array(candidates)
        selected = []

        # Select first point (arbitrary start)
        selected.append(candidates[0])
        
        # Select second point (maximize distance from first)
        if k >= 2:
            max_dist = -1
            idx = -1
            for i, c in enumerate(candidates[1:], 1):
                d = np.linalg.norm(c - selected[0])
                if d > max_dist:
                    max_dist = d
                    idx = i
            selected.append(candidates[idx])

        # Select third point (maximize triangle area with first two)
        if k >= 3:
            max_area = -1
            idx = -1
            for i, c in enumerate(candidates):
                if any(np.allclose(c, s) for s in selected):
                    continue
                area = 0.5 * abs((selected[1][0]-selected[0][0])*(c[1]-selected[0][1]) - 
                                 (c[0]-selected[0][0])*(selected[1][1]-selected[0][1]))
                if area > max_area:
                    max_area = area
                    idx = i
            selected.append(candidates[idx])

        # Select remaining points (maximize global min triangle area)
        for _ in range(3, k):
            best_candidate = None
            best_min_area = -1
            for c in candidates:
                if any(np.allclose(c, s) for s in selected):
                    continue
                temp_set = np.vstack([np.array(selected), c])
                min_area = get_smallest_triangle_area(temp_set)
                if min_area > best_min_area:
                    best_min_area = min_area
                    best_candidate = c
            if best_candidate is None:
                break
            selected.append(best_candidate)

        return np.array(selected)

    # Helper: find optimal 11th point for 10-point config
    def find_best_11th_point(points_10, num_candidates=100):
        candidates = []
        while len(candidates) < num_candidates:
            x = np.random.uniform(x_min, x_max)
            y = np.random.uniform(y_min, y_max)
            p = np.array([x, y])
            if is_inside_triangle(p.reshape(1, 2), A, B, C):
                candidates.append(p)
        
        best_candidate = None
        best_global_min_area = -1
        
        for c in candidates:
            temp_points = np.vstack([points_10, c])
            global_min_area = get_smallest_triangle_area(temp_points)
            
            if global_min_area > best_global_min_area:
                best_global_min_area = global_min_area
                best_candidate = c
                
        return best_candidate

    # Helper: perturb points slightly
    def perturb_points(points, magnitude):
        perturbed = []
        for p in points:
            theta = np.random.uniform(0, 2 * np.pi)
            dx = magnitude * np.cos(theta)
            dy = magnitude * np.sin(theta)
            perturbed.append(p + [dx, dy])
        return np.array(perturbed)

    # Helper: generate symmetry-based configuration (with uniform edge points)
    def generate_symmetry_configuration():
        # Start with centroid
        centroid = (A + B + C) / 3
        points = [centroid]
        
        # Add midpoints of edges
        points.append((A + B) / 2)
        points.append((B + C) / 2)
        points.append((C + A) / 2)
        
        # Add points at 1/3 and 2/3 on each edge (replaces golden ratio)
        points.append(A + (B - A) / 3)
        points.append(A + 2 * (B - A) / 3)
        points.append(B + (C - B) / 3)
        points.append(B + 2 * (C - B) / 3)
        points.append(C + (A - C) / 3)
        points.append(C + 2 * (A - C) / 3)
        
        # Filter points inside triangle
        valid_points = []
        for p in points:
            if is_inside_triangle(p.reshape(1, 2), A, B, C):
                valid_points.append(p)
        
        # If we have more than 11 points, select the best 11 using area-aware sampling
        if len(valid_points) > 11:
            return area_aware_sampling(valid_points, 11)
        
        # If fewer than 11, add random points to complete
        while len(valid_points) < 11:
            x = np.random.uniform(x_min, x_max)
            y = np.random.uniform(y_min, y_max)
            p = np.array([x, y])
            if is_inside_triangle(p.reshape(1, 2), A, B, C):
                valid_points.append(p)
        
        return np.array(valid_points)

    # Initialize with four strategies (20 restarts each)
    total_restarts = 80
    restarts_per_type = 20
    deltas_hex = np.logspace(np.log10(0.3), np.log10(2.0), restarts_per_type)

    for restart_idx in range(total_restarts):
        np.random.seed(base_seed + restart_idx)
        
        if restart_idx < restarts_per_type:  # Hexagonal lattice
            d = d0 * deltas_hex[restart_idx]
            lattice_points = generate_boundary_adapted_lattice(d)
            if len(lattice_points) < 11:
                continue
            points = area_aware_sampling(lattice_points, 11)
            
        elif restart_idx < 2 * restarts_per_type:  # Random points
            points = []
            while len(points) < 11:
                x = np.random.uniform(x_min, x_max)
                y = np.random.uniform(y_min, y_max)
                p = np.array([x, y])
                if is_inside_triangle(p.reshape(1, 2), A, B, C):
                    points.append(p)
            points = np.array(points)
            
        elif restart_idx < 3 * restarts_per_type:  # Known 10-point configuration
            d = d0 * deltas_hex[restart_idx - 2 * restarts_per_type]
            lattice_points = generate_boundary_adapted_lattice(d)
            if len(lattice_points) < 10:
                continue
            points_10 = area_aware_sampling(lattice_points, 10)
            p11 = find_best_11th_point(points_10)
            points = np.vstack([points_10, p11])
            points = perturb_points(points, d * 0.01)

        else:  # Symmetry-based configuration
            points = generate_symmetry_configuration()

        # Simulated annealing with adaptive critical point weighting
        T0 = 0.1
        T = T0
        cooling_rate = 0.999
        total_iters = 10000
        stagnation_count = 0
        weight_base = 2.0
        weight_max = 5.0
        stagnation_threshold = 500  # Initial value, will adapt
        block_start_min = get_smallest_triangle_area(points)
        block_start_iter = 0

        for iter_idx in range(total_iters):
            current_min = get_smallest_triangle_area(points)

            # Identify critical points (in smallest triangles)
            critical_points = set()
            threshold = max(1e-12, 1e-4 * current_min)
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                         (points[k,0]-points[i,0])*(points[j,1]-points[i,1]))
                        if abs(area - current_min) < threshold:
                            critical_points.update([i, j, k])

            # Adaptive critical point weighting
            weight = weight_base
            if stagnation_count > stagnation_threshold:
                steps = stagnation_count - stagnation_threshold
                if steps <= 18:
                    weight = weight_base * (1.15 ** steps)  # Increased growth rate
                else:
                    weight = weight_max
            
            # Adaptive stagnation threshold update
            if iter_idx > 0 and (iter_idx - block_start_iter) >= 1000:
                improvement = max(0, current_min - block_start_min)
                avg_improvement = improvement / (iter_idx - block_start_iter)
                stagnation_threshold = 200 if avg_improvement < 1e-6 else 800
                block_start_min = current_min
                block_start_iter = iter_idx

            # Biased point selection
            weights = np.ones(11)
            if critical_points:
                weights[list(critical_points)] = weight
            weights /= weights.sum()
            idx = np.random.choice(11, p=weights)

            # Exploration schedule
            num_directions = max(30, int(50 * T / T0) + 10)
            best_improvement = -np.inf
            best_candidate = None

            for _ in range(num_directions):
                theta = np.random.uniform(0, 2 * np.pi)
                magnitude = np.sqrt(T)
                dx = magnitude * np.cos(theta)
                dy = magnitude * np.sin(theta)

                candidate = points.copy()
                candidate[idx] += [dx, dy]
                if not is_inside_triangle(candidate[idx:idx+1], A, B, C):
                    continue

                new_min = get_smallest_triangle_area(candidate)
                if new_min > best_improvement:
                    best_improvement = new_min
                    best_candidate = candidate

            prev_min_area = current_min
            if best_candidate is not None:
                delta = best_improvement - current_min
                if delta >= 0:
                    points = best_candidate
                    if best_improvement > current_min:
                        stagnation_count = 0
                    else:
                        stagnation_count += 1
                else:
                    if np.random.rand() < np.exp(delta / T):
                        points = best_candidate
                        stagnation_count += 1
                    else:
                        stagnation_count += 1

            T *= cooling_rate

        current_min_area = get_smallest_triangle_area(points)
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_points = points.copy()

    return best_points.astype(np.float32)