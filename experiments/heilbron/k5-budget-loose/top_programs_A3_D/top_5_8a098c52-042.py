from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

# Helper function to find closest point on triangle boundary
def find_closest_point_on_triangle(point, A, B, C):
    def point_to_line_segment(p, a, b):
        ap = p - a
        ab = b - a
        t = np.dot(ap, ab) / np.dot(ab, ab)
        t = max(0, min(1, t))
        projection = a + t * ab
        return projection, np.linalg.norm(projection - p)

    # Check all three edges
    p1, d1 = point_to_line_segment(point, A, B)
    p2, d2 = point_to_line_segment(point, B, C)
    p3, d3 = point_to_line_segment(point, C, A)
    
    if d1 <= d2 and d1 <= d3:
        return p1
    elif d2 <= d1 and d2 <= d3:
        return p2
    else:
        return p3

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Seed based on input for diverse exploration per configuration
        seed = hash(points.tobytes()) & 0xFFFFFFFF
        np.random.seed(seed)
        
        n = 11
        input_score = get_smallest_triangle_area(points)
        best = points.copy()
        best_score = input_score
        current = points.copy()
        current_score = input_score

        initial_step = 0.05
        initial_temp = 0.1  # Increased from 0.05 to 0.1

        for iteration in range(100):
            # Compute all triangles to identify bottleneck
            areas = []
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = current[i], current[j], current[k]
                        area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        areas.append(area_val)
                        triangles.append((i, j, k))
            
            min_area_val = min(areas)
            # Use relative tolerance instead of fixed
            tolerance = 1e-4 * min_area_val
            bottleneck_triangles = []
            for idx, area_val in enumerate(areas):
                if area_val <= min_area_val + tolerance:
                    bottleneck_triangles.append(triangles[idx])

            critical_points = set()
            for tri in bottleneck_triangles:
                critical_points.update(tri)
            critical_points = list(critical_points)
            
            if not critical_points:
                continue

            directions = np.zeros((n, 2))
            weights = np.zeros(n)
            for tri in bottleneck_triangles:
                i, j, k = tri
                area_val = 0.5 * abs((current[j][0]-current[i][0])*(current[k][1]-current[i][1]) - 
                                  (current[j][1]-current[i][1])*(current[k][0]-current[i][0]))
                
                # Weight inversely proportional to area
                weight = 1.0 / (area_val + 1e-10)
                
                # For point i (opposite side j-k)
                base = current[k] - current[j]
                normal = np.array([-base[1], base[0]])
                v = current[i] - current[j]
                d = np.dot(v, normal)
                sign_d = 1.0 if d >= 0 else -1.0
                directions[i] += normal * sign_d * weight
                weights[i] += weight

                # For point j (opposite side i-k)
                base = current[k] - current[i]
                normal = np.array([-base[1], base[0]])
                v = current[j] - current[i]
                d = np.dot(v, normal)
                sign_d = 1.0 if d >= 0 else -1.0
                directions[j] += normal * sign_d * weight
                weights[j] += weight

                # For point k (opposite side i-j)
                base = current[j] - current[i]
                normal = np.array([-base[1], base[0]])
                v = current[k] - current[i]
                d = np.dot(v, normal)
                sign_d = 1.0 if d >= 0 else -1.0
                directions[k] += normal * sign_d * weight
                weights[k] += weight

            # Normalize directions by weights
            for i in range(n):
                if weights[i] > 1e-10:
                    directions[i] /= weights[i]
                norm = np.linalg.norm(directions[i])
                if norm > 1e-10:
                    directions[i] /= norm

            step = initial_step * (0.97 ** iteration)  # Slowed decay from 0.95 to 0.97
            T = initial_temp * (0.99 ** iteration)      # Slowed decay from 0.98 to 0.99

            candidate = current.copy()
            
            # Boundary handling: proper projection onto triangle boundary
            for i in critical_points:
                candidate[i] = current[i] + step * directions[i]
                if not is_inside_triangle(candidate[i], A, B, C):
                    # Project onto nearest boundary edge
                    candidate[i] = find_closest_point_on_triangle(candidate[i], A, B, C)

            # Increased frequency and magnitude of non-critical perturbations
            if np.random.rand() < 0.3:  # Increased from 0.1 to 0.3
                for i in range(n):
                    if i not in critical_points:
                        # Increased magnitude from 0.1*step to 0.3*step
                        candidate[i] += 0.3 * step * np.random.uniform(-1, 1, size=2)
                        if not is_inside_triangle(candidate[i], A, B, C):
                            candidate[i] = find_closest_point_on_triangle(candidate[i], A, B, C)

            # Verify all points are inside
            if not is_inside_triangle(candidate, A, B, C):
                continue

            candidate_score = get_smallest_triangle_area(candidate)

            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score

            if candidate_score > current_score:
                current = candidate
                current_score = candidate_score
            else:
                delta = candidate_score - current_score
                if T > 1e-10 and np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = candidate_score

        return best

    return improve