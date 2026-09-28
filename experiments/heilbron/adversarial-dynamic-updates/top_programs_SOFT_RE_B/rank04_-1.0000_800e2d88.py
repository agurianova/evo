from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

class MoveMemory:
    def __init__(self, decay_rate=0.05):
        self.moves = []  # Will store (timestamp, improvement_delta, idx, move)
        self.decay_rate = decay_rate
        self.current_time = 0

    def add(self, improvement_delta, idx, move):
        self.moves.append((self.current_time, improvement_delta, idx, move.copy()))
        self.current_time += 1

    def get_weighted_moves(self, max_moves=50):
        """Return moves sorted by decayed importance (exp(-decay*age) * improvement_delta)"""
        if not self.moves:
            return []
        
        # Calculate current importance with exponential decay
        current_importance = [
            (np.exp(-self.decay_rate * (self.current_time - timestamp)) * improvement_delta, 
             idx, move)
            for timestamp, improvement_delta, idx, move in self.moves
        ]
        
        # Sort by importance descending
        current_importance.sort(key=lambda x: x[0], reverse=True)
        return current_importance[:max_moves]

    def get_size(self):
        return len(self.moves)

def get_top_k_smallest_triangles(points, min_gap=0.01, max_k=5):
    """Return indices of top-k smallest triangles based on adaptive gap analysis."""
    n = len(points)
    triangle_areas = []
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Create triangle with these three points
                triangle = np.array([points[i], points[j], points[k]])
                # Calculate area using cross product
                area = 0.5 * abs(
                    (triangle[1,0] - triangle[0,0]) * (triangle[2,1] - triangle[0,1]) -
                    (triangle[2,0] - triangle[0,0]) * (triangle[1,1] - triangle[0,1])
                )
                triangle_areas.append((area, i, j, k))
    
    # Sort by area
    triangle_areas.sort(key=lambda x: x[0])
    
    if not triangle_areas:
        return []
    
    # Adaptive k selection based on relative gaps
    min_area = triangle_areas[0][0]
    k = 1
    
    # Always include at least one triangle
    for i in range(1, min(max_k, len(triangle_areas))):
        gap = (triangle_areas[i][0] - min_area) / (min_area + 1e-10)
        if gap < 0.05:  # Consider triangles within 5% of smallest
            k += 1
        else:
            break
    
    # Return top-k triangles
    return [indices[1:] for indices in triangle_areas[:k]]

def project_to_triangle(point, A, B, C):
    """Project a point to the nearest point inside the triangle."""
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
    
    if abs(denom) < 1e-10:
        return point
        
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w

    # Clamp barycentric coordinates to ensure point is inside triangle
    if u < 0:
        # Project to edge BC
        total = v + w
        if total > 0:
            v, w = v / total, w / total
        u = 0
    if v < 0:
        # Project to edge AC
        total = u + w
        if total > 0:
            u, w = u / total, w / total
        v = 0
    if w < 0:
        # Project to edge AB
        total = u + v
        if total > 0:
            u, v = u / total, v / total
        w = 0

    # Ensure coordinates sum to 1
    total = u + v + w
    if total > 0:
        u, v, w = u/total, v/total, w/total
    
    return u * A + v * B + w * C

