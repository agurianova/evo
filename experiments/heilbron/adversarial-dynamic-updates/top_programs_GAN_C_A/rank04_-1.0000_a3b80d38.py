import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
from scipy.optimize import minimize

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Calculate triangle height for boundary calculations
    height = np.linalg.norm(C - A)
    
    # ADAPTIVE boundary buffer based on optimization progress
    def get_boundary_buffer(current_min_area, target_min_area=0.0365):
        progress = max(0.0, min(1.0, current_min_area / target_min_area))
        # Buffer size: 1e-5 when starting, 1e-10 when near optimum
        return (1e-5 - 9.99e-6 * progress) * height

    target_min_area = 0.0365

    # Expanded row distributions with domain-specific Heilbronn patterns
    distributions = [
        [5, 3, 2, 1],
        [4, 3, 2, 1, 1],
        [5, 3, 2, 1],
        [4, 4, 2, 1],
        [3, 3, 3, 2],
        [6, 3, 2],
        [4, 3, 3, 1],
        [5, 2, 2, 2],
        [3, 2, 3, 2, 1],
        [4, 3, 2, 2],
        [7, 2, 2],
        [3, 3, 2, 2, 1]
    ]
    
    # Track performance for UCB1 selection
    pattern_scores = {i: {'score': -1.0, 'count': 0} for i in range(len(distributions))}
    total_evals = 0
    
    best_config = None
    best_score = -1
    
    # Calculate pattern complexity score (higher for more asymmetric patterns)
    def get_pattern_complexity(row_dist):
        n = sum(row_dist)
        entropy = 0
        for count in row_dist:
            p = count / n
            if p > 0:
                entropy -= p * np.log(p)
        # Normalize entropy to [0,1]
        max_entropy = np.log(len(row_dist)) if len(row_dist) > 1 else 1
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        # Complexity = 1 - normalized_entropy (more uneven = higher complexity)
        return 1 - normalized_entropy

    # Calculate distance to boundary
    def distance_to_boundary(point):
        # Calculate distance to each edge using line-point distance formula
        def edge_distance(p, v1, v2):
            line_vec = v2 - v1
            point_vec = p - v1
            line_len = np.linalg.norm(line_vec)
            if line_len < 1e-10:
                return np.linalg.norm(point_vec)
            proj = np.dot(point_vec, line_vec) / line_len
            proj = max(0, min(line_len, proj))
            closest = v1 + (proj / line_len) * line_vec
            return np.linalg.norm(p - closest)
        
        d1 = edge_distance(point, A, B)
        d2 = edge_distance(point, B, C)
        d3 = edge_distance(point, C, A)
        return min(d1, d2, d3)

    # Project to triangle boundary if needed
    def project_to_triangle(point):
        # Find closest point on any edge
        def point_to_line_distance(p, a, b):
            ab = b - a
            ap = p - a
            ab_length_sq = np.dot(ab, ab)
            if ab_length_sq < 1e-10:
                return a, np.linalg.norm(ap)
            t = max(0.0, min(1.0, np.dot(ap, ab) / ab_length_sq))
            projection = a + t * ab
            distance = np.linalg.norm(p - projection)
            return projection, distance

        edges = [(A, B), (B, C), (C, A)]
        min_distance = float('inf')
        closest_point = None
        
        for edge in edges:
            proj, dist = point_to_line_distance(point, edge[0], edge[1])
            if dist < min_distance:
                min_distance = dist
                closest_point = proj
        
        # Check if point is inside triangle
        v0 = B - A
        v1 = C - A
        v2 = point - A

        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01

        if abs(denom) < 1e-10:
            return (A + B + C) / 3

        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w

        if u >= 0 and v >= 0 and w >= 0:
            return point

        return closest_point

    # Calculate point influence based on inverse area weighting
    def calculate_point_influence(points, k=8):
        n = points.shape[0]
        point_influence = np.zeros(n)
        
        # Find smallest triangles
        triangle_data = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    triangle_data.append((area, i, j, k))
        
        # Sort by area and take top k
        triangle_data.sort(key=lambda x: x[0])
        top_triangles = triangle_data[:k]
        
        # Weight by inverse area squared
        for area, i, j, k in top_triangles:
            weight = 1.0 / max(area, 1e-10)**2
            point_influence[i] += weight
            point_influence[j] += weight
            point_influence[k] += weight
        
        # Normalize
        max_influence = np.max(point_influence) if np.max(point_influence) > 0 else 1.0
        if max_influence > 0:
            point_influence = point_influence / max_influence
        
        return point_influence

    # Find smallest triangle
    def find_smallest_triangle(points):
        n = points.shape[0]
        min_area = float('inf')
        best_indices = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    if area < min_area:
                        min_area = area
                        best_indices = (i, j, k)
        return min_area, best_indices

    # Resistance-oriented scoring function with exponential weighting
    def resistance_score(points):
        areas = []
        n = points.shape[0]
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    areas.append(area)
        
        # Sort and take top k smallest
        areas.sort()
        k = min(8, len(areas))
        top_areas = areas[:k]
        
        # ADAPTIVE triangle weighting with parameterized exponent
        current_min_area = min(areas) if areas else 0.0
        headroom = (target_min_area - current_min_area) / target_min_area
        # Parameterize exponent: higher when more headroom, lower when near optimal
        alpha = 1.5 + 1.5 * headroom
        weights = [1.0 / (i + 1)**alpha for i in range(k)]
        # Normalize weights to sum to 1
        weights = [w / sum(weights) for w in weights]

        # Calculate gradient directions for each small triangle
        gradient_directions = []
        for i in range(k):
            # Generate random direction for diversity
            angle = i * 2 * np.pi / k
            direction = np.array([np.cos(angle), np.sin(angle)])
            gradient_directions.append(direction)
        
        # Calculate gradient conflict score (higher = more conflicting = harder to improve)
        conflict_score = 0
        if len(gradient_directions) >= 2:
            total_alignment = 0
            for i in range(len(gradient_directions)):
                for j in range(i+1, len(gradient_directions)):
                    alignment = np.dot(gradient_directions[i], gradient_directions[j])
                    total_alignment += alignment
            
            if len(gradient_directions) > 1:
                avg_alignment = total_alignment / (len(gradient_directions) * (len(gradient_directions)-1) / 2)
                conflict_score = 1.0 - abs(avg_alignment)

        # EVOLVED conflict weight parameters
        base_weight = 0.18 + 0.04 * np.random.beta(2, 5)
        scaling_factor = 0.52 + 0.04 * np.random.beta(2, 5)
        max_weight = 0.72 + 0.04 * np.random.beta(2, 5)

        # Calculate pattern complexity for adaptive threshold
        pattern_complexity = get_pattern_complexity([5, 3, 2, 1])  # Default pattern
        adaptive_threshold = 0.033 + 0.003 * pattern_complexity

        # ADAPTIVE conflict weight (increases as progress increases)
        current_min_area = min(areas) if areas else 0.0
        progress = max(0.0, min(1.0, current_min_area / target_min_area))
        conflict_weight = base_weight + scaling_factor * progress
        if current_min_area > adaptive_threshold:  # Near-optimal region
            conflict_weight = min(max_weight, conflict_weight)

        # Return weighted area sum plus conflict score
        return sum(w * a for w, a in zip(weights, top_areas)) + conflict_weight * conflict_score

    # UCB1 selection for distribution patterns
    def select_distribution():
        nonlocal total_evals
        c = 1.414  # Exploration parameter
        
        # Calculate UCB1 scores
        ucb_scores = []
        for i, dist in enumerate(distributions):
            if pattern_scores[i]['count'] == 0:
                return i  # Always explore untried patterns first
            
            avg_score = pattern_scores[i]['score']
            ucb = avg_score + c * np.sqrt(np.log(total_evals) / pattern_scores[i]['count'])
            ucb_scores.append((ucb, i))
        
        # Select pattern with highest UCB score
        _, selected_idx = max(ucb_scores, key=lambda x: x[0])
        return selected_idx

    # Try distributions with UCB1 selection
    adaptive_restart_count = 10
    improvement_count = 0
    resistance_history = []
    plateau_threshold = 0.0001
    plateau_window = 3
    
    for _ in range(adaptive_restart_count):
        total_evals += 1
        dist_idx = select_distribution()
        pattern_scores[dist_idx]['count'] += 1
        
        row_dist = distributions[dist_idx]
        points = []
        rows = len(row_dist)
        
        # Calculate pattern complexity for this distribution
        pattern_complexity = get_pattern_complexity(row_dist)
        adaptive_threshold = 0.033 + 0.003 * pattern_complexity
        
        # Generate initial grid with boundary-aware perturbation scaling
        for i, num_in_row in enumerate(row_dist):
            v = (i + 0.5) / rows
            for j in range(num_in_row):
                u = (j + 0.5) / num_in_row * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                
                # BOUNDARY-AWARE perturbation scaling
                boundary_dist = distance_to_boundary(P)
                boundary_factor = 1.0 - min(1.0, boundary_dist / (0.1 * height))
                scale = 0.02 * (1 - v) * (1 - boundary_factor)
                
                perturbation = np.random.uniform(-scale * (1 - v), scale * (1 - v), size=2)
                points.append(P + perturbation)

        current = np.array(points)
        current_score = resistance_score(current)
        
        # Simulated annealing parameters
        initial_temp = 0.005
        temp_decay = 0.985
        step_size = 0.025
        max_iter = 6000
        early_stop = 600
        
        no_improve = 0
        last_improve_score = current_score
        improve_window = 150
        last_improve_iter = 0
        
        # ADAPTIVE bottleneck targeting probability
        current_resistance = current_score / target_min_area
        bottleneck_prob = max(0.3, 0.8 - 0.5 * current_resistance)
        
        # Track best in this restart
        restart_best = current.copy()
        restart_best_score = current_score
        
        for it in range(max_iter):
            # Identify bottleneck triangles (top 8 smallest)
            bottleneck_triples = []
            n = current.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = current[i], current[j], current[k]
                        area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        bottleneck_triples.append((area, i, j, k))
            
            # Sort by area and take top 8
            bottleneck_triples.sort(key=lambda x: x[0])
            all_bottleneck_indices = set()
            for _, i, j, k in bottleneck_triples[:8]:
                all_bottleneck_indices.update([i, j, k])
            
            # Use adaptive probability to select points from bottlenecks
            if np.random.rand() < bottleneck_prob and all_bottleneck_indices:
                idx = np.random.choice(list(all_bottleneck_indices))
            else:
                idx = np.random.randint(0, 11)

            # Calculate point influence for adaptive step sizing
            point_influence = calculate_point_influence(current, k=8)
            influence_weight = 1.0 / (1.0 + 0.5 * point_influence[idx])

            # Generate candidate move with influence-based scaling
            candidate = current.copy()
            candidate[idx] += np.random.normal(0, step_size * influence_weight, size=2)

            # Minimal boundary check with adaptive buffer
            buffer = get_boundary_buffer(current_score, target_min_area)
            if not is_inside_triangle(candidate[idx], A, B, C):
                # Move toward boundary but maintain buffer
                direction = project_to_triangle(candidate[idx]) - candidate[idx]
                if np.linalg.norm(direction) > buffer:
                    direction = direction / np.linalg.norm(direction) * buffer
                candidate[idx] += direction

            # Evaluate candidate
            new_score = resistance_score(candidate)

            # Simulated annealing acceptance
            if new_score > current_score:
                current = candidate
                current_score = new_score
                if new_score > restart_best_score:
                    restart_best = candidate.copy()
                    restart_best_score = new_score
                
                # Update adaptive bottleneck probability
                current_resistance = current_score / target_min_area
                bottleneck_prob = max(0.3, 0.8 - 0.5 * current_resistance)
                
                # Track improvement for adaptive cooling
                no_improve = 0
                last_improve_iter = it
            else:
                delta = current_score - new_score
                if np.random.rand() < np.exp(-delta / temp_decay):
                    current = candidate
                    current_score = new_score
                    no_improve = 0
                else:
                    no_improve += 1

            # Adaptive step decay
            if it % 50 == 0 and it > 0:
                improvement_rate = (current_score - last_improve_score) / 50
                last_improve_score = current_score
                
                # Adjust step size based on improvement rate
                if improvement_rate > 1e-6:
                    step_size = max(0.01, step_size * 0.99)
                else:
                    step_size = min(0.05, step_size * 1.01)

            # Dynamic temperature decay
            if it % improve_window == 0 and it > 0:
                improvement_rate = (current_score - last_improve_score) / improve_window
                last_improve_score = current_score
                
                # Adjust temperature decay based on improvement rate
                if improvement_rate > 1e-6:
                    temp_decay = max(0.98, temp_decay * 0.995)
                else:
                    temp_decay = min(0.995, temp_decay * 1.005)

            # Early stopping
            if no_improve >= early_stop:
                break

        # EXPANDED LOCAL SEARCH PHASE AFTER ANNEALING
        min_area, _ = find_smallest_triangle(restart_best)
        # Use pattern-adaptive threshold instead of fixed 0.034
        if min_area > adaptive_threshold:  # Near-optimal region - expand to multiple triangles
            # Find top k smallest triangles
            n = restart_best.shape[0]
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = restart_best[i], restart_best[j], restart_best[k]
                        area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        triangles.append((area, i, j, k))
            
            triangles.sort(key=lambda x: x[0])
            top_triangles = triangles[:min(3, len(triangles))]
            
            # Get all points involved in these triangles
            points_to_optimize = set()
            for _, i, j, k in top_triangles:
                points_to_optimize.add(i)
                points_to_optimize.add(j)
                points_to_optimize.add(k)
            points_to_optimize = list(points_to_optimize)
            
            # Define multi-triangle objective function
            def objective(x):
                candidate = restart_best.copy()
                # Update points
                for idx, point_idx in enumerate(points_to_optimize):
                    candidate[point_idx] = x[idx*2:idx*2+2]
                    
                # Project points back to triangle with adaptive buffer
                buffer = get_boundary_buffer(restart_best_score, target_min_area)
                for idx in range(len(points_to_optimize)):
                    if not is_inside_triangle(candidate[points_to_optimize[idx]], A, B, C):
                        # Move toward boundary but maintain buffer
