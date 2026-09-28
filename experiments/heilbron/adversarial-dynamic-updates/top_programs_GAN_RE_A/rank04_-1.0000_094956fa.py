import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Function to place points along an edge with adaptive distribution
    def place_along_edge(start, end, positions):
        points = []
        for t in positions:
            point = (1-t) * start + t * end
            points.append(point)
        return points
    
    # Generate adaptive edge spacing using quality-dependent distribution
    def get_edge_spacings(quality_factor):
        # As quality improves (quality_factor decreases), shift points toward vertices
        # Using beta distribution to control point density
        distribution_factor = 1.0 - quality_factor
        
        # Beta distribution parameters: (alpha, beta)
        # When distribution_factor=0 (perfect quality), points cluster at vertices (alpha=beta=0.5)
        # When distribution_factor=1 (poor quality), points are uniform (alpha=beta=1.0)
        alpha = 0.5 + 0.5 * distribution_factor
        beta = 0.5 + 0.5 * distribution_factor
        
        # Generate positions using beta distribution
        positions = np.random.beta(alpha, beta, 3)
        positions = np.sort(positions)  # Ensure ordered positions
        
        # Ensure points stay within edge (0,1)
        positions = np.clip(positions, 0.05, 0.95)
        
        return positions.tolist()

    # Generate adaptive interior points with variable count and positions
    def get_interior_points(quality_factor, base_points):
        # As quality improves, add more interior points and position them strategically
        interior_points = []
        
        # Base interior points (always included)
        for bp in base_points:
            interior_points.append(bp)
        
        # Add additional interior points based on quality
        if quality_factor < 0.7:  # Good quality configuration
            # Add points in strategic locations
            interior_points.append(A + 0.25 * (C - A) + 0.25 * (B - A))
            interior_points.append(A + 0.75 * (C - A) + 0.25 * (B - A))
            
        if quality_factor < 0.4:  # Excellent quality configuration
            # Add even more strategic points
            interior_points.append(A + 0.5 * (C - A) + 0.35 * (B - A))
            
        return interior_points

    # Strategic Heilbronn configuration for n=11 with interior points
    edge_points = []
    # Generate base edge points without quality factor
    ab_spacings = get_edge_spacings(0.5)  # Initial guess
    bc_spacings = get_edge_spacings(0.5)
    ca_spacings = get_edge_spacings(0.5)

    # AB edge: parameterized positions
    edge_points.extend(place_along_edge(A, B, ab_spacings))
    # BC edge: parameterized positions
    edge_points.extend(place_along_edge(B, C, bc_spacings))
    # CA edge: parameterized positions
    edge_points.extend(place_along_edge(C, A, ca_spacings))
    
    # Add base interior points
    base_interior1 = A + 0.33 * (C - A) + 0.15 * (B - A)
    base_interior2 = A + 0.67 * (C - A) + 0.15 * (B - A)
    edge_points.append(base_interior1)
    edge_points.append(base_interior2)
    
    # Convert to numpy array
    points = np.array(edge_points)
    
    # Calculate quality factor based on current configuration
    def calculate_quality_factor(current_min_area, target=0.0365):
        return max(0.0, min(1.0, 1.0 - current_min_area / target))

    # Calculate initial quality AFTER generating points
    initial_min_area = get_smallest_triangle_area(points)
    quality_factor = calculate_quality_factor(initial_min_area)

    # Recalculate edge spacings based on actual quality
    ab_spacings = get_edge_spacings(quality_factor)
    bc_spacings = get_edge_spacings(quality_factor)
    ca_spacings = get_edge_spacings(quality_factor)

    # Regenerate edge points with proper quality-based spacing
    edge_points = []
    edge_points.extend(place_along_edge(A, B, ab_spacings))
    edge_points.extend(place_along_edge(B, C, bc_spacings))
    edge_points.extend(place_along_edge(C, A, ca_spacings))
    
    # Generate adaptive interior points
    base_interior_points = [
        A + 0.33 * (C - A) + 0.15 * (B - A),
        A + 0.67 * (C - A) + 0.15 * (B - A)
    ]
    interior_points = get_interior_points(quality_factor, base_interior_points)
    
    # Combine all points
    all_points = edge_points + interior_points
    
    # If we have too many points, select the best 11
    if len(all_points) > 11:
        # Calculate minimum triangle area for each possible subset
        # For efficiency, we'll use a greedy approach
        selected_indices = list(range(6))  # Always keep edge points
        remaining_indices = list(range(6, len(all_points)))
        
        # Add interior points that maximize minimum triangle area
        while len(selected_indices) < 11 and remaining_indices:
            best_score = -1
            best_idx = -1
            
            for idx in remaining_indices:
                test_indices = selected_indices + [idx]
                test_points = np.array([all_points[i] for i in test_indices])
                score = get_smallest_triangle_area(test_points)
                
                if score > best_score:
                    best_score = score
                    best_idx = idx
            
            if best_idx >= 0:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)

        points = np.array([all_points[i] for i in selected_indices])
    else:
        points = np.array(all_points)

    # Calculate gradient of triangle area with respect to vertex positions
    def calculate_area_gradient(points, triangle_indices):
        i, j, k = triangle_indices
        a, b, c = points[i], points[j], points[k]
        
        # Area = 0.5 * |(b-a) × (c-a)|
        grad_a = np.array([-(b[1] - c[1]), b[0] - c[0]]) * 0.5
        grad_b = np.array([-(c[1] - a[1]), c[0] - a[0]]) * 0.5
        grad_c = np.array([-(a[1] - b[1]), a[0] - b[0]]) * 0.5
        
        # Calculate distances for weighting
        dist_ab = max(1e-10, np.linalg.norm(a - b))
        dist_bc = max(1e-10, np.linalg.norm(b - c))
        dist_ca = max(1e-10, np.linalg.norm(c - a))
        
        # Weight gradients by inverse distance product
        weight_a = 1.0 / (dist_ab * dist_ca)
        weight_b = 1.0 / (dist_ab * dist_bc)
        weight_c = 1.0 / (dist_bc * dist_ca)
        
        grad_a = grad_a * weight_a
        grad_b = grad_b * weight_b
        grad_c = grad_c * weight_c

        # Normalize gradients
        norm_a = np.linalg.norm(grad_a)
        norm_b = np.linalg.norm(grad_b)
        norm_c = np.linalg.norm(grad_c)
        
        if norm_a > 1e-10:
            grad_a = grad_a / norm_a
        if norm_b > 1e-10:
            grad_b = grad_b / norm_b
        if norm_c > 1e-10:
            grad_c = grad_c / norm_c

        return grad_a, grad_b, grad_c

    # Calculate barycentric coordinates to determine distance to boundary
    def get_barycentric_coords(point, A, B, C):
        v0 = C - A
        v1 = B - A
        v2 = point - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1 - v - w
        return u, v, w

    # Soft boundary repulsion with hard projection fallback
    def boundary_repulsion(point, A, B, C):
        u, v, w = get_barycentric_coords(point, A, B, C)
        
        # Calculate distance to each boundary (smaller value = closer to boundary)
        dist_to_AB = u
        dist_to_BC = v
        dist_to_CA = w
        
        # Apply repulsion force when near boundaries (stronger near boundaries)
        repulsion_strength = 0.05 * (1.0 + 0.5 * quality_factor)  # Adaptive strength
        threshold = 0.1
        repulsion = np.zeros(2)
        
        # Repulsion from AB boundary (u=0)
        if dist_to_AB < threshold:
            repulsion += repulsion_strength * (threshold - dist_to_AB) * (C - point)
        
        # Repulsion from BC boundary (v=0)
        if dist_to_BC < threshold:
            repulsion += repulsion_strength * (threshold - dist_to_BC) * (A - point)
        
        # Repulsion from CA boundary (w=0)
        if dist_to_CA < threshold:
            repulsion += repulsion_strength * (threshold - dist_to_CA) * (B - point)
        
        # Apply repulsion
        new_point = point + repulsion
        
        # Hard projection fallback to ensure validity
        if not is_inside_triangle(new_point, A, B, C):
            def closest_point_on_segment(p, a, b):
                ap = p - a
                ab = b - a
                t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
                t = max(0.0, min(1.0, t))
                return a + t * ab

            p1 = closest_point_on_segment(new_point, A, B)
            p2 = closest_point_on_segment(new_point, B, C)
            p3 = closest_point_on_segment(new_point, C, A)

            d1 = np.linalg.norm(new_point - p1)
            d2 = np.linalg.norm(new_point - p2)
            d3 = np.linalg.norm(new_point - p3)

            if d1 <= d2 and d1 <= d3:
                return p1
            elif d2 <= d1 and d2 <= d3:
                return p2
            else:
                return p3
        
        return new_point

    # Get adaptive triangle indices based on current min_area with stagnation awareness
    def get_adaptive_triangle_indices(points, min_ratio=0.01, improvement_history=None):
        n = len(points)
        areas = []
        indices = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                    areas.append(area)
                    indices.append((i, j, k))
        
        if not areas:
            return [(0, 1, 2)]
            
        min_area = min(areas)
        
        # Calculate adaptive ratio based on improvement history
        adaptive_ratio = 1.15
        if improvement_history and len(improvement_history) >= 10:
            recent_improvements = improvement_history[-10:]
            avg_improvement = np.mean(recent_improvements)
            if avg_improvement < 1e-6:
                # Stagnation detected - widen search window
                adaptive_ratio = min(1.25, 1.15 + 0.1 * (1.0 - quality_factor))
            else:
                # Making progress - narrow search window
                adaptive_ratio = max(1.05, 1.15 - 0.1 * (1.0 - quality_factor))
        
        # Only include triangles with area < adaptive_ratio*min_area
        adaptive_indices = [idx for area, idx in zip(areas, indices) if area < adaptive_ratio * min_area]
        
        # If none found (shouldn't happen), return smallest one
        if not adaptive_indices:
            sorted_indices = [idx for _, idx in sorted(zip(areas, indices))]
            return [sorted_indices[0]]
            
        return adaptive_indices

    # Multi-chain annealing implementation with adaptive gradient usage
    def run_annealing_chain(initial_points, base_step, T0, T_decay_base, step_decay_base, min_ratio):
        best = initial_points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Adaptive number of rounds based on quality
        n_rounds = int(200 + 300 * quality_factor)
        T_decay = T_decay_base
        step_decay = step_decay_base

        # Track improvement history for adaptive cooling
        improvement_history = []
        stagnation_counter = 0
        stagnation_threshold = max(15, min(30, int(20 * (1 + 0.5 * quality_factor))))

        # Track success rates of different move types
        gradient_success_history = []
        isotropic_success_history = []
        
        # Dynamic gradient usage based on success rate
        gradient_usage = 0.5

        for round_idx in range(n_rounds):
            # Adjust cooling rate based on recent progress
            if improvement_history and len(improvement_history) >= 10:
                recent_improvements = improvement_history[-10:]
                avg_improvement = np.mean(recent_improvements)
                if avg_improvement < 1e-6:
                    T_decay = max(0.996, T_decay * 1.001)
                    step_decay = min(0.9995, step_decay * 1.0005)
                    stagnation_counter += 1
                else:
                    T_decay = min(0.9985, T_decay * 0.9998)
                    step_decay = max(0.997, step_decay * 0.9997)
                    stagnation_counter = max(0, stagnation_counter - 1)
            
            # Partial reset if stuck for too long
            if stagnation_counter > stagnation_threshold:
                T_decay = (T_decay + T_decay_base) / 2
                step_decay = (step_decay + step_decay_base) / 2
                
                # Add noise to current best solution
                noise_scale = 0.005 * (1.0 + 0.5 * stagnation_counter / stagnation_threshold)
                for i in range(len(best)):
                    best[i] += np.random.normal(0, noise_scale, size=2)
                    best[i] = boundary_repulsion(best[i], A, B, C)
                
                stagnation_counter = max(0, stagnation_counter - 5)
                improvement_history = improvement_history[-20:]

            T = T0 * (T_decay ** round_idx)
            current_step = base_step * (step_decay ** round_idx)
            
            # Update gradient usage based on success history
            if gradient_success_history and isotropic_success_history:
                gradient_success_rate = np.mean(gradient_success_history[-10:])
                isotropic_success_rate = np.mean(isotropic_success_history[-10:])
                
                # Adjust gradient usage based on relative success
                if isotropic_success_rate > 0:
                    success_ratio = gradient_success_rate / isotropic_success_rate
