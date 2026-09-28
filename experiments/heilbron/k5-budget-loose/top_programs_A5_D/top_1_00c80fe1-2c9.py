from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Set seed based on input configuration for reproducible per-instance randomness
        seed = hash(points.tobytes()) % (2**32)
        np.random.seed(seed)

        def compute_min_triangle(pts):
            n = pts.shape[0]
            min_area = float('inf')
            min_indices = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = pts[i]
                        x2, y2 = pts[j]
                        x3, y3 = pts[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area < min_area:
                            min_area = area
                            min_indices = (i, j, k)
            return min_area, min_indices

        # Initialize with current configuration
        current = points.copy()
        current_score, critical_indices = compute_min_triangle(current)
        best = current.copy()
        best_score = current_score

        # Simulated Annealing parameters
        T0 = 0.01
        decay_temp = 0.95
        base_step = 0.05
        decay_step = 0.95
        n_iterations = 200

        for iteration in range(n_iterations):
            T = T0 * (decay_temp ** iteration)
            step_size = base_step * (decay_step ** iteration)

            candidate = current.copy()

            # Decide move type: 80% single-point, 20% multi-point
            if np.random.random() < 0.8:
                # Single-point move (90% critical, 10% non-critical)
                if np.random.random() < 0.9:
                    idx = np.random.choice(critical_indices)
                else:
                    idx = np.random.randint(0, 11)

                # Apply gradient-based move for critical points, isotropic for non-critical
                if idx in critical_indices:
                    i0, i1, i2 = critical_indices
                    tri = [candidate[i0], candidate[i1], candidate[i2]]
                    pos = np.where(np.array(critical_indices) == idx)[0][0]
                    x0, y0 = tri[0]
                    x1, y1 = tri[1]
                    x2, y2 = tri[2]
                    f = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
                    sign_f = 1 if f >= 0 else -1

                    if pos == 0:
                        grad_x = 0.5 * sign_f * (y1 - y2)
                        grad_y = 0.5 * sign_f * (x2 - x1)
                    elif pos == 1:
                        grad_x = 0.5 * sign_f * (y2 - y0)
                        grad_y = 0.5 * sign_f * (x0 - x2)
                    elif pos == 2:
                        grad_x = 0.5 * sign_f * (y0 - y1)
                        grad_y = 0.5 * sign_f * (x1 - x0)

                    grad_vec = np.array([grad_x, grad_y])
                    grad_len = np.linalg.norm(grad_vec)
                    if grad_len > 1e-10:
                        unit_grad = grad_vec / grad_len
                    else:
                        unit_grad = np.random.randn(2)
                        unit_grad /= np.linalg.norm(unit_grad)
                    candidate[idx] += step_size * unit_grad
                else:
                    candidate[idx] += np.random.randn(2) * step_size

            else:
                # Multi-point move (2 or 3 points)
                num_points = 2 if np.random.random() < 0.75 else 3
                idxs = []
                while len(idxs) < num_points:
                    if np.random.random() < 0.9 and len(critical_indices) > 0:
                        idx = np.random.choice(critical_indices)
                    else:
                        idx = np.random.randint(0, 11)
                    if idx not in idxs:
                        idxs.append(idx)

                for idx in idxs:
                    if idx in critical_indices:
                        i0, i1, i2 = critical_indices
                        tri = [candidate[i0], candidate[i1], candidate[i2]]
                        pos = np.where(np.array(critical_indices) == idx)[0][0]
                        x0, y0 = tri[0]
                        x1, y1 = tri[1]
                        x2, y2 = tri[2]
                        f = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
                        sign_f = 1 if f >= 0 else -1

                        if pos == 0:
                            grad_x = 0.5 * sign_f * (y1 - y2)
                            grad_y = 0.5 * sign_f * (x2 - x1)
                        elif pos == 1:
                            grad_x = 0.5 * sign_f * (y2 - y0)
                            grad_y = 0.5 * sign_f * (x0 - x2)
                        elif pos == 2:
                            grad_x = 0.5 * sign_f * (y0 - y1)
                            grad_y = 0.5 * sign_f * (x1 - x0)

                        grad_vec = np.array([grad_x, grad_y])
                        grad_len = np.linalg.norm(grad_vec)
                        if grad_len > 1e-10:
                            unit_grad = grad_vec / grad_len
                        else:
                            unit_grad = np.random.randn(2)
                            unit_grad /= np.linalg.norm(unit_grad)
                        candidate[idx] += step_size * unit_grad
                    else:
                        candidate[idx] += np.random.randn(2) * step_size

            # Boundary check
            if not is_inside_triangle(candidate, A, B, C):
                continue

            # Evaluate candidate
            candidate_score, _ = compute_min_triangle(candidate)

            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score

            # Update critical indices for next iteration (from current state)
            _, critical_indices = compute_min_triangle(current)

        return best

    return improve