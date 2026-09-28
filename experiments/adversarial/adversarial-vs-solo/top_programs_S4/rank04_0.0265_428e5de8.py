import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Distance helper functions for boundary adaptation
    def dist_to_edge(P, A, B):
        AB = B - A
        AP = P - A
        len2_AB = np.dot(AB, AB)
        if len2_AB < 1e-10:
            return np.linalg.norm(AP)
        t = np.dot(AP, AB) / len2_AB
        t = max(0.0, min(1.0, t))
        closest = A + t * AB
        return np.linalg.norm(P - closest)

    def dist_to_boundary(P):
        return min(dist_to_edge(P, A, B), 
                   dist_to_edge(P, B, C), 
                   dist_to_edge(P, C, A))

    # Generate initial configuration with literature-backed row distribution
    rows_distribution = [4, 3, 2, 1, 1]  # Reverted to literature-backed asymmetric pattern
    total_rows = len(rows_distribution)
    
    # Compute adaptive vertical spacing using harmonic mean of adjacent row counts
    deltas = []
    for i in range(total_rows - 1):
        n_i = rows_distribution[i]
        n_i1 = rows_distribution[i + 1]
        deltas.append(1.0 / np.sqrt(n_i * n_i1))
    total_delta = sum(deltas)
    
    cumulative_sum = [0.0]
    for i in range(total_rows - 1):
        cumulative_sum.append(cumulative_sum[-1] + deltas[i])
    
    points = []
    for i, num_in_row in enumerate(rows_distribution):
        # Adaptive vertical position with boundary margins
        v = 0.5 / total_rows + ((total_rows - 1) / total_rows) * (cumulative_sum[i] / total_delta)
        for j in range(num_in_row):
            u = (j + 0.5) / num_in_row * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            # Apply increased initial perturbation for better exploration
            candidate = P + np.random.uniform(-0.10, 0.10, 2)
            if not is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                candidate = project_to_triangle(candidate, A, B, C)
            points.append(candidate)
    
    current = np.array(points)
    best = current.copy()
    best_min_area = get_smallest_triangle_area(best)

    # Simulated annealing parameters
    T = 0.5
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

    # Collinearity metric helper
    def min_triangle_angle(points, i, j, k):
        # Get vectors
        v1 = points[j] - points[i]
        v2 = points[k] - points[i]
        # Normalize
        v1_norm = np.linalg.norm(v1)
        v2_norm = np.linalg.norm(v2)
        if v1_norm < 1e-10 or v2_norm < 1e-10:
            return 0.0  # Degenerate case
        v1 = v1 / v1_norm
        v2 = v2 / v2_norm
        # Dot product gives cosine of angle
        cos_angle = np.clip(np.dot(v1, v2), -1.0, 1.0)
        angle = np.arccos(cos_angle)
        # Return smallest angle in triangle (considering all three vertices)
        angles = [angle]
        
        v1 = points[i] - points[j]
        v2 = points[k] - points[j]
        v1_norm = np.linalg.norm(v1)
        v2_norm = np.linalg.norm(v2)
        if v1_norm > 1e-10 and v2_norm > 1e-10:
            v1 = v1 / v1_norm
            v2 = v2 / v2_norm
            cos_angle = np.clip(np.dot(v1, v2), -1.0, 1.0)
            angles.append(np.arccos(cos_angle))
        
        v1 = points[i] - points[k]
        v2 = points[j] - points[k]
        v1_norm = np.linalg.norm(v1)
        v2_norm = np.linalg.norm(v2)
        if v1_norm > 1e-10 and v2_norm > 1e-10:
            v1 = v1 / v1_norm
            v2 = v2 / v2_norm
            cos_angle = np.clip(np.dot(v1, v2), -1.0, 1.0)
            angles.append(np.arccos(cos_angle))
        
        return min(angles)

    for _ in range(max_iter):
        n = len(current)
        
        # Use helper function for efficiency
        min_area = get_smallest_triangle_area(current)

        # Adaptive threshold for near-minimal triangles (relative scaling with decay)
        threshold_factor = 1.2 - (0.15 * (1 - T/0.5))  # Start at 1.2, decay to 1.05 as T decreases
        threshold = min_area * threshold_factor
        
        # Count near-minimal triangles per point
        count = np.zeros(n, dtype=int)
        # Also track minimum angles for collinearity handling
        min_angles = np.zeros((n, n, n))
        
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
                        # Store minimum angle for collinearity handling
                        min_angles[i, j, k] = min_triangle_angle(current, i, j, k)
        
        # Adaptive step size based on temperature and geometric scale
        step = max(0.005, T * 0.2)

        # Attempt two-point move with adaptive probability
        two_point_done = False
        # Adaptive two-point probability: higher when temperature is high
        two_point_prob = 0.4 * (T / 0.5)
        
        if np.random.rand() < two_point_prob:
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
                
                # Boundary-adaptive step sizing
                d1 = dist_to_boundary(current[p1])
                d2 = dist_to_boundary(current[p2])
                step_local = step * 1.5 if (d1 < 0.01 or d2 < 0.01) else step
                
                # Compute edge vector and perpendicular for height optimization
                vec = current[p2] - current[p1]
                norm = np.linalg.norm(vec)
                if norm > 1e-10:
                    u = vec / norm  # unit vector along edge
                    v = np.array([-u[1], u[0]])  # unit perpendicular vector (90 deg CCW)
                    
                    # Compute midpoint and vector to third vertex
                    mid = (current[p1] + current[p2]) / 2.0
                    w = current[k] - mid
                    d = np.dot(w, v)  # signed distance
                    
                    # Determine direction to move edge away from third vertex
                    if abs(d) < 1e-10:
                        move_dir = np.zeros(2)
                    else:
                        move_dir = -v * np.sign(d)
                    
                    # Adaptive step allocation based on triangle geometry
                    base_ratio = 0.5 + 0.3 * min(1.0, abs(d) / norm)  # More base expansion for flatter triangles
                    step_base = step_local * base_ratio
                    step_perp = step_local * (1 - base_ratio)
                    
                    candidate1 = current[p1] - step_base * u + step_perp * move_dir
                    candidate2 = current[p2] + step_base * u + step_perp * move_dir
                    
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

                    # Enhanced acceptance criterion with collinearity metric
                    current_min_angle = min_triangle_angle(current, i, j, k)
                    new_min_angle = min_triangle_angle(new_config, i, j, k)
                    
                    # Prioritize moves that increase minimum angle in near-degenerate triangles
                    angle_improvement = new_min_angle - current_min_angle
                    
                    # IMPROVEMENT: Increased base factor to 2.0 for near-collinear triangles
                    if current_min_angle < 0.1:
                        angle_factor = 2.0 + max(0, angle_improvement)
                    else:
                        angle_factor = 1.0 + max(0, angle_improvement)
                    
                    # Acceptance criterion with angle-based bonus
                    delta = (new_min_area * angle_factor) - (min_area * 1.0)
                    if delta > 0 or np.random.rand() < np.exp(delta / T):
                        current = new_config
                        if new_min_area > best_min_area:
                            best = current.copy()
                            best_min_area = new_min_area
                    two_point_done = True

        # Single-point move if two-point not done or failed
        if not two_point_done:
            # Weighted selection of bottleneck points based on triangle count
            if np.random.rand() < 0.1:
                idx = np.random.randint(0, n)
            else:
                total = np.sum(count)
                if total == 0:
                    idx = np.random.randint(0, n)
                else:
                    prob = count / total
                    idx = np.random.choice(n, p=prob)
            
            # Boundary-adaptive step sizing
            d = dist_to_boundary(current[idx])
            step_local = step * 1.5 if d < 0.01 else step
            
            # Evaluate candidate directions with higher resolution
            best_candidate = None
            best_new_min_area = -1
            best_angle_improvement = -np.inf
            angles = np.linspace(0, 2*np.pi, 32, endpoint=False)
            for angle in angles:
                direction = np.array([np.cos(angle), np.sin(angle)])
                candidate_point = current[idx] + step_local * direction
                
                # Project to boundary if outside
                if not is_inside_triangle(candidate_point.reshape(1, 2), A, B, C):
                    candidate_point = project_to_triangle(candidate_point, A, B, C)

                # Create candidate configuration
                new_config = current.copy()
                new_config[idx] = candidate_point
                new_min_area = get_smallest_triangle_area(new_config)

                # Track best candidate with angle improvement consideration
                # Find triangles involving this point that were near-minimal
                angle_improvement = 0.0
                for j in range(n):
                    if j == idx: continue
                    for k in range(j + 1, n):
                        if k == idx: continue
                        if min_angles[min(idx, j, k), max(idx, j, k), min(max(idx, j), k)] < 0.1:
                            current_angle = min_triangle_angle(current, idx, j, k)
                            new_angle = min_triangle_angle(new_config, idx, j, k)
                            angle_improvement += max(0, new_angle - current_angle)
                
                # Weight area improvement by angle improvement
                weighted_area = new_min_area * (1 + 0.5 * angle_improvement)
                
                if weighted_area > best_new_min_area:
                    best_new_min_area = weighted_area
                    best_candidate = candidate_point
                    best_angle_improvement = angle_improvement

            # Accept best candidate
            if best_new_min_area > min_area * (1 + 0.5 * best_angle_improvement) or np.random.rand() < np.exp((best_new_min_area - min_area * (1 + 0.5 * best_angle_improvement)) / T):
                current[idx] = best_candidate
                new_min_area = get_smallest_triangle_area(current)
                if new_min_area > best_min_area:
                    best = current.copy()
                    best_min_area = new_min_area

        # Cool down - slower cooling rate
        T *= 0.9995  # Changed from 0.999 to maintain exploration capability

    return best