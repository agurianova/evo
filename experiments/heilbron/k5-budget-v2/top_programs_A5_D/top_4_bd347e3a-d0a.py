from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def triangle_area(a, b, c):
        return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))

    def find_k_smallest_triangles(pts, k):
        n = pts.shape[0]
        triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k_idx in range(j+1, n):
                    area = triangle_area(pts[i], pts[j], pts[k_idx])
                    triangles.append((area, i, j, k_idx))
        triangles.sort(key=lambda x: x[0])
        return triangles[:k]

    def interior_penalty(point, A, B, C, penalty_strength=10.0):
        """Apply penalty to keep points inside the triangle without forcing to boundary."""
        if is_inside_triangle(point, A, B, C):
            return np.zeros(2)
        
        def point_to_line_distance(p, a, b):
            ab = b - a
            ap = p - a
            t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-12)
            t = max(0, min(1, t))
            projection = a + t * ab
            return projection, np.linalg.norm(p - projection)
        
        p_ab, d_ab = point_to_line_distance(point, A, B)
        p_bc, d_bc = point_to_line_distance(point, B, C)
        p_ca, d_ca = point_to_line_distance(point, C, A)
        
        # Calculate penalty gradient (points away from the closest edge)
        if d_ab <= d_bc and d_ab <= d_ca:
            normal = np.array([-(B[1]-A[1]), B[0]-A[0]])
            normal = normal / (np.linalg.norm(normal) + 1e-12)
            return normal * d_ab * penalty_strength
        elif d_bc <= d_ab and d_bc <= d_ca:
            normal = np.array([-(C[1]-B[1]), C[0]-B[0]])
            normal = normal / (np.linalg.norm(normal) + 1e-12)
            return normal * d_bc * penalty_strength
        else:
            normal = np.array([-(A[1]-C[1]), A[0]-C[0]])
            normal = normal / (np.linalg.norm(normal) + 1e-12)
            return normal * d_ca * penalty_strength

    def improve(points: np.ndarray) -> np.ndarray:
        # Make seed input-dependent to diversify exploration
        np.random.seed(hash(points.tobytes()) % (2**32))
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        # Increased initial temperature for better exploration
        initial_temp = 0.1
        cooling_rate = 0.995
        current_temp = initial_temp
        # Increased rounds for more thorough search
        rounds = 1000

        q_max = 0.0365  # Heilbron upper bound

        for round in range(rounds):
            # Dynamic triangle selection based on area distribution
            all_triangles = find_k_smallest_triangles(current, 10)
            smallest_area = all_triangles[0][0]
            fifth_smallest_area = all_triangles[4][0] if len(all_triangles) >= 5 else smallest_area * 1.5
            
            # Adaptive threshold based on current optimization level
            optimization_level = smallest_area / q_max
            # When close to optimal, be more selective (lower threshold)
            # When far from optimal, be more inclusive (higher threshold)
            adaptive_threshold = 1.2 + 0.8 * (1 - optimization_level)
            
            # If smallest areas are close together, select more triangles
            if fifth_smallest_area / (smallest_area + 1e-10) < adaptive_threshold:
                num_triangles = min(5, len(all_triangles))
            else:
                num_triangles = min(3, len(all_triangles))
            
            triangles = all_triangles[:num_triangles]
            
            # Accumulate gradients for points that might be in multiple triangles
            point_gradients = {}
            triangle_counts = {}
            for _, i, j, k in triangles:
                for idx in [i, j, k]:
                    triangle_counts[idx] = triangle_counts.get(idx, 0) + 1
                
                a, b, c = current[i], current[j], current[k]

                f = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                sign_f = 1.0 if f >= 0 else -1.0

                grad_a = np.array([b[1]-c[1], c[0]-b[0]]) * 0.5 * sign_f
                grad_b = np.array([c[1]-a[1], a[0]-c[0]]) * 0.5 * sign_f
                grad_c = np.array([a[1]-b[1], b[0]-a[0]]) * 0.5 * sign_f

                for idx, grad in [(i, grad_a), (j, grad_b), (k, grad_c)]:
                    if idx in point_gradients:
                        point_gradients[idx] += grad
                    else:
                        point_gradients[idx] = grad

            # Adaptive step size with faster decay
            step_size_val = 0.01 * (0.99 ** round)

            def normalize_grad(grad, step_size, count):
                # Use sqrt(count) instead of count to better preserve importance of critical points
                norm = np.linalg.norm(grad)
                if norm < 1e-8:
                    return np.zeros(2)
                return grad / norm * step_size / max(1, np.sqrt(count))

            candidate = current.copy()
            for idx, grad in point_gradients.items():
                count = triangle_counts.get(idx, 1)
                delta = normalize_grad(grad, step_size_val, count)
                candidate[idx] += delta
                
                # Apply interior penalty instead of boundary projection
                penalty = interior_penalty(candidate[idx], A, B, C)
                candidate[idx] += penalty

            # Verify that the gradient move actually improves the critical triangles
            verification_score = 0
            for _, i, j, k in triangles:
                orig_area = triangle_area(current[i], current[j], current[k])
                new_area = triangle_area(candidate[i], candidate[j], candidate[k])
                if new_area > orig_area:
                    verification_score += 1

            # If the move doesn't improve most critical triangles, reduce step size
            if verification_score < 0.7 * len(triangles):
                for idx, grad in point_gradients.items():
                    count = triangle_counts.get(idx, 1)
                    delta = normalize_grad(grad, step_size_val * 0.5, count)  # Half step
                    candidate[idx] = current[idx] + delta
                    penalty = interior_penalty(candidate[idx], A, B, C)
                    candidate[idx] += penalty

            # Final boundary check - should rarely be needed due to interior penalty
            for idx in range(candidate.shape[0]):
                if not is_inside_triangle(candidate[idx], A, B, C):
                    # Fallback: move toward centroid of triangle
                    centroid = (A + B + C) / 3
                    direction = centroid - candidate[idx]
                    direction = direction / (np.linalg.norm(direction) + 1e-12)
                    candidate[idx] = candidate[idx] + direction * 0.01

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - current_score

            if delta > 0 or np.random.rand() < np.exp(delta / current_temp):
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score

            current_temp *= cooling_rate

        return best

    return improve