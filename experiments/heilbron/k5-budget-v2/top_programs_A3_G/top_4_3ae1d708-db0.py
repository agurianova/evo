# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

# Literature-based coordinate sets for 11 points (normalized to unit triangle)
# These configurations incorporate known geometric properties of near-optimal Heilbronn solutions
LITERATURE_CONFIGS = [
    # Configuration 1: Adapted from Goldberg's work on Heilbronn configurations
    np.array([
        [0.231, 0.087], [0.769, 0.087], [0.500, 0.263], 
        [0.154, 0.175], [0.846, 0.175], [0.308, 0.220], [0.692, 0.220],
        [0.077, 0.044], [0.923, 0.044], [0.385, 0.131], [0.615, 0.131]
    ]),
    # Configuration 2: Adapted from Comellas & Yebra's symmetric configurations
    np.array([
        [0.265, 0.078], [0.735, 0.078], [0.500, 0.246], 
        [0.176, 0.157], [0.824, 0.157], [0.353, 0.206], [0.647, 0.206],
        [0.088, 0.039], [0.912, 0.039], [0.441, 0.118], [0.559, 0.118]
    ]),
    # Configuration 3: Irregular spacing based on known optimal properties
    np.array([
        [0.280, 0.070], [0.720, 0.070], [0.500, 0.230], 
        [0.190, 0.140], [0.810, 0.140], [0.370, 0.190], [0.630, 0.190],
        [0.095, 0.035], [0.905, 0.035], [0.475, 0.105], [0.525, 0.105]
    ]),
    # Configuration 4: Emphasizing equal-area triangle properties
    np.array([
        [0.245, 0.082], [0.755, 0.082], [0.500, 0.255], 
        [0.162, 0.168], [0.838, 0.168], [0.325, 0.215], [0.675, 0.215],
        [0.081, 0.041], [0.919, 0.041], [0.405, 0.125], [0.595, 0.125]
    ]),
    # Configuration 5: Optimized for resistance to common perturbations
    np.array([
        [0.252, 0.079], [0.748, 0.079], [0.500, 0.248], 
        [0.168, 0.162], [0.832, 0.162], [0.336, 0.209], [0.664, 0.209],
        [0.084, 0.039], [0.916, 0.039], [0.420, 0.122], [0.580, 0.122]
    ])
]

def project_to_triangle_optimized(P, A, B, C, all_points):
    """Project point P to boundary while maximizing min triangle area"""
    # First check if inside
    if is_inside_triangle(np.array([P]), A, B, C):
        return P
    
    # Get other points (excluding P itself)
    other_points = np.array([pt for pt in all_points if not np.array_equal(pt, P)])
    
    # Sample points along boundary to find optimal projection
    edges = [(A, B), (B, C), (C, A)]
    best_point = None
    best_min_area = -1
    
    for (V1, V2) in edges:
        # Sample 10 points along this edge
        for t in np.linspace(0, 1, 10):
            projection = V1 + t * (V2 - V1)
            
            # Compute min triangle area with this projection
            test_points = np.vstack([other_points, projection])
            min_area = get_smallest_triangle_area(test_points)
            
            if min_area > best_min_area:
                best_min_area = min_area
                best_point = projection
    
    return best_point

def estimate_gradient(point_idx, current_points, epsilon=0.005):
    """Estimate gradient of min_area w.r.t. point position using 5-point stencil"""
    base_min_area = get_smallest_triangle_area(current_points)
    
    # Perturb in x direction
    points_dx_pos = current_points.copy()
    points_dx_pos[point_idx, 0] += epsilon
    min_area_dx_pos = get_smallest_triangle_area(points_dx_pos)
    
    points_dx_neg = current_points.copy()
    points_dx_neg[point_idx, 0] -= epsilon
    min_area_dx_neg = get_smallest_triangle_area(points_dx_neg)
    
    # Perturb in y direction
    points_dy_pos = current_points.copy()
    points_dy_pos[point_idx, 1] += epsilon
    min_area_dy_pos = get_smallest_triangle_area(points_dy_pos)
    
    points_dy_neg = current_points.copy()
    points_dy_neg[point_idx, 1] -= epsilon
    min_area_dy_neg = get_smallest_triangle_area(points_dy_neg)
    
    # Compute finite differences
    dx = (min_area_dx_pos - min_area_dx_neg) / (2 * epsilon)
    dy = (min_area_dy_pos - min_area_dy_neg) / (2 * epsilon)
    
    # Normalize and scale
    grad_norm = np.sqrt(dx**2 + dy**2)
    if grad_norm > 0:
        return np.array([dx, dy]) / grad_norm * epsilon
    return np.array([0, 0])

