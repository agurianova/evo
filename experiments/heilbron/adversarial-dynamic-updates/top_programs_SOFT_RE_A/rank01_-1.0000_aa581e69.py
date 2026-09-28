import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

class MoveMemory:
    def __init__(self, base_decay_rate=0.15):
        self.moves = []  # Will store (timestamp, improvement_delta, idx, move)
        self.base_decay_rate = base_decay_rate
        self.current_time = 0

    def add(self, improvement_delta, idx, move):
        self.moves.append((self.current_time, improvement_delta, idx, move.copy()))
        self.current_time += 1

    def get_weighted_moves(self, max_moves=50, progress=0.0):
        """Return moves sorted by decayed importance (exp(-decay*age) * improvement_delta)"""
        if not self.moves:
            return []
        
        # Calculate dynamic decay rate based on optimization progress
        # IMPLEMENTATION CHANGE: Slower decay near plateaus to retain effective moves
        if progress < 0.3:  # Early phase: faster decay to forget initial exploration patterns
            decay_factor = 1.2
        elif progress > 0.7:  # Late phase: slower decay to retain effective moves
            decay_factor = 0.7
        else:  # Mid phase: standard decay
            decay_factor = 1.0
        
        decay_rate = self.base_decay_rate * decay_factor
        
        # Calculate current importance with exponential decay
        current_importance = [
            (np.exp(-decay_rate * (self.current_time - timestamp)) * improvement_delta, 
             idx, move)
            for timestamp, improvement_delta, idx, move in self.moves
        ]
        
        # Sort by importance descending
        current_importance.sort(key=lambda x: x[0], reverse=True)
        return current_importance[:max_moves]

    def get_size(self):
        return len(self.moves)

class TriangleCache:
    """Efficiently tracks and updates triangle areas with incremental computation."""
    def __init__(self, points):
        self.n = len(points)
        self.points = points.copy()
        # Precompute all triangle areas
        self.areas = np.zeros((self.n, self.n, self.n))
        for i in range(self.n):
            for j in range(i+1, self.n):
                for k in range(j+1, self.n):
                    self.areas[i,j,k] = self._calculate_triangle_area(i, j, k)

    def _calculate_triangle_area(self, i, j, k):
        """Calculate area of triangle formed by points i, j, k."""
        return 0.5 * abs(
            (self.points[j,0]-self.points[i,0])*(self.points[k,1]-self.points[i,1]) - 
            (self.points[k,0]-self.points[i,0])*(self.points[j,1]-self.points[i,1])
        )

    def update_point(self, idx, new_point):
        """Update a point and only recalculate affected triangles."""
        old_point = self.points[idx].copy()
        self.points[idx] = new_point
        
        # Update all triangles involving this point
        for i in range(self.n):
            if i == idx:
                continue
            for j in range(i+1, self.n):
                if j == idx:
                    continue
                # Sort indices to match storage order
                indices = sorted([idx, i, j])
                i1, i2, i3 = indices[0], indices[1], indices[2]
                self.areas[i1,i2,i3] = self._calculate_triangle_area(i1, i2, i3)
        
        return old_point

    def get_min_area(self):
        """Get the minimum triangle area from cached values."""
        min_area = float('inf')
        for i in range(self.n):
            for j in range(i+1, self.n):
                for k in range(j+1, self.n):
                    if self.areas[i,j,k] < min_area:
                        min_area = self.areas[i,j,k]
        return min_area

    def get_triangle_areas(self):
        """Get all triangle areas as a flat list."""
        areas = []
        for i in range(self.n):
            for j in range(i+1, self.n):
                for k in range(j+1, self.n):
                    areas.append(self.areas[i,j,k])
        return areas

    def get_participation_counts(self, threshold_ratio=1.1):
        """Calculate how many triangles near the minimum area each point participates in."""
        min_area = self.get_min_area()
        threshold = min_area * threshold_ratio
        participation = np.zeros(self.n, dtype=int)
        
        for i in range(self.n):
            for j in range(i+1, self.n):
                for k in range(j+1, self.n):
                    if self.areas[i,j,k] <= threshold:
                        participation[i] += 1
                        participation[j] += 1
                        participation[k] += 1
        
        return participation

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