def calculate_central_difference_gradient(point_idx, config, A, B, C, min_area=None):
    """Calculate central difference gradient for more accurate estimation with adaptive epsilon."""
    if min_area is None:
        min_area = get_smallest_triangle_area(config)
    
    # Adaptive epsilon scaling with current min_area for numerical stability
    epsilon = max(1e-7, 0.01 * min_area)
    
    # Central differences: sample both positive and negative directions
    dx_pos = np.zeros(2)
    dx_neg = np.zeros(2)
    dx_pos[0] = epsilon
    dx_neg[0] = -epsilon
    
    dy_pos = np.zeros(2)
    dy_neg = np.zeros(2)
    dy_pos[1] = epsilon
    dy_neg[1] = -epsilon

    # Positive x direction
    config_x_pos = config.copy()
    config_x_pos[point_idx] += dx_pos
    if not is_inside_triangle(config_x_pos[point_idx].reshape(1, 2), A, B, C):
        config_x_pos[point_idx] = project_to_triangle(config_x_pos[point_idx], A, B, C)
    score_x_pos = get_smallest_triangle_area(config_x_pos)

    # Negative x direction
    config_x_neg = config.copy()
    config_x_neg[point_idx] += dx_neg
    if not is_inside_triangle(config_x_neg[point_idx].reshape(1, 2), A, B, C):
        config_x_neg[point_idx] = project_to_triangle(config_x_neg[point_idx], A, B, C)
    score_x_neg = get_smallest_triangle_area(config_x_neg)

    # Positive y direction
    config_y_pos = config.copy()
    config_y_pos[point_idx] += dy_pos
    if not is_inside_triangle(config_y_pos[point_idx].reshape(1, 2), A, B, C):
        config_y_pos[point_idx] = project_to_triangle(config_y_pos[point_idx], A, B, C)
    score_y_pos = get_smallest_triangle_area(config_y_pos)

    # Negative y direction
    config_y_neg = config.copy()
    config_y_neg[point_idx] += dy_neg
    if not is_inside_triangle(config_y_neg[point_idx].reshape(1, 2), A, B, C):
        config_y_neg[point_idx] = project_to_triangle(config_y_neg[point_idx], A, B, C)
    score_y_neg = get_smallest_triangle_area(config_y_neg)

    # Central difference calculation (second-order accurate)
    grad_x = (score_x_pos - score_x_neg) / (2 * epsilon)
    grad_y = (score_y_pos - score_y_neg) / (2 * epsilon)
    
    return np.array([grad_x, grad_y])

def calculate_forward_difference_gradient(point_idx, config, A, B, C, min_area=None):
    """Calculate forward difference gradient for efficiency with adaptive epsilon."""
    if min_area is None:
        min_area = get_smallest_triangle_area(config)
    
    # Adaptive epsilon scaling with current min_area for numerical stability
    epsilon = max(1e-7, 0.01 * min_area)
    
    # Current score
    current_score = get_smallest_triangle_area(config)
    
    # Forward differences: sample only positive directions
    dx = np.zeros(2)
    dx[0] = epsilon
    
    dy = np.zeros(2)
    dy[1] = epsilon

    # Positive x direction
    config_x = config.copy()
    config_x[point_idx] += dx
    if not is_inside_triangle(config_x[point_idx].reshape(1, 2), A, B, C):
        config_x[point_idx] = project_to_triangle(config_x[point_idx], A, B, C)
    score_x = get_smallest_triangle_area(config_x)

    # Positive y direction
    config_y = config.copy()
    config_y[point_idx] += dy
    if not is_inside_triangle(config_y[point_idx].reshape(1, 2), A, B, C):
        config_y[point_idx] = project_to_triangle(config_y[point_idx], A, B, C)
    score_y = get_smallest_triangle_area(config_y)

    # Forward difference calculation
    grad_x = (score_x - current_score) / epsilon
    grad_y = (score_y - current_score) / epsilon
    
    return np.array([grad_x, grad_y])

def move_along_edge(point_idx, config, A, B, C, current_score, rng, edge_prob=0.3):
    """Move a point along the nearest triangle edge with adaptive step size.
    Returns: (new_config, success) where success indicates valid boundary movement
    """
    point = config[point_idx]
    
    # Define triangle edges
    edges = [(A, B), (B, C), (C, A)]
    edge_names = ['AB', 'BC', 'CA']
    
    # Find closest edge and projection
    min_dist = float('inf')
    closest_edge_idx = -1
    projected_point = None
    
    for i, (P1, P2) in enumerate(edges):
        # Vector from P1 to P2
        edge_vec = P2 - P1
        edge_len_sq = np.dot(edge_vec, edge_vec)
        
        # Vector from P1 to point
        point_vec = point - P1
        
        # Project point onto edge line
        t = np.dot(point_vec, edge_vec) / edge_len_sq
        t = max(0.0, min(1.0, t))  # Clamp to segment
        proj = P1 + t * edge_vec
