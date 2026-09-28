# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy import optimize

np.random.seed(42)
random.seed(42)

def clip_point(p, A, B, C, s):
    p = np.array(p)
    if p[1] < 0:
        p[1] = 0
    if p[1] > np.sqrt(3) * p[0]:
        x0 = (p[0] + np.sqrt(3) * p[1]) / 4
        y0 = np.sqrt(3) * x0
        p = np.array([x0, y0])
    if p[1] > np.sqrt(3) * (s - p[0]):
        x0 = (p[0] + 3 * s - np.sqrt(3) * p[1]) / 4
        y0 = np.sqrt(3) * (s - x0)
        p = np.array([x0, y0])
    return p

def generate_concentric_triangles(A, B, C):
    # Vertices (3 points)
    points = [A, B, C]
    
    # Edge points at 0.35 and 0.65 positions (6 points)
    ratios = [0.35, 0.65]
    for p1, p2 in [(A, B), (B, C), (C, A)]:
        for r in ratios:
            points.append(p1 + r * (p2 - p1))
    
    # Inner triangle scaled by 0.4 from centroid (3 points)
    centroid = (A + B + C) / 3
    scale = 0.4
    inner_A = centroid + scale * (A - centroid)
    inner_B = centroid + scale * (B - centroid)
    inner_C = centroid + scale * (C - centroid)
    points.extend([inner_A, inner_B, inner_C])
    
    # Final point near centroid
    points.append(centroid * 1.05)
    
    return np.array(points[:11])

def min_distance_constraint(x):
    pts = x.reshape(11, 2)
    dists = np.linalg.norm(pts[:, None] - pts, axis=2)
    np.fill_diagonal(dists, np.inf)
    min_dist = np.min(dists)
    return min_dist - 0.05

def gradient_approximation(x, A, B, C, s, eps=1e-5):
    base_area = get_smallest_triangle_area(x)
    n = len(x)
    grad = np.zeros_like(x)
    
    for i in range(n):
        for j in range(2):
            x_plus = x.copy()
            x_plus[i, j] += eps
            x_plus[i] = clip_point(x_plus[i], A, B, C, s)
            
            if not is_inside_triangle(x_plus[i], A, B, C):
                continue
                
            area_plus = get_smallest_triangle_area(x_plus)
            grad[i, j] = (area_plus - base_area) / eps
    
    return grad

def find_smallest_triangle(points):
    n = len(points)
    min_area = float('inf')
    min_idx = None
    
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                area = 0.5 * abs(
                    points[i, 0] * (points[j, 1] - points[k, 1]) +
                    points[j, 0] * (points[k, 1] - points[i, 1]) +
                    points[k, 0] * (points[i, 1] - points[j, 1])
                )
                if area < min_area:
                    min_area = area
                    min_idx = (i, j, k)
    
    return min_idx, min_area

