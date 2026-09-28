from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib


def entrypoint():
    A, B, C = get_unit_triangle()

    def get_min_triangle(points):
        n = points.shape[0]
        min_area = float('inf')
        min_indices = (0, 1, 2)
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    x1, y1 = points[i]
                    x2, y2 = points[j]
                    x3, y3 = points[k]
                    area = 0.5 * abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        return min_area, min_indices

    def improve(points: np.ndarray) -> np.ndarray:
        # Seed randomness based on input configuration
        seed = int(hashlib.sha256(points.tobytes()).hexdigest(), 16) % (2**32)
        np.random.seed(seed)
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        initial_temp = 0.5
        cooling_rate = 0.95
        max_iter = 500
        no_improve_count = 0
        
        for iter in range(max_iter):
            temp = initial_temp * (cooling_rate ** iter)
            
            # Find smallest triangle
            current_score, (i, j, k) = get_min_triangle(current)
            p1, p2, p3 = current[i], current[j], current[k]
            
            # Compute triangle area and side lengths
            area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p2[1]-p1[1])*(p3[0]-p1[0]))
            base_jk = np.linalg.norm(p3 - p2)
            base_ik = np.linalg.norm(p3 - p1)
            base_ij = np.linalg.norm(p2 - p1)
            
            # Compute heights for each vertex
            height_i = 2 * area / base_jk if base_jk > 1e-10 else float('inf')
            height_j = 2 * area / base_ik if base_ik > 1e-10 else float('inf')
            height_k = 2 * area / base_ij if base_ij > 1e-10 else float('inf')
            
            # Select bottleneck point (smallest height)
            heights = [height_i, height_j, height_k]
            idx = [i, j, k][np.argmin(heights)]
            min_height = min(heights)
            
            # Determine opposite side and compute normal direction
            if idx == i:
                a, b = p2, p3
            elif idx == j:
                a, b = p1, p3
            else:
                a, b = p1, p2
            
            base = b - a
            normal = np.array([-base[1], base[0]])
            if np.linalg.norm(normal) < 1e-10:
                direction = np.random.normal(0, 1, size=2)
                direction = direction / np.linalg.norm(direction)
            else:
                normal = normal / np.linalg.norm(normal)
                # Determine outward direction
                vec = current[idx] - a
                sign = np.sign(np.dot(vec, normal))
                direction = sign * normal
            
            # Adaptive step size based on bottleneck height
            step_magnitude = temp * (0.001 / (min_height + 1e-5))
            step = step_magnitude * direction
            
            # Generate candidate point with boundary projection
            candidate = current[idx] + step
            if not is_inside_triangle(candidate, A, B, C):
                s = 1.0
                for _ in range(10):
                    s /= 2
                    candidate = current[idx] + s * step
                    if is_inside_triangle(candidate, A, B, C):
                        break

            # Create candidate configuration
            new_points = current.copy()
            new_points[idx] = candidate
            new_score = get_smallest_triangle_area(new_points)

            # Acceptance logic
            if new_score > current_score or np.random.rand() < np.exp((new_score - current_score) / temp):
                current = new_points
                current_score = new_score

            # Update best solution
            if new_score > best_score:
                best = new_points.copy()
                best_score = new_score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Early stopping
            if no_improve_count >= 50:
                break

        return best

    return improve