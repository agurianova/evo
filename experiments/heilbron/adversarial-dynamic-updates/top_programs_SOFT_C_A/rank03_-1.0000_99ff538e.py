import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

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

    def clamp_bary(u, v):
        """Clamp barycentric coordinates to be inside the triangle."""
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))
        if u + v > 1.0:
            scale = 1.0 / (u + v)
            u *= scale
            v *= scale
        return u, v

    def get_boundary_projection(p, grad, improvement_rate=0.0):
        """Project gradient to be tangent to nearest boundary or vertex with adaptive push strength."""
        u, v = to_bary(p)
        w = 1 - u - v
        
        # Adaptive push factor based on improvement rate
        push_factor = 0.2 + 0.5 * (1.0 - improvement_rate)
        
        # Find closest boundary/vertex
        min_coord = min(u, v, w)
        epsilon = 1e-5
        
        if min_coord < epsilon:
            # Vertex handling - using edge normals instead of angle bisectors
            if u < epsilon and v < epsilon:  # Near vertex C (w=1)
                # Use normal vector pointing toward interior
                direction = (A + B) / 2 - C
                direction = direction / (np.linalg.norm(direction) + 1e-9)
                proj = np.dot(grad, direction) * direction
                # Add component pushing away from vertex
                away_dir = C - p
                away_norm = np.linalg.norm(away_dir)
                if away_norm > 1e-9:
                    away_dir = away_dir / away_norm
                    proj += push_factor * np.dot(grad, away_dir) * away_dir
                return proj
            elif u < epsilon and w < epsilon:  # Near vertex B (v=1)
                direction = (A + C) / 2 - B
                direction = direction / (np.linalg.norm(direction) + 1e-9)
                proj = np.dot(grad, direction) * direction
                # Add component pushing away from vertex
                away_dir = B - p
                away_norm = np.linalg.norm(away_dir)
                if away_norm > 1e-9:
                    away_dir = away_dir / away_norm
                    proj += push_factor * np.dot(grad, away_dir) * away_dir
                return proj
            elif v < epsilon and w < epsilon:  # Near vertex A (u=1)
                direction = (B + C) / 2 - A
                direction = direction / (np.linalg.norm(direction) + 1e-9)
                proj = np.dot(grad, direction) * direction
                # Add component pushing away from vertex
                away_dir = A - p
                away_norm = np.linalg.norm(away_dir)
                if away_norm > 1e-9:
                    away_dir = away_dir / away_norm
                    proj += push_factor * np.dot(grad, away_dir) * away_dir
                return proj

            # Edge handling
            if u <= v and u <= w:  # Closest to BC edge (u=0)
                # Project gradient to be parallel to BC edge
                bc_dir = C - B
                bc_dir = bc_dir / np.linalg.norm(bc_dir)
                proj = np.dot(grad, bc_dir) * bc_dir
                # Add component pushing away from edge
                normal = np.array([B[1] - C[1], C[0] - B[0]])
                normal = normal / (np.linalg.norm(normal) + 1e-9)
                proj += push_factor * np.dot(grad, normal) * normal
                return proj
            elif v <= u and v <= w:  # Closest to AC edge (v=0)
                # AC edge direction: C - A
                ac_dir = C - A
                ac_dir = ac_dir / np.linalg.norm(ac_dir)
                proj = np.dot(grad, ac_dir) * ac_dir
                # Add component pushing away from edge
                normal = np.array([A[1] - C[1], C[0] - A[0]])
                normal = normal / (np.linalg.norm(normal) + 1e-9)
                proj += push_factor * np.dot(grad, normal) * normal
                return proj
            else:  # Closest to AB edge (w=0)
                # AB edge direction: B - A
                ab_dir = B - A
                ab_dir = ab_dir / np.linalg.norm(ab_dir)
                proj = np.dot(grad, ab_dir) * ab_dir
                # Add component pushing away from edge
                normal = np.array([A[1] - B[1], B[0] - A[0]])
                normal = normal / (np.linalg.norm(normal) + 1e-9)
                proj += push_factor * np.dot(grad, normal) * normal
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

    def get_weighted_minimal_triangles(area_cache, top_k=12, temperature=0.007, improvement_rate=0.0):
        """Find top-k minimal area triangles with adaptive parameters based on area distribution."""
        if not area_cache:
            return [], float('inf'), {}
        
        # Sort triangles by area
        sorted_areas = sorted(area_cache.items(), key=lambda x: x[1])
        min_area = sorted_areas[0][1]
        
        # Calculate standard deviation of top areas for adaptive temperature
        top_areas = [area for _, area in sorted_areas[:min(5, len(sorted_areas))]]
        std_dev = np.std(top_areas) if len(top_areas) > 1 else 0.0
        
        # Adaptive temperature based on std_dev and improvement rate
        temperature = max(0.002, 0.002 + 0.008 * (std_dev / (min_area + 1e-10)))
        temperature = temperature * (0.7 + 0.3 * (1.0 - improvement_rate))
        
        # ADAPTIVE: Make top-k dynamic based on improvement rate
        top_k = max(3, min(20, int(15*(1-improvement_rate) + 3*improvement_rate)))
        
        # Take top-k triangles
        top_k = min(top_k, len(sorted_areas))
        top_triangles = sorted_areas[:top_k]
        
        # Calculate weights using softmax over negative area differences
        weights = {}
        total_weight = 0.0
        for triplet, area in top_triangles:
            # Exponential decay based on how much larger than min
            area_diff = area - min_area
            weight = np.exp(-area_diff / (temperature * min_area))
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
    n_restarts = 5
    
    # Track improvement history for adaptive parameters
    improvement_history = []

    for restart in range(n_restarts):
        # Diverse initialization strategies per restart
        strategy = restart % 3
        
        # ADAPTIVE: Randomized lattice parameters within valid range
        hex_radius = 0.22 + 0.03 * np.random.random()
        ring_ratio = 1.6 + 0.3 * np.random.random()
        
        points = []
        
        if strategy == 0:  # Hexagonal lattice
            # Center point
            points.append(to_cart(0.5, 0.25))

            # First ring (6 points)
            for i in range(6):
                angle = i * (2 * np.pi / 6)
                r = hex_radius
                u = 0.5 + r * np.cos(angle)
                v = 0.25 + r * np.sin(angle)
                # Apply symmetry-breaking perturbation
                perturbation = 0.02 * np.random.randn(2)
                u += perturbation[0]
                v += perturbation[1]
                u, v = clamp_bary(u, v)
                points.append(to_cart(u, v))

            # Second ring (4 points - adjusted for 11 total points)
            for i in range(4):
                angle = i * (2 * np.pi / 4) + np.pi/4
                r = ring_ratio * hex_radius
                u = 0.5 + r * np.cos(angle)
                v = 0.25 + r * np.sin(angle)
                # Apply symmetry-breaking perturbation
                perturbation = 0.02 * np.random.randn(2)
                u += perturbation[0]
                v += perturbation[1]
                u, v = clamp_bary(u, v)
                points.append(to_cart(u, v))

        elif strategy == 1:  # Triangular lattice
            # Center point
            points.append(to_cart(0.5, 0.5))

            # First ring (3 points)
            for i in range(3):
                angle = i * (2 * np.pi / 3) + np.pi/6
                r = hex_radius * 0.8
                u = 0.5 + r * np.cos(angle)
                v = 0.5 + r * np.sin(angle)
                perturbation = 0.02 * np.random.randn(2)
                u += perturbation[0]
                v += perturbation[1]
                u, v = clamp_bary(u, v)
                points.append(to_cart(u, v))

            # Second ring (6 points)
            for i in range(6):
                angle = i * (2 * np.pi / 6) + np.pi/12
                r = hex_radius * 1.6
                u = 0.5 + r * np.cos(angle)
                v = 0.5 + r * np.sin(angle)
                perturbation = 0.02 * np.random.randn(2)
                u += perturbation[0]
                v += perturbation[1]
                u, v = clamp_bary(u, v)
                points.append(to_cart(u, v))

            # One additional point
            u, v = 0.5, 0.25
            perturbation = 0.02 * np.random.randn(2)
            u += perturbation[0]
            v += perturbation[1]
            u, v = clamp_bary(u, v)
            points.append(to_cart(u, v))

        else:  # Grid pattern
            # Create a triangular grid pattern
            rows = 4
            for row in range(rows):
                num_points = row + 1
                y = 0.1 + 0.8 * (row / (rows - 1)) if rows > 1 else 0.5
                for col in range(num_points):
                    x = 0.1 + 0.8 * (col / (num_points - 1)) if num_points > 1 else 0.5
                    # Convert grid coordinates to barycentric
                    u = x * (1 - y)
                    v = y
                    # Apply perturbation
                    perturbation = 0.02 * np.random.randn(2)
                    u += perturbation[0] * 0.1
                    v += perturbation[1] * 0.1
                    u, v = clamp_bary(u, v)
                    points.append(to_cart(u, v))

            # Add remaining points with strategic placement
            while len(points) < 11:
                u = np.random.random() * 0.8
                v = np.random.random() * 0.8
                if u + v <= 1.0:
                    u, v = clamp_bary(u, v)
                    points.append(to_cart(u, v))

        points = np.array(points)
        n = 11

        # Initialize triangle area cache for all combinations
        all_triangles = [(i, j, k) for i in range(n) for j in range(i+1, n) for k in range(j+1, n)]
        area_cache = calculate_triangle_areas(points, all_triangles)
        min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, improvement_rate=0.0)
        
        best_points = points.copy()
        best_score = min_area
        
        # Initialize momentum for gradient history
        momentum = {i: np.zeros(2) for i in range(n)}
        momentum_decay = 0.85

        # Parameters for search
        initial_step = 0.05
        gradient_step = initial_step
        random_step = initial_step * 0.8
        stagnation_count = 0
        max_iterations = 500
        tol = 1e-9
        distinctness_threshold = 1e-5
        min_distance = 0.01
        
        # Track improvement rate for adaptive parameters
        improvement_rate = 0.0

        for _ in range(max_iterations):
            if not min_triplets:
                area_cache = calculate_triangle_areas(best_points, all_triangles)
                min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, improvement_rate=improvement_rate)
                if not min_triplets:
                    break

            # Count vertex frequencies in minimal triangles with criticality weighting
            freq = [0] * n
            criticality = [0.0] * n
            for triplet in min_triplets:
                i, j, k = triplet
                area = area_cache[triplet]
                # Weight by normalized area difference from minimum
                critical_weight = np.exp(-(area - min_area) / (0.008 * min_area))
                
                freq[i] += 1
                freq[j] += 1
                freq[k] += 1
                
                criticality[i] += critical_weight
                criticality[j] += critical_weight
                criticality[k] += critical_weight
            
            # Sort vertices by combined criticality score
            candidate_indices = sorted(range(n), key=lambda i: -criticality[i])
            
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
                grad_i = get_boundary_projection(p_i, grad_i, improvement_rate)
                grad_j = get_boundary_projection(p_j, grad_j, improvement_rate)
                grad_k = get_boundary_projection(p_k, grad_k, improvement_rate)

                # Apply momentum
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
                    # Only recalculate affected triangles
                    affected = get_affected_triangles([i, j, k], n)
                    new_areas = calculate_triangle_areas(candidate, affected)
                    
                    # Update cache temporarily
                    old_cache = area_cache.copy()
                    area_cache.update(new_areas)
                    _, new_min_area, _ = get_weighted_minimal_triangles(area_cache, improvement_rate=improvement_rate)
                    
                    # Restore cache
                    area_cache = old_cache
                    
                    if new_min_area > min_area:
                        best_points = candidate
                        best_score = new_min_area
                        
                        # Update cache with new areas
                        area_cache.update(new_areas)
                        min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, improvement_rate=improvement_rate)
                        
                        improved = True
                        stagnation_count = 0
                        
                        # Update improvement history
                        improvement = (new_min_area - min_area) / min_area
                        improvement_history.append(improvement)
                        if len(improvement_history) > 20:
                            improvement_history.pop(0)
                        improvement_rate = np.mean(improvement_history) if improvement_history else 0
                        
                        # Asymmetric step adaptation
                        gradient_step = min(gradient_step * 1.05, initial_step)
                        break

            # Add orthogonal perturbations when gradient moves stall
            if not improved and np.random.random() < 0.2:
                for triplet in min_triplets:
                    i, j, k = triplet
                    p_i, p_j, p_k = best_points[i], best_points[j], best_points[k]
                    
                    # Calculate gradient as before
                    grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                    grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                    grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                    
                    # Create orthogonal perturbation (rotate 90 degrees)
                    ortho_i = np.array([-grad_i[1], grad_i[0]])
                    ortho_j = np.array([-grad_j[1], grad_j[0]])
                    ortho_k = np.array([-grad_k[1], grad_k[0]])
                    
                    # Normalize and scale - increased from 0.5 to 0.8
                    if np.linalg.norm(ortho_i) > 0: ortho_i = ortho_i / np.linalg.norm(ortho_i) * gradient_step * 0.8
                    if np.linalg.norm(ortho_j) > 0: ortho_j = ortho_j / np.linalg.norm(ortho_j) * gradient_step * 0.8
                    if np.linalg.norm(ortho_k) > 0: ortho_k = ortho_k / np.linalg.norm(ortho_k) * gradient_step * 0.8

                    # Boundary-aware projection
                    ortho_i = get_boundary_projection(p_i, ortho_i, improvement_rate)
                    ortho_j = get_boundary_projection(p_j, ortho_j, improvement_rate)
                    ortho_k = get_boundary_projection(p_k, ortho_k, improvement_rate)

                    # Create candidate
                    candidate = best_points.copy()
                    candidate[i] += ortho_i
                    candidate[j] += ortho_j
                    candidate[k] += ortho_k

                    # Check and evaluate candidate
                    if is_inside_triangle(candidate, A, B, C):
                        # Only recalculate affected triangles
                        affected = get_affected_triangles([i, j, k], n)
                        new_areas = calculate_triangle_areas(candidate, affected)
                        
                        # Update cache temporarily
                        old_cache = area_cache.copy()
                        area_cache.update(new_areas)
                        _, new_min_area, _ = get_weighted_minimal_triangles(area_cache, improvement_rate=improvement_rate)
                        
                        # Restore cache
                        area_cache = old_cache
                        
                        if new_min_area > min_area:
                            best_points = candidate
                            best_score = new_min_area
                            
                            # Update cache with new areas
                            area_cache.update(new_areas)
                            min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, improvement_rate=improvement_rate)
                            
                            improved = True
                            stagnation_count = 0
                            
                            # Update improvement history
                            improvement = (new_min_area - min_area) / min_area
                            improvement_history.append(improvement)
                            if len(improvement_history) > 20:
                                improvement_history.pop(0)
                            improvement_rate = np.mean(improvement_history) if improvement_history else 0
                            break

            if improved:
                continue

            # If geometric moves didn't work, try barycentric perturbations
            for idx in candidate_indices:
                if criticality[idx] < 1e-5:
                    break

                # Get current barycentric coordinates
                u, v = to_bary(best_points[idx])
                
                # Try multiple perturbations with Cauchy distribution for heavy-tailed exploration
                for _ in range(10):
                    # Use Cauchy distribution for better exploration
                    du = np.random.standard_cauchy() * (random_step / side_length)
                    dv = np.random.standard_cauchy() * (random_step / side_length)
                    
                    # Add gradient direction bias based on frequency
                    grad_strength = 0.3 * (criticality[idx] / (sum(criticality) + 1e-10))
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

                    u_new, v_new = clamp_bary(u + du, v + dv)
                    
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
                    
                    # Only recalculate affected triangles
                    affected = get_affected_triangles([idx], n)
                    new_areas = calculate_triangle_areas(candidate, affected)
                    
                    # Update cache temporarily
                    old_cache = area_cache.copy()
                    area_cache.update(new_areas)
                    _, new_min_area, _ = get_weighted_minimal_triangles(area_cache, improvement_rate=improvement_rate)
                    
                    # Restore cache
                    area_cache = old_cache
                    
                    if new_min_area > min_area:
                        best_points = candidate
                        best_score = new_min_area
                        
                        # Update cache with new areas
                        area_cache.update(new_areas)
                        min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, improvement_rate=improvement_rate)
                        
                        improved = True
                        stagnation_count = 0
                        
                        # Update improvement history
                        improvement = (new_min_area - min_area) / min_area
                        improvement_history.append(improvement)
                        if len(improvement_history) > 20:
                            improvement_history.pop(0)
                        improvement_rate = np.mean(improvement_history) if improvement_history else 0
                        
                        # Asymmetric step adaptation
                        random_step = min(random_step * 1.03, initial_step)
                        break
        
            if not improved:
                # Adaptive step size decay based on improvement rate
                adaptive_decay = 0.98 - 0.05 * improvement_rate
                gradient_step *= adaptive_decay
                random_step *= adaptive_decay
                stagnation_count += 1

                # Adaptive restart threshold based on improvement rate
                adaptive_restart_threshold = max(10, int(30 * (1.0 - improvement_rate)))

                # Adaptive restart mechanism with increased perturbation strength
                if stagnation_count >= adaptive_restart_threshold:
                    # Restart with larger perturbation (0.5 * initial_step instead of 0.25)
                    restart_step = 0.5 * initial_step
                    candidate = best_points.copy()
                    for i in range(n):
                        u, v = to_bary(best_points[i])
                        du = np.random.standard_cauchy() * (restart_step / side_length)
                        dv = np.random.standard_cauchy() * (restart_step / side_length)
                        u_new, v_new = clamp_bary(u + du, v + dv)
                        candidate[i] = to_cart(u_new, v_new)
                    
                    if is_inside_triangle(candidate, A, B, C):
                        # Evaluate with cache update
                        affected = get_affected_triangles(list(range(n)), n)
                        new_areas = calculate_triangle_areas(candidate, affected)
                        
                        old_cache = area_cache.copy()
                        area_cache.update(new_areas)
                        _, new_min_area, _ = get_weighted_minimal_triangles(area_cache, improvement_rate=improvement_rate)
                        area_cache = old_cache
                        
                        if new_min_area > min_area:
                            best_points = candidate
                            best_score = new_min_area
                            
                            # Update cache with new areas
                            area_cache.update(new_areas)
                            min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, improvement_rate=improvement_rate)
                    
                    # Reset search parameters
                    gradient_step = 0.1 * initial_step
                    random_step = 0.08 * initial_step
                    stagnation_count = 0

            # Reset step sizes if too small
            if gradient_step < 1e-5:
                gradient_step = 0.1 * initial_step
            if random_step < 1e-5:
                random_step = 0.08 * initial_step

        # Simulated annealing phase for deep local optima
        if stagnation_count >= 15:
            temperature = 0.01 * (1 + min(2, stagnation_count / 50))
            cooling_rate = 0.95
            sa_iterations = 150
            
            current = best_points.copy()
            current_score = best_score
            current_cache = area_cache.copy()
            current_min_triplets, current_min_area, current_weights = min_triplets, min_area, weights
            
            for _ in range(sa_iterations):
                # Randomly select a point to perturb
                idx = np.random.randint(0, n)
                u, v = to_bary(current[idx])
                
                # Larger perturbation for exploration
                du = np.random.normal(0, 0.1)
                dv = np.random.normal(0, 0.1)
                u_new, v_new = clamp_bary(u + du, v + dv)
                
                # Create candidate
                candidate = current.copy()
                candidate[idx] = to_cart(u_new, v_new)
                
                if is_inside_triangle(candidate, A, B, C):
                    # Only recalculate affected triangles
                    affected = get_affected_triangles([idx], n)
                    new_areas = calculate_triangle_areas(candidate, affected)
                    
                    # Update cache temporarily
                    temp_cache = current_cache.copy()
                    temp_cache.update(new_areas)
                    _, new_min_area, _ = get_weighted_minimal_triangles(temp_cache, improvement_rate=improvement_rate)
                    
                    # Metropolis criterion
                    delta = new_min_area - current_min_area
                    if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                        current = candidate
                        current_score = new_min_area
                        current_cache = temp_cache
                        current_min_area = new_min_area
                        
                        if new_min_area > best_score:
                            best_points = candidate.copy()
                            best_score = new_min_area
                            area_cache = current_cache.copy()
                            min_triplets, min_area, weights = get_weighted_minimal_triangles(area_cache, improvement_rate=improvement_rate)

                    # Cool temperature
                    temperature *= cooling_rate

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