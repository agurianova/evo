import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from itertools import combinations

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Calculate triangle geometry properties
    base = np.linalg.norm(B - A)
    height = np.sqrt(3)/2 * base
    area_target = 0.0365
    
    # Strategic initialization with adaptive ring configuration based on Heilbronn research
    points = np.zeros((11, 2))
    center = (A + B + C) / 3
    
    # ADAPTIVE RING ALLOCATION: 3-4-4 configuration based on research for 11 points
    # Center ring: 3 points
    # Inner ring: 4 points
    # Outer ring: 4 points
    
    # THEORETICAL RADIUS RATIOS based on known optimal configurations
    # For equilateral triangle, optimal spacing follows theoretical expectations
    radius_inner = 0.33 * height / np.sqrt(3)
    radius_outer = 0.65 * height / np.sqrt(3)

    # Center points (3 points with strategic asymmetry)
    for i in range(3):
        # Asymmetric placement with controlled randomness
        angle = 2 * np.pi * i / 3 + 0.1 * np.random.uniform(-1, 1)
        jitter = 0.05 * height * np.random.uniform(0, 0.2)
        x = jitter * np.cos(angle)
        y = jitter * np.sin(angle)
        
        # Rotate to align with triangle orientation
        x_rot = -y
        y_rot = x
        
        points[i] = center + np.array([x_rot, y_rot])

    # Inner ring points (4 points)
    for i in range(4):
        # STRATEGIC SYMMETRY BREAKING: 10% angle jitter
        angle_jitter = 0.1 * np.random.uniform(-1, 1) * 2 * np.pi / 4
        angle = 2 * np.pi * i / 4 + angle_jitter
        x = radius_inner * np.cos(angle)
        y = radius_inner * np.sin(angle)
        
        # Rotate and translate to fit triangle orientation
        x_rot = -y
        y_rot = x
        
        points[i+3] = center + np.array([x_rot, y_rot])

    # Outer ring points (4 points)
    for i in range(4):
        # STRATEGIC SYMMETRY BREAKING: 10% angle jitter
        angle_jitter = 0.1 * np.random.uniform(-1, 1) * 2 * np.pi / 4
        angle = 2 * np.pi * i / 4 + angle_jitter
        x = radius_outer * np.cos(angle)
        y = radius_outer * np.sin(angle)
        
        # Rotate and translate
        x_rot = -y
        y_rot = x
        
        points[i+7] = center + np.array([x_rot, y_rot])

    # Ensure all points are inside the triangle
    for i in range(11):
        if not is_inside_triangle(points[i], A, B, C):
            v0 = B - A
            v1 = C - A
            v2 = points[i] - A
            
            d00 = np.dot(v0, v0)
            d01 = np.dot(v0, v1)
            d11 = np.dot(v1, v1)
            d20 = np.dot(v2, v0)
            d21 = np.dot(v2, v1)
            
            denom = d00 * d11 - d01 * d01
            if abs(denom) < 1e-10:
                points[i] = A
            else:
                v = (d11 * d20 - d01 * d21) / denom
                w = (d00 * d21 - d01 * d20) / denom
                
                if v < 0: v = 0
                if w < 0: w = 0
                if v + w > 1:
                    total = v + w
                    v /= total
                    w /= total
                
                points[i] = A + v * v0 + w * v1

    # ADAPTIVE OPTIMIZATION WITH IMPROVED EXPLORATION MECHANISMS
    current_min_area = get_smallest_triangle_area(points)
    
    # ADAPTIVE STEP SIZING BASED ON TRIANGLE HEIGHT
    base_step = 0.02 * height

    # Optimization parameters with improved exploration mechanisms
    phase1_end = 400
    phase2_end = 800
    total_steps = 1200
    
    # ENHANCED SIMULATED ANNEALING PARAMETERS
    temperature = 0.1  # Increased from 0.05 for better exploration
    improvement_history = []
    history_window = 50
    no_improve_count = 0
    
    # Track point involvement in critical triangles
    point_involvement = np.zeros(11)
    
    # Main optimization loop with enhanced exploration capabilities
    for iteration in range(total_steps):
        # Determine current phase for adaptive step sizing
        if iteration < phase1_end:
            step_size = base_step
            # No boundary repulsion in early phase
            boundary_repulsion = 0.0
        elif iteration < phase2_end:
            step_size = base_step * 0.4
            # Start boundary repulsion
            boundary_repulsion = 0.003 * (iteration - phase1_end) / (phase2_end - phase1_end)
        else:
            step_size = base_step * 0.1
            # Stronger boundary repulsion in final phase
            boundary_repulsion = 0.003 + 0.007 * (iteration - phase2_end) / (total_steps - phase2_end)

        # Find all triangles and their areas
        triangles = []
        for i, j, k in combinations(range(11), 3):
            ax, ay = points[i]
            bx, by = points[j]
            cx, cy = points[k]
            s_val = 0.5 * ((bx - ax) * (cy - ay) - (cx - ax) * (by - ay))
            abs_area = abs(s_val)
            triangles.append((abs_area, i, j, k, s_val))

        # Sort by area
        triangles.sort(key=lambda x: x[0])
        smallest_area = triangles[0][0]
        
        # PHASE-DEPENDENT THRESHOLD: Hybrid approach for consistent selection
        # Transition from percentage-based to absolute near optimum
        quality_ratio = current_min_area / 0.0365
        # Percentage component decreases as we approach optimum
        percentage_component = 0.25 * (1 - quality_ratio)
        # Absolute component increases as we approach optimum
        absolute_component = 0.0003 * quality_ratio
        area_threshold = smallest_area * (1 + percentage_component) + absolute_component
        
        # Adaptive selection: all triangles within threshold of smallest area
        top_triangles = [t for t in triangles if t[0] <= area_threshold]

        # Track point involvement for targeted optimization
        point_involvement = np.zeros(11)
        for _, i, j, k, _ in top_triangles:
            point_involvement[i] += 1
            point_involvement[j] += 1
            point_involvement[k] += 1
        
        # Initialize gradient accumulators for all points
        gradients = np.zeros_like(points)
        
        # Process each top triangle
        for abs_area, i, j, k, s_val in top_triangles:
            # WEIGHT ADJUSTMENT: Increased clamp value and smoother transition
            weight = 1.0 / np.sqrt(abs_area + 1e-10)
            weight = min(weight, 8.0)  # Increased from 5.0 to 8.0
            
            A_pt = points[i]
            B_pt = points[j]
            C_pt = points[k]

            sign_S = 1.0 if s_val >= 0 else -1.0

            # Compute gradients that increase triangle area
            grad_A = sign_S * np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]])
            grad_B = sign_S * np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[0]])
            grad_C = sign_S * np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]])

            # Accumulate weighted gradients
            gradients[i] += weight * grad_A
            gradients[j] += weight * grad_B
            gradients[k] += weight * grad_C

        # Scale gradients by point involvement count with logarithmic weighting
        for i in range(11):
            if point_involvement[i] > 0:
                # LOGARITHMIC SCALING: Diminishing returns for high involvement
                scale_factor = 1.0 + 0.3 * np.log(1 + point_involvement[i])
                gradients[i] *= scale_factor

        # Apply boundary REPULSION (not attraction) to create protective buffer
        if boundary_repulsion > 0:
            for i in range(11):
                p = points[i]
                # Calculate distance to each edge
                dist_to_AB = np.abs(np.cross(B-A, p-A)) / np.linalg.norm(B-A)
                dist_to_BC = np.abs(np.cross(C-B, p-B)) / np.linalg.norm(C-B)
                dist_to_CA = np.abs(np.cross(A-C, p-C)) / np.linalg.norm(A-C)
                
                min_dist = min(dist_to_AB, dist_to_BC, dist_to_CA)
                # Only apply repulsion if too close to boundary
                if min_dist < 0.05:
                    # Direction away from closest edge
                    if min_dist == dist_to_AB:
                        normal = np.array([A[1]-B[1], B[0]-A[0]])
                    elif min_dist == dist_to_BC:
                        normal = np.array([B[1]-C[1], C[0]-B[0]])
                    else:
                        normal = np.array([C[1]-A[1], A[0]-C[0]])
                    
                    normal = normal / np.linalg.norm(normal)
                    repulsion_strength = boundary_repulsion * (0.05 - min_dist) / 0.05
                    gradients[i] += repulsion_strength * normal

        # Create candidate configuration
        candidate = points.copy()
        for i in range(11):
            if np.linalg.norm(gradients[i]) > 1e-10:
                # Partial normalization to maintain magnitude sensitivity
                grad_dir = gradients[i] / (np.linalg.norm(gradients[i]) ** 0.5)
                candidate[i] += step_size * grad_dir

        # Project any points outside the triangle back onto the boundary
        for i in range(11):
            if not is_inside_triangle(candidate[i], A, B, C):
                v0 = B - A
                v1 = C - A
                v2 = candidate[i] - A
                
                d00 = np.dot(v0, v0)
                d01 = np.dot(v0, v1)
                d11 = np.dot(v1, v1)
                d20 = np.dot(v2, v0)
                d21 = np.dot(v2, v1)
                
                denom = d00 * d11 - d01 * d01
                if abs(denom) < 1e-10:
                    candidate[i] = A
                else:
                    v = (d11 * d20 - d01 * d21) / denom
                    w = (d00 * d21 - d01 * d20) / denom
                    
                    if v < 0: v = 0
                    if w < 0: w = 0
                    if v + w > 1:
                        total = v + w
                        v /= total
                        w /= total
                    
                    candidate[i] = A + v * v0 + w * v1

        # Check distinctness
        dists = np.linalg.norm(candidate[:, None, :] - candidate[None, :, :], axis=2)
        np.fill_diagonal(dists, np.inf)
        if np.min(dists) < 1e-5:
            continue

        new_min_area = get_smallest_triangle_area(candidate)
        
        # TRACK IMPROVEMENT HISTORY FOR ADAPTIVE LANDSCAPE ANALYSIS
        improvement = new_min_area - current_min_area
        improvement_history.append(improvement)
        if len(improvement_history) > history_window:
            improvement_history.pop(0)
        
        # ADAPTIVE TEMPERATURE DECAY based on landscape ruggedness
        if len(improvement_history) > 0:
            # Calculate area distribution statistics
            areas = [t[0] for t in triangles]
            mean_area = np.mean(areas)
            std_dev = np.std(areas)
            ruggedness = std_dev / mean_area
