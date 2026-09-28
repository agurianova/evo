import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get the unit triangle vertices
    A, B, C = get_unit_triangle()
    
    # Precompute side length for barycentric scaling
    side_length = np.linalg.norm(B - A)
    
    # Helper functions for barycentric conversion
    denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
    
    def to_bary(p):
        u = ((B[1] - C[1]) * (p[0] - C[0]) + (C[0] - B[0]) * (p[1] - C[1])) / denom
        v = ((C[1] - A[1]) * (p[0] - C[0]) + (A[0] - C[0]) * (p[1] - C[1])) / denom
        return u, v
    
    def to_cart(u, v):
        w = 1 - u - v
        return u * A + v * B + w * C
    
    def clamp_bary(u, v):
        """Clamp barycentric coordinates to be inside the triangle."""
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))
        if u + v > 1.0:
            scale = 1.0 / (u + v)
            u *= scale
            v *= scale
        return u, v
    
    def calculate_max_valid_step(point, direction, A, B, C):
        """Calculate maximum step size before hitting triangle boundary."""
        # Convert direction to unit vector
        dir_norm = np.linalg.norm(direction)
        if dir_norm < 1e-10:
            return 0.0
        direction = direction / dir_norm
        
        # Check distance to each edge
        max_step = float('inf')
        
        # Edge AB (from A to B)
        edge_vec = B - A
        normal = np.array([-edge_vec[1], edge_vec[0]])
        normal = normal / np.linalg.norm(normal)
        dist_to_edge = np.dot(C - point, normal)
        if dist_to_edge > 0:
            step_to_edge = dist_to_edge / max(1e-10, np.dot(direction, normal))
            if np.dot(direction, normal) > 0:
                max_step = min(max_step, step_to_edge)

        # Edge BC (from B to C)
        edge_vec = C - B
        normal = np.array([-edge_vec[1], edge_vec[0]])
        normal = normal / np.linalg.norm(normal)
        dist_to_edge = np.dot(A - point, normal)
        if dist_to_edge > 0:
            step_to_edge = dist_to_edge / max(1e-10, np.dot(direction, normal))
            if np.dot(direction, normal) > 0:
                max_step = min(max_step, step_to_edge)

        # Edge CA (from C to A)
        edge_vec = A - C
        normal = np.array([-edge_vec[1], edge_vec[0]])
        normal = normal / np.linalg.norm(normal)
        dist_to_edge = np.dot(B - point, normal)
        if dist_to_edge > 0:
            step_to_edge = dist_to_edge / max(1e-10, np.dot(direction, normal))
            if np.dot(direction, normal) > 0:
                max_step = min(max_step, step_to_edge)

        return max(0.0, max_step - 1e-10)

    def build_triangle_dependencies(n):
        """Create mapping from point index to affected triangles."""
        point_to_triangles = [[] for _ in range(n)]
        triangles = []
        
        idx = 0
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    triangles.append((i, j, k))
                    point_to_triangles[i].append(idx)
                    point_to_triangles[j].append(idx)
                    point_to_triangles[k].append(idx)
                    idx += 1
                    
        return triangles, point_to_triangles

    def enforce_symmetry(points):
        """Enforce 3-fold rotational symmetry around triangle centroid."""
        centroid = (A + B + C) / 3.0
        
        # For equilateral triangle, rotation matrix for 120 degrees
        cos120 = -0.5
        sin120 = np.sqrt(3)/2
        rot_matrix = np.array([[cos120, -sin120], [sin120, cos120]])
        
        # Identify points near symmetry axes
        axis_points = []
        symmetric_points = []
        
        for i, p in enumerate(points):
            # Distance to each symmetry axis (simplified)
            d1 = np.linalg.norm(p - A)
            d2 = np.linalg.norm(p - B)
            d3 = np.linalg.norm(p - C)
            min_dist = min(d1, d2, d3)
            
            # Heuristic for axis points (near medians)
            if min_dist < 0.3 * side_length:
                axis_points.append(i)
            else:
                symmetric_points.append(i)
        
        new_points = points.copy()
        
        # Process symmetric triplets (3 groups of 3 points)
        if len(symmetric_points) >= 9:
            for group in range(3):
                idxs = symmetric_points[group*3:group*3+3]
                pts = [points[i] for i in idxs]
                
                # Calculate symmetric positions
                avg = np.mean(pts, axis=0)
                
                # Project to centroid-relative coordinates
                rel_pts = [p - centroid for p in pts]
                
                # Enforce symmetry by averaging rotations
                new_rel_pts = []
                for i in range(3):
                    rotated = np.dot(rot_matrix, rel_pts[(i+1)%3])
                    new_rel = (rel_pts[i] + rotated) / 2.0
