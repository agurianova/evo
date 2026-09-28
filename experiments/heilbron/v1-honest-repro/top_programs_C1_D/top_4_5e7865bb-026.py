from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def project_to_line_segment(P, A, B):
    AB = B - A
    AP = P - A
    AB_sq = np.dot(AB, AB)
    if AB_sq == 0:
        return A
    t = np.dot(AP, AB) / AB_sq
    t = np.clip(t, 0, 1)
    return A + t * AB

def project_to_triangle(P, A, B, C):
    if is_inside_triangle(P, A, B, C):
        return P
    p1 = project_to_line_segment(P, A, B)
    p2 = project_to_line_segment(P, B, C)
    p3 = project_to_line_segment(P, C, A)
    d1 = np.linalg.norm(P - p1)
    d2 = np.linalg.norm(P - p2)
    d3 = np.linalg.norm(P - p3)
    if d1 <= d2 and d1 <= d3:
        return p1
    elif d2 <= d1 and d2 <= d3:
        return p2
    else:
        return p3

def compute_area_gradient(pts, i, j, k):
    A, B, C = pts[i], pts[j], pts[k]
    grad_i = 0.5 * np.array([B[1] - C[1], C[0] - B[0]])
    grad_j = 0.5 * np.array([C[1] - A[1], A[0] - C[0]])
    grad_k = 0.5 * np.array([A[1] - B[1], B[0] - A[0]])
    return grad_i, grad_j, grad_k

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        np.random.seed(42)
        best = points.copy()
        best_score = get_smallest_triangle_area(best)

        base_scale = 0.002
        max_noise_scale = 0.1
        initial_temp = 0.001
        cooling_rate = 0.995
        n_iterations = 200

        # Adaptive bottleneck targeting
        k_smallest = 1
        no_improve_count = 0
        max_no_improve = 20

        for step in range(n_iterations):
            current_min_area = best_score
            noise_scale = base_scale / (np.sqrt(current_min_area) + 1e-5)
            if noise_scale > max_noise_scale:
                noise_scale = max_noise_scale

            # Get k smallest triangles
            triangles = []
            n = best.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = best[i]
                        x2, y2 = best[j]
                        x3, y3 = best[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        triangles.append((area, i, j, k))
            
            triangles.sort(key=lambda x: x[0])
            smallest_triangles = triangles[:k_smallest]

            # Compute combined gradient
            grad = np.zeros_like(best)
            for _, i, j, k in smallest_triangles:
                grad_i, grad_j, grad_k = compute_area_gradient(best, i, j, k)
                grad[i] += grad_i
                grad[j] += grad_j
                grad[k] += grad_k

            # Normalize gradients
            for i in range(len(grad)):
                norm = np.linalg.norm(grad[i])
                if norm > 1e-10:
                    grad[i] /= norm

            # Apply gradient-guided perturbation
            candidate = best.copy()
            for i in range(len(best)):
                if np.linalg.norm(grad[i]) > 1e-10:
                    # Blend gradient direction with random noise
                    direction = grad[i]
                    candidate[i] += direction * noise_scale * 0.7 + np.random.normal(0, noise_scale * 0.3, size=2)
                else:
                    candidate[i] += np.random.normal(0, noise_scale, size=2)

            # Project back to triangle
            for i in range(len(candidate)):
                candidate[i] = project_to_triangle(candidate[i], A, B, C)

            new_score = get_smallest_triangle_area(candidate)

            if new_score > best_score:
                best = candidate
                best_score = new_score
                no_improve_count = 0
                # If making progress with current k, reduce for finer tuning
                if k_smallest > 1:
                    k_smallest -= 1
            else:
                no_improve_count += 1
                if no_improve_count >= max_no_improve and k_smallest < 3:
                    k_smallest += 1
                    no_improve_count = 0

                delta = best_score - new_score
                temperature = initial_temp * (cooling_rate ** step)
                if np.random.rand() < np.exp(-delta / temperature):
                    best = candidate
                    best_score = new_score

        return best

    return improve