n            # SLOW COOLING IN RUGGED LANDSCAPES
            # When ruggedness is high, cool slower to maintain exploration
            cooling_rate = 0.995 - 0.005 * ruggedness
            temperature *= cooling_rate

        # ADAPTIVE GLOBAL PERTURBATIONS FOR DEEP LOCAL MINIMA
        # DYNAMIC THRESHOLD BASED ON SOLUTION QUALITY
        quality_ratio = current_min_area / 0.0365
        # Threshold decreases as we approach optimum (more exploration needed when far from optimum)
        perturbation_threshold = max(30, 75 * (1 - quality_ratio) + 25)
        
        if no_improve_count >= perturbation_threshold:
            # Scale perturbation by point involvement
            perturbation = np.zeros_like(candidate)
            for i in range(11):
                # Base perturbation scaled by involvement
                scale = 0.03 * (1 + 0.5 * point_involvement[i])
                perturbation[i] = np.random.uniform(-scale, scale, size=2)
            
            candidate = points + perturbation
            
            # Project back to triangle
            for i in range(11):
                if not is_inside_triangle(candidate[i], A, B, C):
                    v0 = B - A
                    v1 = C - A
                    v2 = candidate[i] - A
                    
                    d00 = np.dot(v0, v0)
                    d01 = np.dot(v0, v1)
                    d11 = np.dot(v1, v1)
                    d20 = np.dot(v2, v0)
                    d21 = np.dot(v2, v1)
                    
                    denom = d00 * d11 - d01 * d01
                    if abs(denom) < 1e-10:
                        candidate[i] = A
                    else:
                        v = (d11 * d20 - d01 * d21) / denom
                        w = (d00 * d21 - d01 * d20) / denom
                        
                        if v < 0: v = 0
                        if w < 0: w = 0
                        if v + w > 1:
                            total = v + w
                            v /= total
                            w /= total
                        
                        candidate[i] = A + v * v0 + w * v1

            new_min_area = get_smallest_triangle_area(candidate)
            no_improve_count = 0

        # SIMULATED ANNEALING ACCEPTANCE CRITERION
        if new_min_area > current_min_area:
            points = candidate
            current_min_area = new_min_area
            no_improve_count = 0
        else:
            delta = new_min_area - current_min_area
            if delta > -1e-8:  # Almost equal, accept to diversify
                points = candidate
                current_min_area = new_min_area
                no_improve_count = 0
            elif temperature > 1e-8:  # Use simulated annealing
                prob = np.exp(delta / temperature)
                if np.random.random() < prob:
                    points = candidate
                    current_min_area = new_min_area
                    no_improve_count = 0
                else:
                    no_improve_count += 1
            else:
                no_improve_count += 1

    return points