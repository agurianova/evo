import random
import math
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area

def entrypoint() -> np.ndarray:
    base_seed = 42
    best_min_area = -1
    best_cart_points = None

    # Asymmetric row patterns (removed symmetric ones as in child lineage)
    candidate_patterns = [
        [1, 3, 3, 2, 2],
        [1, 2, 3, 3, 2],
        [1, 3, 2, 3, 2],
        [1, 4, 2, 2, 2],
        [2, 3, 2, 2, 2]
    ]
    pattern_scores = [0.0] * len(candidate_patterns)
    sa_history = []  # Stores (T, cooling_rate, min_area) for restarts

    for restart in range(10):
        np.random.seed(base_seed + restart)
        random.seed(base_seed + restart)

        # Softmax pattern selection using historical performance
        weights = np.exp(pattern_scores)
        weights /= weights.sum()
        pattern_idx = np.random.choice(len(candidate_patterns), p=weights)
        rows = candidate_patterns[pattern_idx]
        total_rows = len(rows)

        # Tunable spacing exponent (alpha ∈ [0.4, 0.6])
        alpha = random.uniform(0.4, 0.6)

        # Generate barycentric points with tunable spacing
        bary_points = []
        for i, n in enumerate(rows):
            w_val = 1 - ((i + 0.5) / total_rows) ** alpha
            if n == 1:
                t = 0.5
                u_val = t * (1 - w_val)
                v_val = (1 - w_val) * (1 - t)
                bary_points.append((u_val, v_val, w_val))
            else:
                for j in range(n):
                    t = j / (n - 1)
                    u_val = t * (1 - w_val)
                    v_val = (1 - w_val) * (1 - t)
                    bary_points.append((u_val, v_val, w_val))

        # Reduced noise magnitude: ±0.01*(1-w)
        randomized_bary = []
        for (u, v, w) in bary_points:
            noise_mag = 0.01 * (1 - w)
            du, dv = np.random.uniform(-noise_mag, noise_mag, 2)
            dw = -du - dv
            bary_new = np.clip([u + du, v + dv, w + dw], 0, None)
            total = sum(bary_new)
            if total > 0:
                bary_new = bary_new / total
            else:
                bary_new = [1/3, 1/3, 1/3]
            randomized_bary.append(tuple(bary_new))
        bary_points = randomized_bary

        # Adaptive SA parameter selection from historical successes
        if sa_history:
            sorted_history = sorted(sa_history, key=lambda x: x[2], reverse=True)
            top_k = max(1, len(sorted_history) // 5)
            T, cooling_rate, _ = random.choice(sorted_history[:top_k])
        else:
            T = 0.1
            cooling_rate = 0.9995

        A, B, C = get_unit_triangle()
        current_bary = bary_points
        cart_points = np.array([u*A + v*B + w*C for (u, v, w) in current_bary])
        current_min_area = get_smallest_triangle_area(cart_points)
        best_bary = current_bary
        best_min_area_restart = current_min_area
        
        # Simulated annealing phase
        step_sa_initial = 0.05
        for k in range(5000):
            step_sa = step_sa_initial * (cooling_rate ** k)
            idx = random.randint(0, 10)
            u0, v0, w0 = current_bary[idx]

            du, dv = np.random.uniform(-step_sa, step_sa, 2)
            dw = -du - dv
            bary_new = np.clip([u0 + du, v0 + dv, w0 + dw], 0, None)
            total = sum(bary_new)
            if total > 0:
                bary_new = bary_new / total
            else:
                bary_new = [1/3, 1/3, 1/3]

            new_bary = current_bary[:]
            new_bary[idx] = tuple(bary_new)
            new_cart = np.array([u*A + v*B + w*C for (u, v, w) in new_bary])
            new_min_area = get_smallest_triangle_area(new_cart)

            delta = new_min_area - current_min_area
            if delta > 0 or random.random() < math.exp(delta / T):
                current_bary, current_min_area = new_bary, new_min_area
                if new_min_area > best_min_area_restart:
                    best_bary, best_min_area_restart = new_bary, new_min_area

            T = T * cooling_rate

        # Early termination if SA result is too weak
        if best_min_area > 0 and best_min_area_restart < 0.5 * best_min_area:
            candidate_min_area = best_min_area_restart
n            current_bary = best_bary
        else:
            # Aggressive hill-climbing with step adaptation (1.5/0.5 factors)
            current_bary = best_bary
            cart_points = np.array([u*A + v*B + w*C for (u, v, w) in current_bary])
            current_min_area = get_smallest_triangle_area(cart_points)
            step_hill = 0.01
            no_improve = 0

            for _ in range(20000):
                if no_improve >= 5000:
                    break

                idx = random.randint(0, 10)
                u0, v0, w0 = current_bary[idx]
                du, dv = np.random.uniform(-step_hill, step_hill, 2)
                dw = -du - dv
                bary_new = np.clip([u0 + du, v0 + dv, w0 + dw], 0, None)
                total = sum(bary_new)
                if total > 0:
                    bary_new = bary_new / total
                else:
                    bary_new = [1/3, 1/3, 1/3]

                new_bary = current_bary[:]
                new_bary[idx] = tuple(bary_new)
                new_cart = np.array([u*A + v*B + w*C for (u, v, w) in new_bary])
                new_min_area = get_smallest_triangle_area(new_cart)

                if new_min_area > current_min_area:
                    current_bary, current_min_area = new_bary, new_min_area
                    step_hill = min(step_hill * 1.5, 0.2)
                    no_improve = 0
                else:
                    step_hill = max(step_hill * 0.5, 0.0001)
                    no_improve += 1

            # Fine-tuning phase for deep basin convergence
            step_fine = 1e-5
            for _ in range(1000):
                idx = random.randint(0, 10)
                u0, v0, w0 = current_bary[idx]
                du, dv = np.random.uniform(-step_fine, step_fine, 2)
                dw = -du - dv
                bary_new = np.clip([u0 + du, v0 + dv, w0 + dw], 0, None)
                total = sum(bary_new)
                if total > 0:
                    bary_new = bary_new / total
                else:
                    bary_new = [1/3, 1/3, 1/3]

                new_bary = current_bary[:]
                new_bary[idx] = tuple(bary_new)
                new_cart = np.array([u*A + v*B + w*C for (u, v, w) in new_bary])
                new_min_area = get_smallest_triangle_area(new_cart)

                if new_min_area > current_min_area:
                    current_bary, current_min_area = new_bary, new_min_area

            candidate_min_area = current_min_area

        # Update global best configuration
        if candidate_min_area > best_min_area:
            best_min_area = candidate_min_area
            best_cart_points = np.array([u*A + v*B + w*C for (u, v, w) in current_bary])

        # Update historical records for adaptive learning
        pattern_scores[pattern_idx] = max(pattern_scores[pattern_idx], candidate_min_area)
        sa_history.append((T, cooling_rate, candidate_min_area))

    return best_cart_points