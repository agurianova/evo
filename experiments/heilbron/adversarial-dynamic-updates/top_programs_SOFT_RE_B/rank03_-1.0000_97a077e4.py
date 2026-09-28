from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib
import scipy.linalg


def entrypoint():
    """Return an improve(points) -> improved_points callable with advanced search."""
    A, B, C = get_unit_triangle()
    
    # Constants for the annealing process
    INITIAL_TEMP = 0.015
    COOLING_RATE = 0.97
    MIN_TEMP = 1e-5
    MAX_ITERATIONS = 250
    RESTARTS = 4
    THEORETICAL_MAX = 0.0365  # Known theoretical maximum for 11 points
    
    # Triangle area cache to avoid redundant calculations
    area_cache = {}
    
    def clear_area_cache():
        nonlocal area_cache
        area_cache = {}

    def calculate_triangle_area(points, i, j, k):
        """Calculate area of triangle i,j,k with caching."""
        # Create a unique key for this triangle (sorted to ensure consistent ordering)
        key = tuple(sorted([i, j, k]))
        
        # Check if we've already calculated this area
        if key in area_cache:
            return area_cache[key]
        
        # Calculate area using the shoelace formula
        area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                       (points[k,0]-points[i,0])*(points[j,1]-points[i,1]))
        
        # Store in cache
        area_cache[key] = area
        return area

    def identify_symmetry_axes(points):
        """Identify potential symmetry axes using PCA and reflection analysis."""
        # Center the points
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        
        # Apply PCA to find principal axes
        cov = np.cov(centered.T)
        eigenvals, eigenvecs = scipy.linalg.eigh(cov)
        
        # Sort eigenvectors by eigenvalue (descending)
        idx = np.argsort(eigenvals)[::-1]
        eigenvecs = eigenvecs[:, idx]
        
        # Consider the first principal axis as a potential symmetry axis
        primary_axis = eigenvecs[:, 0]
        
        # Check for reflection symmetry across this axis
        reflection_errors = []
        for i in range(len(points)):
            # Project point onto axis
            proj = np.dot(points[i] - centroid, primary_axis) * primary_axis
            reflection = centroid + 2 * proj - points[i]
            
            # Find closest point to reflection
            distances = np.linalg.norm(points - reflection, axis=1)
            min_dist = np.min(distances)
            reflection_errors.append(min_dist)

        # Calculate symmetry score (lower = better symmetry)
        symmetry_score = np.mean(reflection_errors)
        
        # Return axes with good symmetry score
        if symmetry_score < 0.05:  # Threshold for acceptable symmetry
            return [primary_axis]
        return []

    def symmetry_preserving_perturbation(points, symmetry_axes):
        """Apply coordinated perturbations that preserve symmetry."""
        if not symmetry_axes:
            return points.copy()
        
        # Use the first symmetry axis
        axis = symmetry_axes[0]
        centroid = np.mean(points, axis=0)
        
        # Identify symmetric point pairs
        pairs = []
        used = set()
        for i in range(len(points)):
            if i in used:
                continue
            
            # Project point onto axis
            proj = np.dot(points[i] - centroid, axis) * axis
            reflection = centroid + 2 * proj - points[i]
            
            # Find closest point to reflection
            min_dist = float('inf')
            match_idx = -1
            for j in range(len(points)):
                if j == i or j in used:
                    continue
                dist = np.linalg.norm(points[j] - reflection)
                if dist < min_dist:
                    min_dist = dist
                    match_idx = j
            
            if match_idx >= 0 and min_dist < 0.05:
                pairs.append((i, match_idx))
                used.add(i)
                used.add(match_idx)

        # Apply coordinated perturbation to symmetric pairs
        candidate = points.copy()
        for i, j in pairs:
            # Generate a random perturbation
            perturbation = np.random.normal(0, 0.01, size=2)
            
            # Project perturbation to be symmetric
            proj = np.dot(perturbation, axis) * axis
            perp = perturbation - proj
            
            # Apply symmetric perturbation
            candidate[i] += proj + perp
            candidate[j] += proj - perp

        # Project any points that moved outside the triangle
        for i in range(11):
            if not is_inside_triangle(candidate[i], A, B, C):
                candidate[i] = project_to_triangle(candidate[i])

        return candidate

    def identify_bottleneck_triangles(points, threshold_factor=0.05):
        """Identify triangles within threshold of min_area and their constituent points."""
        n = len(points)
        min_area = get_smallest_triangle_area(points)
        bottleneck_triangles = []
        bottleneck_points = set()
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    # Calculate area of triangle i,j,k using cached version
                    area = calculate_triangle_area(points, i, j, k)
                    # Include triangles within threshold of min_area
                    if abs(area - min_area) < threshold_factor * min_area:
                        bottleneck_triangles.append((i, j, k))
                        bottleneck_points.update([i, j, k])
        
        return list(bottleneck_triangles), list(bottleneck_points), min_area

    def compute_gradient(points, base_score, temp=None, bottleneck_points=None):
        """Compute gradient of min_area using finite differences with adaptive epsilon and bottleneck focus."""
        n_points = len(points)
        gradient = np.zeros_like(points)
        
        # If bottleneck_points not provided, compute for all points
        if bottleneck_points is None:
            bottleneck_points = list(range(n_points))
        
        # Adaptive epsilon based on temperature
        if temp is not None:
            epsilon = 1e-4 * (temp / INITIAL_TEMP) ** 0.5
        else:
            epsilon = 1e-4
        
        # Flag to determine if we should use central differences for better accuracy
        use_central = False
        
        for i in bottleneck_points:
            for j in range(2):  # x and y dimensions
                # Try forward difference first
                candidate_forward = points.copy()
                candidate_forward[i, j] += epsilon
                
                # Ensure point stays inside triangle
                if not is_inside_triangle(candidate_forward[i], A, B, C):
                    candidate_forward[i] = project_to_triangle(candidate_forward[i])
                
                # Calculate new minimum area
                score_forward = get_smallest_triangle_area(candidate_forward)

                # If we're going to use central differences, calculate backward difference too
                if use_central:
                    candidate_backward = points.copy()
                    candidate_backward[i, j] -= epsilon
                    
                    # Ensure point stays inside triangle
                    if not is_inside_triangle(candidate_backward[i], A, B, C):
                        candidate_backward[i] = project_to_triangle(candidate_backward[i])
                    
                    score_backward = get_smallest_triangle_area(candidate_backward)
                    
                    # Central difference gradient (more accurate)
                    gradient[i, j] = (score_forward - score_backward) / (2 * epsilon)
                else:
                    # Forward difference gradient
                    gradient[i, j] = (score_forward - base_score) / epsilon
        
        # Check if gradient magnitude is low (flat region)
        gradient_magnitude = np.linalg.norm(gradient)
        if gradient_magnitude < 1e-5:
            use_central = True
            # Recompute gradient with central differences for better accuracy
            for i in bottleneck_points:
                for j in range(2):
                    candidate_forward = points.copy()
                    candidate_forward[i, j] += epsilon
                    
                    if not is_inside_triangle(candidate_forward[i], A, B, C):
                        candidate_forward[i] = project_to_triangle(candidate_forward[i])
                    
                    score_forward = get_smallest_triangle_area(candidate_forward)

                    candidate_backward = points.copy()
                    candidate_backward[i, j] -= epsilon
                    
                    if not is_inside_triangle(candidate_backward[i], A, B, C):
                        candidate_backward[i] = project_to_triangle(candidate_backward[i])
                    
                    score_backward = get_smallest_triangle_area(candidate_backward)
                    
                    gradient[i, j] = (score_forward - score_backward) / (2 * epsilon)

        return gradient

    def project_to_triangle(point):
        """Project a point to the nearest point inside the triangle with boundary repulsion."""
        # Convert to barycentric coordinates
        v0 = B - A
        v1 = C - A
        v2 = point - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        if abs(denom) < 1e-10:  # Degenerate triangle, shouldn't happen
            return (A + B + C) / 3
        
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w
        
        # Clamp to triangle
        if u < 0:
            # Project to edge BC
            total = v + w
            if total > 0:
                v, w = v / total, w / total
            else:
                v, w = 0.5, 0.5  # Midpoint of BC
            u = 0
        if v < 0:
            # Project to edge AC
            total = u + w
            if total > 0:
                u, w = u / total, w / total
            else:
                u, w = 0.5, 0.5  # Midpoint of AC
            v = 0
        if w < 0:
            # Project to edge AB
            total = u + v
            if total > 0:
                u, v = u / total, v / total
            else:
                u, v = 0.5, 0.5  # Midpoint of AB
            w = 0
        
        # Ensure coordinates sum to 1
        total = u + v + w
        if total > 0:
            u, v, w = u/total, v/total, w/total
        else:
            # If all coordinates are zero (shouldn't happen), use centroid
            u, v, w = 1/3, 1/3, 1/3
        
        return u * A + v * B + w * C

    def repair_collinear_points(candidate, temp, current_min_area):
        """Identify and repair collinear points using orthogonal projection to collinear axis."""
        n = len(candidate)
        min_area = get_smallest_triangle_area(candidate)
        
        if min_area >= 1e-5:
            return candidate, min_area
        
        # Find problematic triangles
        problematic_points = set()
        problematic_triangles = []
        min_triangle_area = float('inf')
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    # Calculate area of triangle i,j,k using cached version
                    area = calculate_triangle_area(candidate, i, j, k)
                    if area < 1e-5:
                        problematic_points.update([i, j, k])
                        problematic_triangles.append((i, j, k, area))
                        if area < min_triangle_area:
                            min_triangle_area = area
        
        if not problematic_points:
            return candidate, min_area
        
        # For each problematic triangle, move points along orthogonal direction
        repaired = candidate.copy()
        
        for i, j, k, area in problematic_triangles:
            # Get vectors between points
            v1 = candidate[j] - candidate[i]
            v2 = candidate[k] - candidate[i]
            
            # Calculate collinear axis (normalized)
            axis_norm = np.linalg.norm(v1)
            if axis_norm < 1e-8:
                # Very small triangle, use random perpendicular direction
                collinear_axis = np.array([0, 1]) if abs(v1[0]) < 1e-8 else np.array([-v1[1], v1[0]])
                collinear_axis = collinear_axis / np.linalg.norm(collinear_axis)
            else:
                collinear_axis = v1 / axis_norm
            
            # Project v2 onto collinear axis to get parallel component
            proj = np.dot(v2, collinear_axis) * collinear_axis
            # Orthogonal component is the difference
            ortho = v2 - proj

            # If nearly collinear, ortho will be small - normalize to get direction
            ortho_norm = np.linalg.norm(ortho)
            if ortho_norm < 1e-5:
                # Generate random perpendicular direction
                collinear_perp = np.array([-collinear_axis[1], collinear_axis[0]])
            else:
                collinear_perp = ortho / ortho_norm
            
            # Calculate step size based on degeneracy severity
            step_size = 0.01 * np.sqrt(max(1e-6, min_triangle_area))
            
            # Move middle point orthogonally away from the line
            repaired[j] += collinear_perp * step_size * 0.5
            repaired[k] -= collinear_perp * step_size * 0.5
            repaired[i] += collinear_perp * step_size * 0.1  # Small adjustment to anchor point
        
        # Project any points that moved outside the triangle
        for i in range(11):
            if not is_inside_triangle(repaired[i], A, B, C):
                repaired[i] = project_to_triangle(repaired[i])
        
        # Check if repair was successful
        repaired_min_area = get_smallest_triangle_area(repaired)
        if repaired_min_area < min_area:
            return candidate, min_area  # Keep original if repair made things worse
        
        return repaired, repaired_min_area

    def random_direction_search(current, current_score, temp, stagnation_depth, num_directions=3):
        """Sample multiple random directions when gradient is small to escape flat regions."""
        best_candidate = current.copy()
        best_score = current_score
        
        # Adaptive radius based on temperature and stagnation
        radius = 0.01 * (temp / INITIAL_TEMP) * (1 + 0.3 * stagnation_depth)
        
        for _ in range(num_directions):
            # Generate a random direction on the sphere
            direction = np.random.normal(0, 1, size=(11, 2))
            direction_norm = np.linalg.norm(direction, axis=1, keepdims=True)
            direction_norm[direction_norm == 0] = 1  # Avoid division by zero
            direction = direction / direction_norm
            
            # Scale by adaptive radius
            step = direction * radius
            
            # Create candidate
            candidate = current + step
            
            # Project any points that moved outside the triangle
            for i in range(11):
                if not is_inside_triangle(candidate[i], A, B, C):
                    candidate[i] = project_to_triangle(candidate[i])
            
            # Repair collinear points if needed
            candidate, candidate_score = repair_collinear_points(candidate, temp, current_score)
            
            # Track best candidate
            if candidate_score > best_score:
                best_candidate = candidate
                best_score = candidate_score

        return best_candidate, best_score

    def improve(points: np.ndarray) -> np.ndarray:
        # Create a local RNG seeded by a hash of the input points for determinism per input
        points_hash = hashlib.sha256(points.tobytes()).hexdigest()
        seed = int(points_hash[:8], 16)  # Take first 8 hex chars as seed
        rng = np.random.RandomState(seed)
        
        # Initial setup
        current = points.copy()
        best = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_score = current_score
        
        # Track improvement history for adaptive parameters
        improvement_history = []
        max_history = 20
        
        # Simulated annealing parameters
        temp = INITIAL_TEMP
        no_improve_count = 0
        restart_count = 0
        iteration = 0
        
        # Track stagnation depth for resistance-based adaptation
        stagnation_depth = 0
        resistance_proxy = 1.0
        
        # Dynamic restart threshold based on temperature and restart count
        BASE_NO_IMPROVEMENT_LIMIT = 25
        
        # Track perturbation success rates for adaptive exploration
        perturbation_success = {1: 0.2, 2: 0.3, 3: 0.25}  # Updated based on Heilbron characteristics
        perturbation_attempts = {1: 1, 2: 1, 3: 1}
        
        while iteration < MAX_ITERATIONS and restart_count < RESTARTS:
            # Enhanced stagnation detection with resistance-based metrics
            if len(improvement_history) > 0:
                avg_improvement = np.mean(improvement_history)
                # Calibrated threshold relative to current minimum area
                resistance_proxy = 1.0 - min(1.0, avg_improvement / (0.005 * current_score))
            
            # Dynamic threshold: increases with resistance_proxy
            NO_IMPROVEMENT_LIMIT = int(BASE_NO_IMPROVEMENT_LIMIT * (1 + 0.8 * resistance_proxy))
            
            # Identify bottleneck triangles with adaptive threshold (exponential decay)
            progress_ratio = current_score / THEORETICAL_MAX
            
            # DYNAMICALLY ADAPTED THRESHOLD FACTOR
            # Replaced fixed exponential decay with dual-parameter adaptive formulation
            # k_temp: controls how quickly threshold narrows as temperature drops
            # k_progress: controls how threshold narrows as progress increases
            k_temp = 3.0  # Was 2.0 - narrows more aggressively as temp drops
            k_progress = 1.5  # New parameter - narrows as progress increases
            threshold_factor = 0.07 * np.exp(-k_temp * temp / INITIAL_TEMP) * np.exp(-k_progress * progress_ratio) + 0.005
            
            _, bottleneck_points, _ = identify_bottleneck_triangles(current, threshold_factor)
            
            # Current progress toward theoretical maximum
            
            # Apply symmetry-preserving perturbation with probability based on symmetry strength and progress
            if bottleneck_points and rng.rand() < 0.25 and current_score > 0.015:
                symmetry_axes = identify_symmetry_axes(current)
                if symmetry_axes:
                    sym_candidate = symmetry_preserving_perturbation(current, symmetry_axes)
                    sym_score = get_smallest_triangle_area(sym_candidate)
                    if sym_score > current_score:
                        current = sym_candidate
                        current_score = sym_score
                        if sym_score > best_score:
                            best = sym_candidate.copy()
                            best_score = sym_score
                        # Update improvement history
                        if iteration > 0:
                            improvement_history.append(sym_score - current_score)
                            if len(improvement_history) > max_history:
                                improvement_history.pop(0)
                        continue

            # Generate candidate by perturbing 1-3 random points
            candidate = current.copy()
            
            # Adjusted perturbation probabilities based on historical success
            total_attempts = sum(perturbation_attempts.values())
            success_rates = {k: perturbation_success[k] / perturbation_attempts[k] 
                            for k in perturbation_success}
            max_rate = max(success_rates.values())
            # Ensure probabilities sum to 1
            probs = [success_rates[i] / (max_rate + 1e-8) for i in range(1, 4)]
            probs = [p / sum(probs) for p in probs]
            
            # Determine how many points to perturb (1-3)
            num_perturb = rng.choice([1, 2, 3], p=probs)
            perturbation_attempts[num_perturb] += 1
            
            # DYNAMICALLY ADAPTED EXPLORATION-EXPLOITATION BIAS
            # Parameterized sigmoid curve that evolves with optimization phase
            # Early phase: broader exploration (higher x0, lower effective k)
            # Late phase: focused exploitation (lower x0, higher k)
            k_base = 6.0  # Base value for k
            k_progress_factor = 4.0  # Additional k as progress increases
            k = k_base + k_progress_factor * progress_ratio

            x0_base = 0.65  # Base transition point
            x0_progress_factor = -0.2  # Shift left as progress increases
            x0 = x0_base + x0_progress_factor * progress_ratio

            # Ensure x0 stays in reasonable range
            x0 = max(0.3, min(0.8, x0))

            sigmoid_bias = 1.0 / (1.0 + np.exp(-k * (progress_ratio - x0)))
            bottleneck_bias = 0.25 + 0.7 * sigmoid_bias

            # Select points to perturb - bias toward bottleneck points
            if bottleneck_points and rng.rand() < bottleneck_bias:
                indices = rng.choice(bottleneck_points, 
                                   size=min(num_perturb, len(bottleneck_points)), 
                                   replace=False)
            else:
                indices = rng.choice(11, size=num_perturb, replace=False)
            
            # Continuous step size exponent based on improvement rate
            if len(improvement_history) > 0:
                avg_improvement = np.mean(improvement_history)
                improvement_rate = max(0, min(1, avg_improvement / 0.0005))
            else:
                improvement_rate = 0.5
            
            # Adaptive step size exponent with resistance-aware scaling
            base_exponent = 0.1 + 0.3 * progress_ratio
            resistance_factor = 1.0 + 0.8 * resistance_proxy
            step_size_exponent = base_exponent * resistance_factor

            # Adaptive step size with dynamic exponent
            step_size = 0.06 * (temp / INITIAL_TEMP) ** step_size_exponent
            
            for idx in indices:
                # Gaussian perturbation with adaptive step size
                perturbation = rng.normal(0, step_size, size=2)
                candidate[idx] += perturbation
                
                # Ensure point stays inside triangle
                if not is_inside_triangle(candidate[idx], A, B, C):
                    candidate[idx] = project_to_triangle(candidate[idx])

            # Check for near-collinear points and attempt repair
            candidate, candidate_score = repair_collinear_points(candidate, temp, current_score)
            
            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta > 0 or (delta > -1e-5 and rng.rand() < np.exp(delta / temp)):
                current = candidate
                current_score = candidate_score
                
                # Update improvement history
                if iteration > 0:
                    improvement_history.append(delta)
                    if len(improvement_history) > max_history:
                        improvement_history.pop(0)
                
                if candidate_score > best_score:
                    best = candidate.copy()
                    best_score = candidate_score
                    # Update success rate
                    perturbation_success[num_perturb] += 1
                    no_improve_count = 0
                    
                    # DYNAMICALLY ADAPTED STAGNATION RESPONSE
                    # Transformed fixed stagnation increments into dynamic response
                    # Based on resistance proxy and improvement rate
                    stagnation_factor = 0.2 * (1.0 + resistance_proxy) * (1.0 - improvement_rate)
                    stagnation_depth = max(0, stagnation_depth - 0.5)
                else:
                    no_improve_count += 1
                    
                    # DYNAMICALLY ADAPTED STAGNATION RESPONSE
                    # Transformed fixed stagnation increments into dynamic response
                    # Based on resistance proxy and improvement rate
                    stagnation_factor = 0.2 * (1.0 + resistance_proxy) * (1.0 - improvement_rate)
                    stagnation_depth = min(15, stagnation_depth + stagnation_factor)
            else:
                no_improve_count += 1
                
                # DYNAMICALLY ADAPTED STAGNATION RESPONSE
                # Transformed fixed stagnation increments into dynamic response
                # Based on resistance proxy and improvement rate
                stagnation_factor = 0.2 * (1.0 + resistance_proxy) * (1.0 - improvement_rate)
                stagnation_depth = min(15, stagnation_depth + stagnation_factor)
            
            # Directional search when stuck in local optimum
            if no_improve_count > NO_IMPROVEMENT_LIMIT * 0.5:
                # Compute gradient only for bottleneck points
                gradient = compute_gradient(current, current_score, temp=temp, 
                                         bottleneck_points=bottleneck_points)
                
                # Check for near-zero gradients (flat region)
                gradient_magnitude = np.linalg.norm(gradient)
                if gradient_magnitude < 1e-5:
                    # Multi-direction sampling for flat regions - scaled with temperature and stagnation
                    base_directions = 3
                    stagnation_effect = 5 * (1 - np.exp(-stagnation_depth / 3.0))
                    temp_effect = 2 * (1 - temp / INITIAL_TEMP)
                    num_directions = int(min(15, base_directions + stagnation_effect + temp_effect))
                    
                    gradient_candidate, gradient_score = random_direction_search(
                        current, current_score, temp, stagnation_depth, num_directions=num_directions)
                else:
                    # Scale step by gradient magnitude with temperature-dependent factor
                    step_direction = gradient * (0.015 * temp / INITIAL_TEMP / (gradient_magnitude + 1e-8))
                    
                    # Create candidate in gradient direction
                    gradient_candidate = current + step_direction
                    
                    # Project any points that moved outside the triangle
                    for i in range(11):
                        if not is_inside_triangle(gradient_candidate[i], A, B, C):
                            gradient_candidate[i] = project_to_triangle(gradient_candidate[i])
                    
                    # Repair collinear points if needed
                    gradient_candidate, gradient_score = repair_collinear_points(
                        gradient_candidate, temp, current_score)

                # Accept if it improves the score
                if gradient_score > current_score:
                    current = gradient_candidate
                    current_score = gradient_score
                    no_improve_count = 0
                    
                    # DYNAMICALLY ADAPTED STAGNATION RESPONSE
                    # Transformed fixed stagnation increments into dynamic response
                    # Based on resistance proxy and improvement rate
                    stagnation_factor = 0.2 * (1.0 + resistance_proxy) * (1.0 - improvement_rate)
                    stagnation_depth = max(0, stagnation_depth - 1.0)
                    
                    if gradient_score > best_score:
                        best = gradient_candidate.copy()
                        best_score = gradient_score

            # Cool down
            temp = max(MIN_TEMP, temp * COOLING_RATE)
            iteration += 1
            
            # DYNAMICALLY ADAPTED CACHE CLEARING
            # Replaced fixed cache clearing interval with dynamic scheduling
            # Based on optimization progress and resistance
            cache_clear_interval = max(5, int(20 * (1.0 - progress_ratio) + 5 * resistance_proxy))
            if iteration % cache_clear_interval == 0:
                clear_area_cache()
            
            # Early stopping if stuck for too long
            if no_improve_count >= NO_IMPROVEMENT_LIMIT:
                # Progressive focusing - gradually narrow the search space
                if restart_count > 0:
                    # Gradually reduce exploration range based on previous success
                    exploration_factor = 0.85 ** (restart_count * (1 + improvement_rate))
                else:
                    exploration_factor = 1.0
                
                # Restart from best configuration
                current = best.copy()
                current_score = best_score
                
                # Adjust temperature based on exploration factor
                temp = max(MIN_TEMP, INITIAL_TEMP * exploration_factor)
                
                no_improve_count = 0
                restart_count += 1
        
        # Final validation check
        if not is_inside_triangle(best, A, B, C) or get_smallest_triangle_area(best) < 1e-6:
            return points  # Return original if our improvement is invalid
        
        return best

    return improve