def calculate_adaptive_gradient(point_idx, config, A, B, C, min_area=None, progress=0.0, stagnation_depth=0, recent_improvement_window=10):
    """Calculate gradient with adaptive method: central differences early, forward differences late with stagnation-aware switching."""
    if min_area is None:
        min_area = get_smallest_triangle_area(config)
    
    # Adaptive epsilon scaling with current min_area for numerical stability
    epsilon = 0.5 * max(min_area, 1e-7)  # Adaptive scaling proportional to min_area
    
    # IMPLEMENTATION CHANGE: Adaptive gradient switching based on stagnation
    # RIGIDITY FIX: Replace fixed threshold with stagnation-aware one
    # Original rigid pattern used hardcoded 0.7 threshold
    # Now: progress_threshold = 0.8 - 0.2 * (stagnation_depth/recent_improvement_window)
    # This maintains central differences longer when stuck in local optima
    progress_threshold = 0.8 - 0.2 * min(1.0, stagnation_depth/recent_improvement_window)
    progress_threshold = max(0.7, min(0.9, progress_threshold))  # Keep in reasonable range
    
    # Switch from central to forward differences based on optimization progress AND stagnation
    if progress < progress_threshold:  # Use central differences during exploration phase
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
    else:  # Use forward differences during exploitation phase (more efficient)
        dx = np.zeros(2)
        dy = np.zeros(2)
        dx[0] = epsilon
        dy[1] = epsilon

        # Positive x direction
        config_x_pos = config.copy()
        config_x_pos[point_idx] += dx
        if not is_inside_triangle(config_x_pos[point_idx].reshape(1, 2), A, B, C):
            config_x_pos[point_idx] = project_to_triangle(config_x_pos[point_idx], A, B, C)
        score_x_pos = get_smallest_triangle_area(config_x_pos)

        # Positive y direction
        config_y_pos = config.copy()
        config_y_pos[point_idx] += dy
        if not is_inside_triangle(config_y_pos[point_idx].reshape(1, 2), A, B, C):
            config_y_pos[point_idx] = project_to_triangle(config_y_pos[point_idx], A, B, C)
        score_y_pos = get_smallest_triangle_area(config_y_pos)

        # Current score
        current_score = get_smallest_triangle_area(config)

        # Forward difference calculation (first-order accurate)
        grad_x = (score_x_pos - current_score) / epsilon
        grad_y = (score_y_pos - current_score) / epsilon
        
        return np.array([grad_x, grad_y])

def generate_initial_configuration(A, B, C):
    """Generate symmetry-aware initial configuration using one-sextant sampling and reflection."""
    # Calculate triangle center and rotation points
    center = (A + B + C) / 3
    
    # Define the 60-degree wedge near vertex A (one sextant of the triangle)
    # This is the fundamental domain for the equilateral triangle's symmetry group
    wedge_points = []
    
    # Generate points in the wedge using farthest-point sampling
    wedge_points.append(A)
    
    # Helper function to check if point is in the wedge
    def is_in_wedge(point):
        # Check if point is in the 60-degree wedge near A
        # The wedge is bounded by edge AB and the median from A to BC
        v1 = B - A
        v2 = center - A
        vp = point - A
        
        # Normalize vectors
        v1 = v1 / np.linalg.norm(v1)
        v2 = v2 / np.linalg.norm(v2)
        vp = vp / np.linalg.norm(vp)
        
        # Check if point is between v1 and v2
        cross1 = np.cross(v1, vp)
        cross2 = np.cross(vp, v2)
        return cross1 >= -1e-10 and cross2 >= -1e-10

    # Generate 2 points in the wedge (we'll reflect to get 12 total, then remove one)
    for _ in range(2):
        max_min_dist = 0
        candidate_point = None
        
        # Sample candidate points in the wedge
        for _ in range(500):
            # Generate random point in triangle using barycentric coordinates
            u, v = np.random.random(2)
            if u + v > 1:
                u, v = 1 - u, 1 - v
            w = 1 - u - v
            point = u * A + v * B + w * C
            
            # Only consider points in the wedge
            if not is_in_wedge(point):
                continue
            
            # Find minimum distance to existing wedge points
            min_dist = min(np.linalg.norm(point - p) for p in wedge_points)
            
            if min_dist > max_min_dist:
                max_min_dist = min_dist
                candidate_point = point
        
        if candidate_point is not None:
            wedge_points.append(candidate_point)
    
    # Now reflect points across symmetry axes to fill the triangle
    all_points = wedge_points.copy()
    
    # Rotation matrix for 60 degrees
    angle = np.pi / 3
    rot_matrix = np.array([
        [np.cos(angle), -np.sin(angle)],
        [np.sin(angle), np.cos(angle)]
    ])
    
    # Reflect points 5 times (60, 120, 180, 240, 300 degrees)
    for i in range(5):
        angle = (i + 1) * np.pi / 3
        rot_matrix = np.array([
            [np.cos(angle), -np.sin(angle)],
            [np.sin(angle), np.cos(angle)]
        ])
        
        for point in wedge_points:
            # Translate point to origin, rotate, translate back
            rotated = np.dot(rot_matrix, (point - center).T).T + center