n                    new_rel_pts.append(new_rel)
                
                # Convert back to absolute coordinates
                for i, idx in enumerate(idxs):
                    new_points[idx] = centroid + new_rel_pts[i]
        
        # Process axis points (should be 2)
        if len(axis_points) >= 2:
            # Average positions to maintain symmetry
            avg_pos = (points[axis_points[0]] + points[axis_points[1]]) / 2.0
            for idx in axis_points:
                new_points[idx] = avg_pos

        # Ensure all points are inside the triangle
        if is_inside_triangle(new_points, A, B, C):
            return new_points
        return points

    def get_local_min_distance(point_idx, points, triangle_areas, point_to_triangles):
        """Calculate minimum distance constraint based on local triangle areas."""
        # Get all triangles containing this point
        affected_triangles = point_to_triangles[point_idx]
        
        if not affected_triangles:
            return 0.008  # Default
        
        # Calculate average area of surrounding triangles
        total_area = 0.0
        count = 0
        for tri_idx in affected_triangles:
            total_area += triangle_areas[tri_idx]
            count += 1
        
        avg_area = total_area / count
        
        # Scale minimum distance based on average area
        # Larger areas allow closer points
        min_dist = 0.005 + 0.02 * (1.0 - avg_area / 0.04)  # Scale between 0.005 and 0.025
        return max(0.005, min(0.025, min_dist))

    def generate_initial_configuration():
        """Generate randomized symmetric initial configuration."""
        points = []
        
        # Centroid for symmetry
        centroid = (A + B + C) / 3.0
        
        # Generate symmetric patterns
        # 3 symmetric groups of 3 points (9 points total)
        for group in range(3):
            # Random radius and angle
            radius = np.random.uniform(0.15, 0.3)
            angle = np.random.uniform(0, 2*np.pi/3)
            
            # First point in group
            dx = radius * np.cos(angle)
            dy = radius * np.sin(angle)
            p1 = centroid + np.array([dx, dy])
            
            # Second point (120° rotation)
            angle2 = angle + 2*np.pi/3
            dx2 = radius * np.cos(angle2)
            dy2 = radius * np.sin(angle2)
            p2 = centroid + np.array([dx2, dy2])
            
            # Third point (240° rotation)
            angle3 = angle + 4*np.pi/3
            dx3 = radius * np.cos(angle3)
            dy3 = radius * np.sin(angle3)
            p3 = centroid + np.array([dx3, dy3])
            
            # Add to points if valid
            for p in [p1, p2, p3]:
                if is_inside_triangle(np.array([p]), A, B, C):
                    points.append(p)
                else:
                    # Fallback: near centroid
                    points.append(centroid + np.random.uniform(-0.05, 0.05, 2))

        # 2 axis points (on symmetry axes)
        for _ in range(2):
            # Random position along median
            t = np.random.uniform(0.2, 0.8)
            # Pick a random median (A-centroid, B-centroid, C-centroid)
            if np.random.random() < 0.33:
                p = A + t * (centroid - A)
            elif np.random.random() < 0.66:
                p = B + t * (centroid - B)
            else:
                p = C + t * (centroid - C)
            
            # Small perturbation perpendicular to median
            median_dir = p - centroid
            perp_dir = np.array([-median_dir[1], median_dir[0]])
            perp_dir = perp_dir / np.linalg.norm(perp_dir) * np.random.uniform(-0.03, 0.03)
            p = p + perp_dir
            
            points.append(p)

        # Ensure we have exactly 11 points
        if len(points) < 11:
            while len(points) < 11:
                # Add random interior points
                u = np.random.uniform(0.2, 0.8)
                v = np.random.uniform(0.2, 0.8)
                if u + v > 1.0:
                    u, v = v, u
                points.append(to_cart(u, v))
        
        return np.array(points[:11])

    def optimize_configuration(initial_points):
        """Optimize a single configuration using resistance-aware search."""
        n = 11
        points = initial_points.copy()
        best_points = points.copy()
        best_score = get_smallest_triangle_area(best_points)
        
        # Build triangle dependency structure
        triangles, point_to_triangles = build_triangle_dependencies(n)
        num_triangles = len(triangles)
        
        # Initialize triangle area cache and vulnerability weights
        triangle_areas = np.zeros(num_triangles)
        # Initialize vulnerability weights (higher = more vulnerable to attacks)
        triangle_vulnerability = np.ones(num_triangles) * 0.5
        
        for idx, (i, j, k) in enumerate(triangles):
            x1, y1 = points[i]
            x2, y2 = points[j]
            x3, y3 = points[k]
            area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
            triangle_areas[idx] = area
        
        # Convert all points to barycentric for internal processing
        bary_points = np.array([to_bary(p) for p in points])
        
        # Adaptive search parameters
        initial_step = 0.05
        step_size = initial_step
        stagnation_count = 0
        max_iterations = 300
        tol = 1e-10
        improvement_history = []
        base_restart_threshold = 25
        
        # Track resistance metric (higher = more vulnerable)
        resistance_metric = 0.0

        for _ in range(max_iterations):
            # Find minimal area triangles from cache
            min_area = np.min(triangle_areas)
            min_triplets = []
            
            for idx, area in enumerate(triangle_areas):
                if abs(area - min_area) < tol:
                    min_triplets.append(triangles[idx])
            
            if not min_triplets:
                break

            # Count vertex frequencies in minimal triangles with vulnerability weighting
            freq = [0] * n
            for idx, triplet in enumerate(triangles):
                if triplet in min_triplets:
                    # Weight by vulnerability (higher vulnerability = more weight)
                    weight = triangle_vulnerability[idx]
                    for point_idx in triplet:
                        freq[point_idx] += weight
            
            # Sort vertices by frequency (descending)
            candidate_indices = sorted(range(n), key=lambda i: -freq[i])
            
            # Try to improve by perturbing critical vertices
            improved = False
            
            # First try analytical gradient moves on minimal triangles
            for triplet in min_triplets:
                i, j, k = triplet
                p_i, p_j, p_k = points[i], points[j], points[k]
                
                # Calculate gradient for area increase (0.5 * |(C-B) × (A-B)|)
                grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                
                # Normalize gradients
                norm_i = np.linalg.norm(grad_i)
                norm_j = np.linalg.norm(grad_j)
                norm_k = np.linalg.norm(grad_k)
                
                if norm_i > 0: grad_i = grad_i / norm_i
                if norm_j > 0: grad_j = grad_j / norm_j
                if norm_k > 0: grad_k = grad_k / norm_k

                # Calculate maximum valid step size for each point
                max_step_i = calculate_max_valid_step(p_i, grad_i, A, B, C)
                max_step_j = calculate_max_valid_step(p_j, grad_j, A, B, C)
                max_step_k = calculate_max_valid_step(p_k, grad_k, A, B, C)
                
                # Use minimum valid step to maintain triangle shape
                max_valid_step = min(max_step_i, max_step_j, max_step_k, step_size)

                # Create candidate by moving points along gradients
                candidate = points.copy()
                candidate[i] += grad_i * max_valid_step
                candidate[j] += grad_j * max_valid_step
                candidate[k] += grad_k * max_valid_step

                # Check minimum distance to other points
                too_close = False
                for idx1 in [i, j, k]:
                    min_distance = get_local_min_distance(idx1, candidate, triangle_areas, point_to_triangles)
                    for idx2 in range(n):
                        if idx1 == idx2:
                            continue
                        dist = np.linalg.norm(candidate[idx1] - candidate[idx2])
                        if dist < min_distance:
                            too_close = True
                            break
                    if too_close:
                        break
                
                if too_close or not is_inside_triangle(candidate, A, B, C):
                    continue

                # Update only triangles affected by changed points
                affected_triangles = set()
                for idx in [i, j, k]:
                    affected_triangles.update(point_to_triangles[idx])
                
                # Save original areas for rollback
                original_areas = {idx: triangle_areas[idx] for idx in affected_triangles}
                
                # Update triangle areas cache
                for idx in affected_triangles:
                    tri = triangles[idx]
                    x1, y1 = candidate[tri[0]]
                    x2, y2 = candidate[tri[1]]
                    x3, y3 = candidate[tri[2]]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    triangle_areas[idx] = area
                
                # Get new min area from updated cache
                new_min_area = np.min(triangle_areas)
                
                # Rollback cache changes
                for idx, area in original_areas.items():
                    triangle_areas[idx] = area

                if new_min_area > best_score:
                    points = candidate
                    best_points = points.copy()
                    best_score = new_min_area
                    
                    # Update cache with actual changes
                    for idx in affected_triangles:
                        tri = triangles[idx]
                        x1, y1 = points[tri[0]]
                        x2, y2 = points[tri[1]]
                        x3, y3 = points[tri[2]]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        triangle_areas[idx] = area
                    
                    # Update barycentric representation for changed points
                    for idx in [i, j, k]:
                        bary_points[idx] = to_bary(points[idx])
                    
                    improved = True
                    stagnation_count = 0
                    resistance_metric = max(0, resistance_metric - 2)  # Improved resistance
                    
                    # Record improvement for parameter adaptation
                    improvement_history.append(new_min_area - best_score)
                    if len(improvement_history) > 10:
                        improvement_history.pop(0)
                    
                    # Update triangle vulnerability (decay all, then increase for improved triangles)
                    triangle_vulnerability *= 0.95  # Exponential decay
                    for idx in affected_triangles:
                        if triangle_areas[idx] > original_areas[idx]:
                            triangle_vulnerability[idx] = min(2.0, triangle_vulnerability[idx] * 1.1)
                    
                    break

            if improved:
                # Adaptive step growth based on improvement magnitude
                if improvement_history:
                    avg_improvement = np.mean(improvement_history)
                    growth_factor = 1.0 + min(0.05, avg_improvement * 50)
                    step_size = min(step_size * growth_factor, initial_step * 2.0)
                else:
                    step_size = min(step_size * 1.05, initial_step * 2.0)
                continue

            # If gradient moves didn't work, try orthogonal perturbations
            if not improved and np.random.random() < 0.3:
                for triplet in min_triplets:
                    i, j, k = triplet
                    p_i, p_j, p_k = points[i], points[j], points[k]
                    
                    # Calculate gradient as before
                    grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                    grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                    grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                    
                    # Create orthogonal perturbation (rotate 90 degrees)
                    ortho_i = np.array([-grad_i[1], grad_i[0]])
                    ortho_j = np.array([-grad_j[1], grad_j[0]])
                    ortho_k = np.array([-grad_k[1], grad_k[0]])
                    
                    # Normalize and scale
                    norm_i = np.linalg.norm(ortho_i)
                    norm_j = np.linalg.norm(ortho_j)
                    norm_k = np.linalg.norm(ortho_k)
                    
                    if norm_i > 0: ortho_i = ortho_i / norm_i
                    if norm_j > 0: ortho_j = ortho_j / norm_j
                    if norm_k > 0: ortho_k = ortho_k / norm_k

                    # Calculate maximum valid step size
                    max_step_i = calculate_max_valid_step(p_i, ortho_i, A, B, C)
                    max_step_j = calculate_max_valid_step(p_j, ortho_j, A, B, C)
                    max_step_k = calculate_max_valid_step(p_k, ortho_k, A, B, C)
                    max_valid_step = min(max_step_i, max_step_j, max_step_k, step_size * 0.7)

                    # Create candidate
                    candidate = points.copy()
                    candidate[i] += ortho_i * max_valid_step
                    candidate[j] += ortho_j * max_valid_step
                    candidate[k] += ortho_k * max_valid_step

                    # Check minimum distance
                    too_close = False
                    for idx1 in [i, j, k]:
                        min_distance = get_local_min_distance(idx1, candidate, triangle_areas, point_to_triangles)
                        for idx2 in range(n):
                            if idx1 == idx2:
                                continue
                            dist = np.linalg.norm(candidate[idx1] - candidate[idx2])
                            if dist < min_distance:
                                too_close = True
                                break
                        if too_close:
                            break
                    
                    if too_close or not is_inside_triangle(candidate, A, B, C):
                        continue

                    # Update only affected triangles
                    affected_triangles = set()
                    for idx in [i, j, k]:
                        affected_triangles.update(point_to_triangles[idx])
                    
                    original_areas = {idx: triangle_areas[idx] for idx in affected_triangles}
                    
                    # Update cache
                    for idx in affected_triangles:
                        tri = triangles[idx]
                        x1, y1 = candidate[tri[0]]
                        x2, y2 = candidate[tri[1]]
                        x3, y3 = candidate[tri[2]]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        triangle_areas[idx] = area
                    
                    new_min_area = np.min(triangle_areas)
                    
                    # Rollback cache
                    for idx, area in original_areas.items():
                        triangle_areas[idx] = area
                        
                    if new_min_area > best_score:
                        points = candidate
                        best_points = points.copy()
                        best_score = new_min_area
                        
                        # Update cache with actual changes
                        for idx in affected_triangles:
                            tri = triangles[idx]
                            x1, y1 = points[tri[0]]
                            x2, y2 = points[tri[1]]
                            x3, y3 = points[tri[2]]
                            area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                            triangle_areas[idx] = area
                        
                        # Update barycentric representation
                        for idx in [i, j, k]:
                            bary_points[idx] = to_bary(points[idx])
                        
                        improved = True
                        stagnation_count = 0
                        resistance_metric = max(0, resistance_metric - 1)
                        
                        # Record improvement
                        improvement_history.append(new_min_area - best_score)
                        if len(improvement_history) > 10:
                            improvement_history.pop(0)
                        
                        # Update triangle vulnerability
                        triangle_vulnerability *= 0.95
                        for idx in affected_triangles:
                            if triangle_areas[idx] > original_areas[idx]:
                                triangle_vulnerability[idx] = min(2.0, triangle_vulnerability[idx] * 1.05)
                        
                        break

            if improved:
                # Adaptive step growth
                if improvement_history:
                    avg_improvement = np.mean(improvement_history)
                    growth_factor = 1.0 + min(0.05, avg_improvement * 50)
                    step_size = min(step_size * growth_factor, initial_step * 2.0)
                else:
                    step_size = min(step_size * 1.05, initial_step * 2.0)
                continue

            # If gradient and orthogonal moves didn't work, try barycentric perturbations
            for idx in candidate_indices:
                if freq[idx] == 0:
                    break

                # Get current barycentric coordinates
                u, v = bary_points[idx]
                
                # Try multiple perturbations
                for _ in range(10):
                    du = np.random.normal(0, step_size * 0.5)
                    dv = np.random.normal(0, step_size * 0.5)
                    u_new, v_new = clamp_bary(u + du, v + dv)
                    
                    # Convert back to Cartesian
                    candidate = points.copy()
                    candidate[idx] = to_cart(u_new, v_new)
                    
                    # Check minimum distance to other points
                    too_close = False
                    min_distance = get_local_min_distance(idx, candidate, triangle_areas, point_to_triangles)
                    for i in range(n):
                        if i == idx:
                            continue
                        dist = np.linalg.norm(candidate[i] - candidate[idx])
                        if dist < min_distance:
                            too_close = True
                            break
                    
                    if too_close or not is_inside_triangle(candidate, A, B, C):
                        continue

                    # Update only triangles affected by changed point
                    affected_triangles = point_to_triangles[idx]
                    original_areas = {tri_idx: triangle_areas[tri_idx] for tri_idx in affected_triangles}
                    
                    # Update triangle areas cache
                    for tri_idx in affected_triangles:
                        i, j, k = triangles[tri_idx]
                        x1, y1 = candidate[i]
                        x2, y2 = candidate[j]
                        x3, y3 = candidate[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        triangle_areas[tri_idx] = area
                    
                    # Get new min area from updated cache
                    new_min_area = np.min(triangle_areas)
                    
                    # Rollback cache changes
                    for tri_idx, area in original_areas.items():
                        triangle_areas[tri_idx] = area

                    if new_min_area > best_score:
                        points = candidate
                        best_points = points.copy()
                        best_score = new_min_area
                        
                        # Update cache with actual changes
                        for tri_idx in affected_triangles:
                            i, j, k = triangles[tri_idx]
                            x1, y1 = points[i]
                            x2, y2 = points[j]
                            x3, y3 = points[k]
                            area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                            triangle_areas[tri_idx] = area
                        
                        bary_points[idx] = [u_new, v_new]
                        improved = True
                        stagnation_count = 0
                        resistance_metric = max(0, resistance_metric - 1)
                        
                        # Record improvement
                        improvement_history.append(new_min_area - best_score)
                        if len(improvement_history) > 10:
                            improvement_history.pop(0)
                        
                        # Update triangle vulnerability
                        triangle_vulnerability *= 0.95
                        for tri_idx in affected_triangles:
                            if triangle_areas[tri_idx] > original_areas[tri_idx]:
                                triangle_vulnerability[tri_idx] = min(2.0, triangle_vulnerability[tri_idx] * 1.05)
                        
                        break
                
                if improved:
                    break

            if improved:
                # Adaptive step growth
                if improvement_history:
                    avg_improvement = np.mean(improvement_history)
                    growth_factor = 1.0 + min(0.05, avg_improvement * 50)
                    step_size = min(step_size * growth_factor, initial_step * 2.0)
                else:
                    step_size = min(step_size * 1.05, initial_step * 2.0)
            else:
                # Adaptive step decay based on stagnation
                decay_factor = 0.95 - min(0.04, stagnation_count * 0.001)
                step_size *= decay_factor
                stagnation_count += 1
                resistance_metric = min(10.0, resistance_metric + 0.5)  # Worsened resistance

                # Dynamic restart threshold based on stagnation severity and resistance
                current_restart_threshold = max(base_restart_threshold, 5 * stagnation_count * (1.0 + resistance_metric/5.0))

                # Adaptive restart mechanism
                if stagnation_count >= current_restart_threshold:
                    # Restart with perturbation magnitude scaled by resistance metric
                    restart_step = 0.15 * initial_step * np.sqrt(stagnation_count) * (1.0 + resistance_metric/5.0)
                    candidate = points.copy()
                    for i in range(n):
                        u, v = bary_points[i]
                        du = np.random.normal(0, restart_step)
                        dv = np.random.normal(0, restart_step)
                        u_new, v_new = clamp_bary(u + du, v + dv)
                        candidate[i] = to_cart(u_new, v_new)
                    
                    # Enforce symmetry on restart
                    candidate = enforce_symmetry(candidate)
                    
                    # Check validity
                    too_close = False
                    for i in range(n):
                        min_distance = get_local_min_distance(i, candidate, triangle_areas, point_to_triangles)
                        for j in range(i+1, n):
                            dist = np.linalg.norm(candidate[i] - candidate[j])
                            if dist < min_distance:
                                too_close = True
                                break
                        if too_close:
                            break
                    
                    if not too_close and is_inside_triangle(candidate, A, B, C):
                        # Update all triangle areas cache
                        for idx, (i, j, k) in enumerate(triangles):
                            x1, y1 = candidate[i]
                            x2, y2 = candidate[j]
                            x3, y3 = candidate[k]
                            area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                            triangle_areas[idx] = area
                        new_min_area = np.min(triangle_areas)
                        
                        if new_min_area > best_score:
                            points = candidate
                            best_points = points.copy()
                            best_score = new_min_area
                            
                            # Update cache with actual changes
                            for idx, (i, j, k) in enumerate(triangles):
                                x1, y1 = points[i]
                                x2, y2 = points[j]
                                x3, y3 = points[k]
                                area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                                triangle_areas[idx] = area
                            
                            bary_points = np.array([to_bary(p) for p in points])

                    # Reset search parameters
                    step_size = 0.2 * initial_step
                    stagnation_count = 0

            # Reset step size if too small
            if step_size < 1e-6:
                step_size = 0.1 * initial_step

        # Final symmetry enforcement
        best_points = enforce_symmetry(best_points)
        return best_points, best_score

    # Run multiple restarts with different initial configurations
    best_overall = None
    best_score_overall = -1
    num_restarts = 8  # Increased from 5 for better exploration
    
    for _ in range(num_restarts):
        initial_points = generate_initial_configuration()
        points, score = optimize_configuration(initial_points)
        
        if score > best_score_overall:
            best_overall = points
            best_score_overall = score

    return best_overall