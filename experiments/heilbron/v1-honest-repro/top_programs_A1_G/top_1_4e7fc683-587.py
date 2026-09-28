# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy import optimize

np.random.seed(42)
random.seed(42)

def area2(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1])

def project_to_triangle(P, A, B, C):
    u_val = area2(P, B, C)
    v_val = area2(P, C, A)
    w_val = area2(P, A, B)
    total = u_val + v_val + w_val
    if abs(total) < 1e-10:
        return (A + B + C) / 3.0
    u_val, v_val, w_val = u_val / total, v_val / total, w_val / total
    
    if u_val < 0:
        u_val = 0
        total2 = v_val + w_val
        if total2 < 1e-10:
            v_val, w_val = 0.5, 0.5
        else:
            v_val, w_val = v_val / total2, w_val / total2
    if v_val < 0:
        v_val = 0
        total2 = u_val + w_val
        if total2 < 1e-10:
            u_val, w_val = 0.5, 0.5
        else:
            u_val, w_val = u_val / total2, w_val / total2
    if w_val < 0:
        w_val = 0
        total2 = u_val + v_val
        if total2 < 1e-10:
            u_val, v_val = 0.5, 0.5
        else:
            u_val, v_val = u_val / total2, v_val / total2
    return u_val * A + v_val * B + w_val * C

def generate_hexagonal_lattice_points(scale, num_points=11):
    # Generate hexagonal lattice points adapted for equilateral triangle
    points = []
    
    # Bottom row
    points.append([0.0 * scale, 0.0 * scale])
    points.append([0.25 * scale, 0.0 * scale])
    points.append([0.5 * scale, 0.0 * scale])
    points.append([0.75 * scale, 0.0 * scale])
    points.append([1.0 * scale, 0.0 * scale])
    
    # Middle row
    points.append([0.125 * scale, 0.2165 * scale])
    points.append([0.375 * scale, 0.2165 * scale])
    points.append([0.625 * scale, 0.2165 * scale])
    points.append([0.875 * scale, 0.2165 * scale])
    
    # Top row
    points.append([0.25 * scale, 0.433 * scale])
    points.append([0.75 * scale, 0.433 * scale])
    
    # Rotate slightly to break symmetry
    theta = np.random.uniform(0, np.pi/6)
    rotation = np.array([
        [np.cos(theta), -np.sin(theta)],
        [np.sin(theta), np.cos(theta)]
    ])
    
    # Translate to center
    center = np.array([0.5 * scale, 0.2887 * scale])
    points = np.array(points) - center
    points = np.dot(points, rotation) + center
    
    return points

def log_sum_exp_min(areas, k=500):
    # Smooth approximation of min(areas) using log-sum-exp
    return -np.log(np.mean(np.exp(-k * np.array(areas)))) / k

def compute_all_triangle_areas(points):
    n = len(points)
    areas = []
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                a = points[i]
                b = points[j]
                c = points[k]
                area_val = abs(area2(a, b, c)) / 2.0
                areas.append(area_val)
    return areas

def smoothed_objective(x):
    pts = x.reshape(11, 2)
    areas = compute_all_triangle_areas(pts)
    return -log_sum_exp_min(areas)

def exact_min_area(x):
    pts = x.reshape(11, 2)
    return -get_smallest_triangle_area(pts)

def constraint(x):
    pts = x.reshape(11, 2)
    constraints = np.zeros(11)
    for i in range(11):
        P = pts[i]
        u_val = area2(P, B, C)
        v_val = area2(P, C, A)
        w_val = area2(P, A, B)
        constraints[i] = min(u_val, v_val, w_val)
    return constraints

def is_resistant(points, num_tests=200, tol=1e-10):
    current_area = get_smallest_triangle_area(points)
    # Adaptive perturbation magnitude based on current solution quality
    base_perturbation = 0.005 * (0.0365 / max(current_area, 0.001))
    
    for _ in range(num_tests):
        idx = np.random.randint(0, 11)
        # Random direction with adaptive magnitude
        angle = np.random.uniform(0, 2*np.pi)
        magnitude = base_perturbation * np.random.uniform(0.5, 1.5)
        perturb = np.array([np.cos(angle), np.sin(angle)]) * magnitude
        
        new_points = points.copy()
        new_points[idx] += perturb
        
        if not is_inside_triangle(new_points[idx:idx+1], A, B, C):
            new_points[idx] = project_to_triangle(new_points[idx], A, B, C)
        
        new_area = get_smallest_triangle_area(new_points)
        if new_area > current_area + tol:
            return False
    return True

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    global A, B, C
    A, B, C = tri
    
    # Generate multiple diverse starting configurations
    scale = 1.5197
    initial_configs = []
    
    # Literature-based configuration
    base_points = [
        [0.000000 * scale, 0.000000 * scale],
        [1.000000 * scale, 0.000000 * scale],
        [0.500000 * scale, 0.866025 * scale],
        [0.250000 * scale, 0.000000 * scale],
        [0.750000 * scale, 0.000000 * scale],
        [0.125000 * scale, 0.216506 * scale],
        [0.875000 * scale, 0.216506 * scale],
        [0.500000 * scale, 0.433013 * scale],
        [0.375000 * scale, 0.649519 * scale],
        [0.625000 * scale, 0.649519 * scale],
        [0.500000 * scale, 0.216506 * scale]
    ]
    initial_configs.append(np.array(base_points))
    
    # Hexagonal lattice variants
    for _ in range(4):
        hex_points = generate_hexagonal_lattice_points(scale)
        initial_configs.append(hex_points)

    best_points = None
    best_area = -np.inf
    
    # Basin-hopping outer loop
    for basin_iter in range(3):
        for config_idx, initial_points in enumerate(initial_configs):
            # Add small noise to break symmetry
            points = initial_points + np.random.uniform(-0.005, 0.005, size=(11, 2))
            
            # Project any out-of-bounds points
            for j in range(11):
                if not is_inside_triangle(points[j:j+1], A, B, C):
                    points[j] = project_to_triangle(points[j], A, B, C)

            # First optimize with smoothed objective for better convergence
            res_smooth = optimize.minimize(
                smoothed_objective,
                points.flatten(),
                method='SLSQP',
                constraints={'type': 'ineq', 'fun': constraint},
                options={'maxiter': 5000, 'ftol': 1e-12}
            )
            
            if res_smooth.success:
                smoothed_points = res_smooth.x.reshape(11, 2)
                smoothed_area = get_smallest_triangle_area(smoothed_points)
                
                # Then refine with exact objective
                res_exact = optimize.minimize(
                    exact_min_area,
                    smoothed_points.flatten(),
                    method='SLSQP',
                    constraints={'type': 'ineq', 'fun': constraint},
                    options={'maxiter': 2000, 'ftol': 1e-12}
                )
                
                if res_exact.success:
                    optimized_points = res_exact.x.reshape(11, 2)
                    area = get_smallest_triangle_area(optimized_points)
                    
                    # Acceptance criteria with temperature-based probability
                    temperature = 0.01 * (3 - basin_iter)
                    if area > best_area or np.random.rand() < np.exp((area - best_area) / temperature):
                        if is_resistant(optimized_points):
                            best_area = area
                            best_points = optimized_points

    # Final validation
    if best_points is None or best_area < 0:
        # Fallback to literature configuration if optimization failed
        best_points = np.array(base_points)
        
    # Ensure all points are inside the triangle
    for j in range(11):
        if not is_inside_triangle(best_points[j:j+1], A, B, C):
            best_points[j] = project_to_triangle(best_points[j], A, B, C)

    return best_points

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