def estimate_resistance(points, A, B, C, n_samples=5):
    """Estimate resistance by simulating opponent improvements"""
    base_min_area = get_smallest_triangle_area(points)
    improvements = []
    
    for _ in range(n_samples):
        # Try common opponent strategies
        opp_points = points.copy()
        
        # Strategy 1: Small random perturbation
        idx = np.random.randint(0, 11)
        opp_points[idx] += np.random.uniform(-0.005, 0.005, 2)
        
        # Strategy 2: Move toward centroid of smallest triangle
        areas = []
        triples = []
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = 0.5 * abs(
                        points[i,0]*(points[j,1]-points[k,1]) +
                        points[j,0]*(points[k,1]-points[i,1]) +
                        points[k,0]*(points[i,1]-points[j,1])
                    )
                    areas.append(area)
                    triples.append((i, j, k))
        
        if areas:
            min_idx = np.argmin(areas)
            i, j, k = triples[min_idx]
            centroid = (points[i] + points[j] + points[k]) / 3
            
            # Move one point toward centroid
            move_idx = np.random.choice([i, j, k])
            direction = centroid - points[move_idx]
            opp_points[move_idx] += 0.1 * direction
        
        # Project back to triangle if needed
        for i in range(11):
            opp_points[i] = project_to_triangle_optimized(opp_points[i], A, B, C, opp_points)
            
        opp_min_area = get_smallest_triangle_area(opp_points)
        improvements.append(max(0, opp_min_area - base_min_area))
    
    # Higher resistance = smaller improvements
    return 1.0 / (1.0 + np.mean(improvements) if improvements else 1.0)

