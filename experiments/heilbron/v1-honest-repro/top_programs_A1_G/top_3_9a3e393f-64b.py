# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import scipy.optimize

np.random.seed(42)
random.seed(42)

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    rows = [3, 4, 3, 1]
    cumulative = 0
    points_list = []
    for n in rows:
        center_area = (cumulative + 0.5 * n) / 11.0
        v = 1.0 - np.sqrt(1.0 - center_area)
        for j in range(n):
            u = (j + 0.5) / n * (1.0 - v)
            P = (1 - u - v) * A + u * B + v * C
            P[0] += random.uniform(-0.01, 0.01)
            P[1] += random.uniform(-0.01, 0.01)
            points_list.append(P)
        cumulative += n

    initial_points = np.array(points_list)

    def objective(flat_points):
        points = flat_points.reshape(11, 2)
        if not is_inside_triangle(points, A, B, C):
            return 1e10
        area = get_smallest_triangle_area(points)
        return -area

    result = scipy.optimize.minimize(
        objective,
        initial_points.flatten(),
        method='Nelder-Mead',
        options={'maxiter': 5000, 'xatol': 1e-5, 'fatol': 1e-5}
    )

    optimized_points = result.x.reshape(11, 2)
    if is_inside_triangle(optimized_points, A, B, C):
        return optimized_points
    else:
        return initial_points

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def _d_entrypoint():
    A, B, C = get_unit_triangle()

    # Precompute barycentric conversion matrix for fixed triangle
    M = np.array([
        [A[0]-C[0], B[0]-C[0]],
        [A[1]-C[1], B[1]-C[1]]
    ])
    M_inv = np.linalg.inv(M)

    def to_bary(p):
        rhs = np.array([p[0]-C[0], p[1]-C[1]])
        u, v = M_inv @ rhs
        w = 1 - u - v
        return np.array([u, v, w])

    def to_cart(b):
        return b[0]*A + b[1]*B + b[2]*C

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        best = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_score = current_score

        # Simulated annealing parameters
        initial_temperature = 0.001
        cooling_rate = 0.99
        max_iter = 500
        initial_step = 0.1
        stagnation_limit = 50
        no_improve_count = 0

        for i in range(max_iter):
            temperature = initial_temperature * (cooling_rate ** i)
            step = initial_step * (cooling_rate ** i)

            # Find smallest triangle
            n = len(current)
            min_area = float('inf')
            min_indices = None
            for i1 in range(n):
                for i2 in range(i1+1, n):
                    for i3 in range(i2+1, n):
                        x1, y1 = current[i1]
                        x2, y2 = current[i2]
                        x3, y3 = current[i3]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area < min_area:
                            min_area = area
                            min_indices = (i1, i2, i3)

            # Perturb one point from the smallest triangle
            idx = np.random.choice(min_indices)
            bary = to_bary(current[idx])
            u, v, w = bary

            # Perturb in barycentric space with clamping
            u_new = u + step * np.random.normal()
            v_new = v + step * np.random.normal()
            u_new = max(0, u_new)
            v_new = max(0, v_new)
            if u_new + v_new > 1:
                scale = 1.0 / (u_new + v_new)
                u_new *= scale
                v_new *= scale
            w_new = 1 - u_new - v_new
            new_point = to_cart(np.array([u_new, v_new, w_new]))

            # Create candidate
            candidate = current.copy()
            candidate[idx] = new_point
            candidate_score = get_smallest_triangle_area(candidate)

            # Skip degenerate candidates
            if candidate_score <= 0:
                no_improve_count += 1
                continue

            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
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

            # Early stopping
            if no_improve_count >= stagnation_limit:
                break

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)