n            # Only add if inside triangle and distinct from existing points
            if is_inside_triangle(rotated, A, B, C):
                # Check for distinctness
                is_distinct = True
                for p in all_points:
                    if np.linalg.norm(rotated - p) < 1e-5:
                        is_distinct = False
                        break
                if is_distinct:
                    all_points.append(rotated)
    
    # We might have more than 11 points due to symmetry, so trim to 11
    if len(all_points) > 11:
        # Keep the points with largest minimum distances
        distances = []
        for i, p in enumerate(all_points):
            min_dist = min(np.linalg.norm(p - p2) for j, p2 in enumerate(all_points) if i != j)
            distances.append((min_dist, i))
        distances.sort(reverse=True)
        selected_indices = [i for _, i in distances[:11]]
        all_points = [all_points[i] for i in selected_indices]
    
    return np.array(all_points)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate symmetry-aware initial configuration
    points = generate_initial_configuration(A, B, C)
    
    # Validate initial configuration
    if not is_inside_triangle(points, A, B, C):
        points = generate_initial_configuration(A, B, C)
    
    # Memory for successful moves with exponential decay
    move_memory = MoveMemory(base_decay_rate=0.15)  # Increased decay_rate from 0.05 to 0.15
    
    # Create triangle cache for efficient area calculations
    triangle_cache = TriangleCache(points)
    
    # Simulated annealing for robust local optimization
    initial_temp = 0.05 * 1.2  # Increased by 20% for better exploration
    final_temp = 1e-5
    
    # ADJUSTED: Increased iteration budget based on optimization progress
    max_estimated_min_area = 0.0365
    progress_ratio = 0.0  # Will be updated during optimization
    n_steps = max(500, min(1000, int(800 * (1 + 0.5 * (1 - progress_ratio)))))
    
    best_points = points.copy()
    best_score = get_smallest_triangle_area(points)
    current_score = best_score
    
    # Track recent improvements for adaptive scheduling
    improvement_history = []
    recent_improvement_window = 10
    no_improve_count = 0
    stagnation_depth = 0
    max_estimated_min_area = 0.0365  # Theoretical maximum for 11 points

    # Track resistance metrics for adaptive restarts
    resistance_history = []
    resistance_window = 5
    T_resistance = max_estimated_min_area / 9  # ~0.004

    for step in range(n_steps):
        # Track progress for adaptive parameter tuning
        progress = step / n_steps
        progress_ratio = current_score / max_estimated_min_area
        
        # Polynomial temperature decay (slower than exponential)
        temp = initial_temp * (1 - progress) ** 0.3
        
        # ADAPTIVE STEP SIZE DECAY: Responds to optimization dynamics
        # Original rigid pattern used fixed power-law decay
        # Now: step_size = 0.05 * (0.01 / 0.05) ** adaptive_exponent
        if len(improvement_history) > 0:
            avg_improvement = np.mean(improvement_history)
            # Slow decay when improvements are small (need more exploration)
            if avg_improvement < 0.001:
                adaptive_exponent = progress * (1 + 0.5 * max(0, 0.001 - avg_improvement))
            else:
                adaptive_exponent = progress
        else:
            adaptive_exponent = progress
        
        # CHANGE: Enhanced step size adaptation with mid-phase exploration boost
        base_step_size = 0.05
        # FIXED: target_step_size proportional to min_area to prevent overshooting
        # ADDED: floor to maintain minimum exploration capability when min_area is small
        target_step_size = max(0.3 * current_score, 0.005)
        # SHIFTED: exploration boost to earlier phase with stronger magnitude
        mid_phase_boost = 1.0 + 0.3 * np.exp(-4 * (progress - 0.4)**2)
        step_size = base_step_size * (target_step_size / base_step_size) ** adaptive_exponent * mid_phase_boost
        
        # Dynamic bottleneck probability based on recent improvements
        if step > 0:
            improvement_history.append(current_score - previous_score)
            if len(improvement_history) > recent_improvement_window:
                improvement_history.pop(0)
        
        if len(improvement_history) > 0:
            avg_improvement = np.mean(improvement_history)
            # If improvements are large, reduce bottleneck focus to explore more
            if avg_improvement > 0.001:
                adaptive_bottleneck_prob = max(0.3, 0.6 - 0.3 * progress_ratio)
            else:
                # If improvements are small, increase bottleneck focus
                adaptive_bottleneck_prob = min(0.9, 0.6 + 0.3 * progress_ratio)
        else:
            adaptive_bottleneck_prob = 0.6  # Start with moderate focus

        # Identify bottleneck points (triangles within adaptive threshold of min_area)
        bottleneck_points = []
        if step > n_steps * 0.1:  # Start identifying bottlenecks after initial exploration
            # USE TRIANGLE CACHE FOR EFFICIENT CALCULATION
            participation = triangle_cache.get_participation_counts(threshold_ratio=1.15)
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
            # USE TRIANGLE CACHE FOR EFFICIENT CALCULATION
            participation = triangle_cache.get_participation_counts(threshold_ratio=1.15)
            
            # FIXED: Use proper weighting that prioritizes high-participation points
            if len(participation) > 0:
                max_participation = max(participation)
                for idx in indices:
                    # Use adaptive gradient calculation based on optimization progress
                    grad = calculate_adaptive_gradient(idx, candidate, A, B, C, current_score, progress, stagnation_depth, recent_improvement_window)
                    if np.linalg.norm(grad) > 1e-3:
                        # REFINED: Weighting with power=1.5 to focus on true bottlenecks without over-concentration
                        ratio = participation[idx] / max_participation
                        weight = min(1.0, 0.2 + 0.8 * (ratio ** 1.5))
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
        
        # Update triangle cache with candidate configuration
        old_points = triangle_cache.points.copy()
        for idx in indices:
            triangle_cache.update_point(idx, candidate[idx])
        
        # Calculate candidate score using cache
        candidate_score = triangle_cache.get_min_area()
        
        # Simulated annealing acceptance
        delta = candidate_score - current_score
        
        if delta > 0 or (temp > 1e-5 and np.random.random() < np.exp(delta / temp)):
            points = candidate
            current_score = candidate_score
            no_improve_count = 0
            stagnation_depth = 0
            
            # Store successful moves with priority based on improvement magnitude and recency
            if gradient_success:
                improvement_delta = candidate_score - best_score
                for idx in indices:
                    move = candidate[idx] - points[idx]
                    if np.linalg.norm(move) > 1e-5:
                        move_memory.add(improvement_delta, idx, move)

            if candidate_score > best_score:
                best_points = candidate.copy()
                best_score = candidate_score
        else:
            # Restore old points in cache
            for idx in indices:
                triangle_cache.update_point(idx, old_points[idx])
            no_improve_count += 1
            stagnation_depth += 1

        # Track resistance metrics for adaptive restarts
        # FIXED: Using continuous resistance tracking instead of binary
        if delta > 0:
            resistance_impact = 1.0  # Successful move increases resistance
        else:
            # Use sigmoid to capture magnitude of improvement opponents could make
            resistance_impact = 1 / (1 + np.exp(delta / T_resistance))
            
        resistance_history.append(resistance_impact)
        if len(resistance_history) > resistance_window:
            resistance_history.pop(0)

        # Restart mechanism for stagnation - now resistance-aware
        # FIXED: Using progress-dependent threshold to trigger more exploration
        adaptive_restart_threshold = max(3, 8 - 5 * (stagnation_depth / 10))
        
        # CRITICAL ENHANCEMENT: Trigger restarts based on resistance degradation
        # MODERATED: Using higher threshold that depends on optimization progress
        resistance_restart_threshold = max(0.40, 0.6 - 0.20 * progress_ratio)
        
        if len(resistance_history) == resistance_window and np.mean(resistance_history) < resistance_restart_threshold:
            restart_trigger = True
        elif stagnation_depth > adaptive_restart_threshold and move_memory.get_size() > 20:
            restart_trigger = True
        else:
            restart_trigger = False

        if restart_trigger:
            # Get weighted moves sorted by importance
            weighted_moves = move_memory.get_weighted_moves(max_moves=50, progress=progress_ratio)
            
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
                    grad = calculate_adaptive_gradient(idx, restart_candidate, A, B, C, best_score, progress, stagnation_depth, recent_improvement_window)
                    if np.linalg.norm(grad) > 1e-3:
                        grad = grad / np.linalg.norm(grad) * step_size * 1.5
                        restart_candidate[idx] += grad

            # Ensure validity after restart
            for idx in restart_indices:
                if not is_inside_triangle(restart_candidate[idx], A, B, C):
                    restart_candidate[idx] = project_to_triangle(restart_candidate[idx], A, B, C)
            
            # Update triangle cache with restart candidate
            for idx in restart_indices:
                triangle_cache.update_point(idx, restart_candidate[idx])
            restart_score = triangle_cache.get_min_area()
            
            if restart_score > best_score:
                best_points = restart_candidate.copy()
                best_score = restart_score
                points = restart_candidate.copy()
                current_score = restart_score

            # Reset counters after restart
            no_improve_count = 0
            stagnation_depth = max(0, stagnation_depth - 1)
            resistance_history = []  # Reset resistance tracking after successful restart

    return best_points