n                        direction = project_to_triangle(candidate[points_to_optimize[idx]]) - candidate[points_to_optimize[idx]]
                        if np.linalg.norm(direction) > buffer:
                            direction = direction / np.linalg.norm(direction) * buffer
                        candidate[points_to_optimize[idx]] += direction
                
                # Check collinearity for all small triangles
                min_area_val = float('inf')
                for _, i, j, k in top_triangles:
                    a, b, c = candidate[i], candidate[j], candidate[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    if area < min_area_val:
                        min_area_val = area
                
                constraint_threshold = max(1e-7, 5e-7 * min_area_val)
                if min_area_val < constraint_threshold:
                    return -np.inf  # Penalize collinearity
                
                # Return negative resistance score for minimization
                return -resistance_score(candidate)
            
            # Initial guess
            x0 = []
            for idx in points_to_optimize:
                x0.extend(restart_best[idx])
            x0 = np.array(x0)
            
            # Adaptive simplex size based on improvement headroom
            headroom = 0.0365 - min_area
            simplex_size = 0.05 * np.sqrt(headroom)
            
            # Run Nelder-Mead
            try:
                result = minimize(objective, x0, method='Nelder-Mead', 
                                 options={'xatol': 1e-8, 'fatol': 1e-8,
                                         'initial_simplex': [x0 + np.random.normal(0, simplex_size, size=x0.shape) 
                                                            for _ in range(len(x0)+1)]})
                
                if result.success:
                    improved = result.x.reshape(-1, 2)
                    # Update points and validate
                    candidate = restart_best.copy()
                    for idx, point_idx in enumerate(points_to_optimize):
                        candidate[point_idx] = improved[idx]
                    # Project any out-of-bound points with adaptive buffer
                    buffer = get_boundary_buffer(restart_best_score, target_min_area)
                    for idx in points_to_optimize:
                        if not is_inside_triangle(candidate[idx], A, B, C):
                            direction = project_to_triangle(candidate[idx]) - candidate[idx]
                            if np.linalg.norm(direction) > buffer:
                                direction = direction / np.linalg.norm(direction) * buffer
                            candidate[idx] += direction
                    # Check if improvement
                    new_score = resistance_score(candidate)
                    if new_score > restart_best_score:
                        restart_best = candidate
                        restart_best_score = new_score
            except:
                # Fall back to original if optimization fails
                pass
        else:
            # Original single-triangle optimization
            min_area, (i, j, k) = find_smallest_triangle(restart_best)
            if min_area < 0.0365 * 0.95:  # Only if not near optimal
                # Define objective function for Nelder-Mead
                def objective(x):
                    candidate = restart_best.copy()
                    candidate[[i, j, k]] = x.reshape(3, 2)
                    
                    # Project points back to triangle with adaptive buffer
                    buffer = get_boundary_buffer(restart_best_score, target_min_area)
                    for idx in [i, j, k]:
                        if not is_inside_triangle(candidate[idx], A, B, C):
                            direction = project_to_triangle(candidate[idx]) - candidate[idx]
                            if np.linalg.norm(direction) > buffer:
                                direction = direction / np.linalg.norm(direction) * buffer
                            candidate[idx] += direction
                    
                    # Check collinearity
                    a, b, c = candidate[i], candidate[j], candidate[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    constraint_threshold = max(1e-7, 5e-7 * min_area)
                    if area < constraint_threshold:
                        return -np.inf  # Penalize collinearity
                    
                    # Return negative resistance score for minimization
                    return -resistance_score(candidate)
                
                # Initial guess
                x0 = restart_best[[i, j, k]].flatten()
                # Adaptive simplex size based on improvement headroom
                headroom = 0.0365 - min_area
                simplex_size = 0.05 * np.sqrt(headroom)
                
                # Run Nelder-Mead
                try:
                    result = minimize(objective, x0, method='Nelder-Mead', 
                                     options={'xatol': 1e-8, 'fatol': 1e-8,
                                             'initial_simplex': [x0 + np.random.normal(0, simplex_size, size=x0.shape) 
                                                                for _ in range(len(x0)+1)]})
                    
                    if result.success:
                        improved = result.x.reshape(3, 2)
                        # Update points and validate
                        candidate = restart_best.copy()
                        candidate[[i, j, k]] = improved
                        # Project any out-of-bound points with adaptive buffer
                        buffer = get_boundary_buffer(restart_best_score, target_min_area)
                        for idx in [i, j, k]:
                            if not is_inside_triangle(candidate[idx], A, B, C):
                                direction = project_to_triangle(candidate[idx]) - candidate[idx]
                                if np.linalg.norm(direction) > buffer:
                                    direction = direction / np.linalg.norm(direction) * buffer
                                candidate[idx] += direction
                        # Check if improvement
                        new_score = resistance_score(candidate)
                        if new_score > restart_best_score:
                            restart_best = candidate
                            restart_best_score = new_score
                except:
                    # Fall back to original if optimization fails
                    pass

        # Update global best
        if restart_best_score > best_score:
            best_score = restart_best_score
            best_config = restart_best
            improvement_count += 1
        
        # Update pattern score
        pattern_scores[dist_idx]['score'] = (
            pattern_scores[dist_idx]['score'] * (pattern_scores[dist_idx]['count'] - 1) + 
            restart_best_score
        ) / pattern_scores[dist_idx]['count']

        # Track resistance history for plateau detection
        resistance_history.append(restart_best_score)
        if len(resistance_history) > plateau_window:
            resistance_history.pop(0)
            # Check if we've plateaued
            if max(resistance_history) - min(resistance_history) < plateau_threshold:
                # Continue with additional restarts
                adaptive_restart_count = min(25, adaptive_restart_count + 2)

    # Final validation - only fix points violating containment with adaptive buffer
    buffer = get_boundary_buffer(best_score, target_min_area)
    for i in range(11):
        if not is_inside_triangle(best_config[i], A, B, C):
            # Move toward boundary but maintain buffer
            boundary_point = project_to_triangle(best_config[i])
            direction = boundary_point - best_config[i]
            if np.linalg.norm(direction) > buffer:
                direction = direction / np.linalg.norm(direction) * buffer
            best_config[i] += direction

    return best_config