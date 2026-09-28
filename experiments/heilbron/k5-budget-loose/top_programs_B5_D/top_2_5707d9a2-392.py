from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint():
    np.random.seed(42)
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Precompute edges for boundary projection
        edges = [(A, B), (B, C), (C, A)]

        # Helper: project point to triangle boundary if outside
        def project_point(p):
            if is_inside_triangle(p.reshape(1, 2), A, B, C):
                return p
            best_point = None
            best_dist = float('inf')
            for (X, Y) in edges:
                XY = Y - X
                XP = p - X
                t = np.dot(XP, XY) / (np.dot(XY, XY) + 1e-10)
                t = max(0.0, min(1.0, t))
                proj = X + t * XY
                dist = np.linalg.norm(p - proj)
                if dist < best_dist:
                    best_dist = dist
                    best_point = proj
            return best_point

        # Helper: get indices of points in the k smallest triangles
        def get_points_from_smallest_triangles(pts, k=3):
            n = len(pts)
            triangle_areas = []
            
            for i in range(n):
                for j in range(i + 1, n):
                    for l in range(j + 1, n):
                        a, b, c = pts[i], pts[j], pts[l]
                        area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        triangle_areas.append((area, i, j, l))
            
            # Sort by area and take top k
            triangle_areas.sort(key=lambda x: x[0])
            top_k = triangle_areas[:min(k, len(triangle_areas))]
            
            # Get unique point indices
            point_indices = set()
            for _, i, j, l in top_k:
                point_indices.add(i)
                point_indices.add(j)
                point_indices.add(l)
            
            return list(point_indices)

        # Initialize with input configuration
        current = points.copy()
        best = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_score = current_score

        # Skip if input is degenerate (shouldn't happen per problem constraints)
        if current_score <= 0:
            return points

        # Simulated annealing parameters - adapted to optimization gap
        initial_temp = max(0.001, 0.1 * (0.0365 - current_score))
        initial_step = 0.05
        max_iter = 500  # Increased from 200
        step_decay = 0.995  # Changed from 0.99

        for iteration in range(max_iter):
            # Decay temperature and step size
            T = initial_temp * (step_decay ** iteration)
            step = initial_step * (step_decay ** iteration)

            # Identify points in top-k smallest triangles (k=3)
            point_indices = get_points_from_smallest_triangles(current, k=3)

            # Generate candidate by perturbing these points
            candidate = current.copy()
            for idx in point_indices:
                perturbation = np.random.normal(0, step, size=2)
                candidate[idx] += perturbation
                candidate[idx] = project_point(candidate[idx])

            # Skip degenerate candidates
            candidate_score = get_smallest_triangle_area(candidate)
            if candidate_score <= 0:
                continue

            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score

        return best

    return improve