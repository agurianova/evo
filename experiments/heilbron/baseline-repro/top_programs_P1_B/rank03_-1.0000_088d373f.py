from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_triangle(point, A, B, C):
        if is_inside_triangle([point], A, B, C):
            return point
        
        edges = [(A, B), (B, C), (C, A)]
        best_point = None
        best_dist = float('inf')
        
        for (p0, p1) in edges:
            v = p1 - p0
            w = point - p0
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 < 1e-10:
                proj = p0
            else:
                b = c1 / c2
                if b < 0.0:
                    proj = p0
                elif b > 1.0:
                    proj = p1
                else:
                    proj = p0 + b * v
            
            dist = np.linalg.norm(point - proj)
            if dist < best_dist:
                best_dist = dist
                best_point = proj
                
        return best_point

    def improve(points: np.ndarray) -> np.ndarray:
        base_score = get_smallest_triangle_area(points)
        n_points = points.shape[0]
        
        # Adaptive parameters based on input difficulty
        k = max(1, min(5, int(10 * (0.0365 - base_score) / 0.0365)))
        initial_temp = 0.5 * (0.0365 - base_score)
        cooling_rate = 0.95 + 0.04 * (base_score / 0.0365)

        best = points.copy()
        best_score = base_score

        for restart in range(3):
            step_size_base = 0.05 / (restart + 1)
            current = points.copy()
            jitter = np.random.uniform(-0.5, 0.5, current.shape) * step_size_base * 10
            current += jitter
            for i in range(n_points):
                current[i] = project_to_triangle(current[i], A, B, C)
            
            current_score = get_smallest_triangle_area(current)
            if current_score > best_score:
                best = current.copy()
                best_score = current_score

            T = initial_temp
            n_steps = 0
            no_improve_count = 0

            while T > 1e-7 and n_steps < 1000 and no_improve_count < 200:
                n_steps += 1

                # Identify top k smallest triangles
                triangles = []
                for i in range(n_points):
                    for j in range(i + 1, n_points):
                        for k_idx in range(j + 1, n_points):
                            p1, p2, p3 = current[i], current[j], current[k_idx]
                            area = 0.5 * abs((p2[0] - p1[0]) * (p3[1] - p1[1]) - 
                                           (p3[0] - p1[0]) * (p2[1] - p1[1]))
                            triangles.append((area, i, j, k_idx))
                triangles.sort(key=lambda x: x[0])
                top_triangles = triangles[:min(k, len(triangles))]

                total_grad = {}
                for (area, i, j, k_idx) in top_triangles:
                    # Weight gradient by criticality (inverse area)
                    weight = 1.0 / (area + 1e-8)
                    p1, p2, p3 = current[i], current[j], current[k_idx]
                    dx1 = p2[0] - p1[0]
                    dy1 = p2[1] - p1[1]
                    dx2 = p3[0] - p1[0]
                    dy2 = p3[1] - p1[1]
                    cross = dx1 * dy2 - dx2 * dy1
                    s = 1.0 if cross >= 0 else -1.0

                    grad_p1 = s * np.array([p2[1] - p3[1], p3[0] - p2[0]])
                    grad_p2 = s * np.array([p3[1] - p1[1], p1[0] - p3[0]])
                    grad_p3 = s * np.array([p1[1] - p2[1], p2[0] - p1[0]])

                    for idx, grad in zip([i, j, k_idx], [grad_p1, grad_p2, grad_p3]):
                        weighted_grad = weight * grad
                        total_grad[idx] = total_grad.get(idx, np.zeros(2)) + weighted_grad

                candidate = current.copy()
                step = step_size_base * T

                for idx, grad in total_grad.items():
                    if np.linalg.norm(grad) > 1e-10:
                        grad = grad / np.linalg.norm(grad)
                        candidate[idx] += step * grad
                    candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

                # Only check triangle containment during search (relax other constraints)
                constraint_violated = not is_inside_triangle(candidate, A, B, C)

                if constraint_violated:
                    no_improve_count += 1
                else:
                    candidate_score = get_smallest_triangle_area(candidate)
                    delta = candidate_score - current_score
n                    if delta > 0 or np.random.rand() < np.exp(delta / T):
                        current = candidate
                        current_score = candidate_score
                        if candidate_score > best_score:
                            best = candidate
                            best_score = candidate_score
                            no_improve_count = 0
                        else:
                            no_improve_count += 1
                    else:
                        no_improve_count += 1

                T *= cooling_rate

        return best

    return improve