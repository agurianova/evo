import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Generate initial configuration with literature-backed row distribution
    rows_distribution = [3, 3, 2, 2, 1]  # Changed to match proven Heilbronn patterns for 11 points
    total_rows = len(rows_distribution)
    points = []
    for i, num_in_row in enumerate(rows_distribution):
        v = (i + 0.5) / total_rows
        for j in range(num_in_row):
            u = (j + 0.5) / num_in_row * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            # Apply reduced initial perturbation with boundary projection
            candidate = P + np.random.uniform(-0.02, 0.02, 2)
            if not is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                candidate = project_to_triangle(candidate, A, B, C)
            points.append(candidate)
    
    current = np.array(points)
    best = current.copy()
    best_min_area = get_smallest_triangle_area(best)

    # Simulated annealing parameters
    T = 0.5  # Increased initial temperature
    max_iter = 20000
    
    # Helper function for boundary projection
    def project_to_triangle(P, A, B, C):
        def point_to_segment(p, a, b):
            ab = b - a
            ap = p - a
            len2_ab = np.dot(ab, ab)
            if len2_ab < 1e-10:
                return a
            t = np.dot(ap, ab) / len2_ab
            t = max(0.0, min(1.0, t))
            return a + t * ab
        
        p1 = point_to_segment(P, A, B)
        p2 = point_to_segment(P, B, C)
        p3 = point_to_segment(P, C, A)
        d1 = np.linalg.norm(P - p1)
        d2 = np.linalg.norm(P - p2)
        d3 = np.linalg.norm(P - p3)
        if d1 <= d2 and d1 <= d3:
            return p1
        elif d2 <= d1 and d2 <= d3:
            return p2
        else:
            return p3

    for _ in range(max_iter):
        n = len(current)
        
        # Find global minimum triangle area
        min_area = float('inf')
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    x1, y1 = current[i]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area < min_area:
                        min_area = area
        
        # Adaptive threshold for near-minimal triangles
        threshold = min_area + min(0.001, 0.1 * min_area)
        
        # Count near-minimal triangles per point
        count = np.zeros(n, dtype=int)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    x1, y1 = current[i]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area <= threshold:
                        count[i] += 1
                        count[j] += 1
                        count[k] += 1
        
        # Adaptive step size based on temperature and geometric scale
        step = max(0.02, T * 0.2)

        # Attempt two-point move with 20% probability
        two_point_done = False
        if np.random.rand() < 0.2:
            # Find all near-minimal triangles
            near_min_triangles = []
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        x1, y1 = current[i]
                        x2, y2 = current[j]
                        x3, y3 = current[k]
                        area_val = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area_val <= threshold:
                            near_min_triangles.append((i, j, k))
            
            if near_min_triangles:
                # Select random triangle and edge
                i, j, k = random.choice(near_min_triangles)
                edge_idx = np.random.randint(0, 3)
                if edge_idx == 0:
                    p1, p2 = i, j
                elif edge_idx == 1:
                    p1, p2 = j, k
                else:
                    p1, p2 = k, i
                
                # Move points apart along edge direction
                vec = current[p2] - current[p1]
                norm = np.linalg.norm(vec)
                if norm > 1e-10:
                    direction = vec / norm
                    candidate1 = current[p1] - step * direction
                    candidate2 = current[p2] + step * direction
                    
                    # Project to boundary if outside
                    if not is_inside_triangle(candidate1.reshape(1, 2), A, B, C):
                        candidate1 = project_to_triangle(candidate1, A, B, C)
                    if not is_inside_triangle(candidate2.reshape(1, 2), A, B, C):
                        candidate2 = project_to_triangle(candidate2, A, B, C)

                    # Create candidate configuration
                    new_config = current.copy()
                    new_config[p1] = candidate1
                    new_config[p2] = candidate2
                    new_min_area = get_smallest_triangle_area(new_config)

                    # Acceptance criterion
                    delta = new_min_area - min_area
                    if delta > 0 or np.random.rand() < np.exp(delta / T):
                        current = new_config
                        if new_min_area > best_min_area:
                            best = current.copy()
                            best_min_area = new_min_area
                    two_point_done = True

        # Single-point move if two-point not done or failed
        if not two_point_done:
            # Select point to move: 10% chance random, else top-3 bottleneck points
            if np.random.rand() < 0.1:
                idx = np.random.randint(0, n)
            else:
                top3_indices = np.argsort(count)[-3:]
                idx = np.random.choice(top3_indices)
            
            # Evaluate candidate directions
            best_candidate = None
            best_new_min_area = -1
            angles = np.linspace(0, 2*np.pi, 8, endpoint=False)
            for angle in angles:
                direction = np.array([np.cos(angle), np.sin(angle)])
                candidate_point = current[idx] + step * direction
                
                # Project to boundary if outside
                if not is_inside_triangle(candidate_point.reshape(1, 2), A, B, C):
                    candidate_point = project_to_triangle(candidate_point, A, B, C)

                # Create candidate configuration
                new_config = current.copy()
                new_config[idx] = candidate_point
                new_min_area = get_smallest_triangle_area(new_config)

                # Track best candidate
                if new_min_area > best_new_min_area:
                    best_new_min_area = new_min_area
                    best_candidate = candidate_point

            # Accept best candidate
            if best_new_min_area > min_area or np.random.rand() < np.exp((best_new_min_area - min_area) / T):
                current[idx] = best_candidate
                if best_new_min_area > best_min_area:
                    best = current.copy()
                    best_min_area = best_new_min_area

        # Cool down
        T *= 0.999

    return best