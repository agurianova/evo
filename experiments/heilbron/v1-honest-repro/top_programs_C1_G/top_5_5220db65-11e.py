import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Helper: signed triangle area (with orientation)
    def signed_triangle_area(a, b, c):
        return 0.5 * (a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
    
    # Helper: convert Cartesian to barycentric coordinates
    def cartesian_to_barycentric(p, A, B, C):
        u = signed_triangle_area(p, B, C)
        v = signed_triangle_area(A, p, C)
        w = signed_triangle_area(A, B, p)
        total = u + v + w
        if abs(total) < 1e-10:
            return (1/3, 1/3, 1/3)
        return (u/total, v/total, w/total)

    # Helper: convert barycentric to Cartesian coordinates
    def barycentric_to_cartesian(u, v, w, A, B, C):
        return u * A + v * B + w * C

    # Helper: find smallest triangle (area and indices)
    def get_min_triangle(pts):
        n = pts.shape[0]
        min_area = float('inf')
        min_indices = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = abs(signed_triangle_area(pts[i], pts[j], pts[k]))
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        return min_area, min_indices

    def optimize_configuration(points):
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_overall = current.copy()
        best_overall_score = current_score

        # Optimization parameters
        max_iter = 10000
        base_noise = 0.05
        initial_temp = 0.1
        cooling_rate = 0.99
        temperature = initial_temp
        
        # Adaptive bottleneck focus parameters
        bottleneck_prob_start = 0.7
        bottleneck_prob_end = 0.5

        for iter_count in range(max_iter):
            # Adaptive noise scaling
            noise_magnitude = base_noise * (1.0 - current_score / 0.0365)
            noise_magnitude = max(0.005, min(base_noise, noise_magnitude))
            
            # Adaptive bottleneck probability
            current_bottleneck_prob = bottleneck_prob_start - \
                (bottleneck_prob_start - bottleneck_prob_end) * (iter_count / max_iter)

            # Determine perturbation strategy
            if np.random.rand() < current_bottleneck_prob:
                # Focus on critical triangle
                _, min_indices = get_min_triangle(current)
                points_to_perturb = min_indices
                
                if np.random.rand() < 0.5:
                    # Targeted perturbation: move away from centroid
                    candidate = current.copy()
                    centroid = np.mean(current[list(min_indices)], axis=0)
                    for idx in points_to_perturb:
                        direction = candidate[idx] - centroid
                        norm = np.linalg.norm(direction)
                        if norm < 1e-10:
                            continue
                        direction = direction / norm
                        step = 0.01 * noise_magnitude * direction
                        candidate[idx] += step
                        
                        # Project back to triangle if outside
                        if not is_inside_triangle(candidate[idx], A, B, C):
                            u, v, w = cartesian_to_barycentric(candidate[idx], A, B, C)
                            u = max(0, min(1, u))
                            v = max(0, min(1, v))
                            total = u + v
                            if total > 1:
                                u, v = u/total, v/total
                            w = 1 - u - v
                            candidate[idx] = barycentric_to_cartesian(u, v, w, A, B, C)
                else:
                    # Random barycentric perturbation on critical points
                    candidate = current.copy()
                    for idx in points_to_perturb:
                        p = candidate[idx]
                        u, v, w = cartesian_to_barycentric(p, A, B, C)
                        du = np.random.normal(0, noise_magnitude)
                        dv = np.random.normal(0, noise_magnitude)
                        u_new, v_new = u + du, v + dv
                        u_new = max(0, u_new)
                        v_new = max(0, v_new)
                        total = u_new + v_new
                        if total > 1:
                            u_new, v_new = u_new/total, v_new/total
                        w_new = 1 - u_new - v_new
                        candidate[idx] = barycentric_to_cartesian(u_new, v_new, w_new, A, B, C)
            else:
                # Randomly select 2-4 points
                num_points = random.randint(2, 4)
                points_to_perturb = random.sample(range(11), num_points)
                candidate = current.copy()
                for idx in points_to_perturb:
                    p = candidate[idx]
                    u, v, w = cartesian_to_barycentric(p, A, B, C)
                    du = np.random.normal(0, noise_magnitude)
                    dv = np.random.normal(0, noise_magnitude)
                    u_new, v_new = u + du, v + dv
                    u_new = max(0, u_new)
                    v_new = max(0, v_new)
                    total = u_new + v_new
                    if total > 1:
                        u_new, v_new = u_new/total, v_new/total
                    w_new = 1 - u_new - v_new
                    candidate[idx] = barycentric_to_cartesian(u_new, v_new, w_new, A, B, C)

            candidate_score = get_smallest_triangle_area(candidate)
            
            # Update global best
            if candidate_score > best_overall_score:
                best_overall = candidate.copy()
                best_overall_score = candidate_score

            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current, current_score = candidate, candidate_score

            # Cool temperature
            temperature *= cooling_rate
            
            # Early stopping if near-optimal
            if best_overall_score >= 0.036:
                break

        return best_overall

    # Predefined valid 5-row structures summing to 11 points
    structures = [
        (1, 2, 3, 3, 2),
        (1, 3, 3, 2, 2),
        (2, 2, 3, 2, 2),
        (1, 2, 4, 2, 2),
        (2, 3, 2, 3, 1),
        (1, 1, 4, 3, 2)
    ]

    best_points = None
    best_score = -1

    for _ in range(30):
        # Randomly select row structure and heights
        structure = random.choice(structures)
        row_heights = sorted([random.uniform(0.05, 0.95) for _ in range(5)])
        
        # Generate base configuration with dynamic structure
        base_points = []
        for i, num_in_row in enumerate(structure):
            y = row_heights[i]  # Fraction from top (0=top, 1=base)
            w_row = 1.0 - y     # Barycentric coordinate for top vertex
            base_offset = random.uniform(0.02, 0.1)
            
            for j in range(num_in_row):
                # Symmetric position along row
                x_sym = (j + 1) / (num_in_row + 1)
                # Alternating offset scaled by row width
                offset = base_offset * w_row * (-1)**j
                x_perturbed = max(0.0, min(1.0, x_sym + offset))
                
                # Barycentric coordinates
                u = x_perturbed * y
                v = (1 - x_perturbed) * y
                w = w_row
                
                base_points.append(barycentric_to_cartesian(u, v, w, A, B, C))
        
        base_points = np.array(base_points)
        
        # Add small diversity perturbation
        for i in range(11):
            u, v, w = cartesian_to_barycentric(base_points[i], A, B, C)
            du = random.uniform(-0.01, 0.01)
            dv = random.uniform(-0.01, 0.01)
            u_new = max(0, u + du)
            v_new = max(0, v + dv)
            total = u_new + v_new
            if total > 1:
                u_new, v_new = u_new/total, v_new/total
            w_new = 1 - u_new - v_new
            base_points[i] = barycentric_to_cartesian(u_new, v_new, w_new, A, B, C)

        optimized_points = optimize_configuration(base_points)
        score = get_smallest_triangle_area(optimized_points)
        
        if score > best_score:
            best_score = score
            best_points = optimized_points

    return best_points