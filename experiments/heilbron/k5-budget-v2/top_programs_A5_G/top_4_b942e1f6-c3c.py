# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def _g_entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Parameters
    num_trials = 100
    hill_climbing_steps = 5000
    base_seed = 42
    initial_temp = 0.1

    best_config = None
    best_min_area = -1

    for trial in range(num_trials):
        # Set deterministic seed per trial
        np.random.seed(base_seed + trial)
        random.seed(base_seed + trial)
        
        # 80% chance for row structure initialization (increased from 50%), 20% for quadratic curve
        if random.random() < 0.8:
            # Targeted row count: 5 rows (70%), 4 rows (15%), 6 rows (15%)
            r = random.random()
            if r < 0.7:
                rows = 5
            elif r < 0.85:
                rows = 4
            else:
                rows = 6
            
            # Base allocation: 1 point per row
            points_per_row = [1] * rows
            # Distribute remaining points cyclically (max 2 extra per row)
            remaining = 11 - rows
            for i in range(remaining):
                points_per_row[i % rows] += 1
            random.shuffle(points_per_row)
            v_levels = sorted([random.uniform(0.1, 0.9) for _ in range(rows)])

            points = []
            for i in range(rows):
                n = points_per_row[i]
                v = v_levels[i]
                shift = random.uniform(-0.1, 0.1) * (1 - v)
                for j in range(n):
                    u = (j + 0.5) / n * (1 - v) + shift
                    u = max(0, min(u, 1 - v))
                    P = (1 - u - v) * A + u * B + v * C
                    # Reduced perturbation for row-based initialization (±0.002 instead of ±0.01)
                    P += np.random.uniform(-0.002, 0.002, size=2)
                    points.append(P)
            config = np.array(points)
        else:
            # Quadratic curve initialization (barycentric parabolic distribution)
            points = []
            for i in range(11):
                v = i / 10.0  # Height coordinate (weight for C)
                u = (1 - v)**2 / 2.0  # Weight for B
                w = 1 - u - v  # Weight for A
                P = w * A + u * B + v * C
                # Original perturbation maintained for quadratic curve
                P += np.random.uniform(-0.01, 0.01, size=2)
                points.append(P)
            config = np.array(points)
        
        # Validate initial config
        if not is_inside_triangle(config, A, B, C):
            continue
        current_min_area = get_smallest_triangle_area(config)
        if current_min_area <= 0:
            continue
        
        # Simulated annealing setup with adaptive cooling
        current_config = config.copy()
        trial_best_config = config
        trial_best_min_area = current_min_area
        T = initial_temp
        base_cooling = 0.99
        cooling_rate = base_cooling
        acceptance_history = []  # Track recent move acceptances

        for step in range(hill_climbing_steps):
            # Linear step size decay starting from 0.1
            step_size = 0.1 + (0.001 - 0.1) * (step / hill_climbing_steps)
            
            # Adaptive perturbation scope: 90% chance for 1-3 points, 10% for 4-5
            if random.random() < 0.9:
                k = random.randint(1, 3)
            else:
                k = random.randint(4, 5)
            indices = random.sample(range(11), k)
            new_config = current_config.copy()
            
            for idx in indices:
                angle = random.uniform(0, 2 * np.pi)
                dx = step_size * np.cos(angle)
                dy = step_size * np.sin(angle)
                perturbation = np.array([dx, dy])
                new_config[idx] += perturbation
            
            # Check validity
            if not is_inside_triangle(new_config, A, B, C):
                continue
            
            new_min_area = get_smallest_triangle_area(new_config)
            if new_min_area <= 0:
                continue
            
            # Simulated annealing acceptance
            delta = new_min_area - current_min_area
            accepted = delta > 0 or random.random() < np.exp(delta / T)
            
            if accepted:
                current_config = new_config
                current_min_area = new_min_area
                if current_min_area > trial_best_min_area:
                    trial_best_config = current_config
                    trial_best_min_area = current_min_area

            # Update acceptance history
            acceptance_history.append(accepted)
            if len(acceptance_history) > 100:
                acceptance_history.pop(0)

            # Adaptive cooling every 10 steps (CORRECTED LOGIC)
            if step % 10 == 0 and step > 0 and acceptance_history:
                recent_acceptance = sum(acceptance_history) / len(acceptance_history)
                if recent_acceptance < 0.4:  # Too few moves accepted -> cool slower
                    cooling_rate = min(0.999, cooling_rate * 1.05)
                elif recent_acceptance > 0.6:  # Too many moves accepted -> cool faster
                    cooling_rate = max(0.9, cooling_rate * 0.95)

            # Cool temperature
            T *= cooling_rate

        # Adaptive multi-scale local search
        step_size_local = 0.01
        max_local_steps = 100
        for local_step in range(max_local_steps):
            improved = False
            # Define directions with current step size
            directions = [
                (step_size_local, 0), (-step_size_local, 0),
                (0, step_size_local), (0, -step_size_local),
                (step_size_local, step_size_local), (step_size_local, -step_size_local),
                (-step_size_local, step_size_local), (-step_size_local, -step_size_local)
            ]
            for i in range(11):
                current_min = get_smallest_triangle_area(current_config)
                for dx, dy in directions:
                    new_config = current_config.copy()
                    new_config[i] += np.array([dx, dy])
                    if not is_inside_triangle(new_config, A, B, C):
                        continue
                    new_min = get_smallest_triangle_area(new_config)
                    if new_min > current_min:
                        current_config = new_config
                        improved = True
            if not improved:
                # Reduce step size and check termination
                step_size_local *= 0.5
                if step_size_local < 1e-5:
                    break

        # Update global best
        final_min_area = get_smallest_triangle_area(current_config)
        if final_min_area > best_min_area:
            best_config = current_config
            best_min_area = final_min_area

    return best_config

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import random


