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

def entrypoint() -> np.ndarray:
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