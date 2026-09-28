import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from sklearn.decomposition import PCA

np.random.seed(42)

class MoveMemory:
    def __init__(self, decay_rate=0.05):
        self.moves = []  # Will store (timestamp, improvement_delta, idx, move)
        self.decay_rate = decay_rate
        self.current_time = 0
        # Track correlated move patterns for defensive purposes
        self.correlated_moves_history = []

    def add(self, improvement_delta, idx, move):
        self.moves.append((self.current_time, improvement_delta, idx, move.copy()))
        self.current_time += 1

    def add_correlated_move(self, correlated_pattern):
        """Track correlated move patterns for defensive analysis"""
        self.correlated_moves_history.append((self.current_time, correlated_pattern.copy()))

    def get_correlated_move_patterns(self, n_components=2, min_moves=20):
        """Analyze historical moves to identify common correlated patterns"""
        if len(self.correlated_moves_history) < min_moves:
            return None
        
        patterns = [pattern for _, pattern in self.correlated_moves_history]
        patterns_matrix = np.array(patterns)
        
        # Apply PCA to find principal components of move patterns
        pca = PCA(n_components=n_components)
        pca.fit(patterns_matrix)
        
        return pca.components_

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
    """Calculate central difference gradient with adaptive epsilon for numerical stability."""
    if min_area is None:
        min_area = get_smallest_triangle_area(config)
    
    # Scaled epsilon threshold prevents numerical instability with small areas
    # CHANGED: Reduced multiplier from 0.02 to 0.015 for better gradient precision
    epsilon = max(1e-5, 0.015 * min_area)
    
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

def calculate_triangle_participation(config):
    """Calculate how many small triangles each point participates in with adaptive threshold."""
    n = len(config)
    participation = np.zeros(n, dtype=int)
    min_area = get_smallest_triangle_area(config)
    max_estimated_min_area = 0.0365  # Theoretical maximum for 11 points
    
    # CHANGED: Widen threshold from 1+0.01+0.06*progress_ratio to 1+0.01+0.08*progress_ratio
    progress_ratio = min_area / max_estimated_min_area
    threshold = min_area * (1 + 0.01 + 0.08 * progress_ratio)

    # Count participation in triangles close to the minimum area
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Calculate area of triangle i,j,k
                area = 0.5 * abs(
                    (config[j,0]-config[i,0])*(config[k,1]-config[i,1]) - 
                    (config[k,0]-config[i,0])*(config[j,1]-config[i,1])
                )
                if area <= threshold:
                    participation[i] += 1
                    participation[j] += 1
                    participation[k] += 1
    
    return participation

def detect_correlated_vulnerability(config, move_memory, A, B, C):
    """Detect if configuration is vulnerable to PCA-based correlated moves"""
    if move_memory.get_size() < 50:
        return False
    
    components = move_memory.get_correlated_move_patterns(n_components=2, min_moves=20)
    if components is None:
        return False
    
    # Check if applying the principal component would improve the configuration
    test_config = config.copy()
    component = components[0]
    # Normalize component to reasonable magnitude
    component = component / np.linalg.norm(component) * 0.01
    
    # Apply component to all points
    for i in range(len(test_config)):
        test_config[i] += component[i % len(component)]
        if not is_inside_triangle(test_config[i].reshape(1, 2), A, B, C):
            test_config[i] = project_to_triangle(test_config[i], A, B, C)
    
    # If this improves the minimum area, we're vulnerable
    original_score = get_smallest_triangle_area(config)
    test_score = get_smallest_triangle_area(test_config)
    
    return test_score > original_score

def apply_correlated_defense(config, move_memory, A, B, C):
    """Apply defensive perturbations to make configuration resistant to correlated moves"""
    if not detect_correlated_vulnerability(config, move_memory, A, B, C):
        return config
    
    # Create a defensive configuration by perturbing in the opposite direction
    defensive_config = config.copy()
    components = move_memory.get_correlated_move_patterns(n_components=2, min_moves=20)
    if components is None:
        return defensive_config
    
    component = components[0]
    # Normalize component to reasonable magnitude but in opposite direction
    component = -component / np.linalg.norm(component) * 0.005
    
    # Apply component to all points
    for i in range(len(defensive_config)):
        defensive_config[i] += component[i % len(component)]
        if not is_inside_triangle(defensive_config[i].reshape(1, 2), A, B, C):
            defensive_config[i] = project_to_triangle(defensive_config[i], A, B, C)
    
    # Verify the defensive configuration is valid
    if is_inside_triangle(defensive_config, A, B, C):
        return defensive_config
    return config

def calculate_opponent_hardness(improvement_history, window=20):
    """Estimate opponent hardness based on early improvement rates"""
    if len(improvement_history) < window:
        return 0.5  # Default medium hardness
    
    # Hardness is inversely proportional to improvement rate
    # Lower improvement rate = harder problem = higher hardness
    early_improvements = improvement_history[:window]
    avg_early_improvement = np.mean(early_improvements)
    
    # Normalize to [0,1] range
    hardness = 1.0 / (1.0 + 100.0 * avg_early_improvement)
    return min(1.0, hardness)

