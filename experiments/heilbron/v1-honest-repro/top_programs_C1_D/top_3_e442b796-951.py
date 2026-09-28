from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib


def entrypoint():
    A, B, C = get_unit_triangle()
    # Calculate side length of the unit-area equilateral triangle
    side_length = np.linalg.norm(B - A)

    def seed_from_points(points):
        # Create a deterministic but configuration-specific seed
        point_hash = hashlib.md5(str(np.round(points, 6)).encode()).hexdigest()
        return int(point_hash[:8], 16) % (2**32)

    def project_to_triangle(point, A, B, C):
        """Project a point outside the triangle back to the nearest boundary point."""
        if is_inside_triangle(point, A, B, C):
            return point
        
        # Project onto each edge and find closest point
        edges = [(A, B), (B, C), (C, A)]
        min_dist = float('inf')
        closest_point = None
        
        for (P1, P2) in edges:
            # Vector from P1 to P2
            v = P2 - P1
            # Vector from P1 to point
            w = point - P1
            # Project w onto v
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 == 0:
                b = 0
            else:
                b = max(0, min(1, c1 / c2))
            # Closest point on the line segment
            proj = P1 + b * v
            dist = np.linalg.norm(point - proj)
            if dist < min_dist:
                min_dist = dist
                closest_point = proj
        
        return closest_point

    def improve(points: np.ndarray) -> np.ndarray:
        # Seed randomness based on input configuration
        np.random.seed(seed_from_points(points))
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        
        # If input is degenerate (shouldn't happen per problem constraints), return as-is
        if current_score <= 0:
            return current

        # Track the best configuration seen
        best_points = current.copy()
        best_score = current_score
        
        # Initialize annealing parameters with absolute scaling
        T = 0.001  # Fixed temperature independent of min_area
        cooling_rate = 0.99
        max_iter = 300
        
        # Absolute scaling based on triangle side length
        step_size = 0.001 * side_length
        noise_size = 0.0001 * side_length
        k_smallest = 3  # Consider top k smallest triangles

        for it in range(max_iter):
            # Find top k smallest triangles
            triangles = find_k_smallest_triangles(current, k_smallest)
            
            # Initialize combined gradients
            grads = np.zeros_like(current)
            
            # Compute gradients for each of the k smallest triangles
            for min_area_val, i, j, k in triangles:
                a, b, c = current[i], current[j], current[k]
                S = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                sign = 1 if S >= 0 else -1

                # Compute gradients for |S| (area without 0.5 factor)
                grad_a = np.array([b[1]-c[1], c[0]-b[0]]) * sign
                grad_b = np.array([c[1]-a[1], a[0]-c[0]]) * sign
                grad_c = np.array([a[1]-b[1], b[0]-a[0]]) * sign

                # Normalize gradients
                def normalize(g):
                    norm = np.linalg.norm(g)
                    return g / norm if norm > 0 else g

                # Add to combined gradients (weighted by 1/rank to prioritize smaller triangles)
                weight = 1.0 / (triangles.index((min_area_val, i, j, k)) + 1)
                grads[i] += weight * normalize(grad_a)
                grads[j] += weight * normalize(grad_b)
                grads[k] += weight * normalize(grad_c)

            # Create candidate by moving points according to combined gradients
            candidate = current.copy()
            for idx in range(len(candidate)):
                if np.linalg.norm(grads[idx]) > 0:
                    displacement = step_size * normalize(grads[idx]) + \
                                  np.random.normal(0, noise_size, 2)
                    candidate[idx] += displacement

            # Project any points outside the triangle back to boundary
            for idx in range(len(candidate)):
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

            new_score = get_smallest_triangle_area(candidate)
            if new_score <= 0:  # Degenerate triangle
                # Still cool down but don't update current
                T *= cooling_rate
                continue

            # Update best solution if improved
            if new_score > best_score:
                best_points = candidate.copy()
                best_score = new_score

            # Simulated annealing acceptance for current state
            delta = new_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current = candidate
                current_score = new_score

            T *= cooling_rate

        return best_points

    def find_k_smallest_triangles(points, k):
        n = points.shape[0]
        triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = triangle_area(points[i], points[j], points[k])
                    triangles.append((area, i, j, k))
        
        # Sort by area and return top k
        triangles.sort(key=lambda x: x[0])
        return triangles[:k]

    def triangle_area(a, b, c):
        return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    def normalize(g):
        norm = np.linalg.norm(g)
        return g / norm if norm > 0 else g

    return improve