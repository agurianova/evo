# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
import numpy as np
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def _g_entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Helper function: project point to line segment
    def project_point_to_segment(p, a, b):
        ap = p - a
        ab = b - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)  # Avoid division by zero
        t = max(0, min(1, t))
        return a + t * ab

    # Helper function: project point to triangle boundary
    def project_to_triangle(p, A, B, C):
        if is_inside_triangle(p, A, B, C):
            return p
        edges = [(A, B), (B, C), (C, A)]
        best_point = None
        best_sq_dist = float('inf')
        for (a, b) in edges:
            proj = project_point_to_segment(p, a, b)
            diff = p - proj
            sq_dist = diff[0]*diff[0] + diff[1]*diff[1]
            if sq_dist < best_sq_dist:
                best_sq_dist = sq_dist
                best_point = proj
        return best_point

    best_points = None
    best_min_area = -1

    for restart in range(5):
        # Set deterministic seed for each restart
        np.random.seed(42 + restart)
        random.seed(42 + restart)

        # Initialize 11 points randomly using barycentric coordinates
        points = []
        for _ in range(11):
            u = random.random()
            v = random.random() * (1 - u)
            w = 1 - u - v
            P = u * A + v * B + w * C
            points.append(P)
        points = np.array(points)

        # Simulated annealing parameters
        step_size = 0.1
        T = 1.0
        alpha = 0.9995
        n_iterations = 20000

        current_min_area = get_smallest_triangle_area(points)

        for _ in range(n_iterations):
            # Select random point to perturb
            idx = random.randint(0, 10)
            old_point = points[idx].copy()

            # Generate random displacement vector
            angle = random.uniform(0, 2 * math.pi)
            dx = math.cos(angle)
            dy = math.sin(angle)
            displacement = np.array([dx, dy]) * step_size

            candidate = old_point + displacement

            # Project to triangle if outside
            if not is_inside_triangle(candidate, A, B, C):
                candidate = project_to_triangle(candidate, A, B, C)

            # Temporarily update point and evaluate
            points[idx] = candidate
            new_min_area = get_smallest_triangle_area(points)

            # Revert if invalid configuration (degenerate triangles)
            if new_min_area <= 0:
                points[idx] = old_point
                continue

            # Acceptance criterion for maximization
            if new_min_area > current_min_area:
                current_min_area = new_min_area
            else:
                delta = current_min_area - new_min_area
                if random.random() < math.exp(-delta / T):
                    current_min_area = new_min_area
                else:
                    points[idx] = old_point

            # Cool acceptance temperature
            T *= alpha

        # Track best configuration across restarts
        if current_min_area > best_min_area:
            best_points = points.copy()
            best_min_area = current_min_area

    return best_points

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def _d_entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_triangle(p, A, B, C):
        edges = [(A, B), (B, C), (C, A)]
        best_proj = None
        best_dist = float('inf')
        for (X, Y) in edges:
            v = Y - X
            w = p - X
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 < 1e-10:
                proj = X
            else:
                b = c1 / c2
                if b < 0:
                    proj = X
                elif b > 1:
                    proj = Y
                else:
                    proj = X + b * v
            dist = np.linalg.norm(p - proj)
            if dist < best_dist:
                best_dist = dist
                best_proj = proj
        return best_proj

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        n = points.shape[0]

        T0 = 0.1 * best_score
        T = T0
        step_size0 = 0.05
        cooling_factor = 0.9995
        max_iter = 10000
        plateau_length = 1000
        no_improve_count = 0

        rng = np.random.RandomState(42)

        for _ in range(max_iter):
            current_min = get_smallest_triangle_area(best)
            min_triangles = []
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = best[i], best[j], best[k]
                        area_val = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                        if area_val <= current_min + 1e-10:
                            min_triangles.append((i, j, k))

            critical_points = set()
            for tri in min_triangles:
                critical_points.update(tri)
            critical_points = list(critical_points)

            num_perturb = rng.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
            if not critical_points:
                chosen_indices = rng.choice(n, size=num_perturb, replace=False)
            else:
                num_to_choose = min(num_perturb, len(critical_points))
                chosen_indices = rng.choice(critical_points, size=num_to_choose, replace=False)
                if num_to_choose < num_perturb:
                    remaining = list(set(range(n)) - set(critical_points))
                    if remaining:
                        additional = rng.choice(remaining, size=num_perturb - num_to_choose, replace=False)
                        chosen_indices = np.concatenate([chosen_indices, additional])

            candidate = best.copy()
            step_size = step_size0 * (T / T0)

            for idx in chosen_indices:
                perturbation = rng.uniform(-step_size, step_size, size=2)
                candidate[idx] += perturbation

            for i in range(n):
                if not is_inside_triangle(candidate[i], A, B, C):
                    candidate[i] = project_to_triangle(candidate[i], A, B, C)

            score = get_smallest_triangle_area(candidate)

            if score > best_score:
                best = candidate
                best_score = score
                no_improve_count = 0
            else:
                delta = score - best_score
                if rng.random() < np.exp(delta / T):
                    best = candidate
                    best_score = score
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            T *= cooling_factor

            if no_improve_count >= plateau_length:
                break

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)