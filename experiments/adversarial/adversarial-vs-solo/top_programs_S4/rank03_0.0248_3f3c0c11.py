import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Generate initial configuration with balanced row distribution
    rows_distribution = [3, 3, 3, 2]
    total_rows = len(rows_distribution)
    points = []
    for i, num_in_row in enumerate(rows_distribution):
        v = (i + 0.5) / total_rows
        for j in range(num_in_row):
            u = (j + 0.5) / num_in_row * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            # Apply larger perturbation with boundary check
            for _ in range(10):
                candidate = P + np.random.uniform(-0.05, 0.05, 2)
                if is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                    P = candidate
                    break
            points.append(P)
    
    current = np.array(points)
    best = current.copy()

    # Precompute all triangle indices (i,j,k) with i<j<k
    triangle_indices = []
    n = len(current)
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                triangle_indices.append((i, j, k))
    num_triangles = len(triangle_indices)
    
    # Initialize area cache
    areas = np.zeros(num_triangles)
    for idx_tri, (i, j, k) in enumerate(triangle_indices):
        x1, y1 = current[i]
        x2, y2 = current[j]
        x3, y3 = current[k]
        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
        areas[idx_tri] = area
    best_min_area = np.min(areas)

    # Simulated annealing parameters
    T = 0.1
    max_iter = 20000
    
    # Helper function for boundary projection
    def project_to_triangle(p, A, B, C):
        if is_inside_triangle(p.reshape(1, 2), A, B, C):
            return p
        
        edges = [(A, B), (B, C), (C, A)]
        best_point = None
        best_dist = float('inf')
        
        for (v1, v2) in edges:
            v1v2 = v2 - v1
            v1p = p - v1
            len2 = np.dot(v1v2, v1v2)
            if len2 < 1e-10:
                proj = v1
            else:
                t = np.dot(v1p, v1v2) / len2
                t = max(0.0, min(1.0, t))
                proj = v1 + t * v1v2
            dist = np.linalg.norm(p - proj)
            if dist < best_dist:
                best_dist = dist
                best_point = proj
        
        return best_point

    for _ in range(max_iter):
        # Compute current min area and bottleneck counts
        min_area = np.min(areas)
        threshold = min_area * 1.1
        count = np.zeros(n, dtype=int)
        for idx_tri, (i, j, k) in enumerate(triangle_indices):
            if areas[idx_tri] <= threshold:
                count[i] += 1
                count[j] += 1
                count[k] += 1

        # Select point to move: 10% chance random, else bottleneck point
        if np.random.rand() < 0.1:
            idx = np.random.randint(0, n)
        else:
            max_count = np.max(count)
            candidates = np.where(count == max_count)[0]
            idx = np.random.choice(candidates)

        # Save areas for triangles containing idx
        indices_to_update = []
        old_areas = []
        for idx_tri, (i, j, k) in enumerate(triangle_indices):
            if idx in (i, j, k):
                indices_to_update.append(idx_tri)
                old_areas.append(areas[idx_tri])

        # Generate random movement direction
        direction = np.random.uniform(-1, 1, 2)
        norm_dir = np.linalg.norm(direction)
        if norm_dir < 1e-10:
            direction = np.array([1.0, 0.0])
        else:
            direction /= norm_dir

        # Compute step size (increased multiplier from 0.1 to 0.3)
        step = 0.3 * max(T, 0.05)
        candidate_point = current[idx] + step * direction

        # Boundary handling via projection
        if not is_inside_triangle(candidate_point.reshape(1, 2), A, B, C):
            candidate_point = project_to_triangle(candidate_point, A, B, C)

        # Create candidate configuration
        new_config = current.copy()
        new_config[idx] = candidate_point
        
        # Update areas for triangles containing idx
        for pos, idx_tri in enumerate(indices_to_update):
            i, j, k = triangle_indices[idx_tri]
            x1, y1 = new_config[i]
            x2, y2 = new_config[j]
            x3, y3 = new_config[k]
            area_val = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
            areas[idx_tri] = area_val
        new_min_area = np.min(areas)

        # Acceptance criterion
        delta = new_min_area - min_area
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            current = new_config
            if new_min_area > best_min_area:
                best = new_config.copy()
                best_min_area = new_min_area
        else:
            # Restore old areas for rejected move
            for pos, idx_tri in enumerate(indices_to_update):
                areas[idx_tri] = old_areas[pos]

        # Slow cooling
        T *= 0.9995

    return best