def robust_objective(x_flat, A, B, C, s):
    x = x_flat.reshape(11, 2)
    base_area = get_smallest_triangle_area(x)
    num_adversaries = 20
    num_failed = 0

    for adv_idx in range(num_adversaries):
        x_pert = x.copy()
        
        strategy = adv_idx % 3
        
        if strategy == 0:  # Gradient-based
            grad = gradient_approximation(x, A, B, C, s)
            step_size = random.uniform(0.02, 0.04)
            x_pert += step_size * grad
            
        elif strategy == 1:  # Random perturbation
            noise = np.random.uniform(-0.03, 0.03, size=x.shape)
            x_pert += noise
            
        else:  # Targeted triangle expansion
            min_tri_idx, _ = find_smallest_triangle(x)
            i, j, k = min_tri_idx
            line_vec = x[k] - x[j]
            perp_vec = np.array([-line_vec[1], line_vec[0]])
            perp_vec = perp_vec / (np.linalg.norm(perp_vec) + 1e-10)
            x_pert[i] += 0.05 * perp_vec

        for i in range(len(x_pert)):
            x_pert[i] = clip_point(x_pert[i], A, B, C, s)
            
        if not is_inside_triangle(x_pert, A, B, C):
            num_failed += 1
            continue
            
        area_pert = get_smallest_triangle_area(x_pert)
        if area_pert <= base_area:
            num_failed += 1

    resistance_score = num_failed / num_adversaries
    return -(0.5 * base_area + 0.5 * resistance_score)

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    s = B[0]

    def constraint1(x):
        pts = x.reshape(11, 2)
        return pts[:, 1]

    def constraint2(x):
        pts = x.reshape(11, 2)
        return np.sqrt(3) * pts[:, 0] - pts[:, 1]

    def constraint3(x):
        pts = x.reshape(11, 2)
        return np.sqrt(3) * (s - pts[:, 0]) - pts[:, 1]

    constraints = [
        {'type': 'ineq', 'fun': constraint1},
        {'type': 'ineq', 'fun': constraint2},
        {'type': 'ineq', 'fun': constraint3},
        {'type': 'ineq', 'fun': min_distance_constraint}
    ]

    best_candidate = None
    best_robust_value = -np.inf

    for _ in range(25):
        initial = generate_concentric_triangles(A, B, C)
        perturbed = initial + np.random.uniform(-0.005, 0.005, size=initial.shape)

        res_main = optimize.minimize(
            lambda x: -get_smallest_triangle_area(x.reshape(11, 2)),
            perturbed.flatten(),
            method='COBYLA',
            constraints=constraints,
            options={'maxiter': 5000}
        )
        
        if not res_main.success:
            candidate = perturbed
        else:
            candidate = res_main.x.reshape(11, 2)

        res_boost = optimize.minimize(
            lambda x: robust_objective(x, A, B, C, s),
            candidate.flatten(),
            method='COBYLA',
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if res_boost.success:
            candidate_boost = res_boost.x.reshape(11, 2)
        else:
            candidate_boost = candidate

        base_area = get_smallest_triangle_area(candidate_boost)
        num_adversaries_test = 20
        improvements = 0
        for _ in range(num_adversaries_test):
            strategy = random.randint(0, 2)
            x_pert = candidate_boost.copy()
            
            if strategy == 0:
                grad = gradient_approximation(candidate_boost, A, B, C, s)
                x_pert += 0.03 * grad
            elif strategy == 1:
                x_pert += np.random.uniform(-0.02, 0.02, size=x_pert.shape)
            else:
                min_tri_idx, _ = find_smallest_triangle(candidate_boost)
                i, j, k = min_tri_idx
                line_vec = candidate_boost[k] - candidate_boost[j]
                perp_vec = np.array([-line_vec[1], line_vec[0]])
                perp_vec = perp_vec / (np.linalg.norm(perp_vec) + 1e-10)
                x_pert[i] += 0.04 * perp_vec

            for i in range(len(x_pert)):
                x_pert[i] = clip_point(x_pert[i], A, B, C, s)
            
            if is_inside_triangle(x_pert, A, B, C):
                area_pert = get_smallest_triangle_area(x_pert)
                if area_pert > base_area:
                    improvements += 1
        
        test_resistance = 1.0 - improvements / num_adversaries_test
        quality = min(base_area / 0.0365, 1.0)
        robust_val = 0.5 * quality + 0.5 * test_resistance
        
        if robust_val > best_robust_value:
            best_robust_value = robust_val
            best_candidate = candidate_boost

    if best_candidate is None:
        return generate_concentric_triangles(A, B, C)
    return best_candidate

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.spatial import Delaunay
import random

np.random.seed(42)

def _d_entrypoint():
    A_big, B_big, C_big = get_unit_triangle()

    def reflect_point(p, a, b):
        """Reflect point p across the line defined by points a and b."""
        ab = b - a
        if np.linalg.norm(ab) < 1e-10:
            return p
        ab_norm = ab / np.linalg.norm(ab)
        ap = p - a
        proj = np.dot(ap, ab_norm) * ab_norm
        return a + 2 * proj - ap

    def project_to_triangle(points, A, B, C):
        """Project points outside the triangle back to the boundary."""
        projected = points.copy()
        for i in range(len(projected)):
            if not is_inside_triangle(projected[i], A, B, C):
                # Find closest point on each edge and take the minimum
                edges = [(A, B), (B, C), (C, A)]
                min_dist = float('inf')
                closest_point = projected[i]
                
                for edge in edges:
                    a, b = edge
                    ab = b - a
                    ap = projected[i] - a
                    t = np.dot(ap, ab) / np.dot(ab, ab)
                    t = max(0, min(1, t))
                    point_on_edge = a + t * ab
                    
                    dist = np.linalg.norm(projected[i] - point_on_edge)
                    if dist < min_dist:
                        min_dist = dist
                        closest_point = point_on_edge
                
                projected[i] = closest_point
        
        return projected

    def apply_symmetry(config):
        """Try reflecting and rotating points and return the best configuration."""
        best_config = config.copy()
        best_score = get_smallest_triangle_area(config)
        
        # For equilateral triangle, symmetry axes go from vertices to midpoints of opposite sides
        mid_BC = (B_big + C_big) / 2
        mid_AC = (A_big + C_big) / 2
        mid_AB = (A_big + B_big) / 2
        
        axes = [
            (A_big, mid_BC),
            (B_big, mid_AC),
            (C_big, mid_AB)
        ]
        
        for a, b in axes:
            reflected = np.array([reflect_point(p, a, b) for p in config])
            reflected = project_to_triangle(reflected, A_big, B_big, C_big)
            score = get_smallest_triangle_area(reflected)
            if score > best_score:
                best_score = score
                best_config = reflected.copy()
        
        # Add rotational symmetry (120° and 240° rotations around centroid)
        centroid = (A_big + B_big + C_big) / 3
        for angle in [120, 240]:
            radians = np.radians(angle)
            rotation_matrix = np.array([
                [np.cos(radians), -np.sin(radians)],
                [np.sin(radians), np.cos(radians)]
            ])
            
            rotated = np.array([centroid + rotation_matrix @ (p - centroid) for p in config])
            rotated = project_to_triangle(rotated, A_big, B_big, C_big)
            score = get_smallest_triangle_area(rotated)
            if score > best_score:
                best_score = score
                best_config = rotated.copy()
        
        return best_config

    def get_critical_triangles(config, threshold_ratio=0.9):
        """Get triangles with area below threshold_ratio * current_best_score."""
        areas = []
        indices = []
        n = config.shape[0]
        current_best_score = get_smallest_triangle_area(config)
        
        for i in range(n):
            for j in range(i + 1, n):
                for l in range(j + 1, n):
                    p1, p2, p3 = config[i], config[j], config[l]
                    area2_val = abs(p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1]))
                    areas.append(area2_val)
                    indices.append((i, j, l))
        
        # Sort by area
        sorted_indices = [idx for _, idx in sorted(zip(areas, indices))]
        
        # Only return triangles below threshold
        threshold = threshold_ratio * current_best_score
        critical_indices = []
        for idx in sorted_indices:
            i, j, l = idx
            p1, p2, p3 = config[i], config[j], config[l]
            area_val = abs(p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1])) / 2
            if area_val < threshold:
                critical_indices.append(idx)
        
        # If no triangles below threshold, return the smallest one
        if not critical_indices:
            return [sorted_indices[0]]
        
        return critical_indices

    def generate_adaptive_directions(triangle_points, num_directions=8):
        """Generate directions based on the geometry of the triangle."""
        directions = []
        
        # Get the three edges of the triangle
        p1, p2, p3 = triangle_points
        edges = [(p2 - p1), (p3 - p2), (p1 - p3)]
        
        # For each edge, compute normal directions
        for edge in edges:
            if np.linalg.norm(edge) > 1e-10:
                normal = np.array([-edge[1], edge[0]])
                normal = normal / np.linalg.norm(normal)
                
                # Add the normal and some variations around it
                for i in range(num_directions // 3):
                    angle = (i - num_directions // 6) * np.pi / (num_directions // 3)
                    rotated = np.array([
                        normal[0] * np.cos(angle) - normal[1] * np.sin(angle),
                        normal[0] * np.sin(angle) + normal[1] * np.cos(angle)
                    ])
                    directions.append(rotated)
        
        # Add some random exploration directions
        for _ in range(num_directions - len(directions)):
            angle = np.random.uniform(0, 2 * np.pi)
            directions.append(np.array([np.cos(angle), np.sin(angle)]))
        
        return directions

    def move_point_inside(point, direction, step, A, B, C):
        candidate = point + step * direction
        if is_inside_triangle(candidate, A, B, C):
            return candidate, step
        else:
            # Binary search to find the maximum valid step
            low, high = 0.0, step
            for _ in range(15):
                mid = (low + high) / 2
                candidate = point + mid * direction
                if is_inside_triangle(candidate, A, B, C):
                    low = mid
                else:
                    high = mid
            return point + low * direction, low

    def improve(points: np.ndarray) -> np.ndarray:
        # Parameters for simulated annealing
        initial_temp = 0.5
        cooling_rate = 0.95
        min_temp = 1e-6
        step_size_factor = 10.0

        # Parameters for multi-triangle targeting
        threshold_ratio = 0.9
        symmetry_prob = 0.3

        # Multi-start parameters
        n_starts = 5
        perturbation_scale = 0.05

        best_overall = points.copy()
        best_overall_score = get_smallest_triangle_area(points)

        for start in range(n_starts):
            # Create a perturbed starting point
            if start == 0:
                current = points.copy()
            else:
                current = points.copy() + np.random.uniform(-perturbation_scale, perturbation_scale, points.shape)
                # Project back to triangle if needed
                for i in range(len(current)):
                    if not is_inside_triangle(current[i], A_big, B_big, C_big):
                        current[i] = project_to_triangle(np.array([current[i]]), A_big, B_big, C_big)[0]
            
            best = current.copy()
            current_score = get_smallest_triangle_area(current)
            best_score = current_score
            
            # Simulated annealing main loop
            temp = initial_temp
            while temp > min_temp:
                # Use adaptive triangle selection
                critical_triangles = get_critical_triangles(current, threshold_ratio)
                triangle_indices = random.choice(critical_triangles)
                
                # Get the triangle points
                triangle_points = [current[i] for i in triangle_indices]
                
                # Generate adaptive directions
                directions = generate_adaptive_directions(triangle_points)
                
                # Try moving each point in the triangle
                for idx in triangle_indices:
                    for direction in directions:
                        # Use step_size_factor to decouple step size from temperature
                        step_size = step_size_factor * temp
                        while step_size > 1e-5:
                            candidate_points = current.copy()
                            new_point, actual_step = move_point_inside(
                                current[idx], direction, step_size, A_big, B_big, C_big
                            )
                            candidate_points[idx] = new_point
                            
                            candidate_score = get_smallest_triangle_area(candidate_points)
                            
                            # Simulated annealing acceptance criterion
                            delta = candidate_score - current_score
                            if delta > 0 or (delta > -1e-7 and np.random.rand() < np.exp(delta / temp)):
                                current = candidate_points
                                current_score = candidate_score
                                if current_score > best_score:
                                    best = current.copy()
                                    best_score = current_score
                                break  # Move to next direction after accepting a move
                            
                            if actual_step < step_size * 0.9:  # If we hit the boundary
                                break
                            
                            step_size *= 0.5  # Try smaller step
                
                # Periodically try symmetry-based improvements
                if np.random.rand() < symmetry_prob:
                    symmetric_points = apply_symmetry(current)
                    symmetric_score = get_smallest_triangle_area(symmetric_points)
                    if symmetric_score > current_score:
                        current = symmetric_points
                        current_score = symmetric_score
                        if current_score > best_score:
                            best = current.copy()
                            best_score = current_score
                
                # Cool the temperature
                temp *= cooling_rate
            
            # Update overall best
            if best_score > best_overall_score:
                best_overall = best.copy()
                best_overall_score = best_score

        return best_overall

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)