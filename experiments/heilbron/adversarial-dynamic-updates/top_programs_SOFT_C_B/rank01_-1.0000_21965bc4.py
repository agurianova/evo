from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.spatial import Delaunay
import scipy.spatial.qhull as qhull

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

    def get_boundary_penalty(p, power=2.5):
        """Returns scaling factors for x and y components based on boundary proximity with adaptive power."""
        u, v = to_bary(p)
        w = 1 - u - v
        
        # Distance to each boundary (0 = on boundary, 1 = centroid)
        dist_to_AB = w
        dist_to_AC = v
        dist_to_BC = u
        
        # Get nearest boundary distance
        min_dist = min(dist_to_AB, dist_to_AC, dist_to_BC)
        
        # Smooth scaling factor (1.0 at center, approaches 0 near boundaries)
        # Using parameterized power function for adaptability
        scale_factor = 1.0 - (1.0 - min_dist)**power
        
        return scale_factor

    def update_triangle_cache(points, cache, perturbed_indices):
        """Update only triangles containing perturbed points."""
        n = len(points)
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    # Only update triangles containing at least one perturbed point
                    if i in perturbed_indices or j in perturbed_indices or k in perturbed_indices:
                        x1, y1 = points[i]
                        x2, y2 = points[j]
                        x3, y3 = points[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        cache[(i, j, k)] = area
        return cache

    def get_minimal_triangles(points, cache=None):
        """Get minimal area triangles, using cache if available."""
        n = len(points)
        min_area = float('inf')
        min_triplets = []
        
        # Initialize cache if not provided
        if cache is None:
            cache = {}
            
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    # Check cache first
                    if (i, j, k) in cache:
                        area = cache[(i, j, k)]
                    else:
                        x1, y1 = points[i]
                        x2, y2 = points[j]
                        x3, y3 = points[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        cache[(i, j, k)] = area
                        
                    if area < min_area:
                        min_area = area
                        min_triplets = [(i, j, k)]
                    elif abs(area - min_area) < 1e-9:
                        min_triplets.append((i, j, k))
                        
        return min_triplets, min_area, cache

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Convert all points to barycentric for internal processing
        bary_points = np.array([to_bary(p) for p in best])
        
        # Initialize triangle cache
        triangle_cache = {}
        _, _, triangle_cache = get_minimal_triangles(best, triangle_cache)
        
        # PROBE PHASE: Analyze initial improvement rate to calibrate parameters
        probe_iterations = 15
        initial_improvement = 0
        probe_points = best.copy()
        probe_bary = bary_points.copy()
        probe_cache = triangle_cache.copy()
        
        for _ in range(probe_iterations):
            min_triplets, min_area, _ = get_minimal_triangles(probe_points, probe_cache)
            if not min_triplets:
                break
            
            # Try a basic gradient move
            i, j, k = min_triplets[0]
            p_i, p_j, p_k = probe_points[i], probe_points[j], probe_points[k]
            
            grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
            grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
            grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
            
            scale_i = get_boundary_penalty(p_i)
            scale_j = get_boundary_penalty(p_j)
            scale_k = get_boundary_penalty(p_k)
            
            # Fixed gradient normalization: preserve magnitude information
            norm_i = np.linalg.norm(grad_i)
            norm_j = np.linalg.norm(grad_j)
            norm_k = np.linalg.norm(grad_k)
            
            grad_i = grad_i * 0.05 / norm_i if norm_i > 0 else np.zeros(2)
            grad_j = grad_j * 0.05 / norm_j if norm_j > 0 else np.zeros(2)
            grad_k = grad_k * 0.05 / norm_k if norm_k > 0 else np.zeros(2)

            grad_i = grad_i * scale_i
            grad_j = grad_j * scale_j
            grad_k = grad_k * scale_k

            candidate = probe_points.copy()
            candidate[i] += grad_i
            candidate[j] += grad_j
            candidate[k] += grad_k

            if is_inside_triangle(candidate, A, B, C):
                score = get_smallest_triangle_area(candidate)
                if score > min_area:
                    initial_improvement += (score - min_area)
                    probe_points = candidate
                    probe_bary[i] = to_bary(candidate[i])
                    probe_bary[j] = to_bary(candidate[j])
                    probe_bary[k] = to_bary(candidate[k])
                    probe_cache = update_triangle_cache(probe_points, probe_cache, [i, j, k])

        # Calculate improvement rate (normalize by iterations and scale)
        improvement_rate = initial_improvement / (probe_iterations * 1e-5) if probe_iterations > 0 else 0.0
        improvement_rate = min(1.0, improvement_rate)  # Cap at 1.0
        
        # Calibrate step parameters based on improvement rate
        # Harder problems (low improvement rate) get smaller steps but higher growth potential
        initial_step = 0.02 + 0.06 * (1.0 - improvement_rate)  # 0.02-0.08 range
        step_growth = 1.02 + 0.05 * improvement_rate          # 1.02-1.07 range
        step_decay = 0.98 - 0.03 * improvement_rate           # 0.95-0.98 range

        # MULTI-SCALE SEARCH SETUP
        # Create 3 search populations with different step sizes
        populations = [
            {'step_size': initial_step * 0.4, 'best': best.copy(), 'score': best_score, 'bary': bary_points.copy(),
             'cache': triangle_cache.copy(), 'stagnation': 0, 'boundary_power': 2.0},
            {'step_size': initial_step, 'best': best.copy(), 'score': best_score, 'bary': bary_points.copy(),
             'cache': triangle_cache.copy(), 'stagnation': 0, 'boundary_power': 2.5},
            {'step_size': initial_step * 2.5, 'best': best.copy(), 'score': best_score, 'bary': bary_points.copy(),
             'cache': triangle_cache.copy(), 'stagnation': 0, 'boundary_power': 3.0}
        ]
        
        # Track boundary move success rates for adaptation
        boundary_success = {'count': 0, 'success': 0}
        
        # Migration period based on difficulty
        migration_period = max(5, int(20 * (1.0 - improvement_rate)))
        iteration = 0
        max_iterations = 300
        n = 11
        
        # Adaptive restart threshold based on improvement momentum
        base_restart_threshold = 30
        adaptive_restart_threshold = int(base_restart_threshold * (1.0 + 0.5 * (1.0 - improvement_rate)))

        while iteration < max_iterations:
            # Process each population
            for pop_idx, population in enumerate(populations):
                step_size = population['step_size']
                best = population['best']
                best_score = population['score']
                bary_points = population['bary']
                triangle_cache = population['cache']
                stagnation_count = population['stagnation']
                boundary_power = population['boundary_power']
                
                # Get minimal triangles using cache
                min_triplets, min_area, triangle_cache = get_minimal_triangles(best, triangle_cache)
                
                if not min_triplets:
                    continue

                # Count vertex frequencies in minimal triangles
                freq = [0] * n
                for triplet in min_triplets:
                    for idx in triplet:
                        freq[idx] += 1
                
                # Sort vertices by frequency (descending)
                candidate_indices = sorted(range(n), key=lambda i: -freq[i])
                
                # Try to improve by perturbing critical vertices
                improved = False
                
                # First try geometric gradient moves on minimal triangles
                for triplet in min_triplets:
                    i, j, k = triplet
                    p_i, p_j, p_k = best[i], best[j], best[k]
                    
                    # Calculate gradient for area increase (0.5 * |(C-B) × (A-B)|)
                    # Gradient w.r.t. A is 0.5*(C-B) rotated 90 degrees
                    grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                    grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                    grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                    
                    # Apply boundary penalties to gradients
                    scale_i = get_boundary_penalty(p_i, boundary_power)
                    scale_j = get_boundary_penalty(p_j, boundary_power)
                    scale_k = get_boundary_penalty(p_k, boundary_power)
                    
                    # FIXED GRADIENT NORMALIZATION: preserve magnitude information
                    norm_i = np.linalg.norm(grad_i)
                    norm_j = np.linalg.norm(grad_j)
                    norm_k = np.linalg.norm(grad_k)
                    
                    if norm_i > 0: grad_i = grad_i * step_size / norm_i
                    if norm_j > 0: grad_j = grad_j * step_size / norm_j
                    if norm_k > 0: grad_k = grad_k * step_size / norm_k

                    grad_i = grad_i * scale_i
                    grad_j = grad_j * scale_j
                    grad_k = grad_k * scale_k

                    # Create candidate by moving points along gradients
                    candidate = best.copy()
                    candidate[i] += grad_i
                    candidate[j] += grad_j
                    candidate[k] += grad_k

                    # Check containment
                    if is_inside_triangle(candidate, A, B, C):
                        # Track boundary move success
                        if scale_i < 0.5 or scale_j < 0.5 or scale_k < 0.5:
                            boundary_success['count'] += 1
                        
                        score = get_smallest_triangle_area(candidate)
                        if score > best_score:
                            best = candidate
                            best_score = score
                            improved = True
                            stagnation_count = 0
                            
                            # Update caches
                            bary_points[i] = to_bary(candidate[i])
                            bary_points[j] = to_bary(candidate[j])
                            bary_points[k] = to_bary(candidate[k])
                            triangle_cache = update_triangle_cache(best, triangle_cache, [i, j, k])
                            
                            # Record success for boundary adaptation
                            if scale_i < 0.5 or scale_j < 0.5 or scale_k < 0.5:
                                boundary_success['success'] += 1
                            break

                if improved:
                    # Adaptive step size increase when improving
                    step_size = min(step_size * step_growth, initial_step * 2.0)
                    # Update population
                    populations[pop_idx] = {
                        'step_size': step_size,
                        'best': best,
                        'score': best_score,
                        'bary': bary_points,
                        'cache': triangle_cache,
                        'stagnation': stagnation_count,
                        'boundary_power': boundary_power
                    }
                    continue

                # STRATEGIC ORTHOGONAL PERTURBATIONS - diversify when gradients stall
                if not improved and np.random.random() < 0.2:
                    for triplet in min_triplets:
                        i, j, k = triplet
                        p_i, p_j, p_k = best[i], best[j], best[k]
                        
                        # Calculate gradient as before
                        grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                        grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                        grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                        
                        # Create orthogonal perturbation (rotate 90 degrees)
                        ortho_i = np.array([-grad_i[1], grad_i[0]])
                        ortho_j = np.array([-grad_j[1], grad_j[0]])
                        ortho_k = np.array([-grad_k[1], grad_k[0]])
                        
                        # Apply boundary penalties
                        scale_i = get_boundary_penalty(p_i, boundary_power)
                        scale_j = get_boundary_penalty(p_j, boundary_power)
                        scale_k = get_boundary_penalty(p_k, boundary_power)
                        
                        # FIXED NORMALIZATION FOR ORTHOGONAL PERTURBATIONS
                        norm_i = np.linalg.norm(ortho_i)
                        norm_j = np.linalg.norm(ortho_j)
                        norm_k = np.linalg.norm(ortho_k)
                        
                        if norm_i > 0: ortho_i = ortho_i * step_size / norm_i * scale_i
                        if norm_j > 0: ortho_j = ortho_j * step_size / norm_j * scale_j
                        if norm_k > 0: ortho_k = ortho_k * step_size / norm_k * scale_k

                        candidate = best.copy()
                        candidate[i] += ortho_i
                        candidate[j] += ortho_j
                        candidate[k] += ortho_k

                        if is_inside_triangle(candidate, A, B, C):
                            score = get_smallest_triangle_area(candidate)
                            if score > best_score:
                                best = candidate
                                best_score = score
                                improved = True
                                stagnation_count = 0
                                
                                # Update caches
                                bary_points[i] = to_bary(candidate[i])
                                bary_points[j] = to_bary(candidate[j])
                                bary_points[k] = to_bary(candidate[k])
                                triangle_cache = update_triangle_cache(best, triangle_cache, [i, j, k])
                                break

                if improved:
                    # Adaptive step size increase when improving
                    step_size = min(step_size * step_growth, initial_step * 2.0)
                    # Update population
                    populations[pop_idx] = {
                        'step_size': step_size,
                        'best': best,
                        'score': best_score,
                        'bary': bary_points,
                        'cache': triangle_cache,
                        'stagnation': stagnation_count,
                        'boundary_power': boundary_power
                    }
                    continue

                # If geometric moves didn't work, try Delaunay-based optimization
                try:
                    tri = Delaunay(best)
                    delaunay_triplets = []
                    for simplex in tri.simplices:
                        i, j, k = simplex
                        # Only consider triangles that are part of the Delaunay triangulation
                        delaunay_triplets.append((i, j, k))
                    
                    # Find minimal area among Delaunay triangles
                    min_delaunay_area = float('inf')
                    min_delaunay_triplets = []
                    for triplet in delaunay_triplets:
                        i, j, k = triplet
                        if (i, j, k) in triangle_cache:
                            area = triangle_cache[(i, j, k)]
                        else:
                            x1, y1 = best[i]
                            x2, y2 = best[j]
                            x3, y3 = best[k]
                            area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                            triangle_cache[(i, j, k)] = area
                        
                        if area < min_delaunay_area - 1e-9:
                            min_delaunay_area = area
                            min_delaunay_triplets = [triplet]
                        elif abs(area - min_delaunay_area) < 1e-9:
                            min_delaunay_triplets.append(triplet)
                    
                    if min_delaunay_triplets:
                        # Try to improve one of the minimal Delaunay triangles
                        for triplet in min_delaunay_triplets:
                            i, j, k = triplet
                            p_i, p_j, p_k = best[i], best[j], best[k]
                            
                            # Calculate gradient for area increase
                            grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                            grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                            grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                            
                            # Apply boundary penalties
                            scale_i = get_boundary_penalty(p_i, boundary_power)
                            scale_j = get_boundary_penalty(p_j, boundary_power)
                            scale_k = get_boundary_penalty(p_k, boundary_power)
                            
                            # FIXED GRADIENT NORMALIZATION
                            norm_i = np.linalg.norm(grad_i)
                            norm_j = np.linalg.norm(grad_j)
                            norm_k = np.linalg.norm(grad_k)
                            
                            if norm_i > 0: grad_i = grad_i * step_size / norm_i * scale_i
                            if norm_j > 0: grad_j = grad_j * step_size / norm_j * scale_j
                            if norm_k > 0: grad_k = grad_k * step_size / norm_k * scale_k

                            # Create candidate by moving points along gradients
                            candidate = best.copy()
                            candidate[i] += grad_i
                            candidate[j] += grad_j
                            candidate[k] += grad_k

                            # Check containment
                            if is_inside_triangle(candidate, A, B, C):
                                score = get_smallest_triangle_area(candidate)
                                if score > best_score:
                                    best = candidate
                                    best_score = score
                                    improved = True
                                    stagnation_count = 0
                                    
                                    # Update caches
                                    bary_points[i] = to_bary(candidate[i])
                                    bary_points[j] = to_bary(candidate[j])
                                    bary_points[k] = to_bary(candidate[k])
                                    triangle_cache = update_triangle_cache(best, triangle_cache, [i, j, k])
                                    break
                            
                    if improved:
                        # Adaptive step size increase when improving
                        step_size = min(step_size * step_growth, initial_step * 2.0)
                        # Update population
                        populations[pop_idx] = {
                            'step_size': step_size,
                            'best': best,
                            'score': best_score,
                            'bary': bary_points,
                            'cache': triangle_cache,
                            'stagnation': stagnation_count,
                            'boundary_power': boundary_power
                        }
                        continue
                except qhull.QhullError as e:
                    # Handle specific Delaunay triangulation errors
                    if "QH6154" in str(e) or "QH6013" in str(e):
                        # Near-degenerate case - apply small random perturbation and retry
                        candidate = best.copy()
                        for i in range(n):
                            u, v = bary_points[i]
                            du = np.random.normal(0, 0.005)
                            dv = np.random.normal(0, 0.005)
                            u_new, v_new = clamp_bary(u + du, v + dv)
                            candidate[i] = to_cart(u_new, v_new)
                        
                        if is_inside_triangle(candidate, A, B, C):
                            score = get_smallest_triangle_area(candidate)
                            if score > best_score:
                                best = candidate
                                best_score = score
                                improved = True
                                stagnation_count = 0
                                
                                # Update caches
                                bary_points = np.array([to_bary(p) for p in best])
                                triangle_cache = update_triangle_cache(best, triangle_cache, list(range(n)))
                                
                                # Update population
                                populations[pop_idx] = {
                                    'step_size': step_size,
                                    'best': best,
                                    'score': best_score,
                                    'bary': bary_points,
                                    'cache': triangle_cache,
                                    'stagnation': stagnation_count,
                                    'boundary_power': boundary_power
                                }
                    # Other errors are ignored and we continue with other strategies

                # If geometric and Delaunay moves didn't work, try barycentric perturbations
                for idx in candidate_indices:
                    if freq[idx] == 0:
                        break

                    # Get current barycentric coordinates
                    u, v = bary_points[idx]
                    
                    # Try multiple perturbations
                    for _ in range(3):
                        du = np.random.normal(0, step_size)
                        dv = np.random.normal(0, step_size)
                        u_new, v_new = clamp_bary(u + du, v + dv)
                        
                        # Convert back to Cartesian
                        candidate = best.copy()
                        candidate[idx] = to_cart(u_new, v_new)
                        
                        # Check if valid and better
                        if is_inside_triangle(candidate, A, B, C):
                            score = get_smallest_triangle_area(candidate)
                            if score > best_score:
                                best = candidate
                                best_score = score
                                bary_points[idx] = [u_new, v_new]
                                improved = True
                                stagnation_count = 0
                                
                                # Update triangle cache
                                triangle_cache = update_triangle_cache(best, triangle_cache, [idx])
                                break
                    
                    if improved:
                        break

                if improved:
                    # Adaptive step size increase when improving
                    step_size = min(step_size * step_growth, initial_step * 2.0)
                else:
                    # Adaptive step size decay based on configuration difficulty
                    step_size *= step_decay
                    stagnation_count += 1

                    # ADAPTIVE RESTART MECHANISM - scales with stagnation severity
                    if stagnation_count >= adaptive_restart_threshold:
                        # Scale restart step with stagnation severity (exponential)
                        stagnation_factor = (stagnation_count - adaptive_restart_threshold) / 10.0
                        restart_step = initial_step * 0.1 * (1.2 ** stagnation_factor)
                        
                        candidate = best.copy()
                        for i in range(n):
                            u, v = bary_points[i]
                            du = np.random.normal(0, restart_step)
                            dv = np.random.normal(0, restart_step)
                            u_new, v_new = clamp_bary(u + du, v + dv)
                            candidate[i] = to_cart(u_new, v_new)
                        
                        if is_inside_triangle(candidate, A, B, C):
                            score = get_smallest_triangle_area(candidate)
                            if score > best_score:
                                best = candidate
                                best_score = score
                                bary_points = np.array([to_bary(p) for p in best])
                                triangle_cache = update_triangle_cache(best, triangle_cache, list(range(n)))
                        
                        # Reset search parameters with adaptive values
                        step_size = initial_step * 0.2
                        stagnation_count = 0

                # Reset step size if too small
                if step_size < 1e-5:
                    step_size = initial_step * 0.2

                # Update population
                populations[pop_idx] = {
                    'step_size': step_size,
                    'best': best,
                    'score': best_score,
                    'bary': bary_points,
                    'cache': triangle_cache,
                    'stagnation': stagnation_count,
                    'boundary_power': boundary_power
                }

            # PERIODIC POPULATION MIGRATION
            if iteration % migration_period == 0 and iteration > 0:
                # Find best solution across all populations
                best_pop_idx = np.argmax([pop['score'] for pop in populations])
                best_solution = populations[best_pop_idx]['best']
                best_score = populations[best_pop_idx]['score']
                
                # Migrate to other populations if it improves them
                for pop_idx in range(len(populations)):
                    if pop_idx != best_pop_idx:
                        # Only migrate if it improves the target population
                        if best_score > populations[pop_idx]['score']:
                            # Copy the solution but adapt step size to target population's scale
                            target_step = populations[pop_idx]['step_size']
                            populations[pop_idx]['best'] = best_solution.copy()
                            populations[pop_idx]['score'] = best_score
                            populations[pop_idx]['bary'] = np.array([to_bary(p) for p in best_solution])
                            # Update cache for the new solution
                            _, _, populations[pop_idx]['cache'] = get_minimal_triangles(best_solution, {})
                            populations[pop_idx]['stagnation'] = 0

            # ADAPTIVE BOUNDARY POWER BASED ON SUCCESS RATE
            if boundary_success['count'] > 10:
                success_rate = boundary_success['success'] / boundary_success['count']
                # If success rate is low, reduce boundary power (softer penalty near edges)
                if success_rate < 0.3:
                    for pop in populations:
                        pop['boundary_power'] = max(1.5, pop['boundary_power'] * 0.9)
                # If success rate is high, increase boundary power (stronger penalty)
                elif success_rate > 0.7:
                    for pop in populations:
                        pop['boundary_power'] = min(4.0, pop['boundary_power'] * 1.1)
                # Reset counters
                boundary_success = {'count': 0, 'success': 0}

            iteration += 1

        # Return the best solution across all populations
        best_idx = np.argmax([pop['score'] for pop in populations])
        return populations[best_idx]['best']

    return improve