n        # Distance to edge
        dist = np.linalg.norm(point - proj)
        if dist < min_dist:
            min_dist = dist
            closest_edge_idx = i
            projected_point = proj
    
    # If point is already on edge, try to move along it
    if min_dist < 1e-5:
        edge_vec = edges[closest_edge_idx][1] - edges[closest_edge_idx][0]
        edge_vec = edge_vec / np.linalg.norm(edge_vec)
        
        # Adaptive step size proportional to current min_area
        step_size = 0.02 * current_score
        
        # Random direction along edge
        direction = 1 if rng.random() < 0.5 else -1
        move = direction * step_size * edge_vec
        
        # Create candidate
        candidate = config.copy()
        candidate[point_idx] = projected_point + move
        
        # Check if still inside triangle (should be, but verify)
        if is_inside_triangle(candidate[point_idx].reshape(1, 2), A, B, C):
            return candidate, True
        
    # If point is near but not on edge, try to project and move
    elif min_dist < 0.05 * current_score:  # Adaptive proximity threshold
        edge_vec = edges[closest_edge_idx][1] - edges[closest_edge_idx][0]
        edge_vec = edge_vec / np.linalg.norm(edge_vec)
        
        # Adaptive step size proportional to current min_area
        step_size = 0.015 * current_score
        
        # Random direction along edge
        direction = 1 if rng.random() < 0.5 else -1
        move = direction * step_size * edge_vec
        
        # Create candidate
        candidate = config.copy()
        candidate[point_idx] = projected_point + move
        
        # Check if inside triangle
        if is_inside_triangle(candidate[point_idx].reshape(1, 2), A, B, C):
            return candidate, True

    return config.copy(), False

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Create input-dependent RNG for adversarial robustness
        seed = abs(hash(points.tobytes())) % (2**32)
        rng = np.random.default_rng(seed)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        
        total_iterations = 500
        early_stop_patience = 30
        T0 = 0.01
        no_improve_count = 0
        stagnation_depth = 0
        
        # Track improvement history for adaptive parameter tuning
        improvement_history = []
        recent_improvement_window = 20
        
        # Adaptive decay rate based on progress and stagnation
        progress = 0.0
        adaptive_decay_rate = 0.02 + 0.08 * (progress + 0.5 * stagnation_depth / total_iterations)
        # Priority-based move memory with exponential decay
        move_memory = MoveMemory(decay_rate=adaptive_decay_rate)

        for i in range(total_iterations):
            # Track progress for adaptive parameter tuning
            progress = i / total_iterations
            if i > 0:
                improvement_history.append(current_score - best_score)
                if len(improvement_history) > recent_improvement_window:
                    improvement_history.pop(0)
            
            # ADAPTIVE TEMPERATURE SCHEDULE
            # Slower decay early, faster decay late
            T = T0 * (1 - progress) ** (0.3 + 0.2 * progress)
            
            # PROGRESSIVE REFINEMENT FOR STEP SIZE
            # Slower decay when improvements are small, faster when improvements are large
            if len(improvement_history) > 5:
                avg_improvement = np.mean(improvement_history[-5:])
                # Scale decay rate based on improvement magnitude
                decay_factor = 1.0 + 0.5 * min(0.1, max(0, -avg_improvement))
            else:
                decay_factor = 1.0
            
            # Adaptive step size with progressive refinement
            sigma = 0.05 * (0.01 / 0.05) ** (decay_factor * progress)
            
            # ADAPTIVE BOTTLENECK COEFFICIENTS BASED ON IMPROVEMENT RATE
            max_estimated_min_area = 0.03  # Theoretical max for 11 points
            
            if len(improvement_history) > 5:
                recent_improvement = np.mean(improvement_history[-5:])
                # If improvements are small, increase focus on bottlenecks
                # CHANGED: Replaced hardcoded 1e-5 threshold with adaptive threshold
                if recent_improvement < max(1e-6, 0.001 * current_score):
                    base_focus_coeff = 0.98  # Increased from hardcoded 0.95
                    slope_focus_coeff = 0.5   # Decreased from hardcoded 0.65
                else:
                    base_focus_coeff = 0.92
                    slope_focus_coeff = 0.7
            else:
                base_focus_coeff = 0.95
                slope_focus_coeff = 0.65

            # ADAPTIVE BOTTLENECK FOCUS PROBABILITY WITH DYNAMIC COEFFICIENTS
            focus_prob = base_focus_coeff - slope_focus_coeff * (current_score / max_estimated_min_area)
            focus_prob = max(0.3, min(0.95, focus_prob))  # Clamp to reasonable range

            # ADAPTIVE BOTTLENECK-FOCUSED PERTURBATION
            if rng.random() < focus_prob:
                # Get adaptive k for smallest triangles based on min_area gap metrics
                triangle_areas = []
                n = len(current)
                for i in range(n):
                    for j in range(i+1, n):
                        for k in range(j+1, n):
                            triangle = np.array([current[i], current[j], current[k]])
                            area = 0.5 * abs(
                                (triangle[1,0] - triangle[0,0]) * (triangle[2,1] - triangle[0,1]) -
                                (triangle[2,0] - triangle[0,0]) * (triangle[1,1] - triangle[0,1])
                            )
                            triangle_areas.append((area, i, j, k))
                
                triangle_areas.sort(key=lambda x: x[0])
                if len(triangle_areas) > 1:
                    # Calculate relative gaps between smallest triangles
                    # CHANGED: Scale gap thresholds by current_score for consistent behavior
                    min_area = triangle_areas[0][0]
                    adaptive_min_gap = 0.015 * min_area
                    adaptive_mid_gap = 0.045 * min_area
                    
                    gaps = [(triangle_areas[i][0] - triangle_areas[0][0]) / (triangle_areas[0][0] + 1e-10) 
                            for i in range(1, min(10, len(triangle_areas)))]
                    # If gaps are small, consider more triangles as bottlenecks
                    if gaps and gaps[0] < adaptive_min_gap:
                        adaptive_max_k = 8
                    elif gaps and gaps[0] < adaptive_mid_gap:
                        adaptive_max_k = 6
                    else:
                        adaptive_max_k = 4
                else:
                    adaptive_max_k = 5
                
                # Get top-k smallest triangles with adaptive selection
                smallest_triangles = get_top_k_smallest_triangles(current, max_k=adaptive_max_k)
                
                # Collect all points participating in bottleneck triangles
                bottleneck_points = set()
                for tri in smallest_triangles:
                    bottleneck_points.update(tri)
                bottleneck_points = list(bottleneck_points)
                
                # Choose 1-3 points from bottleneck points
                num_points = rng.choice([1, 2, 3], p=[0.6, 0.3, 0.1])
                indices = rng.choice(bottleneck_points, size=num_points, replace=False)
            else:
                # Biased probability for number of points to perturb
                num_points = rng.choice([1, 2, 3, 4, 5], p=[0.5, 0.3, 0.15, 0.03, 0.02])
                indices = rng.choice(11, size=num_points, replace=False)

            # CHANGED: Make gradient threshold adaptive based on recent improvement history
            gradient_type_threshold = 0.5
            if len(improvement_history) > 5:
                avg_improvement = np.mean(improvement_history[-5:])
                # If improvements are small relative to current min_area, switch to forward differences earlier
                improvement_ratio = avg_improvement / (1e-4 * current_score + 1e-10)
                gradient_type_threshold = 0.5 + 0.4 * (1 - max(0, min(1, improvement_ratio)))

            # Try gradient-informed perturbation first
            # Adaptive gradient usage with dynamic exponent
            if len(improvement_history) > 5:
                recent_improvement = np.mean(improvement_history[-5:])
                # If improvements are small, use gradients more aggressively
                if recent_improvement < max(1e-6, 0.001 * current_score):
                    adaptive_exponent = 0.4 * 0.7
                else:
                    adaptive_exponent = 0.4 * 1.2
            else:
                adaptive_exponent = 0.4

            use_gradient = 0.3 + 0.7 * (1 - progress) ** adaptive_exponent
            candidate = current.copy()
            gradient_success = False
            
            if rng.random() < use_gradient and i < total_iterations * 0.95:
                # Calculate triangle participation counts for gradient weighting
                participation_counts = np.zeros(11)
                for idx1 in range(11):
                    for idx2 in range(idx1+1, 11):
                        for idx3 in range(idx2+1, 11):
                            # Check if this triangle is among the smallest ones
                            triangle = np.array([candidate[idx1], candidate[idx2], candidate[idx3]])
                            area = 0.5 * abs(
                                (triangle[1,0] - triangle[0,0]) * (triangle[2,1] - triangle[0,1]) -
                                (triangle[2,0] - triangle[0,0]) * (triangle[1,1] - triangle[0,1])
                            )
                            # If area is close to the current smallest, count this triangle
                            if area < current_score * 1.1:  # Consider triangles within 10% of smallest
                                if idx1 in indices or idx2 in indices or idx3 in indices:
                                    participation_counts[idx1] += 1
                                    participation_counts[idx2] += 1
                                    participation_counts[idx3] += 1

                # MODERATED GRADIENT APPLICATION WITH ADAPTIVE TRIANGLE PARTICIPATION WEIGHTING
                for idx in indices:
                    # CHANGED: Use adaptive threshold for gradient type selection
                    if progress < gradient_type_threshold:
                        grad = calculate_central_difference_gradient(idx, candidate, A, B, C, current_score)
                    else:
                        grad = calculate_forward_difference_gradient(idx, candidate, A, B, C, current_score)
                    
                    if np.linalg.norm(grad) > 1e-3:
                        # CHANGED: Adaptive weighting based on bottleneck count
                        if len(smallest_triangles) < 3:  # Few bottlenecks, use reciprocal weighting
                            weight = 1.0 / max(1, participation_counts[idx])
                        else:  # More bottlenecks, use logarithmic weighting
                            weight = 1.0 / np.log(1 + max(1, participation_counts[idx]))
                        # Normalize and scale by adaptive step size
                        grad = grad / np.linalg.norm(grad) * sigma * 2.0 * weight
                        candidate[idx] += grad
                        gradient_success = True
            else:
                # Pure random perturbation
                for idx in indices:
                    candidate[idx] += rng.normal(0, sigma, size=2)

            # CHANGED: SYSTEMATIC BOUNDARY EXPLORATION MECHANISM
            # Add boundary exploration with increasing probability as optimization progresses
            boundary_explore_prob = 0.1 + 0.3 * progress  # Increases from 0.1 to 0.4
            if rng.random() < boundary_explore_prob:
                # Select points near edges for boundary movement
                edge_proximate_points = []
                for idx in range(11):
                    point = candidate[idx]
                    # Check distance to each edge
                    min_edge_dist = float('inf')
                    for (P1, P2) in [(A, B), (B, C), (C, A)]:
                        edge_vec = P2 - P1
                        edge_len_sq = np.dot(edge_vec, edge_vec)
                        point_vec = point - P1
                        t = np.dot(point_vec, edge_vec) / edge_len_sq
                        t = max(0.0, min(1.0, t))
                        proj = P1 + t * edge_vec
                        dist = np.linalg.norm(point - proj)
                        min_edge_dist = min(min_edge_dist, dist)
                    
                    # Consider point edge-proximate if within adaptive threshold
                    if min_edge_dist < 0.05 * current_score:
                        edge_proximate_points.append(idx)

                # If we found edge-proximate points, try to move one along its edge
                if edge_proximate_points:
                    edge_idx = rng.choice(edge_proximate_points)
                    boundary_candidate, success = move_along_edge(
                        edge_idx, candidate, A, B, C, current_score, rng
                    )
                    if success:
                        candidate = boundary_candidate

            # Project to triangle with fallback
            valid = True
            for idx in indices:
                if not is_inside_triangle(candidate[idx].reshape(1, 2), A, B, C):
                    projected = project_to_triangle(candidate[idx], A, B, C)
                    # Check if projection created a degenerate configuration
                    test_config = candidate.copy()
                    test_config[idx] = projected
                    if get_smallest_triangle_area(test_config) < 1e-5:
                        valid = False
                        break
                    candidate[idx] = projected

            if not valid:
                # Amplified random restart as fallback
                candidate = current.copy()
                # CHANGED: Exponential restart_sigma with cap
                restart_sigma = min(0.5, sigma * 5 * (1.2 ** stagnation_depth))
                for idx in indices:
                    candidate[idx] += rng.normal(0, restart_sigma, size=2)
                    if not is_inside_triangle(candidate[idx].reshape(1, 2), A, B, C):
                        candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

            score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            if score > current_score:
                current = candidate
                current_score = score
                no_improve_count = 0
                stagnation_depth = 0
                
                # Store successful moves with priority based on improvement magnitude and recency
                if gradient_success:
                    improvement_delta = score - best_score
                    for idx in indices:
                        move = candidate[idx] - current[idx]
                        if np.linalg.norm(move) > 1e-5:
                            move_memory.add(improvement_delta, idx, move)

                if score > best_score:
                    best = candidate
                    best_score = score
            else:
                delta = score - current_score
                if T > 1e-5 and rng.random() < np.exp(delta / T):
                    current = candidate
                    current_score = score
                    no_improve_count = 0
                    stagnation_depth = max(0, stagnation_depth - 1)
                else:
                    no_improve_count += 1
                    stagnation_depth += 1

            # Restart mechanism for stagnation
            if no_improve_count >= early_stop_patience:
                # Use amplified restart with gradient awareness
                current = best.copy()
                current_score = best_score
                no_improve_count = 0
                stagnation_depth += 1
                
                # ADAPTIVE RESTART THRESHOLD BASED ON PROGRESS TOWARD THEORETICAL MAX
                max_estimated_min_area = 0.03
                adaptive_restart_threshold = max(3, 8 - 5 * (1 - current_score / max_estimated_min_area))
                
                # CHANGED: Exponential restart_sigma with cap
                restart_sigma = min(0.5, sigma * 5 * (1.2 ** stagnation_depth))
                restart_indices = rng.choice(11, size=rng.choice([2, 3]), replace=False)
                
                # Try memory-guided restart when we have enough historical data
                # CHANGED: Make memory threshold adaptive to problem difficulty
                adaptive_memory_threshold = max(15, 20 * (1 - current_score / 0.03))
                if stagnation_depth > adaptive_restart_threshold and move_memory.get_size() > adaptive_memory_threshold:
                    # Get weighted moves sorted by importance (decay * improvement)
                    weighted_moves = move_memory.get_weighted_moves(max_moves=50)
                    
                    for idx in restart_indices:
                        # Find moves for this index in memory
                        relevant_moves = [(imp, move) for imp, i, move in weighted_moves if i == idx]
                        if relevant_moves:
                            # Weight moves by their calculated importance
                            total_imp = sum(imp for imp, _ in relevant_moves)
                            if total_imp > 0:
                                weights = [imp/total_imp for imp, _ in relevant_moves]
                                # Select a move proportional to its importance
                                selected_idx = rng.choice(len(relevant_moves), p=weights)
                                avg_move = relevant_moves[selected_idx][1]
                                # Normalize and scale
                                if np.linalg.norm(avg_move) > 1e-5:
                                    avg_move = avg_move / np.linalg.norm(avg_move) * restart_sigma * 1.5
                                    current[idx] += avg_move
                        else:
                            # Fall back to random perturbation
                            current[idx] += rng.normal(0, restart_sigma, size=2)
                else:
                    # Try gradient-informed restart
                    if rng.random() < 0.6 and stagnation_depth > 5:
                        for idx in restart_indices:
                            # CHANGED: Use appropriate gradient function based on adaptive threshold
                            if progress < gradient_type_threshold:
                                grad = calculate_central_difference_gradient(idx, current, A, B, C, current_score)
                            else:
                                grad = calculate_forward_difference_gradient(idx, current, A, B, C, current_score)
                            if np.linalg.norm(grad) > 1e-3:
                                grad = grad / np.linalg.norm(grad) * restart_sigma * 1.5
                                current[idx] += grad
                    else:
                        # Amplified random perturbation
                        for idx in restart_indices:
                            current[idx] += rng.normal(0, restart_sigma, size=2)

                # Ensure validity after restart
                for idx in restart_indices:
                    if not is_inside_triangle(current[idx].reshape(1, 2), A, B, C):
                        current[idx] = project_to_triangle(current[idx], A, B, C)
                
                if is_inside_triangle(current, A, B, C):
                    current_score = get_smallest_triangle_area(current)
                    if current_score > best_score:
                        best = current.copy()
                        best_score = current_score
                else:
                    current = best.copy()
                    current_score = best_score

            # CHANGED: Update decay rate based on current progress and stagnation
            adaptive_decay_rate = 0.02 + 0.08 * (progress + 0.5 * stagnation_depth / total_iterations)
            move_memory.decay_rate = adaptive_decay_rate

        return best

    return improve