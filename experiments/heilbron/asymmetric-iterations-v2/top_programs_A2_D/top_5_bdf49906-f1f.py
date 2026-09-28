from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    M = np.column_stack((B - A, C - A))
    M_inv = np.linalg.inv(M)

    def cart_to_bary(cart_points):
        bary = np.zeros((len(cart_points), 2))
        for i, P in enumerate(cart_points):
            diff = P - A
            bary[i] = M_inv @ diff
        return bary

    def bary_to_cart(bary_points):
        cart = np.zeros((len(bary_points), 2))
        for i, (u, v) in enumerate(bary_points):
            cart[i] = A + u * (B - A) + v * (C - A)
        return cart

    def find_min_triangle_indices(cart_points):
        n = len(cart_points)
        min_area = float('inf')
        min_indices = None
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    area = 0.5 * abs((cart_points[j, 0] - cart_points[i, 0]) * (cart_points[k, 1] - cart_points[i, 1]) - 
                                     (cart_points[k, 0] - cart_points[i, 0]) * (cart_points[j, 1] - cart_points[i, 1]))
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        return min_indices

    def get_bottleneck_scores(cart_points, threshold_factor=1.5):
        """Get scores for each point based on how many small triangles it participates in."""
        n = len(cart_points)
        scores = np.zeros(n)
        min_area = get_smallest_triangle_area(cart_points)
        threshold = min_area * threshold_factor
        
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    area = 0.5 * abs((cart_points[j, 0] - cart_points[i, 0]) * (cart_points[k, 1] - cart_points[i, 1]) - 
                                     (cart_points[k, 0] - cart_points[i, 0]) * (cart_points[j, 1] - cart_points[i, 1]))
                    if area < threshold:
                        scores[i] += 1
                        scores[j] += 1
                        scores[k] += 1
        return scores

    def estimate_gradient(cart_points, idx, eps=1e-5):
        """Estimate gradient of min_area with respect to point at idx."""
        n = len(cart_points)
        original_point = cart_points[idx].copy()
        
        # Find all triangles involving this point
        min_area = float('inf')
        min_area_triples = []
        
        for i in range(n):
            if i == idx:
                continue
            for j in range(i + 1, n):
                if j == idx:
                    continue
                area = 0.5 * abs((cart_points[i, 0] - original_point[0]) * (cart_points[j, 1] - original_point[1]) - 
                                 (cart_points[j, 0] - original_point[0]) * (cart_points[i, 1] - original_point[1]))
                if area < min_area:
                    min_area = area
                    min_area_triples = [(i, j)]
                elif abs(area - min_area) < 1e-10:
                    min_area_triples.append((i, j))
        
        # If no triangles (shouldn't happen with n>=3), return zero gradient
        if min_area == float('inf'):
            return np.array([0.0, 0.0])
        
        # Perturb in x direction
        cart_points[idx] = original_point + [eps, 0]
        min_area_x = float('inf')
        for i, j in min_area_triples:
            area = 0.5 * abs((cart_points[i, 0] - cart_points[idx, 0]) * (cart_points[j, 1] - cart_points[idx, 1]) - 
                             (cart_points[j, 0] - cart_points[idx, 0]) * (cart_points[i, 1] - cart_points[idx, 1]))
            min_area_x = min(min_area_x, area)
        
        # Perturb in y direction
        cart_points[idx] = original_point + [0, eps]
        min_area_y = float('inf')
        for i, j in min_area_triples:
            area = 0.5 * abs((cart_points[i, 0] - cart_points[idx, 0]) * (cart_points[j, 1] - cart_points[idx, 1]) - 
                             (cart_points[j, 0] - cart_points[idx, 0]) * (cart_points[i, 1] - cart_points[idx, 1]))
            min_area_y = min(min_area_y, area)
        
        # Restore original point
        cart_points[idx] = original_point
        
        # Compute gradient
        grad_x = (min_area_x - min_area) / eps
        grad_y = (min_area_y - min_area) / eps
        
        return np.array([grad_x, grad_y])

    def improve(points: np.ndarray) -> np.ndarray:
        initial_bary = cart_to_bary(points)
        initial_min_area = get_smallest_triangle_area(points)
        
        if initial_min_area < 1e-6:
            initial_min_area = 1e-6

        n_restarts = 5
        iterations_per_restart = 200
        step_start = 0.1
        temp_start = 0.1 * initial_min_area

        global_best_bary = initial_bary.copy()
        global_best_score = initial_min_area

        for _ in range(n_restarts):
            current_bary = initial_bary.copy()
            current_score = initial_min_area
            best_in_restart_bary = current_bary.copy()
            best_in_restart_score = current_score

            for i in range(iterations_per_restart):
                # Exponential cooling instead of linear
                temp = temp_start * (0.95 ** i)
                step = step_start * (1 - i / iterations_per_restart)

                # Weighted selection based on bottleneck scores
                cart = bary_to_cart(current_bary)
                if np.random.rand() < 0.8:
                    bottleneck_scores = get_bottleneck_scores(cart)
                    # Normalize scores to probabilities, with minimum probability to ensure all points can be selected
                    min_prob = 0.05
                    probs = bottleneck_scores / bottleneck_scores.sum()
                    probs = np.maximum(probs, min_prob)
                    probs = probs / probs.sum()
                    idx = np.random.choice(11, p=probs)
                else:
                    idx = np.random.randint(0, 11)

                u, v = current_bary[idx]
                du = np.random.normal(0, step)
                dv = np.random.normal(0, step)

                # Add gradient information 70% of the time
                if np.random.rand() < 0.7:
                    grad = estimate_gradient(cart, idx, eps=1e-4)
                    # Convert gradient to barycentric coordinates
                    grad_cart = np.array([grad[0], grad[1]])
                    grad_bary = M_inv @ grad_cart
                    # Bias the move toward the gradient direction
                    du += 0.3 * grad_bary[0] * step
                    dv += 0.3 * grad_bary[1] * step

                u_new = u + du
                v_new = v + dv

                if u_new < 0:
                    u_new = 0
                if v_new < 0:
                    v_new = 0
                if u_new + v_new > 1:
                    scale = 1.0 / (u_new + v_new)
                    u_new *= scale
                    v_new *= scale

                candidate_bary = current_bary.copy()
                candidate_bary[idx] = [u_new, v_new]

                candidate_cart = bary_to_cart(candidate_bary)
                candidate_score = get_smallest_triangle_area(candidate_cart)

                if candidate_score > current_score:
                    current_bary = candidate_bary
                    current_score = candidate_score
                    if candidate_score > best_in_restart_score:
                        best_in_restart_bary = candidate_bary.copy()
                        best_in_restart_score = candidate_score
                else:
                    delta = current_score - candidate_score
                    if np.random.rand() < np.exp(-delta / temp):
                        current_bary = candidate_bary
                        current_score = candidate_score

            if best_in_restart_score > global_best_score:
                global_best_bary = best_in_restart_bary.copy()
                global_best_score = best_in_restart_score

        return bary_to_cart(global_best_bary)

    return improve