# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
from scipy.optimize import differential_evolution

np.random.seed(42)
random.seed(42)

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    H = C[1]  # Triangle height

    # Generate 10 row distributions: 1 known optimal + 9 random compositions
    row_distributions = [[3, 3, 2, 2, 1]]
    for _ in range(9):
        splits = sorted(random.sample(range(1, 11), 4))
        rows = [
            splits[0],
            splits[1] - splits[0],
            splits[2] - splits[1],
            splits[3] - splits[2],
            11 - splits[3]
        ]
        row_distributions.append(rows)

    # Create initial configurations
    initial_configs = []
    for rows in row_distributions:
        points = []
        cumulative_above = [sum(rows[i+1:]) for i in range(len(rows))]
        for i, n in enumerate(rows):
            above = cumulative_above[i]
            center_area = (above + 0.5 * n) / 11.0
            v = 1.0 - np.sqrt(center_area)
            
            for j in range(n):
                base_u = ((j + 0.5) / n)**2 * (1 - v)
                if i % 2 == 0:
                    u = base_u + 0.5 * (1 - v) / n
                else:
                    u = base_u
                
                P = (1 - u - v) * A + u * B + v * C
                # Enhanced perturbation scaled by row height
                P[1] += 0.01 * (v * H) * (j - (n - 1)/2)**2
                points.append(P)
        initial_configs.append(np.array(points))

    # Smooth containment-penalized objective
    def objective(flat_points):
        points = flat_points.reshape(-1, 2)
        denom = 2.0  # Area(ABC)=1 => |denom|/2=1
        penalty = 0.0
        
        for P in points:
            u = ((P[0]-A[0])*(C[1]-A[1]) - (P[1]-A[1])*(C[0]-A[0])) / denom
            v = ((B[0]-A[0])*(P[1]-A[1]) - (B[1]-A[1])*(P[0]-A[0])) / denom
            a = 1 - u - v
            
            if u < 0: penalty += u**2
            if v < 0: penalty += v**2
            if a < 0: penalty += a**2

        min_area_val = get_smallest_triangle_area(points)
        return -min_area_val + 10000 * penalty

    # Bounding box for optimization
    bounds = [(0, B[0]), (0, C[1])] * 11
    
    # Evaluate all configurations
    best_config = None
    best_min_area = -1

    for init in initial_configs:
        res = differential_evolution(
            objective,
            bounds,
            x0=init.flatten(),
            popsize=10,
            maxiter=22,
            tol=1e-8,
            seed=42,
            polish=False
        )
        candidate = res.x.reshape(-1, 2)
        
        if is_inside_triangle(candidate, A, B, C):
            min_area_candidate = get_smallest_triangle_area(candidate)
            if min_area_candidate > best_min_area:
                best_min_area = min_area_candidate
                best_config = candidate

    return best_config if best_config is not None else initial_configs[0]

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