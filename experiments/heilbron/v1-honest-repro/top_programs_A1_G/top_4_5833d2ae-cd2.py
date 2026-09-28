# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
from scipy.optimize import basinhopping
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Literature-inspired symmetric row distribution [3,3,2,2,1] for n=11
    row_counts = [3, 3, 2, 2, 1]
    total_points = 11
    cumulative = 0
    v_list = []
    
    # Compute row heights using area-aware spacing
    for count in row_counts:
        F = (cumulative + 0.5 * count) / total_points
        v = 1 - np.sqrt(1 - F)
        v_list.append(v)
        cumulative += count

    # Generate symmetric points with robust collinearity-breaking
    points = []
    for i, count in enumerate(row_counts):
        v = v_list[i]
        for j in range(count):
            u = (j + 0.5) * (1 - v) / count
            P = (1 - u - v) * A + u * B + v * C
            # Robust collinearity offset: row-dependent scaling (1-v) and meaningful magnitude 0.001
            offset = 0.001 * (1 - v) * (j - (count - 1) / 2) ** 2
            P[1] += offset
            points.append(P)
    
    initial_points = np.array(points)
    
    # Global optimization with basin-hopping to escape shallow local optima
    def objective(flat_points):
        points = flat_points.reshape((11, 2))
        if not is_inside_triangle(points, *tri):
            return 1e10
        area = get_smallest_triangle_area(points)
        return -area

    res = basinhopping(
        objective,
        initial_points.flatten(),
        niter=5000,
        T=0.1,
        stepsize=0.1,
        minimizer_kwargs={
            "method": "Nelder-Mead",
            "options": {'maxiter': 200, 'xatol': 1e-8, 'fatol': 1e-8}
        },
        interval=100
    )
    
    return res.x.reshape((11, 2))

# --- D's code (entrypoint renamed to _d_entrypoint) ---
import numpy as np
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle

np.random.seed(42)

def _d_entrypoint():
    A, B, C = get_unit_triangle()
    denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])

    def cartesian_to_barycentric(pts):
        u = ((B[1] - C[1]) * (pts[:, 0] - C[0]) + (C[0] - B[0]) * (pts[:, 1] - C[1])) / denom
        v = ((C[1] - A[1]) * (pts[:, 0] - C[0]) + (A[0] - C[0]) * (pts[:, 1] - C[1])) / denom
        return np.column_stack((u, v))

    def barycentric_to_cartesian(bary):
        u = bary[:, 0]
        v = bary[:, 1]
        w = 1 - u - v
        x = u * A[0] + v * B[0] + w * C[0]
        y = u * A[1] + v * B[1] + w * C[1]
        return np.column_stack((x, y))

    def get_one_smallest_triangle_indices(points_cart):
        n = points_cart.shape[0]
        min_area = float('inf')
        best_indices = (0, 1, 2)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    area = 0.5 * abs((points_cart[j, 0] - points_cart[i, 0]) * (points_cart[k, 1] - points_cart[i, 1]) - 
                                      (points_cart[k, 0] - points_cart[i, 0]) * (points_cart[j, 1] - points_cart[i, 1]))
                    if area < min_area:
                        min_area = area
                        best_indices = (i, j, k)
        return best_indices

    def improve(points):
        bary_points = cartesian_to_barycentric(points)
        cart_init = barycentric_to_cartesian(bary_points)
        init_score = get_smallest_triangle_area(cart_init)

        current_bary = bary_points.copy()
        current_score = init_score
        best_bary = bary_points.copy()
        best_score = init_score

        step_size = 0.05
        temperature = 0.001
        no_improve_count = 0
        max_iter = 500

        for iteration in range(max_iter):
            cart_current = barycentric_to_cartesian(current_bary)
            idx1, idx2, idx3 = get_one_smallest_triangle_indices(cart_current)

            if np.random.rand() < 0.9:
                idx = np.random.choice([idx1, idx2, idx3])
            else:
                idx = np.random.randint(0, 11)

            candidate_bary = current_bary.copy()
            du = np.random.normal(0, step_size)
            dv = np.random.normal(0, step_size)
            new_u = candidate_bary[idx, 0] + du
            new_v = candidate_bary[idx, 1] + dv

            if new_u < 0:
                new_u = 0
            if new_v < 0:
                new_v = 0
            if new_u + new_v > 1:
                total = new_u + new_v
                new_u = new_u / total
                new_v = new_v / total
            candidate_bary[idx, 0] = new_u
            candidate_bary[idx, 1] = new_v

            cart_candidate = barycentric_to_cartesian(candidate_bary)
            if not is_inside_triangle(cart_candidate, A, B, C):
                continue

            candidate_score = get_smallest_triangle_area(cart_candidate)
            delta = candidate_score - current_score
            
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current_bary = candidate_bary
                current_score = candidate_score
                if candidate_score > best_score:
                    best_bary = candidate_bary
                    best_score = candidate_score
                    no_improve_count = 0
                else:
                    no_improve_count += 1
            else:
                no_improve_count += 1

            if no_improve_count >= 50:
                step_size *= 0.5
                no_improve_count = 0
                if step_size < 1e-6:
                    break

            temperature *= 0.99

        return barycentric_to_cartesian(best_bary)

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)