def generate_initial_configuration(A, B, C):
    """Generate Voronoi-based initial configuration using farthest-point sampling with enhanced sampling."""
    # Start with centroid
    points = [(A + B + C) / 3]
    
    # Iteratively add points at Voronoi vertices
    for _ in range(10):  # Need 10 more points to reach 11
        max_min_dist = 0
        candidate_point = None
        
        # CHANGED: Increased from 500 to 2000 samples for better quality
        for _ in range(2000):
            # Generate random point in triangle using barycentric coordinates
            u, v = np.random.random(2)
            if u + v > 1:
                u, v = 1 - u, 1 - v
            w = 1 - u - v
            point = u * A + v * B + w * C
            
            # Find minimum distance to existing points
            min_dist = min(np.linalg.norm(point - p) for p in points)
            
            if min_dist > max_min_dist:
                max_min_dist = min_dist
                candidate_point = point
        
        if candidate_point is not None:
            points.append(candidate_point)
    
    return np.array(points)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate Voronoi-based initial configuration
    points = generate_initial_configuration(A, B, C)
    
    # Validate initial configuration
    if not is_inside_triangle(points, A, B, C):
        points = generate_initial_configuration(A, B, C)
    
    # Memory for successful moves with exponential decay
    initial_temp = 0.12
    n_steps = 500
    move_memory = None

    # Simulated annealing for robust local optimization
    final_temp = 1e-5
    best_points = points.copy()
    best_score = get_smallest_triangle_area(points)
    current_score = best_score
    
    # Track recent improvements for adaptive scheduling
    improvement_history = []
    resistance_history = []
    recent_improvement_window = 10
    resistance_window = 20
    no_improve_count = 0
    stagnation_depth = 0
    max_estimated_min_area = 0.0365
    opponent_hardness = 0.5  # Will be updated based on early improvements

    for step in range(n_steps):
        # Track progress for adaptive parameter tuning
        progress = step / n_steps
        progress_ratio = current_score / max_estimated_min_area
        
        # Initialize move memory with adaptive decay rate
        if step == 0:
            # CHANGED: Reduced coefficient from 0.08 to 0.05 for longer retention
            decay_rate = 0.05 + 0.05 * progress_ratio
            move_memory = MoveMemory(decay_rate=decay_rate)
        
        # Adaptive temperature decay exponent for better exploration-exploitation balance
        exponent = 0.75 - 0.15 * progress_ratio
        temp = initial_temp * (1 - progress) ** exponent
        
        # Power-law step size decay with adaptive exponent
        # CHANGED: From progress**0.6 to progress**0.5 for better late-stage exploration
        step_size = 0.05 * (0.01 / 0.05) ** (progress ** 0.5)

        # Dynamic bottleneck probability based on recent improvements
        if step > 0:
            improvement_history.append(current_score - previous_score)
            if len(improvement_history) > recent_improvement_window:
                improvement_history.pop(0)
        
        # Calculate resistance proxy - high when improvements are small/rare
        if step > 0 and current_score - previous_score > 0:
            improvement_magnitude = (current_score - previous_score) / max_estimated_min_area
            resistance_proxy = 1.0 - improvement_magnitude
        else:
            resistance_proxy = 1.0
        
        resistance_history.append(resistance_proxy)
        if len(resistance_history) > resistance_window:
            resistance_history.pop(0)

        if len(improvement_history) > 0:
            avg_improvement = np.mean(improvement_history)
            # If improvements are large, reduce bottleneck focus to explore more
            if avg_improvement > 0.001:
                adaptive_bottleneck_prob = max(0.3, 0.6 - 0.3 * progress_ratio)
            else:
                # CHANGED: Increased cap from 0.65 to 0.75 for stronger bottleneck focus
                adaptive_bottleneck_prob = min(0.75, 0.6 + 0.15 * progress_ratio)
        else:
            adaptive_bottleneck_prob = 0.7

        # Identify bottleneck points (triangles within adaptive threshold of min_area)
        bottleneck_points = []
        if step > n_steps * 0.1:
            participation = calculate_triangle_participation(points)
            bottleneck_points = [i for i, count in enumerate(participation) if count > 0]

        # Select points to perturb - focus on bottlenecks with adaptive probability
        if len(bottleneck_points) > 0 and np.random.random() < adaptive_bottleneck_prob:
            num_points = np.random.choice([1, 2, 3], p=[0.6, 0.3, 0.1])
            indices = np.random.choice(
                bottleneck_points, 
                size=min(num_points, len(bottleneck_points)), 
                replace=False
            )
        else:
            num_points = np.random.choice([1, 2, 3, 4, 5], p=[0.5, 0.3, 0.15, 0.03, 0.02])
            indices = np.random.choice(11, size=num_points, replace=False)
        
        # Create candidate solution
        candidate = points.copy()
        gradient_success = False
        previous_score = current_score
        
        # Try gradient-informed perturbation with participation weighting
        if np.random.random() < 0.7 and step < n_steps * 0.9:
            participation = calculate_triangle_participation(candidate)
            max_participation = np.max(participation) if np.max(participation) > 0 else 1
            for idx in indices:
                grad = calculate_central_difference_gradient(idx, candidate, A, B, C, current_score)
                if np.linalg.norm(grad) > 1e-3:
                    # CHANGED: Reduced from (1.1+0.3*progress_ratio) to (1.1+0.2*progress_ratio)
                    weight = (participation[idx] / max_participation) ** (1.1 + 0.2 * progress_ratio)
                    # Normalize and scale by adaptive step size
                    grad = grad / np.linalg.norm(grad) * step_size * 2.0 * weight
                    candidate[idx] += grad
                    gradient_success = True
        else:
            # Pure random perturbation
            for idx in indices:
                candidate[idx] += np.random.normal(0, step_size, size=2)
        
        # Project to triangle if needed
        for idx in indices:
            if not is_inside_triangle(candidate[idx], A, B, C):
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
        
        # Calculate acceptance probability
        candidate_score = get_smallest_triangle_area(candidate)
        delta = candidate_score - current_score
        
        # Simulated annealing acceptance
        if delta > 0 or (temp > 1e-5 and np.random.random() < np.exp(delta / temp)):
            points = candidate
            current_score = candidate_score
            no_improve_count = 0
            stagnation_depth = 0
            
            # Store successful moves with priority based on improvement magnitude and recency
