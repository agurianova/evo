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

    def generate_base_configuration():
        # Literature-based 5-row structure for 11 points: 1-2-3-3-2
        # Row heights as fractions of triangle height (from top)
        row_heights = [0.9, 0.65, 0.4, 0.2, 0.1]
        
        points = []
        
        # Top row: 1 point
        y = row_heights[0]
        w = 1.0 - y  # Width proportional to height in equilateral triangle
        points.append(barycentric_to_cartesian(0.5, 0.5, 0, A, B, C))
        
        # Row 1: 2 points with symmetry breaking
        y = row_heights[1]
        w = 1.0 - y
        offset = 0.1 * w  # Break symmetry
        for i in range(2):
            x = 0.25 + i * 0.5 + (-1)**i * offset
            points.append(barycentric_to_cartesian(x, 1-x, 0, A, B, C))
        
        # Row 2: 3 points with symmetry breaking
        y = row_heights[2]
        w = 1.0 - y
        offset = 0.05 * w
        for i in range(3):
            x = 0.166 + i * 0.333 + (-1)**i * offset
            points.append(barycentric_to_cartesian(x, 1-x, 0, A, B, C))
        
        # Row 3: 3 points with symmetry breaking
        y = row_heights[3]
        w = 1.0 - y
        offset = 0.07 * w
        for i in range(3):
            x = 0.166 + i * 0.333 + (-1)**i * offset
            points.append(barycentric_to_cartesian(x, 1-x, 0, A, B, C))
        
        # Bottom row: 2 points with symmetry breaking
        y = row_heights[4]
        w = 1.0 - y
        offset = 0.09 * w
        for i in range(2):
            x = 0.25 + i * 0.5 + (-1)**i * offset
            points.append(barycentric_to_cartesian(x, 1-x, 0, A, B, C))

        return np.array(points)

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

        for _ in range(max_iter):
            # Adaptive noise scaling based on current progress
            noise_magnitude = base_noise * (1.0 - current_score / 0.0365)
            noise_magnitude = max(0.005, min(base_noise, noise_magnitude))

            # Identify critical bottleneck (smallest triangle)
            _, min_indices = get_min_triangle(current)
            
            # Bias selection strongly toward critical points (80% probability)
            if np.random.rand() < 0.8:
                points_to_perturb = min_indices
            else:
                # Randomly select 2-4 points when not focusing on bottleneck
                num_points = random.randint(2, 4)
                points_to_perturb = random.sample(range(11), num_points)

            # Create candidate via barycentric perturbation
            candidate = current.copy()
            for idx in points_to_perturb:
                p = candidate[idx]
                u, v, w = cartesian_to_barycentric(p, A, B, C)
                
                # Apply Gaussian noise in barycentric space
                du = np.random.normal(0, noise_magnitude)
                dv = np.random.normal(0, noise_magnitude)
                u_new, v_new = u + du, v + dv
                
                # Project back to valid simplex
                u_new = max(0, u_new)
                v_new = max(0, v_new)
                total = u_new + v_new
                if total > 1:
                    u_new, v_new = u_new/total, v_new/total
                w_new = 1 - u_new - v_new
                
                # Convert back to Cartesian
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
            
            # Early stopping if we hit near-optimal
            if best_overall_score >= 0.036:
                break

        return best_overall

    # Generate and optimize multiple diverse configurations
    best_points = None
    best_score = -1

    for _ in range(30):  # Reduced restarts due to more expensive optimization
        # Generate base config with slight randomization
        base_points = generate_base_configuration()
        
        # Add small perturbations to create diversity
        for i in range(11):
            u, v, w = cartesian_to_barycentric(base_points[i], A, B, C)
            du = random.uniform(-0.02, 0.02)
            dv = random.uniform(-0.02, 0.02)
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