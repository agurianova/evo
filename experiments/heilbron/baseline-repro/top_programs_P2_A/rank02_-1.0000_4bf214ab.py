import numpy as np
from scipy.optimize import differential_evolution
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()

    # Adaptive perturbation operator simulating opponent strategies
    def apply_perturbation(points, base_area):
        n = len(points)
        
        def compute_triangle_area(a, b, c):
            return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

        # Collect near-smallest triangles (within 0.01% of min_area)
        candidates = []
        min_found = float('inf')
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = compute_triangle_area(points[i], points[j], points[k])
                    if area < min_found:
                        min_found = area
                    if area <= base_area * 1.0001:
                        candidates.append((i, j, k, area))
        
        if not candidates or min_found > base_area * 1.001:
            return points
            
        # Randomly select a candidate triangle
        tri = candidates[np.random.randint(0, len(candidates))]
        i, j, k, _ = tri
        vertex_idx = np.random.choice([i, j, k])
        others = [i, j, k]
        others.remove(vertex_idx)
        P, Q, R = points[vertex_idx], points[others[0]], points[others[1]]

        # Compute direction to increase triangle area
        QR = R - Q
        cross_val = (R[0]-Q[0])*(P[1]-Q[1]) - (R[1]-Q[1])*(P[0]-Q[0])
        direction = np.array([-QR[1], QR[0]]) if cross_val > 0 else np.array([QR[1], -QR[0]])
        
        if np.linalg.norm(direction) < 1e-10:
            return points
        direction = direction / np.linalg.norm(direction)

        # Adaptive step size scaled by current solution quality
        step0 = 0.05 * np.sqrt(base_area / 0.03)
        step = step0
        new_point = None
        for _ in range(5):
            candidate_pt = P + step * direction
            if is_inside_triangle(candidate_pt, A, B, C):
                new_point = candidate_pt
                break
            step /= 2.0

        if new_point is None:
            return points
            
        new_points = points.copy()
        new_points[vertex_idx] = new_point
        return new_points

    # Robustness-aware objective function
    def objective(x):
        points = x.reshape(11, 2)
        if not is_inside_triangle(points, A, B, C):
            return 1e10

        base_area = get_smallest_triangle_area(points)
        
        # Simulate 5 opponent strategies
        k = 5
        count_failures = 0
        for _ in range(k):
            perturbed_points = apply_perturbation(points, base_area)
            improved_area = get_smallest_triangle_area(perturbed_points)
            if improved_area <= base_area:
                count_failures += 1

        resistance_score = count_failures / k
        quality = min(base_area / 0.0365, 1.0)
        return -(0.5 * quality + 0.5 * resistance_score)

    # Generate diverse initial population (44 configurations)
    initial_pop = []

    # 1. High-quality seeds: [3,3,3,2] pattern with barycentric buffer and perturbations
    base_pattern = [3, 3, 3, 2]
    total_rows = len(base_pattern)
    for _ in range(5):
        points_bary = []
        for i, num_pts in enumerate(base_pattern):
            v = 0.05 + i * (0.90 / (total_rows - 1))
            for j in range(num_pts):
                u = 0.01 + (j + 0.5) / num_pts * (0.98 - v)
                # Add small barycentric perturbation
                du = np.random.uniform(-0.005, 0.005)
                dv = np.random.uniform(-0.005, 0.005)
                u_pert = max(0.01, min(0.98, u + du))
                v_pert = max(0.01, min(0.98, v + dv))
                if u_pert + v_pert > 0.98:
                    scale = 0.98 / (u_pert + v_pert)
                    u_pert *= scale
                    v_pert *= scale
                points_bary.append([u_pert, v_pert])
        
        points_cart = []
        for (u, v) in points_bary:
            w = 1 - u - v
            P = w * A + u * B + v * C
            points_cart.append(P)
        initial_pop.append(np.array(points_cart).flatten())

    # 2. Adaptive row patterns (20 configurations)
    for _ in range(20):
        num_rows = np.random.randint(2, 6)
        parts = []
        rem = 11
        for i in range(num_rows - 1):
            low = 1
            high = rem - (num_rows - i - 1)
            num_pts = np.random.randint(low, high + 1)
            parts.append(num_pts)
            rem -= num_pts
        parts.append(rem)

        points_bary = []
        for i, num_pts in enumerate(parts):
            v = 0.01 + i * (0.98 / max(1, num_rows - 1))
            for j in range(num_pts):
                u = 0.01 + (j + 0.5) / num_pts * (0.98 - v)
                points_bary.append([u, v])
        
        points_cart = []
        for (u, v) in points_bary:
            w = 1 - u - v
            P = w * A + u * B + v * C
            points_cart.append(P)
        initial_pop.append(np.array(points_cart).flatten())

    # 3. Random interior with barycentric buffer (19 configurations)
    for _ in range(19):
        points = []
        for _ in range(11):
            u = np.random.uniform(0.01, 0.98)
            v = np.random.uniform(0.01, 0.98 - u)
            w = 1 - u - v
            P = w * A + u * B + v * C
            points.append(P)
        initial_pop.append(np.array(points).flatten())

    # Bounding box constraints (with buffer to avoid vertices)
    x_min, x_max = 0.01, 1.5097
    y_min, y_max = 0.01, 1.3061
    bounds = [(x_min, x_max), (y_min, y_max)] * 11

    # Run differential evolution with robustness objective
    try:
        res = differential_evolution(
            objective,
            bounds,
            maxiter=50,
            popsize=1.0,
            init=np.array(initial_pop),
            seed=42,
            polish=False,
            workers=1
        )
        best_config = res.x.reshape(11, 2)
    except:
        # Fallback to best initial configuration
        best_config = None
        best_score = -1
        for config in initial_pop:
            points = config.reshape(11, 2)
            if not is_inside_triangle(points, A, B, C):
                continue
            base_area = get_smallest_triangle_area(points)
            # Estimate resistance (simulate 5 opponents)
            count_failures = 0
            for _ in range(5):
                perturbed = apply_perturbation(points, base_area)
                if get_smallest_triangle_area(perturbed) <= base_area:
                    count_failures += 1
            resistance = count_failures / 5
            quality = min(base_area / 0.0365, 1.0)
            score = 0.5 * quality + 0.5 * resistance
            if score > best_score:
                best_score = score
                best_config = points
        
        if best_config is None:
            # Emergency fallback: known [3,3,3,2] pattern
            pattern = [3, 3, 3, 2]
            total_rows = len(pattern)
            points = []
            for i, num_pts in enumerate(pattern):
                v = 0.05 + i * (0.90 / (total_rows - 1))
                for j in range(num_pts):
                    u = 0.01 + (j + 0.5) / num_pts * (0.98 - v)
                    w = 1 - u - v
                    P = w * A + u * B + v * C
                    points.append(P)
            best_config = np.array(points)

    return best_config