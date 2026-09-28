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

    def clamp_bary(u, v):
        """Clamp barycentric coordinates to be inside the triangle."""
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))
        if u + v > 1.0:
            scale = 1.0 / (u + v)
            u *= scale
            v *= scale
        return u, v

    def get_boundary_penalty(p):
        """Returns scaling factor for movement based on boundary proximity using exponential function."""
        u, v = to_bary(p)
        w = 1 - u - v
        
        # Distance to each boundary (0 = on boundary, 1 = centroid)
        dist_to_AB = w
        dist_to_AC = v
        dist_to_BC = u
        
        # Get nearest boundary distance
        min_dist = min(dist_to_AB, dist_to_AC, dist_to_BC)
        
        # Smooth scaling factor (1.0 at center, approaches 0 near boundaries)
        # Using exponential function for smoother transition (replaces cubic)
        scale_factor = 1.0 - np.exp(-5 * min_dist)
        
        return scale_factor

    def get_boundary_projection(p, grad):
        """Project gradient to be tangent to nearest boundary or corner with diagonal handling."""
        u, v = to_bary(p)
        w = 1 - u - v
        
        # Calculate penetration depth (negative values indicate outside triangle)
        penetration = -min(u, v, w)
        
        # Elastic return force for boundary violations
        if penetration > 0:
            # Determine direction of elastic force
            force_direction = np.zeros(2)
            if u < 0:
                force_direction += np.array([1, 0])
            if v < 0:
                force_direction += np.array([0, 1])
            if w < 0:
                force_direction += np.array([-1, -1])
            
            # Normalize and scale by penetration
            if np.linalg.norm(force_direction) > 0:
                force_direction = force_direction / np.linalg.norm(force_direction)
            return grad + 0.5 * penetration * force_direction

        # Standard boundary projection for points on/near boundary
        min_coord = min(u, v, w)
        epsilon = 1e-5
        
        # Check for corner cases (two coordinates near 0)
        if u < epsilon and v < epsilon:  # Near vertex C (w=1)
            direction = (A + B) / 2 - C
            direction = direction / (np.linalg.norm(direction) + 1e-9)
            proj = np.dot(grad, direction) * direction
            return proj
        elif u < epsilon and w < epsilon:  # Near vertex B (v=1)
            direction = (A + C) / 2 - B
            direction = direction / (np.linalg.norm(direction) + 1e-9)
            proj = np.dot(grad, direction) * direction
            return proj
        elif v < epsilon and w < epsilon:  # Near vertex A (u=1)
            direction = (B + C) / 2 - A
            direction = direction / (np.linalg.norm(direction) + 1e-9)
            proj = np.dot(grad, direction) * direction
            return proj
        
        # Standard edge cases
        if min_coord < epsilon:
            if u <= v and u <= w:  # Closest to BC edge (u=0)
                # Project gradient to be parallel to BC edge
                bc_dir = C - B
                bc_dir = bc_dir / (np.linalg.norm(bc_dir) + 1e-9)
                proj = np.dot(grad, bc_dir) * bc_dir
                return proj
            elif v <= u and v <= w:  # Closest to AC edge (v=0)
                # AC edge direction: C - A
                ac_dir = C - A
                ac_dir = ac_dir / (np.linalg.norm(ac_dir) + 1e-9)
                proj = np.dot(grad, ac_dir) * ac_dir
                return proj
            else:  # Closest to AB edge (w=0)
                # AB edge direction: B - A
                ab_dir = B - A
                ab_dir = ab_dir / (np.linalg.norm(ab_dir) + 1e-9)
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

    def get_weighted_minimal_triangles(area_cache, min_area, tol=1e-9, k=5):
        """Find and weight minimal area triangles from cache using adaptive temperature."""
        if not area_cache:
            return [], float('inf'), {}
        
        # Calculate adaptive temperature based on current min_area - TIGHTENED FOCUS
        progress_factor = min(1.0, min_area / 0.03)
        # CHANGED: Increased coefficients from 0.02+0.08 to 0.03+0.12 for tighter focus
        temperature = max(0.0001, min_area * (0.03 + 0.12 * progress_factor))
        
        # Calculate weights using exponential function: weight = exp(-(area-min_area)/temperature)
        weights = {}
        for triplet, area in area_cache.items():
            diff = area - min_area
            weights[triplet] = np.exp(-diff / temperature) if diff >= 0 else 0
        
        # Sort triplets by weight (descending)
        weighted_triplets = sorted(weights.items(), key=lambda x: -x[1])
        
        # Take top-k or all if fewer than k
        top_k_triplets = [triplet for triplet, _ in weighted_triplets[:k]]
        
        # Normalize weights for the top-k
        total_weight = sum(weights[triplet] for triplet in top_k_triplets)
        if total_weight > 0:
            normalized_weights = {triplet: weights[triplet]/total_weight for triplet in top_k_triplets}
        else:
            normalized_weights = {triplet: 1.0/len(top_k_triplets) for triplet in top_k_triplets}
        
        return top_k_triplets, min_area, normalized_weights

    def get_delaunay_critical_triangles(points, area_cache, stagnation_count):
        """Use Delaunay triangulation to identify geometrically critical triangles with adaptive threshold."""
        try:
            tri = Delaunay(points)
            delaunay_triplets = []
            for simplex in tri.simplices:
                i, j, k = simplex
                delaunay_triplets.append((min(i,j,k), max(min(i,j),k), max(i,j,k)))
            
            # CHANGED: Tightened threshold from 1.005+0.015*stagnation/50 to 1.003+0.025*min(1.0,stagnation_count/40.0)
            delaunay_threshold = 1.003 + 0.025 * min(1.0, stagnation_count / 40.0)
            
            # Find minimal area among Delaunay triangles
            min_delaunay_area = float('inf')
            min_delaunay_triplets = []
            for triplet in delaunay_triplets:
                if triplet in area_cache:
                    area = area_cache[triplet]
                    if area < min_delaunay_area - 1e-9:
                        min_delaunay_area = area
                        min_delaunay_triplets = [triplet]
                    elif abs(area - min_delaunay_area) < 1e-9:
                        min_delaunay_triplets.append(triplet)
            
            return min_delaunay_triplets, min_delaunay_area, delaunay_threshold
        except:
            return [], float('inf'), 1.005

    # Run multiple restarts to find deep basins
    best_overall = None
    best_score_overall = -1
    n_restarts = 5
    
    for restart in range(n_restarts):
        # Randomize strategic placement for diversity with expanded ranges
        points = []
        
        # CHANGED: Expanded vertex offset ranges with restart-proportional scaling
        # Original: base_offset_near = 0.005 + 0.01 * restart/n_restarts
        base_offset_near = 0.01 + 0.04 * restart/n_restarts  # Expanded from 0.005-0.015 to 0.01-0.05
        # Original: base_offset_medium = 0.02 + 0.03 * restart/n_restarts
        base_offset_medium = 0.03 + 0.07 * restart/n_restarts  # Expanded from 0.02-0.05 to 0.03-0.1

        # Points near vertices (2 near each vertex: total 6)
        points.append(to_cart(base_offset_near, base_offset_near))  # Near A
        points.append(to_cart(base_offset_medium, base_offset_medium))  # Near A
        
        points.append(to_cart(1-base_offset_near, base_offset_near))  # Near B
        points.append(to_cart(1-base_offset_medium, base_offset_medium))  # Near B
        
        points.append(to_cart(base_offset_near, 1-base_offset_near))  # Near C
        points.append(to_cart(base_offset_medium, 1-base_offset_medium))  # Near C
        
        # CHANGED: Replaced uniform edge sampling with beta(2,2) distribution
        # Original: edge_offset1 = 0.2 + 0.6 * np.random.random()
        edge_offset1 = np.random.beta(2, 2)  # Centered around 0.5 with higher density
        # Original: edge_offset2 = 0.2 + 0.6 * np.random.random()
        edge_offset2 = np.random.beta(2, 2)
        # Original: edge_offset3 = 0.2 + 0.6 * np.random.random()
        edge_offset3 = np.random.beta(2, 2)
        
        # Points along edges (1 on each edge: total 3)
        points.append(to_cart(edge_offset1, 0))      # AB edge
        points.append(to_cart(0, edge_offset2))      # AC edge
        points.append(to_cart(edge_offset3, 1-edge_offset3))  # BC edge
        
        # Adaptive interior points with expanded ranges
        interior1_u = 0.05 + 0.65 * np.random.random()  # Expanded from 0.15-0.45 to 0.05-0.7
        interior1_v = 0.05 + 0.65 * np.random.random()  # Expanded from 0.15-0.45 to 0.05-0.7
        interior2_u = 0.1 + 0.6 * np.random.random()    # Expanded from 0.4-0.7 to 0.1-0.7
        interior2_v = 0.05 + 0.6 * np.random.random()   # Expanded from 0.1-0.3 to 0.05-0.65
        
        # Interior points (2)
        points.append(to_cart(interior1_u, interior1_v))  # Interior
        points.append(to_cart(interior2_u, interior2_v))  # Interior

        points = np.array(points)
        n = 11

        # Initialize triangle area cache for all combinations
        all_triangles = [(i, j, k) for i in range(n) for j in range(i+1, n) for k in range(j+1, n)]
        area_cache = calculate_triangle_areas(points, all_triangles)
        min_area = min(area_cache.values())
        min_triplets, _, weights = get_weighted_minimal_triangles(area_cache, min_area)
        
        best_points = points.copy()
        best_score = min_area
        
        # Initialize gradient history for momentum
        gradient_history = [np.zeros(2) for _ in range(n)]
        # CHANGED: Increased momentum adjustment step from ±0.015 to ±0.025
        momentum_factor = 0.6  # Start with moderate momentum

        # Parameters for search
        initial_step = 0.05
        gradient_step = initial_step
        random_step = initial_step * 0.8
        stagnation_count = 0
        # CHANGED: Made restart threshold adaptive based on resistance
        # Original: restart_threshold = 30
        resistance_proxy = min(1.0, min_area / 0.0365)
        restart_threshold = max(15, int(25 * (1.0 - resistance_proxy)))
        max_iterations = 500
        tol = 1e-9
        distinctness_threshold = 1e-5
        min_distance = 0.01
        # CHANGED: Increased orthogonal probability base and max with faster rate
        # Original: orthogonal_prob = 0.2
        orthogonal_prob = min(0.8, 0.3 + 0.5 * (stagnation_count / 80.0))

        for _ in range(max_iterations):
            if not min_triplets:
                area_cache = calculate_triangle_areas(best_points, all_triangles)
                min_area = min(area_cache.values())
                min_triplets, _, weights = get_weighted_minimal_triangles(area_cache, min_area)
                if not min_triplets:
                    break

            # Count vertex frequencies in minimal triangles with weights
            freq = [0] * n
            for triplet in min_triplets:
                weight = weights.get(triplet, 1.0/len(min_triplets))
                for idx in triplet:
                    freq[idx] += weight
            
            # Sort vertices by frequency (descending)
            candidate_indices = sorted(range(n), key=lambda i: -freq[i])
            
            # Try Delaunay-based critical triangle identification
            delaunay_triplets, delaunay_min_area, delaunay_threshold = get_delaunay_critical_triangles(best_points, area_cache, stagnation_count)
            
            # Prioritize Delaunay triangles if they're more constrained
            if delaunay_triplets and delaunay_min_area < min_area * delaunay_threshold:
                min_triplets = delaunay_triplets
                
            # Calculate consensus gradients across ALL minimal triangles
            consensus_grad = np.zeros((n, 2))
            total_weight = 0.0
            
            for triplet in min_triplets:
                weight = weights.get(triplet, 1.0)
                i, j, k = triplet
                p_i, p_j, p_k = best_points[i], best_points[j], best_points[k]
                
                # Calculate gradient for area increase
                grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])

                # Normalize and scale gradients
                for idx, grad in [(i, grad_i), (j, grad_j), (k, grad_k)]:
                    grad_norm = np.linalg.norm(grad)
                    if grad_norm > 1e-5:
                        consensus_grad[idx] += grad / grad_norm * weight
                        total_weight += weight

            # Normalize consensus gradients
            for i in range(n):
                if np.linalg.norm(consensus_grad[i]) > 1e-5:
                    consensus_grad[i] /= np.linalg.norm(consensus_grad[i])

            # Boundary-aware gradient projection for consensus gradients
            for i in range(n):
                if np.linalg.norm(consensus_grad[i]) > 1e-5:
                    consensus_grad[i] = get_boundary_projection(best_points[i], consensus_grad[i])

            # Create candidate by moving points along CONSENSUS gradients
            candidate = best_points.copy()
            improved = False
            
            # Apply consensus movement
            for i in range(n):
                if freq[i] > 0.1:
                    # Adjust step size based on frequency
                    step_size = gradient_step * (freq[i] / sum(freq))
                    candidate[i] += consensus_grad[i] * step_size

            # Check containment
            if is_inside_triangle(candidate, A, B, C):
                # Only recalculate affected triangles
                affected = get_affected_triangles(list(range(n)), n)
                new_areas = calculate_triangle_areas(candidate, affected)
                
                # Update cache temporarily
                old_cache = area_cache.copy()
                area_cache.update(new_areas)
                new_min_area = min(area_cache.values())
                _, _, _ = get_weighted_minimal_triangles(area_cache, new_min_area)
                
                # Restore cache
                area_cache = old_cache
                
                if new_min_area > min_area:
                    best_points = candidate
                    best_score = new_min_area
                    
                    # Update cache with new areas
                    area_cache.update(new_areas)
                    min_area = new_min_area
                    min_triplets, _, weights = get_weighted_minimal_triangles(area_cache, min_area)
                    
                    # Update gradient history with momentum
                    for i in range(n):
                        if freq[i] > 0.1:
                            gradient_history[i] = momentum_factor * gradient_history[i] + (1 - momentum_factor) * consensus_grad[i]
                    
                    improved = True
                    stagnation_count = 0
                    
                    # Asymmetric step adaptation
                    gradient_step = min(gradient_step * 1.1, initial_step)
                    continue

            # CHANGED: Increased base orthogonal probability and max with faster rate
            # Original: orthogonal_prob = min(0.7, 0.2 + 0.4 * (stagnation_count / 100.0))
            orthogonal_prob = min(0.8, 0.3 + 0.5 * (stagnation_count / 80.0))
            
            # Try orthogonal perturbations (90-degree rotations) when standard gradients stall
            if not improved and np.random.random() < orthogonal_prob:
                for triplet in min_triplets:
                    i, j, k = triplet
                    p_i, p_j, p_k = best_points[i], best_points[j], best_points[k]
                    
                    # Calculate gradient for area increase
                    grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                    grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                    grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                    
                    # Apply boundary penalty to scale gradient magnitude
                    scale_i = get_boundary_penalty(p_i)
                    scale_j = get_boundary_penalty(p_j)
                    scale_k = get_boundary_penalty(p_k)
                    
                    grad_i = grad_i * scale_i
                    grad_j = grad_j * scale_j
                    grad_k = grad_k * scale_k

                    # Normalize and scale gradients
                    norm_i = np.linalg.norm(grad_i)
                    norm_j = np.linalg.norm(grad_j)
                    norm_k = np.linalg.norm(grad_k)
                    
                    if norm_i > 0: grad_i = grad_i / norm_i * gradient_step
                    if norm_j > 0: grad_j = grad_j / norm_j * gradient_step
                    if norm_k > 0: grad_k = grad_k / norm_k * gradient_step

                    # Rotate gradients 90 degrees for orthogonal perturbation
                    ortho_i = np.array([-grad_i[1], grad_i[0]])
                    ortho_j = np.array([-grad_j[1], grad_j[0]])
                    ortho_k = np.array([-grad_k[1], grad_k[0]])

                    # Boundary-aware gradient projection
                    ortho_i = get_boundary_projection(p_i, ortho_i)
                    ortho_j = get_boundary_projection(p_j, ortho_j)
                    ortho_k = get_boundary_projection(p_k, ortho_k)

                    # Create candidate by moving points along orthogonal directions
                    candidate = best_points.copy()
                    candidate[i] += ortho_i
                    candidate[j] += ortho_j
                    candidate[k] += ortho_k

                    # Check containment
                    if is_inside_triangle(candidate, A, B, C):
                        # Only recalculate affected triangles
                        affected = get_affected_triangles([i, j, k], n)
                        new_areas = calculate_triangle_areas(candidate, affected)
                        
                        # Update cache temporarily
                        old_cache = area_cache.copy()
                        area_cache.update(new_areas)
                        new_min_area = min(area_cache.values())
                        _, _, _ = get_weighted_minimal_triangles(area_cache, new_min_area)
                        
                        # Restore cache
                        area_cache = old_cache
                        
                        if new_min_area > min_area:
                            best_points = candidate
                            best_score = new_min_area
                            
                            # Update cache with new areas
                            area_cache.update(new_areas)
                            min_area = new_min_area
                            min_triplets, _, weights = get_weighted_minimal_triangles(area_cache, min_area)
                            
                            # Update gradient history with momentum - INCREASED on success
                            for idx, grad in zip([i, j, k], [ortho_i, ortho_j, ortho_k]):
                                gradient_history[idx] = momentum_factor * gradient_history[idx] + (1 - momentum_factor) * grad
                            
                            improved = True
                            stagnation_count = 0
                            
                            # Asymmetric step adaptation
                            gradient_step = min(gradient_step * 1.1, initial_step)
                            break

            if improved:
                continue

            # If geometric moves didn't work, try barycentric perturbations
            for idx in candidate_indices:
                if freq[idx] < 0.1:  # Skip points with very low weight
                    break

                # Get current barycentric coordinates
                u, v = to_bary(best_points[idx])
                
                # CHANGED: Replaced pure Cauchy with adaptive Cauchy-Gaussian mixture
                # Original: du = np.random.standard_cauchy() * (random_step / side_length)
                resistance_proxy = min(1.0, min_area / 0.0365)
                cauchy_weight = 0.8 * (1.0 - resistance_proxy)
                
                # Try multiple perturbations with adaptive distribution mix
                for _ in range(10):
                    # Adaptive mix: p*Cauchy+(1-p)*Gaussian where p=0.8*(1-min_area/0.0365)
                    if np.random.random() < cauchy_weight:
                        du = np.random.standard_cauchy() * (random_step / side_length)
                        dv = np.random.standard_cauchy() * (random_step / side_length)
                    else:
                        du = np.random.normal(0, 1) * (random_step / side_length)
                        dv = np.random.normal(0, 1) * (random_step / side_length)
                    
                    # Add gradient direction bias based on frequency - ADAPTIVE STRENGTH
                    resistance_proxy = min(1.0, min_area / 0.0365)
                    grad_strength = (0.2 + 0.3 * (1.0 - resistance_proxy)) * (freq[idx] / sum(freq))
                    if grad_strength > 0:
                        # Use historical gradient direction
                        avg_grad = gradient_history[idx]
                        
                        if np.linalg.norm(avg_grad) > 0:
                            avg_grad = avg_grad / np.linalg.norm(avg_grad)
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
                    new_min_area = min(area_cache.values())
                    _, _, _ = get_weighted_minimal_triangles(area_cache, new_min_area)
                    
                    # Restore cache
                    area_cache = old_cache
                    
                    if new_min_area > min_area:
                        best_points = candidate
                        best_score = new_min_area
                        
                        # Update cache with new areas
                        area_cache.update(new_areas)
                        min_area = new_min_area
                        min_triplets, _, weights = get_weighted_minimal_triangles(area_cache, min_area)
                        
                        # Update gradient history
                        new_u, new_v = to_bary(candidate[idx])
                        delta_bary = np.array([new_u - u, new_v - v])
                        # Convert barycentric delta to Cartesian
                        delta_cart = delta_bary[0] * (A - C) + delta_bary[1] * (B - C)
                        gradient_history[idx] = momentum_factor * gradient_history[idx] + (1 - momentum_factor) * delta_cart
                        
                        improved = True
                        stagnation_count = 0
                        
                        # Asymmetric step adaptation
                        random_step = min(random_step * 1.05, initial_step)
                        break
            
            if not improved:
                # Gradual step size decay with asymmetric rates - SLOWED DECAY FOR BETTER EXPLORATION
                decay_factor = 0.99 if min_area < 0.03 else 0.97
                gradient_step *= decay_factor
                random_step *= decay_factor
                stagnation_count += 1

                # CHANGED: Adaptive restart mechanism with resistance-based threshold and increased magnitude
                # Original: if stagnation_count >= restart_threshold:
                resistance_proxy = min(1.0, min_area / 0.0365)
                adaptive_restart_threshold = max(15, int(25 * (1.0 - resistance_proxy)))
                if stagnation_count >= adaptive_restart_threshold:
                    # CHANGED: Increased base restart magnitude by 50% and corrected resistance scaling
                    # Original: restart_step = 0.1 * initial_step * (1.0 + 0.15 * (stagnation_count // restart_threshold) +
                    restart_step = 0.15 * initial_step * (1.0 + 0.15 * (stagnation_count // adaptive_restart_threshold) + 
                                                      0.05 * ((stagnation_count // adaptive_restart_threshold) ** 1.5)) * (1.0 - resistance_proxy)
                    candidate = best_points.copy()
                    for i in range(n):
                        u, v = to_bary(best_points[i])
                        du = np.random.standard_cauchy() * (restart_step / side_length)
                        dv = np.random.standard_cauchy() * (restart_step / side_length)
                        u_new, v_new = clamp_bary(u + du, v + dv)
                        candidate[i] = to_cart(u_new, v_new)
                    
                    # Apply symmetry-breaking perturbation
                    if restart % 2 == 0:
                        symmetry_break = 0.01 * (1 + stagnation_count / 50.0)
                        candidate[0] += np.array([symmetry_break, 0])
                        
                    if is_inside_triangle(candidate, A, B, C):
                        # Evaluate with cache update
                        affected = get_affected_triangles(list(range(n)), n)
                        new_areas = calculate_triangle_areas(candidate, affected)
                        
                        old_cache = area_cache.copy()
                        area_cache.update(new_areas)
                        new_min_area = min(area_cache.values())
                        _, _, _ = get_weighted_minimal_triangles(area_cache, new_min_area)
                        area_cache = old_cache
                        
                        if new_min_area > min_area:
                            best_points = candidate
                            best_score = new_min_area
                            
                            # Update cache with new areas
                            area_cache.update(new_areas)
                            min_area = new_min_area
                            min_triplets, _, weights = get_weighted_minimal_triangles(area_cache, min_area)
                    
                    # Reset search parameters
                    gradient_step = 0.1 * initial_step
                    random_step = 0.08 * initial_step
                    stagnation_count = 0

            # Adjust momentum factor based on improvement rate - BALANCED ADAPTATION
            # CHANGED: Increased momentum adjustment step from ±0.015 to ±0.025
            if improved:
                # INCREASE momentum on success to build directional persistence
                momentum_factor = min(0.85, momentum_factor + 0.025)
            else:
                # DECREASE momentum on failure to encourage exploration
                momentum_factor = max(0.35, momentum_factor - 0.025)

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