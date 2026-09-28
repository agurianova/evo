from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        np.random.seed(42)
        current = points.copy()
        best = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_score = current_score

        T = 0.05
        cooling_rate = 0.995
        max_iter = 200

        for _ in range(max_iter):
            n = current.shape[0]
            triangles = []
            for i1 in range(n):
                for i2 in range(i1 + 1, n):
                    for i3 in range(i2 + 1, n):
                        a, b, c = current[i1], current[i2], current[i3]
                        area = 0.5 * abs(a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
                        triangles.append((area, (i1, i2, i3)))
            
            triangles.sort(key=lambda x: x[0])
            min_area_val = triangles[0][0]
            bottleneck_tris = [tri for tri in triangles if tri[0] <= min_area_val + 1e-5]
            if not bottleneck_tris:
                bottleneck_tris = [triangles[0]]

            # Prioritize bottlenecks with fewer shared points
            bottleneck_counts = {}
            for _, (i, j, k) in bottleneck_tris:
                for idx in [i, j, k]:
                    bottleneck_counts[idx] = bottleneck_counts.get(idx, 0) + 1
            
            # Select bottleneck with most unique points
            bottleneck_tris.sort(key=lambda x: min(bottleneck_counts[i] for i in x[1]))
            _, (i0, i1, i2) = bottleneck_tris[0]

            candidate = current.copy()
            
            # Compute directional perturbation
            p0, p1, p2 = candidate[i0], candidate[i1], candidate[i2]
            base = p1 - p0
            normal = np.array([-base[1], base[0]])
            normal = normal / (np.linalg.norm(normal) + 1e-8)
            
            # Adaptive step size based on bottleneck severity
            step_size = T * (1.0 / np.sqrt(min_area_val + 1e-8))
            
            # Apply directional perturbation with small random component
            for idx, direction in zip([i0, i1, i2], [-normal, -normal, normal]):
                # Move points in directions that increase triangle area
                candidate[idx] += step_size * (direction * 0.7 + np.random.normal(0, 0.3, 2))

            # Project points back to triangle if outside
            for i in range(len(candidate)):
                if not is_inside_triangle(candidate[i], A, B, C):
                    # Find closest point on each edge
                    def point_to_line_dist(p, a, b):
                        ap = p - a
                        ab = b - a
                        t = np.clip(np.dot(ap, ab) / (np.dot(ab, ab) + 1e-8), 0, 1)
                        projection = a + t * ab
                        return projection, np.linalg.norm(ap - t * ab)
                    
                    p1, d1 = point_to_line_dist(candidate[i], A, B)
                    p2, d2 = point_to_line_dist(candidate[i], B, C)
                    p3, d3 = point_to_line_dist(candidate[i], C, A)
                    
                    if d1 <= d2 and d1 <= d3:
                        candidate[i] = p1
                    elif d2 <= d1 and d2 <= d3:
                        candidate[i] = p2
                    else:
                        candidate[i] = p3

            new_score = get_smallest_triangle_area(candidate)
            if new_score <= 1e-10:
                continue

            delta = new_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate
                    best_score = new_score

            T *= cooling_rate

        return best

    return improve