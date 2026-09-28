# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
import numpy as np
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Precompute triangle dimensions
    base = B[0] - A[0]  # Since flat-bottomed, A[0]=0, B[0]=base
    height = C[1]      # Height from base
    
    def generate_initial_grid():
        n_rows = 3
        points_per_row = [4, 4, 3]
        points = []
        for i in range(n_rows):
            y = (i + 0.5) * (height / n_rows)
            width = base * (1 - y / height)
            x0 = (base - width) / 2
            spacing = width / (points_per_row[i] - 1) if points_per_row[i] > 1 else 0
            
            for j in range(points_per_row[i]):
                x = x0 + j * spacing
                # Apply perturbation with validity checks
                for _ in range(10):
                    dx = random.uniform(-0.01, 0.01)
                    dy = random.uniform(-0.01, 0.01)
                    candidate = np.array([x + dx, y + dy])
                    
                    # Check inside triangle and distinctness
                    if not is_inside_triangle([candidate], A, B, C):
                        continue
                    distinct = True
                    for p in points:
                        if np.linalg.norm(candidate - p) < 0.001:
                            distinct = False
                            break
                    if distinct:
                        points.append(candidate)
                        break
                else:
                    points.append(np.array([x, y]))  # Fallback to unperturbed
        return np.array(points)

    best_config = None
    best_min_area = -1

    for seed in range(10):
        np.random.seed(seed)
        random.seed(seed)
        
        # Generate and validate initial grid
        points = generate_initial_grid()
        if not is_inside_triangle(points, A, B, C):
            continue
        
        # Initial min area
        current_min_area = get_smallest_triangle_area(points)
        
        # Simulated annealing parameters
        T0 = 0.001
        step_size0 = 0.1
        num_iterations = 5000

        for iter in range(num_iterations):
            # Recompute min area and critical points via brute force
            min_area_val = float('inf')
            critical_set = set()
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        a, b, c = points[i], points[j], points[k]
                        area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        if area < min_area_val - 1e-9:
                            min_area_val = area
                            critical_set = {i, j, k}
                        elif abs(area - min_area_val) <= 1e-9:
                            critical_set.update([i, j, k])
            current_min_area = min_area_val

            # Select point to perturb (80% bias to critical points)
            if critical_set and random.random() < 0.8:
                idx = random.choice(list(critical_set))
            else:
                idx = random.randint(0, 10)

            old_point = points[idx].copy()
            frac = iter / num_iterations
            step_size = step_size0 * (1 - frac)
            T = T0 * (1 - frac)

            # Generate and validate candidate
            delta = np.random.uniform(-step_size, step_size, size=2)
            candidate = old_point + delta
            
            if not is_inside_triangle([candidate], A, B, C):
                continue
            
            distinct = True
            for i in range(11):
                if i == idx:
                    continue
                if np.linalg.norm(candidate - points[i]) < 0.001:
                    distinct = False
                    break
            if not distinct:
                continue

            # Evaluate candidate
            points[idx] = candidate
            new_min_area = get_smallest_triangle_area(points)
            if new_min_area <= 0:
                points[idx] = old_point
                continue

            # Simulated annealing acceptance
            delta_area = new_min_area - current_min_area
            if delta_area >= 0:
                current_min_area = new_min_area
            else:
                if T > 1e-9 and random.random() < math.exp(delta_area / T):
                    current_min_area = new_min_area
                else:
                    points[idx] = old_point

        # Track best configuration across seeds
        final_area = get_smallest_triangle_area(points)
        if final_area > best_min_area:
            best_min_area = final_area
            best_config = points.copy()

    return best_config

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def _d_entrypoint():
    A, B, C = get_unit_triangle()

    def project_point_to_triangle(p, A, B, C):
        if is_inside_triangle(np.array([p]), A, B, C):
            return p
        edges = [(A, B), (B, C), (C, A)]
        best_point = None
        best_dist = float('inf')
        for (v1, v2) in edges:
            v = v2 - v1
            w = p - v1
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 < 1e-10:
                proj = v1
            else:
                b = c1 / c2
                if b < 0:
                    proj = v1
                elif b > 1:
                    proj = v2
                else:
                    proj = v1 + b * v
            dist = np.linalg.norm(p - proj)
            if dist < best_dist:
                best_dist = dist
                best_point = proj
        return best_point

    def project_points_to_triangle(points, A, B, C):
        projected = np.zeros_like(points)
        for i in range(len(points)):
            projected[i] = project_point_to_triangle(points[i], A, B, C)
        return projected

    def find_minimal_triplet(pts):
        n = pts.shape[0]
        min_area = float('inf')
        best_triplet = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    x1, y1 = pts[i]
                    x2, y2 = pts[j]
                    x3, y3 = pts[k]
                    area = 0.5 * abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
                    if area < min_area:
                        min_area = area
                        best_triplet = (i, j, k)
        return best_triplet

    def improve(points: np.ndarray) -> np.ndarray:
        n_chains = 5
        jitter_amount = 0.05
        per_chain_max_iter = 300
        early_stop_patience = 50
        
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)

        for _ in range(n_chains):
            current = points.copy() + np.random.uniform(-jitter_amount, jitter_amount, size=points.shape)
            current = project_points_to_triangle(current, A, B, C)
            
            best_chain = current.copy()
            best_chain_score = get_smallest_triangle_area(best_chain)
            current_score = best_chain_score
            T = 1.0  # increased initial temperature
            decay = 0.99
            no_improve_count = 0

            for iter_idx in range(per_chain_max_iter):
                if np.random.rand() < 0.8:
                    i, j, k = find_minimal_triplet(current)
                    x1, y1 = current[i]
                    x2, y2 = current[j]
                    x3, y3 = current[k]
                    f = (x2 - x1)*(y3 - y1) - (x3 - x1)*(y2 - y1)
                    sign_f = 1.0 if f >= 0 else -1.0

                    grad_i = np.array([y2 - y3, x3 - x2]) * sign_f
                    grad_j = np.array([y3 - y1, x1 - x3]) * sign_f
                    grad_k = np.array([y1 - y2, x2 - x1]) * sign_f

                    step_size = 0.01  # fixed step size
                    candidate = current.copy()
                    candidate[i] += step_size * grad_i
                    candidate[j] += step_size * grad_j
                    candidate[k] += step_size * grad_k
                else:
                    i, j, k = np.random.choice(11, 3, replace=False)
                    step_size = 0.01  # fixed step size
                    candidate = current.copy()
                    candidate[i] += np.random.normal(0, step_size, 2)
                    candidate[j] += np.random.normal(0, step_size, 2)
                    candidate[k] += np.random.normal(0, step_size, 2)

                candidate = project_points_to_triangle(candidate, A, B, C)
                candidate_score = get_smallest_triangle_area(candidate)
                delta = candidate_score - current_score

                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = candidate_score
                    if candidate_score > best_chain_score:
                        best_chain = candidate
                        best_chain_score = candidate_score
                        no_improve_count = 0
                    else:
                        no_improve_count += 1
                else:
                    no_improve_count += 1

                T *= decay

                if no_improve_count >= early_stop_patience:
                    break

            if best_chain_score > best_score_overall:
                best_overall = best_chain
                best_score_overall = best_chain_score

        return best_overall

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)