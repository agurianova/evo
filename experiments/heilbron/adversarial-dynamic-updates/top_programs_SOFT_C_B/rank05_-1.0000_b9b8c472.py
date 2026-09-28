from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Precompute denominator for barycentric conversion
    denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
    
    def to_bary(p):
        u = ((B[1] - C[1]) * (p[0] - C[0]) + (C[0] - B[0]) * (p[1] - C[1])) / denom
        v = ((C[1] - A[1]) * (p[0] - C[0]) + (A[0] - C[0]) * (p[1] - C[1])) / denom
        return u, v
    
    def to_cart(u, v):
        w = 1 - u - v
        return u * A + v * B + w * C
    
    def clamp_bary(u, v):
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))
        if u + v > 1.0:
            scale = 1.0 / (u + v)
            u *= scale
            v *= scale
        return u, v

    def get_all_triangles(n):
        """Return all possible triangles for n points."""
        triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    triangles.append((i, j, k))
        return triangles

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

    def get_minimal_triangles(area_cache, tol=1e-9):
        """Find minimal area triangles from cache."""
        if not area_cache:
            return [], float('inf')
        
        min_area = min(area_cache.values())
        min_triplets = [triplet for triplet, area in area_cache.items() 
                       if abs(area - min_area) < tol]
        return min_triplets, min_area

    def get_boundary_projection(p, grad):
        """Project gradient to be tangent to nearest boundary or corner with elastic return."""
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
        # ADAPTIVE: epsilon scales with current step size for consistent boundary handling
        epsilon = max(1e-6, 1e-3 * max(gradient_step, random_step))
        
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
                bc_dir = C - B
                bc_dir = bc_dir / (np.linalg.norm(bc_dir) + 1e-9)
                proj = np.dot(grad, bc_dir) * bc_dir
                return proj
            elif v <= u and v <= w:  # Closest to AC edge (v=0)
                ac_dir = C - A
                ac_dir = ac_dir / (np.linalg.norm(ac_dir) + 1e-9)
                proj = np.dot(grad, ac_dir) * ac_dir
                return proj
            else:  # Closest to AB edge (w=0)
                ab_dir = B - A
                ab_dir = ab_dir / (np.linalg.norm(ab_dir) + 1e-9)
                proj = np.dot(grad, ab_dir) * ab_dir
                return proj
        
        return grad

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Convert all points to barycentric for internal processing
        bary_points = np.array([to_bary(p) for p in best])
        
        initial_step = 0.05
        gradient_step = initial_step
        random_step = initial_step * 0.8
        stagnation_count = 0
        max_iterations = 250
        tol = 1e-9
        n = 11
        
        # Initialize triangle area cache for ALL combinations
        all_triangles = get_all_triangles(n)
        area_cache = calculate_triangle_areas(best, all_triangles)
        min_triplets, min_area = get_minimal_triangles(area_cache, tol)
        
        # Momentum tracking for gradient history
        momentum = [np.zeros(2) for _ in range(n)]
        momentum_decay_base = 0.9  # Increased from 0.85 for better persistence
        
        # Track recent improvement success rate for adaptive step sizing
        success_history = []
        success_window = 10
        improvement_rate = 0.0
        
        for _ in range(max_iterations):
            # Dynamic restart threshold based on improvement rate
            restart_threshold = max(10, int(30 * (1.0 - improvement_rate)))
            
            if not min_triplets:
                # Recalculate all triangles if cache is empty
                area_cache = calculate_triangle_areas(best, all_triangles)
                min_triplets, min_area = get_minimal_triangles(area_cache, tol)
                if not min_triplets:
                    break

            # Calculate potential impact for each vertex, weighted by triangle criticality
            impact = [0.0] * n
            for triplet in min_triplets:
                i, j, k = triplet
                area = area_cache[triplet]
                # ADAPTIVE: Calculate edge-length weighting factor
                p_i, p_j, p_k = best[i], best[j], best[k]
                edge1 = np.linalg.norm(p_j - p_k)
                edge2 = np.linalg.norm(p_i - p_k)
                edge3 = np.linalg.norm(p_i - p_j)
                perimeter = edge1 + edge2 + edge3
                # Normalize perimeter to prevent extreme values
                max_possible_perimeter = np.sqrt(3) * np.sqrt(4 * min_area / np.sqrt(3)) * 2
                edge_weight = min(1.0, perimeter / (max_possible_perimeter + 1e-9))
                
                # Enhanced weighting with adaptive epsilon to prevent extreme focus
                weight = edge_weight / (area + 0.1 * min_area)  # Added epsilon term
                impact[i] += weight
                impact[j] += weight
                impact[k] += weight
            
            # Sort vertices by impact (descending)
            candidate_indices = sorted(range(n), key=lambda i: -impact[i])
            
            # ADAPTIVE: Sigmoidal transition for candidate count (smoother exploration-exploitation balance)
            adaptive_candidate_count = max(3, min(6, 3 + 3 / (1 + np.exp(5 * (improvement_rate - 0.5))))
            
            # Accumulate gradients for all critical points
            grad_accum = [np.zeros(2) for _ in range(n)]
            for triplet in min_triplets:
                i, j, k = triplet
                p_i, p_j, p_k = best[i], best[j], best[k]
                area = area_cache[triplet]
                
                # Calculate gradient for area increase
                grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                
                # ADAPTIVE: Calculate edge-length weighting factor
                edge1 = np.linalg.norm(p_j - p_k)
                edge2 = np.linalg.norm(p_i - p_k)
                edge3 = np.linalg.norm(p_i - p_j)
                perimeter = edge1 + edge2 + edge3
                max_possible_perimeter = np.sqrt(3) * np.sqrt(4 * min_area / np.sqrt(3)) * 2
                edge_weight = min(1.0, perimeter / (max_possible_perimeter + 1e-9))
                
                # Enhanced weighting with adaptive epsilon
                weight = edge_weight / (area + 0.1 * min_area)
                grad_accum[i] += grad_i * weight
                grad_accum[j] += grad_j * weight
                grad_accum[k] += grad_k * weight

            # Apply momentum with adaptive decay
            momentum_decay = momentum_decay_base + 0.15 * improvement_rate  # Increased scaling factor
            for i in range(n):
                if np.linalg.norm(grad_accum[i]) > 0:
                    # Normalize the accumulated gradient before applying momentum
                    grad_direction = grad_accum[i] / np.linalg.norm(grad_accum[i])
                    momentum[i] = momentum_decay * momentum[i] + (1 - momentum_decay) * grad_direction
                    # Scale by step size
                    grad_accum[i] = momentum[i] * gradient_step

            # Apply boundary-aware projection to all gradients
            for i in range(n):
                if np.linalg.norm(grad_accum[i]) > 0:
                    grad_accum[i] = get_boundary_projection(best[i], grad_accum[i])

            # Create candidate by moving all points along accumulated gradients
            candidate = best.copy()
            for i in range(n):
                if np.linalg.norm(grad_accum[i]) > 0:
                    candidate[i] += grad_accum[i]

            # Check containment
            if is_inside_triangle(candidate, A, B, C):
                # ADAPTIVE: Expand affected triangles to include those sharing edges with minimal triangles
                affected = set()
                for i in range(n):
                    for j in range(i+1, n):
                        for k in range(j+1, n):
                            if i in candidate_indices[:adaptive_candidate_count] or \
                               j in candidate_indices[:adaptive_candidate_count] or \
                               k in candidate_indices[:adaptive_candidate_count]:
                                affected.add((i, j, k))
                                # Add triangles sharing edges with this triangle
                                for l in range(n):
                                    if l != i and l != j and l != k:
                                        affected.add(tuple(sorted([i, j, l])))
                                        affected.add(tuple(sorted([i, k, l])))
                                        affected.add(tuple(sorted([j, k, l])))
                affected = list(affected)
                
                new_areas = calculate_triangle_areas(candidate, affected)
                
                # Update cache temporarily
                old_cache = area_cache.copy()
                for triplet, area in new_areas.items():
                    area_cache[triplet] = area
                
                _, new_min_area = get_minimal_triangles(area_cache, tol)
                
                # Restore cache if no improvement
                if new_min_area <= min_area:
                    area_cache = old_cache
                else:
                    best = candidate
                    best_score = new_min_area
                    # Recalculate barycentric coordinates properly
                    bary_points = np.array([to_bary(p) for p in best])
                    min_triplets, min_area = get_minimal_triangles(area_cache, tol)
                    
                    # Update improvement rate for adaptive parameters
                    if best_score > 0:
                        improvement_rate = min(1.0, best_score / 0.0365)
                    
                    # Track success for adaptive step sizing
                    success_history.append(1)
                    stagnation_count = 0
                    continue

            # If geometric moves didn't work, try barycentric perturbations
            improved = False
            for idx in candidate_indices:
                if impact[idx] < 1e-5:  # Skip points with negligible impact
                    break

                # Get current barycentric coordinates
                u, v = bary_points[idx]
                
                # Try multiple perturbations
                for _ in range(5):
                    du = np.random.normal(0, random_step)
                    dv = np.random.normal(0, random_step)
                    u_new, v_new = clamp_bary(u + du, v + dv)
                    
                    # Convert back to Cartesian
                    candidate = best.copy()
                    candidate[idx] = to_cart(u_new, v_new)
                    
                    # Check if valid and better
                    if is_inside_triangle(candidate, A, B, C):
                        # ADAPTIVE: Expand affected triangles to include those sharing edges with minimal triangles
                        affected = set()
                        for i in range(n):
                            for j in range(i+1, n):
                                for k in range(j+1, n):
                                    if i == idx or j == idx or k == idx:
                                        affected.add((i, j, k))
                                        # Add triangles sharing edges with this triangle
                                        for l in range(n):
                                            if l != i and l != j and l != k:
                                                affected.add(tuple(sorted([i, j, l])))
                                                affected.add(tuple(sorted([i, k, l])))
                                                affected.add(tuple(sorted([j, k, l])))
                        affected = list(affected)
                        
                        new_areas = calculate_triangle_areas(candidate, affected)
                        
                        # Update cache temporarily
                        old_cache = area_cache.copy()
                        for triplet, area in new_areas.items():
                            area_cache[triplet] = area
                        
                        _, new_min_area = get_minimal_triangles(area_cache, tol)
                        
                        # Restore cache if no improvement
                        if new_min_area <= min_area:
                            area_cache = old_cache
                        else:
                            best = candidate
                            best_score = new_min_area
                            # Recalculate barycentric coordinates properly
                            bary_points = np.array([to_bary(p) for p in best])
                            min_triplets, min_area = get_minimal_triangles(area_cache, tol)
                            
                            # Update improvement rate
                            if best_score > 0:
                                improvement_rate = min(1.0, best_score / 0.0365)
                            
                            # Track success for adaptive step sizing
                            success_history.append(1)
                            improved = True
                            stagnation_count = 0
                            break
                
                if improved:
                    break

            if not improved:
                # Track failure for adaptive step sizing
                success_history.append(0)
                
                # Adaptive step size adjustment based on success rate
                success_rate = sum(success_history[-success_window:]) / max(1, min(len(success_history), success_window))
                # Increase step size with success, decrease with failure
                gradient_step = gradient_step * (0.95 + 0.1 * success_rate)
                random_step = random_step * (0.96 + 0.1 * success_rate)
                
                # Keep step sizes within bounds
                gradient_step = max(1e-5, min(gradient_step, initial_step * 1.5))
                random_step = max(1e-5, min(random_step, initial_step * 1.5))
                
                stagnation_count += 1

                # ADAPTIVE: Scale restart perturbation with stagnation depth
                restart_step = 0.25 * initial_step * (1 + min(2, stagnation_count / 30))
                
                # Adaptive restart mechanism
                if stagnation_count >= restart_threshold:
                    # Restart with larger perturbation scaled by stagnation depth
                    candidate = best.copy()
                    for i in range(n):
                        u, v = bary_points[i]
                        du = np.random.normal(0, restart_step)
                        dv = np.random.normal(0, restart_step)
                        u_new, v_new = clamp_bary(u + du, v + dv)
                        candidate[i] = to_cart(u_new, v_new)
                    
                    if is_inside_triangle(candidate, A, B, C):
                        # Evaluate with cache update
                        # ADAPTIVE: Expand affected triangles to include those sharing edges with minimal triangles
                        affected = set()
                        for i in range(n):
                            for j in range(i+1, n):
                                for k in range(j+1, n):
                                    affected.add((i, j, k))
                                    # Add triangles sharing edges with this triangle
                                    for l in range(n):
                                        if l != i and l != j and l != k:
                                            affected.add(tuple(sorted([i, j, l])))
                                            affected.add(tuple(sorted([i, k, l])))
                                            affected.add(tuple(sorted([j, k, l])))
                        affected = list(affected)
                        
                        new_areas = calculate_triangle_areas(candidate, affected)
                        
                        old_cache = area_cache.copy()
                        for triplet, area in new_areas.items():
                            area_cache[triplet] = area
                        
                        _, new_min_area = get_minimal_triangles(area_cache, tol)
                        
                        if new_min_area > min_area:
                            best = candidate
                            best_score = new_min_area
                            # Recalculate barycentric coordinates properly
                            bary_points = np.array([to_bary(p) for p in best])
                            min_triplets, min_area = get_minimal_triangles(area_cache, tol)
                            
                            # Update improvement rate
                            if best_score > 0:
                                improvement_rate = min(1.0, best_score / 0.0365)
                        else:
                            area_cache = old_cache
                    
                    # Reset search parameters
                    gradient_step = 0.1 * initial_step
                    random_step = 0.08 * initial_step
                    stagnation_count = 0

        # Simulated annealing phase for deep local optima - triggered by stagnation
        if stagnation_count >= restart_threshold / 2:
            # Adaptive temperature based on stagnation
            temperature = 0.01 * (1 + min(2, stagnation_count / 50))
            cooling_rate = 0.95
            sa_iterations = 150
            
            current = best.copy()
            current_score = best_score
            # Recalculate barycentric coordinates properly
            current_bary = np.array([to_bary(p) for p in current])
            current_cache = area_cache.copy()
            current_min_triplets, current_min_area = min_triplets, min_area
            
            for _ in range(sa_iterations):
                # Randomly select a point to perturb
                idx = np.random.randint(0, n)
                u, v = current_bary[idx]
                
                # Larger perturbation for exploration
                du = np.random.normal(0, 0.1)
                dv = np.random.normal(0, 0.1)
                u_new, v_new = clamp_bary(u + du, v + dv)
                
                # Create candidate
                candidate = current.copy()
                candidate[idx] = to_cart(u_new, v_new)
                
                if is_inside_triangle(candidate, A, B, C):
                    # ADAPTIVE: Expand affected triangles to include those sharing edges with minimal triangles
                    affected = set()
                    for i in range(n):
                        for j in range(i+1, n):
                            for k in range(j+1, n):
                                if i == idx or j == idx or k == idx:
                                    affected.add((i, j, k))
                                    # Add triangles sharing edges with this triangle
                                    for l in range(n):
                                        if l != i and l != j and l != k:
                                            affected.add(tuple(sorted([i, j, l])))
                                            affected.add(tuple(sorted([i, k, l])))
                                            affected.add(tuple(sorted([j, k, l])))
                    affected = list(affected)
                    
                    new_areas = calculate_triangle_areas(candidate, affected)
                    
                    # Update cache temporarily
                    temp_cache = current_cache.copy()
                    for triplet, area in new_areas.items():
                        temp_cache[triplet] = area
                    
                    _, new_min_area = get_minimal_triangles(temp_cache, tol)
                    
                    # Metropolis criterion
                    delta = new_min_area - current_min_area
                    if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                        current = candidate
                        current_score = new_min_area
                        # Recalculate barycentric coordinates properly
                        current_bary = np.array([to_bary(p) for p in current])
                        current_cache = temp_cache
                        current_min_area = new_min_area
                        
                        if new_min_area > best_score:
                            best = candidate.copy()
                            best_score = new_min_area
                            # Recalculate barycentric coordinates properly
                            bary_points = np.array([to_bary(p) for p in best])
                            area_cache = current_cache.copy()
                            min_triplets, min_area = get_minimal_triangles(area_cache, tol)

                    # Cool temperature
                    temperature *= cooling_rate

        return best

    return improve