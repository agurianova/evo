import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Helper function for boundary projection
    def project_to_triangle(p, a, b, c):
        def project_edge(p, a, b):
            ab = b - a
            ap = p - a
            t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
            t = np.clip(t, 0, 1)
            return a + t * ab
        p_ab = project_edge(p, a, b)
        p_bc = project_edge(p, b, c)
        p_ca = project_edge(p, c, a)
        d_ab = np.linalg.norm(p - p_ab)
        d_bc = np.linalg.norm(p - p_bc)
        d_ca = np.linalg.norm(p - p_ca)
        if d_ab <= d_bc and d_ab <= d_ca:
            return p_ab
        elif d_bc <= d_ab and d_bc <= d_ca:
            return p_bc
        else:
            return p_ca

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
    n = len(current)
    
    # Precompute all triangles and area tracking structures
    all_triangles = []
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                all_triangles.append((i, j, k))
    num_tri = len(all_triangles)
    
    # Precompute triangles_by_point for O(1) affected triangle lookup
    triangles_by_point = [[] for _ in range(n)]
    for t, (i, j, k) in enumerate(all_triangles):
        triangles_by_point[i].append(t)
        triangles_by_point[j].append(t)
        triangles_by_point[k].append(t)

    # Initialize area array
    areas = np.zeros(num_tri)
    for t, (i, j, k) in enumerate(all_triangles):
        x1, y1 = current[i]
        x2, y2 = current[j]
        x3, y3 = current[k]
        areas[t] = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))

    best = current.copy()
    best_min_area = np.min(areas)

    # Simulated annealing parameters
    T = 0.1
    max_iter = 20000
    
    for _ in range(max_iter):
        # Current minimum triangle area
        min_area = np.min(areas)

        # Identify bottleneck point (appears in most near-minimal triangles)
        count = np.zeros(n, dtype=int)
        threshold = min_area * 1.1
        for t, (i, j, k) in enumerate(all_triangles):
            if areas[t] <= threshold:
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

        # Generate random movement direction
        direction = np.random.uniform(-1, 1, 2)
        norm_dir = np.linalg.norm(direction)
        if norm_dir < 1e-10:
            direction = np.array([1.0, 0.0])
        else:
            direction /= norm_dir

        # Compute step size with minimum bound (increased multiplier)
        step = 0.3 * max(T, 0.05)
        candidate_point = current[idx] + step * direction

        # Boundary handling with projection
        if not is_inside_triangle(candidate_point.reshape(1, 2), A, B, C):
            candidate_point = project_to_triangle(candidate_point, A, B, C)

        # Create candidate configuration
        new_config = current.copy()
        new_config[idx] = candidate_point
        
        # Compute new_min_area by updating only affected triangles
        candidate_min = float('inf')
        affected_triangles = triangles_by_point[idx]
        for t in range(num_tri):
            if t in affected_triangles:
                i, j, k = all_triangles[t]
                x1, y1 = new_config[i]
                x2, y2 = new_config[j]
                x3, y3 = new_config[k]
                area_val = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
            else:
                area_val = areas[t]
            if area_val < candidate_min:
                candidate_min = area_val
        new_min_area = candidate_min

        # Acceptance criterion
        delta = new_min_area - min_area
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            current = new_config
            # Update areas for affected triangles
            for t in affected_triangles:
                i, j, k = all_triangles[t]
                x1, y1 = current[i]
                x2, y2 = current[j]
                x3, y3 = current[k]
                areas[t] = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
            
            if new_min_area > best_min_area:
                best = current.copy()
                best_min_area = new_min_area

        # Slow cooling
        T *= 0.9995

    return best