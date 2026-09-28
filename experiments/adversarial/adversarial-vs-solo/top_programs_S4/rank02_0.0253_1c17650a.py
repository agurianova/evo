import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Generate initial configuration with symmetric row distribution (recovered from Child 1 improvement)
    rows_distribution = [3, 3, 2, 2, 1]  # Symmetric pattern avoids base clustering
    total_rows = len(rows_distribution)
    points = []
    for i, num_in_row in enumerate(rows_distribution):
        v = (i + 0.5) / total_rows
        for j in range(num_in_row):
            u = (j + 0.5) / num_in_row * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            # Apply initial perturbation
            candidate = P + np.random.uniform(-0.05, 0.05, 2)
            if not is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                candidate = project_to_triangle_with_margin(candidate, A, B, C)
            points.append(candidate)
    
    current = np.array(points)
    best = current.copy()
    best_min_area = get_smallest_triangle_area(best)

    # Simulated annealing parameters
    T = 0.5
    max_iter = 20000

    # Helper function for boundary projection (removed harmful repulsion)
    def project_to_triangle_with_margin(P, A, B, C, min_bary=0.0):
        # Convert to barycentric coordinates
        v0 = B - A
        v1 = C - A
        v2 = P - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        if abs(denom) < 1e-10:
            # Fallback to original projection if degenerate
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

        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w
        
        # Enforce minimum barycentric coordinate (now 0.0 by default)
        u = max(u, min_bary)
        v = max(v, min_bary)
        w = max(w, min_bary)
        total = u + v + w
        u /= total
        v /= total
        w /= total
        
        return u * A + v * B + w * C

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
        
        # Fixed precision threshold for absolute minimal triangles
        threshold = min_area + 1e-10
        
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
        
        # Geometrically scaled step size (dimensionally consistent)
        step = 0.1 * np.sqrt(min_area)

        # Adaptive two-point move probability (decreases with cooling)
        two_point_done = False
        two_point_prob = max(0.1, 0.8 * T)  # Decreasing probability during cooling
        if np.random.rand() < two_point_prob:
            # Find all minimal triangles
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
                # Select random minimal triangle and edge
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
                    
                    # Project to boundary (with min_bary=0.0)
                    if not is_inside_triangle(candidate1.reshape(1, 2), A, B, C):
                        candidate1 = project_to_triangle_with_margin(candidate1, A, B, C)
                    if not is_inside_triangle(candidate2.reshape(1, 2), A, B, C):
                        candidate2 = project_to_triangle_with_margin(candidate2, A, B, C)

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
            
            # Compute gradient directions from minimal triangles involving this point
            gradient_directions = []
            for j in range(n):
                if j == idx: continue
                for k in range(j+1, n):
                    if k == idx: continue
                    x1, y1 = current[idx]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    area_val = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area_val <= threshold:
                        # Compute signed area S (without 0.5)
                        S = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
                        # Gradient direction for point idx: (y_j - y_k, x_k - x_j)
                        dx = y2 - y3
                        dy = x3 - x2
                        direction_vector = np.array([dx, dy])
                        norm_dir = np.linalg.norm(direction_vector)
                        if norm_dir < 1e-10:
                            continue
                        unit_dir = direction_vector / norm_dir
                        # Direction that increases area: sign(S) * unit_dir
                        sign_S = 1.0 if S >= 0 else -1.0
                        gradient_dir = sign_S * unit_dir
                        gradient_directions.append(gradient_dir)
                        if len(gradient_directions) >= 3:
                            break
                if len(gradient_directions) >= 3:
                    break
            
            # Evaluate candidate directions (16 fixed + gradient-informed)
            best_candidate = None
            best_new_min_area = -1
            candidate_directions = []
            # Add 16 fixed directions
            angles = np.linspace(0, 2*np.pi, 16, endpoint=False)
            for angle in angles:
                candidate_directions.append(np.array([np.cos(angle), np.sin(angle)]))
            # Add gradient directions
            candidate_directions.extend(gradient_directions)
            
            for direction in candidate_directions:
                candidate_point = current[idx] + step * direction
                
                # Project to boundary
                if not is_inside_triangle(candidate_point.reshape(1, 2), A, B, C):
                    candidate_point = project_to_triangle_with_margin(candidate_point, A, B, C)

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