n                    gradient_usage = max(0.4, min(0.95, gradient_usage * success_ratio))

            # Get adaptive triangle indices with stagnation awareness
            triangle_indices = get_adaptive_triangle_indices(best, min_ratio, improvement_history)
            
            # Randomly select one of the top triangles to work on
            chosen_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
            
            # Determine move type based on adaptive gradient usage
            use_gradient = np.random.rand() < gradient_usage

            candidate = best.copy()
            move_succeeded = False

            if use_gradient:
                # Gradient-based perturbation with weighted gradients
                grad_i, grad_j, grad_k = calculate_area_gradient(best, chosen_triangle)
                
                # 60% chance to perturb one point, 40% to perturb all three
                if np.random.rand() < 0.6:
                    idx = chosen_triangle[np.random.randint(3)]
                    
                    if idx == chosen_triangle[0]:
                        candidate[idx] += grad_i * current_step
                    elif idx == chosen_triangle[1]:
                        candidate[idx] += grad_j * current_step
                    else:
                        candidate[idx] += grad_k * current_step
                else:
                    candidate[chosen_triangle[0]] += grad_i * current_step
                    candidate[chosen_triangle[1]] += grad_j * current_step
                    candidate[chosen_triangle[2]] += grad_k * current_step
            else:
                # Isotropic perturbation (fallback)
                if np.random.rand() < 0.6:
                    idx = chosen_triangle[np.random.randint(3)]
                    r = current_step * np.sqrt(np.random.rand())
                    theta = 2 * np.pi * np.random.rand()
                    perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                    candidate[idx] += perturbation
                else:
                    for idx in chosen_triangle:
                        r = current_step * np.sqrt(np.random.rand())
                        theta = 2 * np.pi * np.random.rand()
                        perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                        candidate[idx] += perturbation

            # Ensure all points stay inside triangle using boundary repulsion with fallback
            for i in range(len(candidate)):
                candidate[i] = boundary_repulsion(candidate[i], A, B, C)

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - best_score
            
            # Track improvements for adaptive cooling
            if delta > 0:
                improvement_history.append(delta)
                move_succeeded = True
                if len(improvement_history) > 50:
                    improvement_history.pop(0)

            # Track move success for gradient usage adjustment
            if use_gradient:
                gradient_success_history.append(1.0 if move_succeeded else 0.0)
                if len(gradient_success_history) > 20:
                    gradient_success_history.pop(0)
            else:
                isotropic_success_history.append(1.0 if move_succeeded else 0.0)
                if len(isotropic_success_history) > 20:
                    isotropic_success_history.pop(0)

            # Acceptance criterion
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                best = candidate
                best_score = candidate_score

        return best, best_score

    # Run multiple annealing chains with logarithmically spaced parameters
    chains = []
    
    # Use logarithmic spacing for better parameter coverage
    chain_count = max(3, min(6, int(3 + 3 * (1.0 - quality_factor))))
    base_steps = np.logspace(np.log10(0.02), np.log10(0.08), chain_count)
    T0_values = np.logspace(np.log10(0.008), np.log10(0.012), chain_count)
    T_decay_values = np.logspace(np.log10(0.9975), np.log10(0.9985), chain_count)
    step_decay_values = np.logspace(np.log10(0.9985), np.log10(0.9995), chain_count)
    
    for i in range(chain_count):
        # Chain with logarithmically spaced parameters
        chain, score = run_annealing_chain(
            points.copy(),
            base_step=base_steps[i],
            T0=T0_values[i],
            T_decay_base=T_decay_values[i],
            step_decay_base=step_decay_values[i],
            min_ratio=0.01
        )
        chains.append((chain, score))
    
    # Select the best chain result
    best_chain = max(chains, key=lambda x: x[1])
    return best_chain[0]