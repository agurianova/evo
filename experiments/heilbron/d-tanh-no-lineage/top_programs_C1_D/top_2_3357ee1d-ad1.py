from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Helper for boundary projection
        def project_point(P):
            if is_inside_triangle(np.array([P]), A, B, C):
                return P
            edges = [(A, B), (B, C), (C, A)]
            closest_points = []
            for V1, V2 in edges:
                V1V2 = V2 - V1
                V1P = P - V1
                t = np.dot(V1P, V1V2) / (np.dot(V1V2, V1V2) + 1e-10)
                t = max(0.0, min(1.0, t))
                proj = V1 + t * V1V2
                closest_points.append(proj)
            distances = [np.linalg.norm(P - p) for p in closest_points]
            return closest_points[np.argmin(distances)]

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        temperature = 0.001
        step_size = 0.05
        no_improve_count = 0
        max_no_improve = 50

        for iteration in range(200):
            if no_improve_count >= max_no_improve:
                break

            # Identify critical points (vertices of smallest triangles)
            critical_points = set()
            n = 11
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        tri = current[[i, j, k]]
                        area = 0.5 * abs(
                            (tri[1, 0] - tri[0, 0]) * (tri[2, 1] - tri[0, 1]) -
                            (tri[2, 0] - tri[0, 0]) * (tri[1, 1] - tri[0, 1])
                        )
                        if area <= current_score + 1e-8:
                            critical_points.update([i, j, k])
            if not critical_points:
                critical_points = set(range(11))
            non_critical = set(range(11)) - critical_points

            # Select 2-3 points with critical bias
            k = np.random.choice([2, 3])
            selected_indices = []
            for _ in range(k):
                if critical_points and (np.random.rand() < 0.7 or not non_critical):
                    idx = np.random.choice(list(critical_points))
                    critical_points.discard(idx)
                else:
                    idx = np.random.choice(list(non_critical)) if non_critical else np.random.randint(0, 11)
                selected_indices.append(idx)

            # Generate candidate with perturbations and projection
            candidate = current.copy()
            for idx in selected_indices:
                candidate[idx] += np.random.normal(0, step_size, 2)
                candidate[idx] = project_point(candidate[idx])

            candidate_score = get_smallest_triangle_area(candidate)

            # Update best solution
            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / (temperature + 1e-10)):
                current = candidate
                current_score = candidate_score

            # Adaptive cooling
            temperature *= 0.99
            step_size *= 0.99

        return best

    return improve