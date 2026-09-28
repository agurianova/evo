from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)


def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Helper functions
        def project_point_to_line_segment(P, A, B):
            AB = B - A
            AP = P - A
            t = np.dot(AP, AB) / (np.dot(AB, AB) + 1e-12)
            t = np.clip(t, 0, 1)
            return A + t * AB

        def project_to_triangle(P):
            proj_AB = project_point_to_line_segment(P, A, B)
            proj_BC = project_point_to_line_segment(P, B, C)
            proj_CA = project_point_to_line_segment(P, C, A)
            
            d_AB = np.linalg.norm(P - proj_AB)
            d_BC = np.linalg.norm(P - proj_BC)
            d_CA = np.linalg.norm(P - proj_CA)
            
            if d_AB <= d_BC and d_AB <= d_CA:
                return proj_AB
            elif d_BC <= d_AB and d_BC <= d_CA:
                return proj_BC
            else:
                return proj_CA

        def triangle_area(a, b, c):
            return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))

        def get_critical_points(pts, min_area):
            tol = 1e-10
            critical = set()
            n = len(pts)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = triangle_area(pts[i], pts[j], pts[k])
                        if abs(area - min_area) < tol:
                            critical.update([i, j, k])
            return list(critical)

        # Initialize state
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        max_iterations = 200
        T0 = 0.001
        initial_step = 0.05
        no_improve_count = 0

        for i in range(max_iterations):
            # Cooling schedule
            T = T0 * (1 - i / max_iterations)
            T = max(T, 1e-9)
            step_size = initial_step * (T / T0)

            # Select points to perturb (1-3 points)
            k = np.random.randint(1, 4)
            critical_points = get_critical_points(current, current_score)
            
            if critical_points:
                weights = np.ones(11)
                weights[critical_points] = 10.0
                idxs = np.random.choice(11, size=k, replace=False, p=weights/np.sum(weights))
            else:
                idxs = np.random.choice(11, size=k, replace=False)

            # Generate candidate
            candidate = current.copy()
            for idx in idxs:
                candidate[idx] += np.random.normal(0, step_size, size=2)

            # Repair invalid points
            for j in range(11):
                if not is_inside_triangle([candidate[j]], A, B, C):
                    candidate[j] = project_to_triangle(candidate[j])

            # Evaluate candidate
            candidate_score = get_smallest_triangle_area(candidate)
            if candidate_score <= 0:  # Skip collinear/degenerate candidates
                continue

            # Update best solution
            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Early stopping
            if no_improve_count >= 50:
                break

            # Metropolis acceptance
            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current = candidate
                current_score = candidate_score

        return best

    return improve