n            if gradient_success:
                improvement_delta = candidate_score - best_score
                for idx in indices:
                    move = candidate[idx] - points[idx]
                    if np.linalg.norm(move) > 1e-5:
                        move_memory.add(improvement_delta, idx, move)

            if candidate_score > best_score:
                best_points = candidate.copy()
                best_score = candidate_score
        else:
            no_improve_count += 1
            stagnation_depth += 1

        # Update opponent hardness estimate based on early improvements
        if step == 50:  # After initial exploration phase
            opponent_hardness = calculate_opponent_hardness(improvement_history)

        # Restart mechanism for stagnation - enhanced with resistance-based detection
        avg_resistance = np.mean(resistance_history) if resistance_history else 1.0
        resistance_trend = 0
        if len(resistance_history) >= 5:
            resistance_trend = np.polyfit(range(len(resistance_history[-5:])), resistance_history[-5:], 1)[0]

        # Calculate improvement trend for resistance proxy
        improvement_trend = 0
        if len(improvement_history) >= 5:
            improvement_trend = np.polyfit(range(len(improvement_history[-5:])), improvement_history[-5:], 1)[0]

        # CHANGED: Increased base value from 25 to 30 for longer exploitation phases
        adaptive_restart_threshold = max(15, 30 - 15 * progress_ratio)
        if no_improve_count >= adaptive_restart_threshold or (len(improvement_history) >= 5 and improvement_trend < -0.0001):
            # Use memory-guided restart when we have enough historical data
            if stagnation_depth > adaptive_restart_threshold and move_memory.get_size() > 20:
                # Get weighted moves sorted by importance
                weighted_moves = move_memory.get_weighted_moves(max_moves=50)
                
                # Create restart candidate from best configuration
                restart_candidate = best_points.copy()
                restart_indices = np.random.choice(11, size=np.random.choice([2, 3]), replace=False)
                
                for idx in restart_indices:
                    # Find moves for this index in memory
                    relevant_moves = [(imp, move) for imp, i, move in weighted_moves if i == idx]
                    if relevant_moves:
                        # Weight moves by their calculated importance
                        total_imp = sum(imp for imp, _ in relevant_moves)
                        if total_imp > 0:
                            weights = [imp/total_imp for imp, _ in relevant_moves]
                            # Select a move proportional to its importance
                            selected_idx = np.random.choice(len(relevant_moves), p=weights)
                            avg_move = relevant_moves[selected_idx][1]
                            # Normalize and scale
                            if np.linalg.norm(avg_move) > 1e-5:
                                avg_move = avg_move / np.linalg.norm(avg_move) * step_size * 1.5
                                restart_candidate[idx] += avg_move
                    else:
                        # Fall back to gradient-informed restart
                        grad = calculate_central_difference_gradient(idx, restart_candidate, A, B, C, best_score)
                        if np.linalg.norm(grad) > 1e-3:
                            grad = grad / np.linalg.norm(grad) * step_size * 1.5
                            restart_candidate[idx] += grad

                # Ensure validity after restart
                for idx in restart_indices:
                    if not is_inside_triangle(restart_candidate[idx], A, B, C):
                        restart_candidate[idx] = project_to_triangle(restart_candidate[idx], A, B, C)
                
                restart_score = get_smallest_triangle_area(restart_candidate)
                if restart_score > best_score:
                    best_points = restart_candidate.copy()
                    best_score = restart_score
                    points = restart_candidate.copy()
                    current_score = restart_score

            # Reset counters after restart
            no_improve_count = 0
            stagnation_depth = max(0, stagnation_depth - 1)

        # Apply PCA-based defensive mechanism periodically
        if step % 100 == 0 and step > 0:
            points = apply_correlated_defense(points, move_memory, A, B, C)
            current_score = get_smallest_triangle_area(points)
            if current_score > best_score:
                best_points = points.copy()
                best_score = current_score

    return best_points