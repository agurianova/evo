# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area
from scipy import optimize

np.random.seed(42)
random.seed(42)

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    s = B[0]

    # Define triangle boundary constraints for SLSQP
    def constraint1(x):
        pts = x.reshape(11, 2)
        return pts[:, 1]  # y >= 0

    def constraint2(x):
        pts = x.reshape(11, 2)
        return np.sqrt(3) * pts[:, 0] - pts[:, 1]  # y <= sqrt(3)*x

    def constraint3(x):
        pts = x.reshape(11, 2)
        return np.sqrt(3) * (s - pts[:, 0]) - pts[:, 1]  # y <= sqrt(3)*(s - x)

    constraints = [
        {'type': 'ineq', 'fun': constraint1},
        {'type': 'ineq', 'fun': constraint2},
        {'type': 'ineq', 'fun': constraint3}
    ]

    # Objective: maximize minimum triangle area
    def objective(x):
        pts = x.reshape(11, 2)
        return -get_smallest_triangle_area(pts)

    # Generate chaotic initial configuration with logistic map perturbations
    def generate_initial():
        rows = [5, 3, 3]
        base_heights = [0.2, 0.5, 0.8]  # Base heights from triangle base
        r = 3.99  # Chaotic parameter
        
        # Perturb row heights chaotically
        x = random.random()
        perturbations = []
        for _ in range(len(rows)):
            x = r * x * (1 - x)
            perturbations.append(x * 0.04 - 0.02)  # [-0.02, 0.02]
        heights = [base_heights[i] + perturbations[i] for i in range(len(rows))]

        points = []
        for i, row_count in enumerate(rows):
            h = heights[i]
            for j in range(row_count):
                # Base horizontal position
                base_u = (j + 0.5) / row_count * (1 - h)
                
                # Chaotic horizontal offset
                x_offset = (i * 10 + j + 1) * 0.1
                for _ in range(5):
                    x_offset = r * x_offset * (1 - x_offset)
                offset = (x_offset - 0.5) * 0.1 * (1 - h)
                
                u = np.clip(base_u + offset, 0, 1 - h)
                P = (1 - u - h) * A + u * B + h * C
                points.append(P)
        return np.array(points)

    # Multiple restarts with SLSQP optimization
    best_points = None
    best_area = -1.0

    for _ in range(15):
        initial = generate_initial()
        perturbed = initial + np.random.uniform(-0.005, 0.005, size=initial.shape)
        
        res = optimize.minimize(
            objective,
            perturbed.flatten(),
            method='SLSQP',
            constraints=constraints,
            options={'maxiter': 2000, 'ftol': 1e-8}
        )

        if res.success:
            candidate = res.x.reshape(11, 2)
            area = get_smallest_triangle_area(candidate)
            if area > best_area:
                best_area = area
                best_points = candidate

    # Verify local optimality through hill-climbing
    if best_points is not None:
        current = best_points
        current_area = best_area
        for _ in range(5):
            pert = current + np.random.uniform(-0.001, 0.001, size=current.shape)
            res_verify = optimize.minimize(
                objective,
                pert.flatten(),
                method='SLSQP',
                constraints=constraints,
                options={'maxiter': 100}
            )
            if res_verify.success:
                improved = res_verify.x.reshape(11, 2)
                improved_area = get_smallest_triangle_area(improved)
                if improved_area > current_area:
                    current = improved
                    current_area = improved_area
                else:
                    break
        return current
    
    return generate_initial()

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