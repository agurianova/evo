# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy import optimize

np.random.seed(42)
random.seed(42)

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Precomputed edge vectors for efficient constraints
    ab = B - A
    bc = C - B
    ca = A - C
    
    # Constraint function using precomputed vectors
    def constraint_func(x):
        pts = x.reshape(11, 2)
        constraints = []
        for P in pts:
            # AB edge: (B-A) × (P-A) >= 0
            val_ab = ab[0]*(P[1]-A[1]) - ab[1]*(P[0]-A[0])
            constraints.append(val_ab)
            # BC edge: (C-B) × (P-B) >= 0
            val_bc = bc[0]*(P[1]-B[1]) - bc[1]*(P[0]-B[0])
            constraints.append(val_bc)
            # CA edge: (A-C) × (P-C) >= 0
            val_ca = ca[0]*(P[1]-C[1]) - ca[1]*(P[0]-C[0])
            constraints.append(val_ca)
        return np.array(constraints)

    cons = {'type': 'ineq', 'fun': constraint_func}

    # Generate diverse starting configurations
    def generate_starting_points():
        configs = []
        
        # Base barycentric configuration with small perturbations
        base_bary = [
            [0.0000, 0.0000, 1.0000],
            [0.0000, 1.0000, 0.0000],
            [1.0000, 0.0000, 0.0000],
            [0.2000, 0.2000, 0.6000],
            [0.2000, 0.6000, 0.2000],
            [0.6000, 0.2000, 0.2000],
            [0.1000, 0.4500, 0.4500],
            [0.4500, 0.1000, 0.4500],
            [0.4500, 0.4500, 0.1000],
            [0.0500, 0.3000, 0.6500],
            [0.0500, 0.6500, 0.3000]
        ]
        
        # Add perturbed base config
        perturbed = []
        for bary in base_bary:
            a, b, c = bary
            # Add small random perturbation (preserving barycentric sum)
            noise = np.random.uniform(-0.01, 0.01, 3)
            noise[2] = -noise[0] - noise[1]  # Maintain sum=1
            a += noise[0]
            b += noise[1]
            c += noise[2]
            # Clamp to valid barycentric
            a = max(0, min(1, a))
            b = max(0, min(1, b))
            c = 1 - a - b
            P = a * A + b * B + c * C
            perturbed.append(P)
        configs.append(np.array(perturbed))

        # Generate grid-based configurations with jitter
        for _ in range(4):
            grid_points = []
            # Create triangular grid pattern
            rows = 4
            for i in range(rows):
                for j in range(i+1):
                    # Barycentric coordinates for grid point
                    a = (rows - i - 1) / rows
                    b = (i - j) / rows
                    c = j / rows
                    # Add jitter
                    jitter = np.random.uniform(-0.05, 0.05, 3)
                    jitter[2] = -jitter[0] - jitter[1]
                    a = max(0, min(1, a + jitter[0]))
                    b = max(0, min(1, b + jitter[1]))
                    c = 1 - a - b
                    P = a * A + b * B + c * C
                    grid_points.append(P)
            # Fill remaining points with random valid points
            while len(grid_points) < 11:
                r1, r2 = np.random.random(2)
                a = 1 - np.sqrt(r1)
                b = np.sqrt(r1) * (1 - r2)
                c = np.sqrt(r1) * r2
                P = a * A + b * B + c * C
                grid_points.append(P)
            configs.append(np.array(grid_points[:11]))
        
        return configs

    # Smoothed objective function with adaptive k
    def smoothed_objective(x, current_iter):
        k = max(1, 10 - current_iter // 3)  # Adaptive k scheduling
        pts = x.reshape(11, 2)
        n = 11
        areas = []
        for i in range(n):
            for j in range(i+1, n):
                for l in range(j+1, n):
                    dx1 = pts[j,0] - pts[i,0]
                    dy1 = pts[j,1] - pts[i,1]
                    dx2 = pts[l,0] - pts[i,0]
                    dy2 = pts[l,1] - pts[i,1]
                    area = 0.5 * abs(dx1*dy2 - dx2*dy1)
                    areas.append(area)
        areas = np.array(areas)
        sorted_areas = np.sort(areas)
        return -np.sum(sorted_areas[:k])

    # PHASE 1: Optimized with adaptive k and restarts
    best_overall = None
    best_min_area = 0.0
    
    for start_config in generate_starting_points():
        current_best = start_config.copy()
        current_min = get_smallest_triangle_area(current_best)
        stagnation_count = 0

        for iter1 in range(30):
            # Logarithmic adaptive scale
            gap = max(0, (0.0365 - current_min) / 0.0365)
            scale = 0.1 * np.exp(-10 * gap)
            
            # Restart if stuck
            if stagnation_count >= 5:
                scale *= 10  # Larger perturbation
                stagnation_count = 0

            perturbation = scale * np.random.uniform(-1, 1, 22)
            x0 = current_best.flatten() + perturbation

            res = optimize.minimize(
                lambda x: smoothed_objective(x, iter1),
                x0,
                method='COBYLA',
                constraints=cons,
                options={'maxiter': 10000, 'tol': 1e-8}
            )
            
            if res.success:
                optimized = res.x.reshape(11, 2)
                min_area_val = get_smallest_triangle_area(optimized)
                if min_area_val > current_min:
                    current_best = optimized
                    current_min = min_area_val
                    stagnation_count = 0
                else:
                    stagnation_count += 1

        # PHASE 2: True min area optimization with restarts
        stagnation_count = 0
        for _ in range(20):
            gap = max(0, (0.0365 - current_min) / 0.0365)
            scale = 0.1 * np.exp(-10 * gap)
            
            if stagnation_count >= 5:
                scale *= 10
                stagnation_count = 0

            perturbation = scale * np.random.uniform(-1, 1, 22)
            x0 = current_best.flatten() + perturbation

            def objective(x):
                pts = x.reshape(11, 2)
                return -get_smallest_triangle_area(pts)

            res = optimize.minimize(
                objective,
                x0,
                method='COBYLA',
                constraints=cons,
                options={'maxiter': 10000, 'tol': 1e-8}
            )
            
            if res.success:
                optimized = res.x.reshape(11, 2)
                min_area_val = get_smallest_triangle_area(optimized)
                if min_area_val > current_min:
                    current_best = optimized
                    current_min = min_area_val
                    stagnation_count = 0
                else:
                    stagnation_count += 1

        if current_min > best_min_area:
            best_overall = current_best
            best_min_area = current_min

    # MULTI-SCALE RESISTANCE VERIFICATION
    points = best_overall.copy()
    step_sizes = [1e-2, 5e-3, 1e-3, 5e-4, 1e-4, 5e-5, 1e-5]
    directions = [(1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,-1), (1,-1), (-1,1)]

    for step_size in step_sizes:
        improved = True
        while improved:
            improved = False
            best_improvement = 0
            best_point_idx = None
            best_direction = None
            current_min = get_smallest_triangle_area(points)

            for i in range(11):
                for dx, dy in directions:
                    new_points = points.copy()
                    new_points[i, 0] += dx * step_size
                    new_points[i, 1] += dy * step_size

                    # Check containment
                    if not is_inside_triangle(new_points, A, B, C):
                        continue

                    # Check distinctness
                    dists = np.linalg.norm(new_points[:, None, :] - new_points[None, :, :], axis=2)
                    np.fill_diagonal(dists, np.inf)
                    if np.min(dists) < 1e-6:
                        continue

                    new_min = get_smallest_triangle_area(new_points)
                    if new_min > current_min:
                        improvement = new_min - current_min
                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_point_idx = i
                            best_direction = (dx, dy)

            if best_improvement > 0:
                points[best_point_idx, 0] += best_direction[0] * step_size
                points[best_point_idx, 1] += best_direction[1] * step_size
                improved = True

    return points

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