def _d_entrypoint():
    A, B, C = get_unit_triangle()

    def triangle_area(a, b, c):
        return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))

    def find_min_triangles(pts, k=1):
        n = pts.shape[0]
        areas = []
        indices = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = triangle_area(pts[i], pts[j], pts[k])
                    areas.append(area)
                    indices.append((i, j, k))
        
        # Sort by area and take top k
        sorted_idx = np.argsort(areas)
        top_k_areas = [areas[i] for i in sorted_idx[:k]]
        top_k_indices = [indices[i] for i in sorted_idx[:k]]
        
        return top_k_areas, top_k_indices

    def project_to_triangle_boundary(point, A, B, C):
        """Project a point to the closest point on the triangle boundary."""
        # Calculate projections to each edge
        def project_to_line(p, a, b):
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / np.dot(ab, ab)
            t = max(0, min(1, t))
            return a + t * ab
        
        # Project to each edge
        p_ab = project_to_line(point, A, B)
        p_bc = project_to_line(point, B, C)
        p_ca = project_to_line(point, C, A)
        
        # Find closest projection
        d_ab = np.linalg.norm(point - p_ab)
        d_bc = np.linalg.norm(point - p_bc)
        d_ca = np.linalg.norm(point - p_ca)
        
        if d_ab <= d_bc and d_ab <= d_ca:
            return p_ab
        elif d_bc <= d_ab and d_bc <= d_ca:
            return p_bc
        else:
            return p_ca

    def density_aware_threshold(candidate, current_min_area, k=3):
        """Calculate density-aware threshold for distance penalty"""
        n = candidate.shape[0]
        thresholds = []
        
        for i in range(n):
            # Find k nearest neighbors
            distances = []
            for j in range(n):
                if i != j:
                    dist = np.linalg.norm(candidate[i] - candidate[j])
                    distances.append(dist)
            
            distances.sort()
            avg_dist_to_knn = sum(distances[:k]) / k if k <= len(distances) else distances[0]
            
            # Threshold proportional to local density
            # Higher density -> smaller threshold
            density_factor = 1.0 / (avg_dist_to_knn + 1e-8)
            base_threshold = 0.3 * current_min_area
            adaptive_threshold = base_threshold * min(1.0, density_factor * 0.05)
            
            thresholds.append(adaptive_threshold)
        
        # Return average threshold
        return sum(thresholds) / n

    def distance_penalty(candidate, original_points, current_min_area):
        """Penalize movements that create small distances to other points"""
        # Adaptive threshold based on current min_area and local density
        threshold = density_aware_threshold(candidate, current_min_area)
        n = candidate.shape[0]
        penalty = 0.0
        for i in range(n):
            for j in range(i+1, n):
                dist = np.linalg.norm(candidate[i] - candidate[j])
                orig_dist = np.linalg.norm(original_points[i] - original_points[j])
                # If distance decreased significantly and is now small
                if dist < threshold and dist < orig_dist * 0.8:
                    penalty += (threshold - dist) * 10.0  # Stronger penalty for smaller distances
        return penalty

    def improve(points: np.ndarray) -> np.ndarray:
        # Use input-dependent seed for diversification
        seed = int(hash(points.tobytes()) % (2**32))
        np.random.seed(seed)
        random.seed(seed)
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        # FIXED: Temperature initialization is now directly proportional to solution quality
        # Higher min_area (deeper basin) needs MORE exploration, not less
        initial_temp = 0.15 * (current_score / 0.0365) ** 0.7
        initial_temp = max(0.05, min(0.3, initial_temp))  # Bounded between 0.05 and 0.3

        # Track recent improvements for adaptive cooling
        improvement_history = []
        max_history = 50
        
        # Basin-hopping parameters
        basin_hopping_interval = 50
        basin_hopping_counter = 0
        basin_hopping_active = False

        # NEW: Stagnation tracking for temperature reheating
        stagnation_counter = 0
        max_stagnation = 100  # Steps before reheating

        current_temp = initial_temp
        
        # DYNAMIC ITERATION CONTROL
        min_rounds = 100
        max_rounds = 1000
        # CHANGED: stagnation_threshold is now adaptive to current solution quality
        stagnation_threshold = 1e-6 * current_score
        step_size_val = 0.015  # Starting step size

        for round in range(max_rounds):
            # ADAPTIVE STEP SIZE: Increase if stuck, decrease if making progress
            # CHANGED: Scale thresholds by current solution quality
            threshold_scale = max(1e-3, current_score / 0.0365)
            # CHANGED: step_size_adapt_threshold increased from 1e-6 to 1e-5
            step_size_adapt_threshold = 1e-5 * threshold_scale
            
            if len(improvement_history) >= 10:
                recent_improvements = improvement_history[-10:]
                avg_improvement = sum(recent_improvements) / len(recent_improvements)
                if avg_improvement < step_size_adapt_threshold:  # Stuck
                    step_size_val = min(0.03, step_size_val * 1.05)  # Increase to escape
                    basin_hopping_counter += 1
                else:
                    step_size_val = max(0.001, step_size_val * 0.99)  # Decrease for precision
                    basin_hopping_counter = 0
            
            # EARLY STOPPING CRITERIA
            if round > min_rounds and avg_improvement < stagnation_threshold:
                stagnation_counter += 1
                if stagnation_counter >= 50:  # 50 rounds of minimal improvement
                    break
            else:
                stagnation_counter = 0
            
            # BASIN-HOPPING: Escape deep local minima
            if basin_hopping_counter >= basin_hopping_interval:
                # Randomly displace 30% of points beyond boundary
                num_to_displace = max(1, int(0.3 * 11))
                indices = random.sample(range(11), num_to_displace)
                
                for idx in indices:
                    # Displace beyond boundary in random direction
                    direction = np.random.uniform(-1, 1, 2)
                    direction = direction / (np.linalg.norm(direction) + 1e-8)
                    
                    # CHANGED: Fixed displacement formula to increase with solution quality
                    score_ratio = current_score / 0.0365
                    displacement_base = 0.2 + 0.1 * score_ratio
                    displacement_range = 0.2
                    displacement_magnitude = displacement_base + random.random() * displacement_range
                    
                    displacement = direction * displacement_magnitude
                    current[idx] += displacement
                    
                    # Project back to boundary
                    if not is_inside_triangle(current[idx:idx+1], A, B, C):
                        current[idx] = project_to_triangle_boundary(current[idx], A, B, C)
                
                # Recalculate score after basin hop
                current_score = get_smallest_triangle_area(current)
                if current_score > best_score:
                    best = current.copy()
                    best_score = current_score
                basin_hopping_counter = 0
                basin_hopping_active = True
                continue
            
            # Temperature-dependent k selection: higher temp → higher k (more exploration)
            # DYNAMIC TRANSITIONS BASED ON IMPROVEMENT RATE
            if len(improvement_history) >= 20:
                recent_improvements = improvement_history[-20:]
                improvement_rate = sum(recent_improvements) / 20
                # NEW: Scale thresholds by current solution quality
                cooling_slow_threshold = 1e-5 * threshold_scale
                cooling_fast_threshold = 1e-6 * threshold_scale
                
                if improvement_rate > cooling_slow_threshold:  # Good progress
                    k = 3
                elif improvement_rate > cooling_fast_threshold:  # Moderate progress
                    k = 2
                else:  # Stalled
                    k = 1
            else:
                # Early stage - broad exploration
                k = 3
            
            min_areas, min_indices_list = find_min_triangles(current, k=k)
            
            # STRATEGIC TRIANGLE SELECTION BASED ON IMPROVEMENT POTENTIAL
            improvement_potentials = []
            for idx, (tri_area, tri_indices) in enumerate(zip(min_areas, min_indices_list)):
                i, j, k_idx = tri_indices
                a, b, c = current[i], current[j], current[k_idx]
                
                # Calculate gradient as before
                f = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                sign_f = 1.0 if f >= 0 else -1.0
                grad_a = np.array([b[1]-c[1], c[0]-b[0]]) * 0.5 * sign_f
                grad_b = np.array([c[1]-a[1], a[0]-c[0]]) * 0.5 * sign_f
                grad_c = np.array([a[1]-b[1], b[0]-a[0]]) * 0.5 * sign_f
                
                # Calculate combined gradient strength
                total_grad_norm = np.linalg.norm(grad_a) + np.linalg.norm(grad_b) + np.linalg.norm(grad_c)
                
                # FIXED: Boundary penalty is now additive instead of multiplicative
                boundary_penalty = 1.0
                for point_idx in tri_indices:
                    # Project to boundary and calculate distance
                    boundary_point = project_to_triangle_boundary(current[point_idx], A, B, C)
                    dist_to_boundary = np.linalg.norm(current[point_idx] - boundary_point)
                    # Scale boundary reference by triangle geometry
                    triangle_height = np.linalg.norm(C - A)  # Height of the unit triangle
                    boundary_scale = triangle_height * 0.1  # 10% of height as reference
                    # Points closer to boundary have less room to move
                    point_penalty = max(0, 1.0 - dist_to_boundary / boundary_scale)
                    boundary_penalty = min(boundary_penalty, point_penalty)
                
                # Calculate improvement potential
                improvement_potential = total_grad_norm * boundary_penalty
                improvement_potentials.append(improvement_potential)

            # Select triangle with highest improvement potential
            selected_idx = np.argmax(improvement_potentials)
            min_area = min_areas[selected_idx]
            i, j, k_idx = min_indices_list[selected_idx]
            
            a, b, c = current[i], current[j], current[k_idx]

            f = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
            sign_f = 1.0 if f >= 0 else -1.0

            grad_a = np.array([b[1]-c[1], c[0]-b[0]]) * 0.5 * sign_f
            grad_b = np.array([c[1]-a[1], a[0]-c[0]]) * 0.5 * sign_f
            grad_c = np.array([a[1]-b[1], b[0]-a[0]]) * 0.5 * sign_f

            def normalize_grad(grad, step_size):
                norm = np.linalg.norm(grad)
                if norm < 1e-8:
                    return np.zeros(2)
                return grad / norm * step_size

            delta_a = normalize_grad(grad_a, step_size_val)
            delta_b = normalize_grad(grad_b, step_size_val)
            delta_c = normalize_grad(grad_c, step_size_val)

            candidate = current.copy()
            candidate[i] += delta_a
            candidate[j] += delta_b
            candidate[k_idx] += delta_c

            # 15% chance to perturb random non-min-triangle points for global exploration
            # INCREASED INTENSITY WHEN STUCK
            perturbation_prob = 0.15
            if basin_hopping_active or (len(improvement_history) >= 30 and 
                sum(improvement_history[-30:]) < 1e-5):
                perturbation_prob = 0.3  # Higher probability when stuck

            if random.random() < perturbation_prob:
                # Select 2-3 random points that are NOT in the critical triangle
                available_indices = [idx for idx in range(11) if idx not in (i, j, k_idx)]
                if available_indices:
                    num_to_perturb = random.choice([2, 3])
                    if basin_hopping_active:
                        num_to_perturb = random.choice([3, 4, 5])  # More points when escaping
                    perturb_indices = random.sample(available_indices, 
                                                 min(num_to_perturb, len(available_indices)))
                    # CHANGED: Increased perturbation intensity
                    step = step_size_val * 0.5
                    # Apply small random perturbations to these points
                    for idx in perturb_indices:
                        direction = np.random.uniform(-1, 1, 2)
                        direction = direction / (np.linalg.norm(direction) + 1e-8)
                        candidate[idx] += direction * step

            # Boundary projection using exact geometric projection
            for idx in range(candidate.shape[0]):
                if not is_inside_triangle(candidate[idx:idx+1], A, B, C):
                    candidate[idx] = project_to_triangle_boundary(candidate[idx], A, B, C)

            # Apply distance penalty to prevent creating new small triangles elsewhere
            penalty = distance_penalty(candidate, current, current_score)
            candidate_score = get_smallest_triangle_area(candidate)
            # Adjust score to discourage configurations with new small distances
            adjusted_score = candidate_score - penalty * 0.1
            
            # NEW: Track stagnation for temperature recovery
            delta = adjusted_score - current_score
            if delta <= 0:
                stagnation_counter += 1
            else:
                stagnation_counter = 0

            # NEW: Temperature reheating after prolonged stagnation
            if stagnation_counter >= max_stagnation:
                # Reheat temperature proportionally to stagnation duration
                reheating_factor = 1.0 + (stagnation_counter - max_stagnation) / 100.0
                current_temp = min(initial_temp, current_temp * reheating_factor)
                stagnation_counter = 0  # Reset counter after reheating

            improvement_history.append(max(0, delta))
            if len(improvement_history) > max_history:
                improvement_history.pop(0)
            
            # Dynamic cooling rate: slower cooling when making good progress
            if len(improvement_history) >= 10:
                recent_improvements = improvement_history[-10:]
                avg_improvement = sum(recent_improvements) / len(recent_improvements)
                # NEW: Scale thresholds by current solution quality
                cooling_slow_threshold = 1e-5 * threshold_scale
                cooling_fast_threshold = 1e-6 * threshold_scale
                
                # CHANGED: Cooling rates slowed down
                if avg_improvement > cooling_slow_threshold:
                    cooling_rate = 0.9995  # Slower cooling for good progress
                elif avg_improvement > cooling_fast_threshold:
                    cooling_rate = 0.997
                else:
                    cooling_rate = 0.993  # Slower cooling when stuck
            else:
                cooling_rate = 0.9995

            if delta > 0 or np.random.rand() < np.exp(delta / current_temp):
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score
                basin_hopping_active = False

            # Update temperature
            current_temp *= cooling_rate

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)