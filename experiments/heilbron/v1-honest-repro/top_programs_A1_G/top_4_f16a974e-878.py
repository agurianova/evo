# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area
from scipy.optimize import differential_evolution, basinhopping

np.random.seed(42)
A, B, C = get_unit_triangle()

# Convert barycentric (s0,t0) representation to Cartesian coordinates
def to_cartesian(x):
    points = []
    for i in range(11):
        s0 = x[2*i]
        t0 = x[2*i+1]
        s = s0
        t = t0 * (1 - s0)
        P = (1 - s - t) * A + s * B + t * C
        points.append(P)
    return np.array(points)

def _g_entrypoint() -> np.ndarray:
    # Generate 10 initial configurations (7 randomized, 3 near-optimal)
    initial_configs = []
    phi = (1 + np.sqrt(5)) / 2  # Golden ratio
    
    for idx in range(10):
        # 30% near-optimal configs use fixed phase and minimal jitter
        is_near_optimal = idx < 3
        phase = 0.0 if is_near_optimal else np.random.rand()
        jitter_scale = 0.001 if is_near_optimal else 0.01  # 0.1% vs 1%
        
        row_counts = [3, 3, 3, 2]  # Literature-optimal row distribution
        points_bary = []  # Store (s0, t0) for each point
        cumulative = 0
        
        for i, num in enumerate(row_counts):
            # Compute row height using area fraction
            area_frac = (cumulative + 0.5 * num) / 11.0
            c = 1 - np.sqrt(1 - area_frac)  # Barycentric height (gamma)
            
            for j in range(num):
                # Golden-ratio spacing with phase
                u_frac = (j * phi + phase) % 1
                b = u_frac * (1 - c)  # Barycentric coordinate for B
                
                # Convert to optimization variables
                s0 = b
                t0 = c / (1 - b) if (1 - b) > 1e-5 else 0.5
                
                # Apply adaptive jitter
                s0 += (np.random.rand() - 0.5) * jitter_scale
                t0 += (np.random.rand() - 0.5) * jitter_scale
                
                # Enforce boundary constraints
                s0 = np.clip(s0, 1e-5, 1-1e-5)
                t0 = np.clip(t0, 1e-5, 1-1e-5)
                points_bary.append([s0, t0])
            
            cumulative += num
        
        initial_configs.append(np.array(points_bary).flatten())

    # Objective function (minimize = -min_area)
    def objective(x):
        pts = to_cartesian(x)
        return -get_smallest_triangle_area(pts)

    # Optimization bounds for all 22 barycentric variables
    bounds = [(1e-5, 1-1e-5)] * 22
    best_min_area = -np.inf
    best_config_cart = None

    # Run optimization for each initial configuration
    for x0 in initial_configs:
        # Global search with dimension-matched population
        de_result = differential_evolution(
            objective,
            bounds,
            maxiter=1000,
            popsize=11,  # Corrected from 3 to dimension-matched size
            tol=1e-5,
            x0=x0,
            seed=42
        )
        
        # Basin exploration to escape shallow minima
        bh_result = basinhopping(
            objective,
            de_result.x,
            niter=100,
            stepsize=0.01,
            minimizer_kwargs={'method': 'L-BFGS-B', 'bounds': bounds},
            seed=42
        )
        
        # Convert to Cartesian and validate
        config_cart = to_cartesian(bh_result.x)
        min_area = -bh_result.fun
        
        if min_area > best_min_area:
            best_min_area = min_area
            best_config_cart = config_cart

    return best_config_cart

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