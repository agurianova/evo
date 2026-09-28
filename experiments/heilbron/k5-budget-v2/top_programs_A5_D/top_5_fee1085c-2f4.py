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

    def project_to_boundary(point, A, B, C):
        """Project a point to the closest point on the triangle boundary."""
        if is_inside_triangle(point, A, B, C):
            return point.copy()
        
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
        
        if d_ab <= d_bc and d_ab <= d_ca:
            return p_ab
        elif d_bc <= d_ab and d_bc <= d_ca:
            return p_bc
        else:
            return p_ca

    def improve(points: np.ndarray) -> np.ndarray:
        # Make seed input-dependent to diversify exploration
        np.random.seed(hash(points.tobytes()) % (2**32))
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        initial_temp = 0.1  # Increased from 0.01 to allow more exploration
        cooling_rate = 0.995  # Adjusted from 0.999 for better balance
        current_temp = initial_temp
        rounds = 500

        for round in range(rounds):
            # Adaptive triangle selection based on area distribution
            all_triangles = find_k_smallest_triangles(current, 10)
            if len(all_triangles) > 1:
                smallest_area = all_triangles[0][0]
                next_smallest = all_triangles[1][0]
                ratio = smallest_area / (next_smallest + 1e-12)
                
                # If smallest areas are very close, select more triangles
                if ratio < 0.9:  # Areas are relatively close
                    num_triangles = min(5, len(all_triangles))
                elif ratio < 0.95:
                    num_triangles = min(3, len(all_triangles))
                else:
                    num_triangles = 1
            else:
                num_triangles = 1

            triangles = all_triangles[:num_triangles]
            
            # Track how many triangles each point is in for gradient normalization
            point_gradients = {}
            point_triangle_counts = {}
            for _, i, j, k in triangles:
                for idx in [i, j, k]:
                    point_triangle_counts[idx] = point_triangle_counts.get(idx, 0) + 1

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

            # Normalize gradients by triangle count
            for idx in point_gradients:
                point_gradients[idx] /= point_triangle_counts[idx]

            step_size_val = 0.01 * (0.99 ** round)  # Reduced initial size and increased decay

            def normalize_grad(grad, step_size):
                norm = np.linalg.norm(grad)
                if norm < 1e-8:
                    return np.zeros(2)
                return grad / norm * step_size

            candidate = current.copy()
            for idx, grad in point_gradients.items():
                delta = normalize_grad(grad, step_size_val)
                candidate[idx] += delta

            # Project each point to boundary if needed
            for idx in range(candidate.shape[0]):
                candidate[idx] = project_to_boundary(candidate[idx], A, B, C)

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