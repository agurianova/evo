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

    # Helper: generate boundary-adapted lattice
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

    # Helper: farthest-point sampling
    def farthest_point_sampling(candidates, k):
        if k >= len(candidates):
            return np.array(candidates)
        selected = [candidates[0]]
        remaining = candidates[1:]
        
        for _ in range(1, k):
            max_min_dist = -1
            best_idx = -1
            for j, p in enumerate(remaining):
                min_dist = min(np.linalg.norm(p - s) for s in selected)
                if min_dist > max_min_dist:
                    max_min_dist = min_dist
                    best_idx = j
            if best_idx == -1:
                break
            selected.append(remaining[best_idx])
            del remaining[best_idx]
            
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
        best_min_dist = -1
        for c in candidates:
            min_dist = min(np.linalg.norm(c - p) for p in points_10)
            if min_dist > best_min_dist:
                best_min_dist = min_dist
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

    # Initialize with three strategies (10 restarts each)
    total_restarts = 30
    restarts_per_type = 10
    deltas_hex = np.logspace(np.log10(0.5), np.log10(1.5), restarts_per_type)

    for restart_idx in range(total_restarts):
        np.random.seed(base_seed + restart_idx)
        
        if restart_idx < restarts_per_type:  # Hexagonal lattice
            d = d0 * deltas_hex[restart_idx]
            lattice_points = generate_boundary_adapted_lattice(d)
            if len(lattice_points) < 11:
                continue
            points = farthest_point_sampling(lattice_points, 11)
            
        elif restart_idx < 2 * restarts_per_type:  # Random points
            points = []
            while len(points) < 11:
                x = np.random.uniform(x_min, x_max)
                y = np.random.uniform(y_min, y_max)
                p = np.array([x, y])
                if is_inside_triangle(p.reshape(1, 2), A, B, C):
                    points.append(p)
            points = np.array(points)
            
        else:  # Known 10-point configuration
            d = d0 * deltas_hex[restart_idx - 2 * restarts_per_type]
            lattice_points = generate_boundary_adapted_lattice(d)
            if len(lattice_points) < 10:
                continue
            points_10 = farthest_point_sampling(lattice_points, 10)
            p11 = find_best_11th_point(points_10)
            points = np.vstack([points_10, p11])
            points = perturb_points(points, d * 0.01)

        # Simulated annealing
        T0 = 0.1
        T = T0
        cooling_rate = 0.999
        total_iters = 10000

        for iter_idx in range(total_iters):
            current_min = get_smallest_triangle_area(points)

            # Identify critical points (in smallest triangles)
            critical_points = set()
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                         (points[k,0]-points[i,0])*(points[j,1]-points[i,1]))
                        if abs(area - current_min) < 1e-10:
                            critical_points.update([i, j, k])

            # Biased point selection with moderated weighting
            weights = np.ones(11)
            if critical_points:
                weights[list(critical_points)] = 3.0  # Reduced from 10.0
            weights /= weights.sum()
            idx = np.random.choice(11, p=weights)

            # Corrected exploration schedule (decreases with temperature)
            num_directions = int(50 * T / T0) + 10
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

            if best_candidate is not None:
                delta = best_improvement - current_min
                if delta >= 0:
                    points = best_candidate
                else:
                    if np.random.rand() < np.exp(delta / T):
                        points = best_candidate

            T *= cooling_rate

        current_min_area = get_smallest_triangle_area(points)
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_points = points.copy()

    return best_points.astype(np.float32)