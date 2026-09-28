# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random

from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri

    # Define the grid parameters
    rows = 4
    v_vals = [0.125, 0.375, 0.625, 0.875]
    points_per_row = [5, 3, 2, 1]  # total 11

    points = []
    for k in range(rows):
        v = v_vals[k]
        num_points = points_per_row[k]
        for i in range(num_points):
            u = (i + 0.5) / num_points * (1 - v)
            P = (1 - u - v) * A + u * B + v * C
            points.append(P)

    # Convert to numpy array for easier manipulation
    points = np.array(points)

    # Apply initial perturbation (larger than parent)
    for i in range(len(points)):
        original = points[i].copy()
        # Try up to 5 times to get a valid perturbation
        for attempt in range(5):
            perturbation = np.random.uniform(-0.02, 0.02, size=2)
            candidate = original + perturbation
            if is_inside_triangle([candidate], A, B, C):
                points[i] = candidate
                break

    # Now, run hill-climbing to improve min_area
    current_points = points.copy()
    current_min_area = get_smallest_triangle_area(current_points)

    # Parameters for hill-climbing
    max_outer = 100
    trials_per_point = 20
    step_size = 0.01

    for _ in range(max_outer):
        # Shuffle the order of points
        indices = np.random.permutation(11)
        for i in indices:
            original_point = current_points[i].copy()
            best_min_area = current_min_area
            best_point = original_point

            for trial in range(trials_per_point):
                # Random direction and magnitude up to step_size
                angle = np.random.uniform(0, 2*np.pi)
                r = np.random.uniform(0, step_size)
                dx = r * np.cos(angle)
                dy = r * np.sin(angle)
                perturbation = np.array([dx, dy])
                candidate = original_point + perturbation

                # Check if inside the triangle
                if not is_inside_triangle([candidate], A, B, C):
                    continue

                # Create new configuration
                new_points = current_points.copy()
                new_points[i] = candidate
                new_min_area = get_smallest_triangle_area(new_points)

                # If this candidate gives a larger min_area, remember it
                if new_min_area > best_min_area:
                    best_min_area = new_min_area
                    best_point = candidate

            # After trying all trials, if we found an improvement, update
            if best_min_area > current_min_area:
                current_points[i] = best_point
                current_min_area = best_min_area

    return current_points

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def _d_entrypoint():
    A, B, C = get_unit_triangle()

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
        n_chains = 3
        jitter_amount = 0.01
        per_chain_max_iter = 300
        early_stop_patience = 50
        
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)

        for _ in range(n_chains):
            # Start with jittered input
            current = points.copy() + np.random.uniform(-jitter_amount, jitter_amount, size=points.shape)
            if not is_inside_triangle(current, A, B, C):
                continue
                
            best_chain = current.copy()
            best_chain_score = get_smallest_triangle_area(best_chain)
            current_score = best_chain_score
            T = 0.1  # initial temperature
            decay = 0.99
            no_improve_count = 0

            for iter_idx in range(per_chain_max_iter):
                # 80%: gradient move on minimal triplet; 20%: random move on random triplet
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

                    norm_i = np.linalg.norm(grad_i)
                    norm_j = np.linalg.norm(grad_j)
                    norm_k = np.linalg.norm(grad_k)
                    eps = 1e-8
                    if norm_i > eps: grad_i /= norm_i
                    if norm_j > eps: grad_j /= norm_j
                    if norm_k > eps: grad_k /= norm_k

                    step_size = 0.1 * current_score
                    candidate = current.copy()
                    candidate[i] += step_size * grad_i
                    candidate[j] += step_size * grad_j
                    candidate[k] += step_size * grad_k
                else:
                    i, j, k = np.random.choice(11, 3, replace=False)
                    step_size = 0.1 * current_score
                    candidate = current.copy()
                    candidate[i] += np.random.normal(0, step_size, 2)
                    candidate[j] += np.random.normal(0, step_size, 2)
                    candidate[k] += np.random.normal(0, step_size, 2)

                if not is_inside_triangle(candidate, A, B, C):
                    T *= decay
                    no_improve_count += 1
                    continue

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