import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.spatial import Delaunay

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get the unit triangle vertices
    A, B, C = get_unit_triangle()
    
    # Precompute side length and denominator for barycentric conversion
    side_length = np.linalg.norm(B - A)
    denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
    
    # Helper functions for barycentric conversion
    def to_bary(p):
        u = ((B[1] - C[1]) * (p[0] - C[0]) + (C[0] - B[0]) * (p[1] - C[1])) / denom
        v = ((C[1] - A[1]) * (p[0] - C[0]) + (A[0] - C[0]) * (p[1] - C[1])) / denom
        return u, v

    def to_cart(u, v):
        w = 1 - u - v
        return u * A + v * B + w * C

    def boundary_penalty(p):
        """Returns scaling factor based on boundary proximity (1.0 at center, approaches 0 near boundaries)."""
        u, v = to_bary(p)
        w = 1 - u - v
        
        # Distance to each boundary (0 = on boundary, 1 = centroid)
        dist_to_AB = w
        dist_to_AC = v
        dist_to_BC = u
        
        # Get nearest boundary distance
        min_dist = min(dist_to_AB, dist_to_AC, dist_to_BC)
        
        # Linear scaling factor (1.0 at center, approaches 0 near boundaries)
        scale_factor = min_dist
        
        return scale_factor

    def get_boundary_projection(p, grad):
        """Project gradient to be tangent to nearest boundary or vertex if point is near edge."""
        u, v = to_bary(p)
        w = 1 - u - v
        
        # Find closest boundary
        min_coord = min(u, v, w)
        epsilon = 1e-5
        
        # Vertex handling - when two coordinates are near zero
        if min_coord < epsilon:
            if u < epsilon and v < epsilon:  # Near vertex C (w=1)
                # Project toward interior along normal to BC edge
                bc_normal = np.array([C[1] - B[1], B[0] - C[0]])
                bc_normal = bc_normal / np.linalg.norm(bc_normal)
                # Ensure inward direction
                if np.dot(bc_normal, A - C) < 0:
                    bc_normal = -bc_normal
                proj = np.dot(grad, bc_normal) * bc_normal
                return proj
            elif u < epsilon and w < epsilon:  # Near vertex B (v=1)
                # Project toward interior along normal to AC edge
                ac_normal = np.array([C[1] - A[1], A[0] - C[0]])
                ac_normal = ac_normal / np.linalg.norm(ac_normal)
                # Ensure inward direction
                if np.dot(ac_normal, B - A) < 0:
                    ac_normal = -ac_normal
                proj = np.dot(grad, ac_normal) * ac_normal
                return proj
            elif v < epsilon and w < epsilon:  # Near vertex A (u=1)
                # Project toward interior along normal to AB edge
                ab_normal = np.array([B[1] - A[1], A[0] - B[0]])
                ab_normal = ab_normal / np.linalg.norm(ab_normal)
                # Ensure inward direction
                if np.dot(ab_normal, C - A) < 0:
                    ab_normal = -ab_normal
                proj = np.dot(grad, ab_normal) * ab_normal
                return proj

        # Edge handling (original logic)
        if min_coord < epsilon:
            if u <= v and u <= w:  # Closest to BC edge (u=0)
                # Project gradient to be parallel to BC edge
                bc_dir = C - B
                bc_dir = bc_dir / np.linalg.norm(bc_dir)
                proj = np.dot(grad, bc_dir) * bc_dir
                return proj
            elif v <= u and v <= w:  # Closest to AC edge (v=0)
                # AC edge direction: C - A
                ac_dir = C - A
                ac_dir = ac_dir / np.linalg.norm(ac_dir)
                proj = np.dot(grad, ac_dir) * ac_dir
                return proj
            else:  # Closest to AB edge (w=0)
                # AB edge direction: B - A
                ab_dir = B - A
                ab_dir = ab_dir / np.linalg.norm(ab_dir)
                proj = np.dot(grad, ab_dir) * ab_dir
                return proj
        
        return grad

    def get_affected_triangles(perturbed_indices, n):
        """Return indices of all triangles containing any of the perturbed points."""
        affected = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    if i in perturbed_indices or j in perturbed_indices or k in perturbed_indices:
                        affected.append((i, j, k))
        return affected

    def get_edge_connected_triangles(triplets, n):
        """Find all triangles connected through shared edges to the given triplets."""
        edge_to_triangles = {}
        
        # Build edge-to-triangles mapping
        for triplet in triplets:
            i, j, k = triplet
            edges = [(min(i,j), max(i,j)), (min(j,k), max(j,k)), (min(i,k), max(i,k))]
            for edge in edges:
                if edge not in edge_to_triangles:
                    edge_to_triangles[edge] = []
                edge_to_triangles[edge].append(triplet)
        
        # Find all connected triangles
        connected = set(triplets)
        queue = list(triplets)
        
        while queue:
            current = queue.pop(0)
            i, j, k = current
            edges = [(min(i,j), max(i,j)), (min(j,k), max(j,k)), (min(i,k), max(i,k))]
            
            for edge in edges:
                if edge in edge_to_triangles:
                    for neighbor in edge_to_triangles[edge]:
                        if neighbor not in connected:
                            connected.add(neighbor)
                            queue.append(neighbor)
        
        return list(connected)

    def get_delaunay_density_weights(points):
        """Calculate density weights using Delaunay triangulation to identify crowded regions."""
        try:
            # Compute Delaunay triangulation
            tri = Delaunay(points)
            
            # Initialize weights for each point
            weights = np.zeros(len(points))
            
            # For each triangle in the Delaunay mesh
            for simplex in tri.simplices:
                i, j, k = simplex
                # Calculate triangle area
                x1, y1 = points[i]
                x2, y2 = points[j]
                x3, y3 = points[k]
                area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                
                # Small area indicates dense region - higher weight
                if area > 1e-10:
                    density_weight = 1.0 / area
                else:
                    density_weight = 1e6
                
                # Distribute weight to vertices
                weights[i] += density_weight
                weights[j] += density_weight
                weights[k] += density_weight
            
            # Normalize weights
            max_weight = np.max(weights)
            if max_weight > 0:
                weights = weights / max_weight
            
            return weights
        except:
            # Fallback if Delaunay fails (e.g., collinear points)
            return np.ones(len(points))

    def calculate_triangle_areas(points, triangles):
        """Calculate areas for specified triangles only."""
        areas = {}
        for i, j, k in triangles:
            x1, y1 = points[i]
            x2, y2 = points[j]
            x3, y3 = points[k]
            area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
            areas[(i, j, k)] = area
        return areas

    def get_weighted_minimal_triangles(area_cache, current_resistance=0.5, top_k_base=12, temperature_base=0.008):
        """Find minimal area triangles with adaptive top-k and temperature based on resistance."""
        if not area_cache:
            return [], float('inf'), {}
        
        # ADAPTIVE: Dynamic top-k based on current solution quality
        min_area = min(area_cache.values())
        # Slower reduction rate: top_k = max(7, min(12, int(12*(1-0.5*quality_ratio))))
        quality_ratio = min(1.0, min_area / 0.0365)
        top_k = max(7, min(12, int(top_k_base * (1.0 - 0.5 * quality_ratio))))
        
        # ADAPTIVE: Temperature increases when resistance is low (more exploration needed)
        temperature = temperature_base * (1.0 + 0.5 * (1.0 - current_resistance))
        
        # Sort triangles by area
        sorted_areas = sorted(area_cache.items(), key=lambda x: x[1])
        min_area = sorted_areas[0][1]
        
        # Take top-k triangles
        top_triangles = sorted_areas[:top_k]
        
        # Calculate weights using softmax over negative area differences
        weights = {}
        total_weight = 0.0
        for triplet, area in top_triangles:
            # Exponential decay based on how much larger than min
            weight = np.exp(-(area - min_area) / temperature)
            weights[triplet] = weight
            total_weight += weight
        
        # Normalize weights
        if total_weight > 0:
            for triplet in weights:
                weights[triplet] /= total_weight
        
        return [triplet for triplet, _ in top_triangles], min_area, weights

    # Run multiple restarts to find deep basins
    best_overall = None
    best_score_overall = -1
    n_restarts = 8  # Increased for better exploration
    
    # ADAPTIVE: Multiple lattice initialization patterns for n=11
    def generate_lattice_pattern(pattern_type='voronoi'):
        # Triangle centroid
        centroid = (A + B + C) / 3
        points = []
        
        if pattern_type == 'hexagonal':
            # Layer 1: 1 point at center (slightly offset to avoid symmetry)
            center_offset = 0.02 * (np.random.random(2) - 0.5)
            points.append(centroid + center_offset)
            
            # Layer 2: 3 points at first radius
            r1 = 0.22 + 0.03 * np.random.random()  # Adaptive radius
            angles = [0, 2*np.pi/3, 4*np.pi/3]
            for angle in angles:
                dx = r1 * np.cos(angle)
                dy = r1 * np.sin(angle)
                # Rotate to align with triangle orientation
                rotated = np.array([
                    dx * (B[0]-A[0])/side_length - dy * (B[1]-A[1])/side_length,
                    dx * (B[1]-A[1])/side_length + dy * (B[0]-A[0])/side_length
                ])
                point = centroid + rotated
                if is_inside_triangle(point, A, B, C):
                    points.append(point)
                else:
                    # Project back to triangle if needed
                    u, v = to_bary(point)
                    # Use boundary penalty instead of hard clamp
                    scale = boundary_penalty(point)
                    points.append(to_cart(u * scale, v * scale))
            
            # Layer 3: 7 points at second radius
            r2 = 0.42 + 0.03 * np.random.random()  # Adaptive radius
            # First 3 points aligned with layer 2
            for i, angle in enumerate(angles):
                dx = r2 * np.cos(angle)
                dy = r2 * np.sin(angle)
                # Rotate to align with triangle orientation
                rotated = np.array([
                    dx * (B[0]-A[0])/side_length - dy * (B[1]-A[1])/side_length,
                    dx * (B[1]-A[1])/side_length + dy * (B[0]-A[0])/side_length
                ])
                point = centroid + rotated
                if is_inside_triangle(point, A, B, C):
                    points.append(point)
                else:
                    u, v = to_bary(point)
                    scale = boundary_penalty(point)
                    points.append(to_cart(u * scale, v * scale))
            
            # Additional 4 points at intermediate positions
            angles_mid = [np.pi/3, np.pi, 5*np.pi/3]
            for angle in angles_mid:
                dx = r2 * 0.65 * np.cos(angle)  # Between r1 and r2
                dy = r2 * 0.65 * np.sin(angle)
                # Rotate to align with triangle orientation
                rotated = np.array([
                    dx * (B[0]-A[0])/side_length - dy * (B[1]-A[1])/side_length,
                    dx * (B[1]-A[1])/side_length + dy * (B[0]-A[0])/side_length
                ])
                point = centroid + rotated
                if is_inside_triangle(point, A, B, C):
                    points.append(point)
                else:
                    u, v = to_bary(point)
                    scale = boundary_penalty(point)
                    points.append(to_cart(u * scale, v * scale))
            
            # Add one point near the boundary for flexibility
            boundary_offset = 0.05 + 0.05 * np.random.random()
            u_b = boundary_offset
            v_b = boundary_offset
            w_b = 1 - u_b - v_b
            if w_b < 0:
                scale = 1.0 / (u_b + v_b)
                u_b *= scale
                v_b *= scale
            points.append(to_cart(u_b, v_b))
            
        elif pattern_type == 'alternative':
            # Alternative pattern: 1+4+6 configuration
            # Layer 1: 1 point at center (slightly offset)
            center_offset = 0.015 * (np.random.random(2) - 0.5)
            points.append(centroid + center_offset)
            
            # Layer 2: 4 points forming a diamond
            r1 = 0.2 + 0.02 * np.random.random()
            angles = [np.pi/4, 3*np.pi/4, 5*np.pi/4, 7*np.pi/4]
            for angle in angles:
                dx = r1 * np.cos(angle)
                dy = r1 * np.sin(angle)
                # Rotate to align with triangle orientation
                rotated = np.array([
                    dx * (B[0]-A[0])/side_length - dy * (B[1]-A[1])/side_length,
                    dx * (B[1]-A[1])/side_length + dy * (B[0]-A[0])/side_length
                ])
                point = centroid + rotated
                if is_inside_triangle(point, A, B, C):
                    points.append(point)
                else:
                    u, v = to_bary(point)
                    scale = boundary_penalty(point)
                    points.append(to_cart(u * scale, v * scale))
            
            # Layer 3: 6 points at second radius
            r2 = 0.38 + 0.02 * np.random.random()
            angles = np.linspace(0, 2*np.pi, 6, endpoint=False)
            for angle in angles:
                dx = r2 * np.cos(angle)
                dy = r2 * np.sin(angle)
                # Rotate to align with triangle orientation
                rotated = np.array([
                    dx * (B[0]-A[0])/side_length - dy * (B[1]-A[1])/side_length,
                    dx * (B[1]-A[1])/side_length + dy * (B[0]-A[0])/side_length
                ])
                point = centroid + rotated
                if is_inside_triangle(point, A, B, C):
                    points.append(point)
                else:
                    u, v = to_bary(point)
                    scale = boundary_penalty(point)
                    points.append(to_cart(u * scale, v * scale))

        elif pattern_type == 'fibonacci':
            # Fibonacci spiral pattern optimized for triangle
            points = []
            n_points = 11
            golden_angle = np.pi * (3 - np.sqrt(5))  # 137.5 degrees in radians
            
            for i in range(n_points):
                # Radius proportional to sqrt(i)
                r = np.sqrt(i / n_points) * 0.45
                # Angle increases by golden angle
                theta = i * golden_angle
                
                # Convert to Cartesian
                dx = r * np.cos(theta)
                dy = r * np.sin(theta)
                
                # Rotate to align with triangle orientation
                rotated = np.array([
                    dx * (B[0]-A[0])/side_length - dy * (B[1]-A[1])/side_length,
                    dx * (B[1]-A[1])/side_length + dy * (B[0]-A[0])/side_length
                ])
                
                point = centroid + rotated
                if is_inside_triangle(point, A, B, C):
                    points.append(point)
                else:
                    u, v = to_bary(point)
                    scale = boundary_penalty(point)
                    points.append(to_cart(u * scale, v * scale))

        elif pattern_type == 'voronoi':
            # Voronoi-based pattern with strategic boundary placement
            points = []
            
            # 1 point at center
            center_offset = 0.01 * (np.random.random(2) - 0.5)
            points.append(centroid + center_offset)
            
            # 5 points at mid-radius with strategic angles
            r1 = 0.3 + 0.02 * np.random.random()
            angles = [np.pi/6, np.pi/2, 5*np.pi/6, 7*np.pi/6, 3*np.pi/2]
            for angle in angles:
                dx = r1 * np.cos(angle)
                dy = r1 * np.sin(angle)
                # Rotate to align with triangle orientation
                rotated = np.array([
                    dx * (B[0]-A[0])/side_length - dy * (B[1]-A[1])/side_length,
                    dx * (B[1]-A[1])/side_length + dy * (B[0]-A[0])/side_length
                ])
                point = centroid + rotated
                if is_inside_triangle(point, A, B, C):
                    points.append(point)
                else:
                    u, v = to_bary(point)
                    scale = boundary_penalty(point)
                    points.append(to_cart(u * scale, v * scale))

            # 5 points near boundary with strategic placement
            r2 = 0.45 + 0.02 * np.random.random()
            # Place points strategically near edges but not corners
            boundary_points = [
                (0.1, 0.1),  # Near AB edge
                (0.1, 0.8),  # Near AC edge
                (0.8, 0.1),  # Near BC edge
                (0.2, 0.2),  # Near AB edge, slightly inward
                (0.7, 0.2)   # Near BC edge, slightly inward
            ]
            for u_b, v_b in boundary_points:
                w_b = 1 - u_b - v_b
                if w_b < 0:
                    scale = 1.0 / (u_b + v_b)
                    u_b *= scale
                    v_b *= scale
                point = to_cart(u_b, v_b)
                if is_inside_triangle(point, A, B, C):
                    points.append(point)
                else:
                    u, v = to_bary(point)
                    scale = boundary_penalty(point)
                    points.append(to_cart(u * scale, v * scale))

        return np.array(points[:11])  # Ensure exactly 11 points

    for restart in range(n_restarts):
        # ADAPTIVE: Multiple lattice patterns based on restart index
        if restart < n_restarts * 0.3:
            pattern_type = 'hexagonal'
        elif restart < n_restarts * 0.6:
            pattern_type = 'voronoi'
        elif restart < n_restarts * 0.8:
            pattern_type = 'fibonacci'
        else:
            pattern_type = 'alternative'
            
        points = generate_lattice_pattern(pattern_type)
        n = 11

        # Initialize triangle area cache for all combinations
        all_triangles = [(i, j, k) for i in range(n) for j in range(i+1, n) for k in range(j+1, n)]
        area_cache = calculate_triangle_areas(points, all_triangles)
        
        # Get edge-connected triangles for complete vulnerability analysis
        min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, current_resistance=0.5)
        if min_triplets:
            min_triplets = get_edge_connected_triangles(min_triplets, n)
        
        best_points = points.copy()
        best_score = min_area
        
        # Initialize momentum for gradient history
        momentum = {i: np.zeros(2) for i in range(n)}
        # ADAPTIVE: Momentum decay based on resistance
        momentum_decay_base = 0.85
        
        # Parameters for search
        initial_step = 0.055  # Slightly increased for better exploration
        gradient_step = initial_step
        random_step = initial_step * 0.8
        stagnation_count = 0
        # ADAPTIVE: Restart threshold based on improvement rate
        restart_threshold_base = 30
        max_iterations = 700  # Increased for deeper search
        tol = 1e-9
        distinctness_threshold = 1e-5
        min_distance = 0.015  # Slightly increased for stability

        # Track resistance estimate for adaptive parameters
        resistance_estimate = 0.5
        initial_min_area = min_area
        improvement_rate = 0.0

        for iter_idx in range(max_iterations):
            if not min_triplets:
                area_cache = calculate_triangle_areas(best_points, all_triangles)
                min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, resistance_estimate)
                if min_triplets:
                    min_triplets = get_edge_connected_triangles(min_triplets, n)
                if not min_triplets:
                    break

            # ADAPTIVE: Update resistance estimate based on progress
            if initial_min_area > 0:
                improvement_rate = (min_area - initial_min_area) / (0.0365 - initial_min_area)
                # Clamp to [0,1]
                improvement_rate = max(0.0, min(1.0, improvement_rate))
                # Resistance estimate: linear growth
                resistance_estimate = 0.5 + 0.4 * improvement_rate

            # Count vertex frequencies in minimal triangles
            freq = [0] * n
            for triplet in min_triplets:
                for idx in triplet:
                    freq[idx] += 1
            
            # Sort vertices by frequency (descending)
            candidate_indices = sorted(range(n), key=lambda i: -freq[i])
            
            # Get Delaunay-based density weights for spatial awareness
            density_weights = get_delaunay_density_weights(best_points)

            # Try geometric gradient moves on minimal triangles
            improved = False
            
            # Process top triangles with weights
            for triplet in min_triplets:
                weight = weights.get(triplet, 1.0)
                i, j, k = triplet
                p_i, p_j, p_k = best_points[i], best_points[j], best_points[k]
                
                # Calculate gradient for area increase
                grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                
                # Normalize and scale gradients
                norm_i = np.linalg.norm(grad_i)
                norm_j = np.linalg.norm(grad_j)
                norm_k = np.linalg.norm(grad_k)
                
                if norm_i > 0: grad_i = grad_i / norm_i * gradient_step * weight
                if norm_j > 0: grad_j = grad_j / norm_j * gradient_step * weight
                if norm_k > 0: grad_k = grad_k / norm_k * gradient_step * weight

                # Boundary-aware gradient projection
                grad_i = get_boundary_projection(p_i, grad_i)
                grad_j = get_boundary_projection(p_j, grad_j)
                grad_k = get_boundary_projection(p_k, grad_k)

                # Apply momentum with adaptive decay
                momentum_decay = max(0.75, momentum_decay_base - 0.1 * resistance_estimate)
                momentum[i] = momentum_decay * momentum[i] + (1 - momentum_decay) * grad_i
                momentum[j] = momentum_decay * momentum[j] + (1 - momentum_decay) * grad_j
                momentum[k] = momentum_decay * momentum[k] + (1 - momentum_decay) * grad_k

                # Create candidate by moving points along gradients
                candidate = best_points.copy()
                candidate[i] += momentum[i]
                candidate[j] += momentum[j]
                candidate[k] += momentum[k]

                # Check containment
                if is_inside_triangle(candidate, A, B, C):
                    # Only recalculate affected triangles (including edge-connected)
                    affected = get_affected_triangles([i, j, k], n)
                    affected = get_edge_connected_triangles(affected, n)
                    new_areas = calculate_triangle_areas(candidate, affected)
                    
                    # Update cache temporarily
                    old_cache = area_cache.copy()
                    area_cache.update(new_areas)
                    _, new_min_area, _ = get_weighted_minimal_triangles(area_cache, resistance_estimate)
                    
                    # Restore cache
                    area_cache = old_cache
                    
                    if new_min_area > min_area:
                        best_points = candidate
                        best_score = new_min_area
                        
                        # Update cache with new areas
                        area_cache.update(new_areas)
                        min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, resistance_estimate)
                        if min_triplets:
                            min_triplets = get_edge_connected_triangles(min_triplets, n)
                        
                        improved = True
                        stagnation_count = 0
                        
                        # ADAPTIVE: Asymmetric step adaptation based on resistance
                        step_growth = 1.01 + 0.025 * resistance_estimate
                        gradient_step = min(gradient_step * step_growth, initial_step)
                        break

            if improved:
                continue

            # If geometric moves didn't work, try barycentric perturbations
            for idx in candidate_indices:
                if freq[idx] == 0:
                    break

                # Get current barycentric coordinates
                u, v = to_bary(best_points[idx])
                
                # ADAPTIVE: Exploration factor based on resistance
                exploration_factor = 0.3 + 0.7 * resistance_estimate
                
                # Try multiple perturbations with Cauchy distribution for heavy-tailed exploration
                for _ in range(12):
                    # Use Cauchy distribution for better exploration
                    du = np.random.standard_cauchy() * (random_step / side_length)
                    dv = np.random.standard_cauchy() * (random_step / side_length)
                    
                    # Add gradient direction bias based on frequency
                    grad_strength = 0.3 * (freq[idx] / len(min_triplets))
                    if grad_strength > 0:
                        # Use average gradient direction from minimal triangles
                        avg_grad = np.zeros(2)
                        count = 0
                        for triplet in min_triplets:
                            if idx in triplet:
                                i, j, k = triplet
                                p_i, p_j, p_k = best_points[i], best_points[j], best_points[k]
                                if idx == i:
                                    grad = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                                elif idx == j:
                                    grad = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                                else:
                                    grad = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                                
                                if np.linalg.norm(grad) > 0:
                                    grad = grad / np.linalg.norm(grad)
                                    avg_grad += grad
                                    count += 1
                        
                        if count > 0:
                            avg_grad = avg_grad / count
                            du += grad_strength * avg_grad[0] * (random_step / side_length)
                            dv += grad_strength * avg_grad[1] * (random_step / side_length)

                    # Apply boundary penalty scaling to perturbations
                    boundary_factor = boundary_penalty(best_points[idx])
                    du *= boundary_factor
                    dv *= boundary_factor
                    
                    u_new, v_new = u + du, v + dv
                    
                    # Convert back to Cartesian
                    candidate = best_points.copy()
                    candidate[idx] = to_cart(u_new, v_new)
                    
                    # Check minimum distance to other points
                    too_close = False
                    for i in range(n):
                        if i == idx:
                            continue
                        dist = np.linalg.norm(candidate[i] - candidate[idx])
                        if dist < min_distance:
                            too_close = True
                            break
                    
                    # Check and evaluate candidate
                    if too_close or not is_inside_triangle(candidate, A, B, C):
                        continue
                    
                    # Only recalculate affected triangles (including edge-connected)
                    affected = get_affected_triangles([idx], n)
                    affected = get_edge_connected_triangles(affected, n)
                    new_areas = calculate_triangle_areas(candidate, affected)
                    
                    # Update cache temporarily
                    old_cache = area_cache.copy()
                    area_cache.update(new_areas)
                    _, new_min_area, _ = get_weighted_minimal_triangles(area_cache, resistance_estimate)
                    
                    # Restore cache
                    area_cache = old_cache
                    
                    if new_min_area > min_area:
                        best_points = candidate
                        best_score = new_min_area
                        
                        # Update cache with new areas
                        area_cache.update(new_areas)
                        min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, resistance_estimate)
                        if min_triplets:
                            min_triplets = get_edge_connected_triangles(min_triplets, n)
                        
                        improved = True
                        stagnation_count = 0
                        
                        # ADAPTIVE: Asymmetric step adaptation based on resistance
                        step_growth = 1.01 + 0.015 * resistance_estimate
                        random_step = min(random_step * step_growth, initial_step)
                        break
            
            if not improved:
                # ADAPTIVE: Gradual step size decay with asymmetric rates based on improvement rate
                decay_factor = 0.98 - 0.01 * improvement_rate
                gradient_step *= decay_factor
                random_step *= decay_factor + 0.01  # Slightly slower decay for random steps
                stagnation_count += 1

                # ADAPTIVE: Restart threshold based on improvement rate
                adaptive_restart_threshold = max(10, int(restart_threshold_base * improvement_rate))

                # Adaptive restart mechanism with increased perturbation strength
                if stagnation_count >= adaptive_restart_threshold:
                    # Restart with larger perturbation
                    restart_step = 0.5 * initial_step
                    candidate = best_points.copy()
                    for i in range(n):
                        u, v = to_bary(best_points[i])
                        du = np.random.standard_cauchy() * (restart_step / side_length)
                        dv = np.random.standard_cauchy() * (restart_step / side_length)
                        
                        # Apply boundary penalty scaling to restart perturbations
                        boundary_factor = boundary_penalty(best_points[i])
                        du *= boundary_factor
                        dv *= boundary_factor
                        
                        u_new, v_new = u + du, v + dv
                        candidate[i] = to_cart(u_new, v_new)
                    
                    if is_inside_triangle(candidate, A, B, C):
                        # Evaluate with cache update (including edge-connected triangles)
                        affected = get_affected_triangles(list(range(n)), n)
                        affected = get_edge_connected_triangles(affected, n)
                        new_areas = calculate_triangle_areas(candidate, affected)
                        
                        old_cache = area_cache.copy()
                        area_cache.update(new_areas)
                        _, new_min_area, _ = get_weighted_minimal_triangles(area_cache, resistance_estimate)
                        area_cache = old_cache
                        
                        if new_min_area > min_area:
                            best_points = candidate
                            best_score = new_min_area
                            
                            # Update cache with new areas
                            area_cache.update(new_areas)
                            min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, resistance_estimate)
                            if min_triplets:
                                min_triplets = get_edge_connected_triangles(min_triplets, n)
                    
                    # Reset search parameters
                    gradient_step = 0.1 * initial_step
                    random_step = 0.08 * initial_step
                    stagnation_count = 0

            # Reset step sizes if too small
            if gradient_step < 1e-5:
                gradient_step = 0.1 * initial_step
            if random_step < 1e-5:
                random_step = 0.08 * initial_step

        # Update overall best
        if best_score > best_score_overall:
            best_overall = best_points.copy()
            best_score_overall = best_score

    # Final distinctness check
    for i in range(11):
        for j in range(i+1, 11):
            dist = np.linalg.norm(best_overall[i] - best_overall[j])
            if dist < distinctness_threshold:
                # Move both points apart along the connecting line
                direction = (best_overall[j] - best_overall[i]) / dist if dist > 0 else np.array([1.0, 0.0])
                move_amount = 0.5 * (distinctness_threshold - dist)
                best_overall[i] -= direction * move_amount
                best_overall[j] += direction * move_amount

    return best_overall