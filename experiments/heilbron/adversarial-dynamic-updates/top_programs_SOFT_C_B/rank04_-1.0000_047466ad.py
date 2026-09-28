from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.spatial import Delaunay

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

    def get_weighted_minimal_triangles(points, cache=None, temperature=0.001):
        """Get minimal area triangles with exponential weighting based on area difference."""
        n = len(points)
        min_area = float('inf')
        areas = {}
        
        # Initialize cache if not provided
        if cache is None:
            cache = {}
            
        # Compute all triangle areas if not in cache
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    if (i, j, k) not in cache:
                        x1, y1 = points[i]
                        x2, y2 = points[j]
                        x3, y3 = points[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        cache[(i, j, k)] = area
                    areas[(i, j, k)] = cache[(i, j, k)]
                    
                    if cache[(i, j, k)] < min_area:
                        min_area = cache[(i, j, k)]

        # Calculate weights using softmax
        weighted_triplets = []
        for triplet, area in areas.items():
            # Weight proportional to exp(-(area - min_area)/temperature)
            weight = np.exp(-(area - min_area) / max(temperature, 1e-9))
            weighted_triplets.append((triplet, weight))
        
        # Sort by weight descending
        weighted_triplets.sort(key=lambda x: -x[1])
        
        return weighted_triplets, min_area, cache

    def get_boundary_penalty(p):
        """Returns scaling factors for x and y components based on boundary proximity."""
        u, v = to_bary(p)
        w = 1 - u - v
        
        # Distance to each boundary (0 = on boundary, 1 = centroid)
        dist_to_AB = w
        dist_to_AC = v
        dist_to_BC = u
        
        # Get nearest boundary distance
        min_dist = min(dist_to_AB, dist_to_AC, dist_to_BC)
        
        # Smooth scaling factor (1.0 at center, approaches 0 near boundaries)
        # Using cubic function for smooth transition
        scale_factor = 1.0 - (1.0 - min_dist)**3
        
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

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        initial_score = best_score
n        # Convert all points to barycentric for internal processing
        bary_points = np.array([to_bary(p) for p in best])
        
        # Initialize triangle cache
        triangle_cache = {}
        _, _, triangle_cache = get_weighted_minimal_triangles(best, triangle_cache)
        
        # Adaptive step size calibration based on initial improvement rate
        # First analyze improvement potential with small steps
        calibration_steps = 20
        calibration_score = best_score
        for cal_step in range(calibration_steps):
            # Get weighted minimal triangles
            weighted_triplets, min_area, triangle_cache = get_weighted_minimal_triangles(best, triangle_cache)
            
            if not weighted_triplets:
                break

            # Try gradient move on top triangle
            triplet, _ = weighted_triplets[0]
            i, j, k = triplet
            p_i, p_j, p_k = best[i], best[j], best[k]
            
            # Calculate gradient for area increase
            grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
            grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
            grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
            
            # Apply boundary penalties
            scale_i = get_boundary_penalty(p_i)
            scale_j = get_boundary_penalty(p_j)
            scale_k = get_boundary_penalty(p_k)
            
            grad_i = grad_i * scale_i
            grad_j = grad_j * scale_j
            grad_k = grad_k * scale_k

            # Normalize and scale with small step
            step = 0.01
            norm_i = np.linalg.norm(grad_i)
            norm_j = np.linalg.norm(grad_j)
            norm_k = np.linalg.norm(grad_k)
            
            if norm_i > 0: grad_i = grad_i / norm_i * step
            if norm_j > 0: grad_j = grad_j / norm_j * step
            if norm_k > 0: grad_k = grad_k / norm_k * step

            # Create candidate
            candidate = best.copy()
            candidate[i] += grad_i
            candidate[j] += grad_j
            candidate[k] += grad_k

            # Check containment
            if is_inside_triangle(candidate, A, B, C):
                score = get_smallest_triangle_area(candidate)
                if score > calibration_score:
                    calibration_score = score

        # Calculate improvement rate for step size calibration
        improvement_rate = max(0, (calibration_score - initial_score) / (initial_score + 1e-9))
        initial_step = 0.05 * (1 + improvement_rate)
        step_size = initial_step
        
        # Initialize gradient history for momentum
        momentum = 0.85
        grad_history = [np.zeros(2) for _ in range(11)]
        
        stagnation_count = 0
        max_iterations = 300
        tol = 1e-9
        n = 11
        restart_threshold = 35
        
        for _ in range(max_iterations):
            # Get weighted minimal triangles
            weighted_triplets, min_area, triangle_cache = get_weighted_minimal_triangles(best, triangle_cache, 
                temperature=0.001 * initial_score)
            
            if not weighted_triplets:
                break

            # Count vertex frequencies in minimal triangles
            freq = [0] * n
            total_weight = 0
            for (triplet, weight) in weighted_triplets:
                for idx in triplet:
                    freq[idx] += weight
                total_weight += weight
            
            # Normalize frequencies
            if total_weight > 0:
                for i in range(n):
                    freq[i] /= total_weight
            
            # Sort vertices by frequency (descending)
            candidate_indices = sorted(range(n), key=lambda i: -freq[i])
            
            # Try to improve by perturbing critical vertices
            improved = False
            
            # First try geometric gradient moves on minimal triangles
            for (triplet, weight) in weighted_triplets:
                i, j, k = triplet
                p_i, p_j, p_k = best[i], best[j], best[k]
                
                # Calculate gradient for area increase
                grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                
                # Apply boundary penalties to gradients
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
                
                if norm_i > 0: grad_i = grad_i / norm_i * step_size * weight
                if norm_j > 0: grad_j = grad_j / norm_j * step_size * weight
                if norm_k > 0: grad_k = grad_k / norm_k * step_size * weight

                # Update gradient history with momentum
                grad_history[i] = momentum * grad_history[i] + (1 - momentum) * grad_i
                grad_history[j] = momentum * grad_history[j] + (1 - momentum) * grad_j
                grad_history[k] = momentum * grad_history[k] + (1 - momentum) * grad_k

                # Create candidate by moving points along gradients
                candidate = best.copy()
                candidate[i] += grad_history[i]
                candidate[j] += grad_history[j]
                candidate[k] += grad_history[k]

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
                # Gradual step size increase when improving (5% growth)
                step_size = min(step_size * 1.05, initial_step * 1.5)
                continue

            # If geometric moves didn't work, try orthogonal perturbations (20% probability)
            if np.random.random() < 0.2:
                for (triplet, weight) in weighted_triplets:
                    i, j, k = triplet
                    p_i, p_j, p_k = best[i], best[j], best[k]
                    
                    # Calculate gradient for area increase
                    grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                    grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                    grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])
                    
                    # Create orthogonal directions
                    ortho_i = np.array([-grad_i[1], grad_i[0]]) * 0.3 * step_size
                    ortho_j = np.array([-grad_j[1], grad_j[0]]) * 0.3 * step_size
                    ortho_k = np.array([-grad_k[1], grad_k[0]]) * 0.3 * step_size

                    # Create candidate by moving points along orthogonal directions
                    candidate = best.copy()
                    candidate[i] += ortho_i
                    candidate[j] += ortho_j
                    candidate[k] += ortho_k

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
                    step_size = min(step_size * 1.05, initial_step * 1.5)
                    continue

            # If geometric and orthogonal moves didn't work, try Delaunay-based optimization
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
                    
                    if area < min_delaunay_area - tol:
                        min_delaunay_area = area
                        min_delaunay_triplets = [triplet]
                    elif abs(area - min_delaunay_area) < tol:
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
                        
                        if norm_i > 0: grad_i = grad_i / norm_i * step_size
                        if norm_j > 0: grad_j = grad_j / norm_j * step_size
                        if norm_k > 0: grad_k = grad_k / norm_k * step_size

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
                    # Gradual step size increase when improving (5% growth)
                    step_size = min(step_size * 1.05, initial_step * 1.5)
                    continue
            except:
                # Fall back to other strategies if Delaunay fails
                pass

            # If all above didn't work, try barycentric perturbations
            for idx in candidate_indices:
                if freq[idx] < 0.1:  # Only consider vertices with meaningful frequency
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
                # Gradual step size increase when improving (5% growth)
                step_size = min(step_size * 1.05, initial_step * 1.5)
            else:
                # Gradual step size decay when not improving (2% decay - slower than growth)
                step_size *= 0.98
                stagnation_count += 1

                # Enhanced adaptive restart mechanism
                if stagnation_count >= restart_threshold:
                    # Scale restart step with stagnation severity (exponential growth)
                    restart_level = stagnation_count // restart_threshold
                    restart_step = 0.1 * initial_step * (1.5 ** restart_level)
                    
                    candidate = best.copy()
                    for i in range(n):
                        u, v = bary_points[i]
                        du = np.random.normal(0, restart_step)
                        dv = np.random.normal(0, restart_step)
                        
                        # Add historical gradient bias to restarts
                        if np.linalg.norm(grad_history[i]) > 1e-5:
                            direction = grad_history[i] / np.linalg.norm(grad_history[i])
                            du += 0.4 * direction[0] * restart_step
                            dv += 0.4 * direction[1] * restart_step

                        u_new, v_new = clamp_bary(u + du, v + dv)
                        candidate[i] = to_cart(u_new, v_new)
                    
                    if is_inside_triangle(candidate, A, B, C):
                        score = get_smallest_triangle_area(candidate)
                        if score > best_score:
                            best = candidate
                            best_score = score
                            bary_points = np.array([to_bary(p) for p in best])
                            triangle_cache = update_triangle_cache(best, triangle_cache, list(range(n)))
                    
                    # Reset search parameters
                    step_size = 0.1 * initial_step
                    stagnation_count = 0

            # Reset step size if too small
            if step_size < 1e-5:
                step_size = 0.1 * initial_step

        return best

    return improve