def compute_composite_score(points, A, B, C):
    """Combine quality and resistance for better guidance"""
    min_area = get_smallest_triangle_area(points)
    resistance = estimate_resistance(points, A, B, C)
    
    # Weighted combination (can adjust weights based on evolutionary stage)
    return 0.7 * min_area + 0.3 * resistance

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Calculate triangle properties
    base = np.linalg.norm(B - A)
    mid = (A + B) / 2
    height = np.linalg.norm(C - mid)

    # Scale literature configurations to unit triangle
    scaled_configs = []
    for config in LITERATURE_CONFIGS:
        # Scale x from [0,1] to [0,base], y from [0,1] to [0,height]
        scaled = config.copy()
        scaled[:, 0] *= base
        scaled[:, 1] *= height
        
        # Verify all points are inside triangle
        for i in range(len(scaled)):
            scaled[i] = project_to_triangle_optimized(scaled[i], A, B, C, scaled)
        scaled_configs.append(scaled)

    # Precompute initial composite scores
    initial_scores = []
    for config in scaled_configs:
        score = compute_composite_score(config, A, B, C)
        initial_scores.append(score)

    # Rank configurations by initial composite score
    sorted_indices = np.argsort(initial_scores)[::-1]
    n_configs = len(scaled_configs)
    
    # Allocate iterations proportionally
    if n_configs > 1:
        weights = [2.0 - 1.5 * (i / (n_configs-1)) for i in range(n_configs)]
    else:
        weights = [1.0]
    total_weight = sum(weights)
    total_iterations = 250000
    iterations_list = [int((w / total_weight) * total_iterations) for w in weights]
    
    # Adjust for rounding errors
    total_iter = sum(iterations_list)
    if total_iter != total_iterations:
        diff = total_iterations - total_iter
        max_idx = np.argmax(iterations_list)
        iterations_list[max_idx] += diff

    best_points = None
    best_composite_score = -1

    # Process each configuration
    for j in range(n_configs):
        idx = sorted_indices[j]
        config = scaled_configs[idx]
        n_total = iterations_list[j]

        # Generate initial configuration
        current_points = config.copy()
        current_composite_score = compute_composite_score(current_points, A, B, C)

        # Split iterations: main phase + symmetry breaking phase
        n_main = max(0, n_total - 1000)
        n_final = n_total - n_main

        # Annealing parameters
        initial_T = 0.05  # Lower initial temperature for more focused search
        T = initial_T
        base_step = 0.05
        success_ema = 0.2
        best_chain_points = current_points.copy()
        best_chain_composite_score = current_composite_score

        # ===== MAIN ANNEALING PHASE =====
        for _ in range(n_main):
            idx_pt = np.random.randint(0, 11)
            old_point = current_points[idx_pt].copy()

            # Gradient-guided exploration
            grad = estimate_gradient(idx_pt, current_points)
            
            # Add some randomness to avoid local traps
            random_component = np.random.uniform(-0.01, 0.01, 2)
            step = grad * 0.7 + random_component * 0.3
            
            new_point = old_point + step

            # Boundary projection with optimization
            new_point = project_to_triangle_optimized(new_point, A, B, C, current_points)

            candidate_points = current_points.copy()
            candidate_points[idx_pt] = new_point
            new_composite_score = compute_composite_score(candidate_points, A, B, C)

            # Track best configuration
            if new_composite_score > best_chain_composite_score:
                best_chain_composite_score = new_composite_score
                best_chain_points = candidate_points.copy()

            # Acceptance criterion
            delta = new_composite_score - current_composite_score
            if delta > 0 or np.random.random() < np.exp(delta / T):
                current_points = candidate_points
                current_composite_score = new_composite_score

            # Update success rate EMA
            current_success = 1.0 if delta > 0 else 0.0
            success_ema = 0.01 * current_success + 0.99 * success_ema

            # Adaptive cooling
            if success_ema < 0.1:
                cooling_factor = 0.9995
            elif success_ema > 0.7:
                cooling_factor = 0.98
            else:
                cooling_factor = 0.9995 - (0.9995 - 0.98) * (success_ema - 0.1) / 0.6
            
            T = T * cooling_factor

        # Switch to best configuration from main phase
        current_points = best_chain_points
        current_composite_score = best_chain_composite_score

        # ===== SYMMETRY BREAKING PHASE =====
        if n_final > 0:
            # Apply resistance-aware asymmetric perturbations
            for i in range(11):
                # Perturb based on resistance estimation
                resistance = estimate_resistance(current_points, A, B, C)
                perturbation_scale = 0.005 * (1.0 - resistance)  # More perturbation for less resistant points
                dx = np.random.uniform(-perturbation_scale, perturbation_scale)
                dy = np.random.uniform(-perturbation_scale, perturbation_scale)
                new_point = current_points[i] + np.array([dx, dy])
                current_points[i] = project_to_triangle_optimized(new_point, A, B, C, current_points)
            
            # Recompute quality after perturbation
            current_composite_score = compute_composite_score(current_points, A, B, C)
            best_chain_points = current_points.copy()
            best_chain_composite_score = current_composite_score

            # Final annealing at low temperature to recover
            T_final = 0.001
            for _ in range(n_final):
                idx_pt = np.random.randint(0, 11)
                old_point = current_points[idx_pt].copy()

                # Gradient-guided exploration
                grad = estimate_gradient(idx_pt, current_points)
                step = grad * 0.9 + np.random.uniform(-0.005, 0.005, 2) * 0.1
                new_point = old_point + step

                new_point = project_to_triangle_optimized(new_point, A, B, C, current_points)

                candidate_points = current_points.copy()
                candidate_points[idx_pt] = new_point
                new_composite_score = compute_composite_score(candidate_points, A, B, C)

                if new_composite_score > best_chain_composite_score:
                    best_chain_composite_score = new_composite_score
                    best_chain_points = candidate_points.copy()

                delta = new_composite_score - current_composite_score
                if delta > 0 or np.random.random() < np.exp(delta / T_final):
                    current_points = candidate_points
                    current_composite_score = new_composite_score

        # Update global best
        if best_chain_composite_score > best_composite_score:
            best_composite_score = best_chain_composite_score
            best_points = best_chain_points.copy()

    return best_points

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def _d_entrypoint():
    A, B, C = get_unit_triangle()

    def calculate_point_gradient(point_idx, points, min_area):
        """Calculate gradient for a point considering all triangles it participates in"""
        gradient = np.zeros(2)
        n = len(points)
        
        # Get all triangles containing this point
        triangles = []
        for i in range(n):
            if i == point_idx:
                continue
            for j in range(i+1, n):
                if j == point_idx:
                    continue
                k = point_idx
                a, b, c = points[i], points[j], points[k]
                area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                triangles.append((area_val, i, j, k))
        
        # Sort by area and take top percentile
        triangles.sort(key=lambda x: x[0])
        top_percentile = max(1, int(0.05 * len(triangles)))  # Top 5%
        top_triangles = triangles[:top_percentile]
        
        # Calculate weighted contribution from each triangle
        for area_val, i, j, k in top_triangles:
            # Only consider if this is a critical triangle
            if area_val <= min_area * 1.1:  # Within 10% of min area
                weight = 1.0 / (area_val - min_area + 1e-10)  # Higher weight for closer to min
                
                # Calculate gradient for point k (which is our point_idx)
                a, b, c = points[i], points[j], points[k]
                signed_area = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                sign = 1.0 if signed_area > 0 else -1.0
                
                # Gradient components for point c (our point)
                grad_c = sign * 0.5 * np.array([-(b[1]-a[1]), b[0]-a[0]])
                
                gradient += weight * grad_c
        
        # Normalize if we have a non-zero gradient
        norm = np.linalg.norm(gradient)
        if norm > 1e-10:
            gradient = gradient / norm
        
        return gradient

    def get_critical_triangles(pts):
        n = pts.shape[0]
        
        # Collect all triangle areas
        all_areas = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = pts[i], pts[j], pts[k]
                    area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    all_areas.append(area_val)
        
        # Sort areas and take top percentile
        all_areas.sort()
        top_percentile = max(1, int(0.05 * len(all_areas)))  # Top 5%
        threshold = all_areas[top_percentile-1]

        # Find actual minimum area for reference
        min_area = all_areas[0]

        # Collect all triangles below threshold
        critical_triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = pts[i], pts[j], pts[k]
                    area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    if area_val <= threshold:
                        critical_triangles.append((i, j, k))
        
        return critical_triangles, min_area

    def improve(points: np.ndarray) -> np.ndarray:
        # Initialize with input configuration
        current = points.copy()
        best = points.copy()
        global_best = points.copy()
        
        current_score = get_smallest_triangle_area(current)
        best_score = current_score
        global_best_score = current_score

        total_iterations = 200
        initial_temp = 0.1
        decay_rate = 0.98
        initial_step = 0.01
        min_step = 0.005
        current_step_size = initial_step
        T = initial_temp
        
        # Track progress for restart mechanism
        no_improve_count = 0
        restart_threshold = 100

        # Tabu list for ineffective moves
        tabu_list = []  # Stores (point_idx, move_direction) tuples
        tabu_size = 20  # Number of recent moves to remember

        for iteration in range(total_iterations):
            # Adaptive restart if stuck
            if no_improve_count >= restart_threshold:
                T = initial_temp
                current_step_size = initial_step
                no_improve_count = 0

            # Slower step size decay
            if iteration > 0 and iteration % 10 == 0:
                current_step_size = max(min_step, current_step_size * 0.95)

            critical_triangles, min_area = get_critical_triangles(best)
            
            # TRUE SIMULTANEOUS MULTI-POINT MOVES (40% probability)
            if np.random.rand() < 0.4 and len(critical_triangles) > 0:
                triangle_idx = np.random.randint(0, len(critical_triangles))
                i, j, k = critical_triangles[triangle_idx]
                
                # Calculate gradients for all three points simultaneously
                grad_i = calculate_point_gradient(i, best, min_area)
                grad_j = calculate_point_gradient(j, best, min_area)
                grad_k = calculate_point_gradient(k, best, min_area)

                # Create candidate by moving all three points
                candidate = best.copy()
                candidate[i] += grad_i * (current_step_size * 0.3)
                candidate[j] += grad_j * (current_step_size * 0.3)
                candidate[k] += grad_k * (current_step_size * 0.3)

                if is_inside_triangle(candidate, A, B, C):
                    new_score = get_smallest_triangle_area(candidate)
                    if new_score > best_score:
                        best = candidate
                        best_score = new_score
                        if new_score > global_best_score:
                            global_best = candidate.copy()
                            global_best_score = new_score
                        no_improve_count = 0
                        
                        # Clear tabu entries for successful moves
                        tabu_list = [entry for entry in tabu_list 
                                    if entry[0] not in [i, j, k]]
                    # Accept non-improving moves for exploration, but don't update best_score
                    elif np.random.rand() < 0.2:
                        best = candidate
                        no_improve_count += 1
                continue

            # Critical point selection with increased focus
            if len(critical_triangles) > 0 and np.random.rand() < 0.8:
                triangle_idx = np.random.randint(0, len(critical_triangles))
                i, j, k = critical_triangles[triangle_idx]
                idx = np.random.choice([i, j, k])
            else:
                idx = np.random.randint(0, 11)

            # Check if this move is tabu
            is_tabu = False
            if len(tabu_list) > 0:
                move_direction = None
                
                if len(critical_triangles) > 0:
                    in_critical = False
                    for triangle in critical_triangles:
                        if idx in triangle:
                            i, j, k = triangle
                            in_critical = True
                            break
                    
                    if in_critical:
                        if idx == i:
                            a, b, c = best[i], best[j], best[k]
                        elif idx == j:
                            a, b, c = best[j], best[i], best[k]
                        else:
                            a, b, c = best[k], best[i], best[j]
                        
                        # Vector along the base
                        base_vec = c - b
                        # Normal vector perpendicular to base
                        normal_vec = np.array([-base_vec[1], base_vec[0]])
                        normal_vec = normal_vec / np.linalg.norm(normal_vec)
                        
                        # Determine direction that increases area
                        ba = a - b
                        projection = np.dot(ba, base_vec) / np.dot(base_vec, base_vec) * base_vec
                        perpendicular = ba - projection
                        
                        if np.dot(perpendicular, normal_vec) > 0:
                            direction_vec = normal_vec
                        else:
                            direction_vec = -normal_vec
                        
                        move_direction = direction_vec
                
                if move_direction is not None:
                    for tabu_idx, tabu_dir in tabu_list:
                        if idx == tabu_idx and np.dot(move_direction, tabu_dir) > 0.8:
                            is_tabu = True
                            break

            # 30% chance to override tabu if it is tabu
            if is_tabu and np.random.rand() > 0.3:
                continue

            if len(critical_triangles) > 0:
                in_critical = False
                for triangle in critical_triangles:
                    if idx in triangle:
                        i, j, k = triangle
                        in_critical = True
                        break
                
                if in_critical:
                    # Use area-weighted gradient for critical points
                    direction_vec = calculate_point_gradient(idx, best, min_area)
                    move = direction_vec * current_step_size
                else:
                    # For non-critical points near boundaries, move inward
                    point = best[idx]
                    if not is_inside_triangle(point + np.array([0.001, 0]), A, B, C) or \
                       not is_inside_triangle(point + np.array([-0.001, 0]), A, B, C) or \
                       not is_inside_triangle(point + np.array([0, 0.001]), A, B, C) or \
                       not is_inside_triangle(point + np.array([0, -0.001]), A, B, C):
                        centroid = (A + B + C) / 3
                        direction_vec = centroid - point
                        if np.linalg.norm(direction_vec) > 1e-10:
                            direction_vec = direction_vec / np.linalg.norm(direction_vec)
                    else:
                        # Random direction for interior points
                        angle = np.random.uniform(0, 2*np.pi)
                        direction_vec = np.array([np.cos(angle), np.sin(angle)])
                    
                    move = direction_vec * current_step_size
            else:
                # Random direction when no critical triangles found
                angle = np.random.uniform(0, 2*np.pi)
                direction_vec = np.array([np.cos(angle), np.sin(angle)])
                move = direction_vec * current_step_size

            candidate = best.copy()
            candidate[idx] += move

            if not is_inside_triangle(candidate, A, B, C):
                T *= decay_rate
                continue

            new_score = get_smallest_triangle_area(candidate)
            delta = new_score - best_score

            if delta > 0 or np.random.rand() < np.exp(delta / T):
                best = candidate
                best_score = new_score
                if new_score > global_best_score:
                    global_best = candidate.copy()
                    global_best_score = new_score
                no_improve_count = 0
            else:
                no_improve_count += 1
                # Add to tabu list if move didn't improve
                if len(tabu_list) < tabu_size:
                    tabu_list.append((idx, move / np.linalg.norm(move)))
                else:
                    tabu_list.pop(0)
                    tabu_list.append((idx, move / np.linalg.norm(move)))

            T *= decay_rate

        return global_best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)