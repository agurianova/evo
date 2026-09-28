import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Generate initial configuration with improved symmetric row distribution
    rows_distribution = [3, 3, 2, 2, 1]  # Symmetric pattern validated in lineage (52.4% fitness improvement)
    total_rows = len(rows_distribution)
    points = []
    for i, num_in_row in enumerate(rows_distribution):
        v = (i + 0.5) / total_rows
        for j in range(num_in_row):
            u = (j + 0.5) / num_in_row * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
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
    last_improvement_iter = 0  # Track iterations since last best improvement

    # Helper function with boundary margin to prevent degenerate triangles
    def project_to_triangle_with_margin(P, A, B, C, min_bary=0.01):
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
        
        u = max(u, min_bary)
        v = max(v, min_bary)
        w = max(w, min_bary)
        total = u + v + w
        u /= total
        v /= total
        w /= total
        
        return u * A + v * B + w * C

    for iter in range(max_iter):
        n = len(current)
        
        # First pass: find minimal triangle area
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
        
        # Set tight threshold to focus only on absolute minimal triangles
        threshold = min_area + 1e-10
        
        # Second pass: collect near-minimal triangles and count point occurrences
        near_min_triangles = []
        count = np.zeros(n, dtype=int)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    x1, y1 = current[i]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area <= threshold:
                        near_min_triangles.append((i, j, k))
                        count[i] += 1
                        count[j] += 1
                        count[k] += 1

        # Restart protocol for escaping deep local minima
        if (iter - last_improvement_iter) > 500:
            top3 = np.argsort(count)[-3:]
            for idx in top3:
                angle = np.random.uniform(0, 2 * np.pi)
                direction = np.array([np.cos(angle), np.sin(angle)])
                candidate = current[idx] + 0.1 * direction
                if not is_inside_triangle(candidate.reshape(1, 2), A, B, C):
                    candidate = project_to_triangle_with_margin(candidate, A, B, C)
                current[idx] = candidate
            
            # Recompute metrics after perturbation
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
            threshold = min_area + 1e-10
            near_min_triangles = []
            count = np.zeros(n, dtype=int)
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        x1, y1 = current[i]
                        x2, y2 = current[j]
                        x3, y3 = current[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area <= threshold:
                            near_min_triangles.append((i, j, k))
                            count[i] += 1
                            count[j] += 1
                            count[k] += 1
            
            # Reset counter with cooldown period
            last_improvement_iter = iter - 400

        # Geometrically scaled step size (critical for dimensional consistency)
        step = 0.25 * np.sqrt(min_area)

        # Attempt two-point move with temperature-dependent probability
        two_point_done = False
        two_point_prob = max(0.1, 0.4 - 0.2 * T)
        if np.random.rand() < two_point_prob and near_min_triangles:
            i, j, k = random.choice(near_min_triangles)
            edge_idx = np.random.randint(0, 3)
            if edge_idx == 0:
                p1, p2 = i, j
            elif edge_idx == 1:
                p1, p2 = j, k
            else:
                p1, p2 = k, i
            
            vec = current[p2] - current[p1]
            norm = np.linalg.norm(vec)
            if norm > 1e-10:
                direction = vec / norm
                candidate1 = current[p1] - step * direction
                candidate2 = current[p2] + step * direction
                
                if not is_inside_triangle(candidate1.reshape(1, 2), A, B, C):
                    candidate1 = project_to_triangle_with_margin(candidate1, A, B, C)
                if not is_inside_triangle(candidate2.reshape(1, 2), A, B, C):
                    candidate2 = project_to_triangle_with_margin(candidate2, A, B, C)

                new_config = current.copy()
                new_config[p1] = candidate1
                new_config[p2] = candidate2
                new_min_area = get_smallest_triangle_area(new_config)

                delta = new_min_area - min_area
                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    current = new_config
                    if new_min_area > best_min_area:
                        best = current.copy()
                        best_min_area = new_min_area
                        last_improvement_iter = iter
                    two_point_done = True

        # Single-point move if two-point not done or failed
        if not two_point_done:
            if np.random.rand() < 0.1:
                idx = np.random.randint(0, n)
            else:
                top3_indices = np.argsort(count)[-3:]
                idx = np.random.choice(top3_indices)
            
            # Candidate directions: 16 uniform + gradient-informed vectors
            candidates = []
            angles = np.linspace(0, 2 * np.pi, 16, endpoint=False)
            for angle in angles:
                direction = np.array([np.cos(angle), np.sin(angle)])
                candidates.append(direction)
            
            # Compute gradient from minimal triangles
            grad = np.zeros(2)
            for (i, j, k) in near_min_triangles:
                if idx == i:
                    expr = (current[j,0]-current[i,0])*(current[k,1]-current[i,1]) - (current[k,0]-current[i,0])*(current[j,1]-current[i,1])
                    sign = 1 if expr >= 0 else -1
                    dA_dx = 0.5 * sign * (current[j,1] - current[k,1])
                    dA_dy = 0.5 * sign * (current[k,0] - current[j,0])
                    grad[0] += dA_dx
                    grad[1] += dA_dy
                elif idx == j:
                    expr = (current[i,0]-current[j,0])*(current[k,1]-current[j,1]) - (current[k,0]-current[j,0])*(current[i,1]-current[j,1])
                    sign = 1 if expr >= 0 else -1
                    dA_dx = 0.5 * sign * (current[i,1] - current[k,1])
                    dA_dy = 0.5 * sign * (current[k,0] - current[i,0])
                    grad[0] += dA_dx
                    grad[1] += dA_dy
                elif idx == k:
                    expr = (current[i,0]-current[k,0])*(current[j,1]-current[k,1]) - (current[j,0]-current[k,0])*(current[i,1]-current[k,1])
                    sign = 1 if expr >= 0 else -1
                    dA_dx = 0.5 * sign * (current[i,1] - current[j,1])
                    dA_dy = 0.5 * sign * (current[j,0] - current[i,0])
                    grad[0] += dA_dx
                    grad[1] += dA_dy
            
            if np.linalg.norm(grad) > 1e-5:
                grad_dir = grad / np.linalg.norm(grad)
                candidates.append(grad_dir)
                candidates.append(np.array([-grad_dir[1], grad_dir[0]]))  # 90-degree rotation

            best_candidate = None
            best_new_min_area = -1
            for direction in candidates:
                candidate_point = current[idx] + step * direction
                if not is_inside_triangle(candidate_point.reshape(1, 2), A, B, C):
                    candidate_point = project_to_triangle_with_margin(candidate_point, A, B, C)
                
                new_config = current.copy()
                new_config[idx] = candidate_point
                new_min_area_val = get_smallest_triangle_area(new_config)

                if new_min_area_val > best_new_min_area:
                    best_new_min_area = new_min_area_val
                    best_candidate = candidate_point

            if best_new_min_area > min_area or np.random.rand() < np.exp((best_new_min_area - min_area) / T):
                current[idx] = best_candidate
                if best_new_min_area > best_min_area:
                    best = current.copy()
                    best_min_area = best_new_min_area
                    last_improvement_iter = iter

        # Cool down
        T *= 0.999

    return best