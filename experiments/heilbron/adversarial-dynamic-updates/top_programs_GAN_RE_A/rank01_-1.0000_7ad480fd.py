import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
from scipy.spatial import Delaunay, Voronoi

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Function to place points along an edge with strategic spacing
    def place_along_edge(start, end, positions):
        points = []
        for t in positions:
            point = (1-t) * start + t * end
            points.append(point)
        return points
    
    # Generate edge-specific spacing with constrained ranges
    def get_edge_spacings(edge_type, quality_factor):
        # Different spacing patterns for each edge to break symmetry
        if edge_type == 'AB':
            # AB edge: Outer points: 0.05-0.25 (low quality) → 0.10-0.20 (high quality)
            outer_low = 0.05 + 0.05 * (1.0 - quality_factor)
            outer_high = 0.25 - 0.05 * (1.0 - quality_factor)
            # Center point: 0.40-0.60 (low quality) → 0.45-0.55 (high quality)
            center_low = 0.40 + 0.05 * (1.0 - quality_factor)
            center_high = 0.60 - 0.05 * (1.0 - quality_factor)
        elif edge_type == 'BC':
            # BC edge: Outer points: 0.10-0.20 (low quality) → 0.05-0.25 (high quality)
            outer_low = 0.10 - 0.05 * (1.0 - quality_factor)
            outer_high = 0.20 + 0.05 * (1.0 - quality_factor)
            # Center point: 0.35-0.65 (low quality) → 0.40-0.60 (high quality)
            center_low = 0.35 + 0.05 * (1.0 - quality_factor)
            center_high = 0.65 - 0.05 * (1.0 - quality_factor)
        else:  # CA edge
            # CA edge: Outer points: 0.15-0.25 (low quality) → 0.05-0.15 (high quality)
            outer_low = 0.15 - 0.10 * (1.0 - quality_factor)
            outer_high = 0.25 - 0.10 * (1.0 - quality_factor)
            # Center point: 0.30-0.70 (low quality) → 0.45-0.55 (high quality)
            center_low = 0.30 + 0.15 * (1.0 - quality_factor)
            center_high = 0.70 - 0.15 * (1.0 - quality_factor)
        
        # Generate random positions within constrained ranges
        left_pos = np.random.uniform(outer_low, outer_high)
        center_pos = np.random.uniform(center_low, center_high)
        right_pos = 1.0 - np.random.uniform(outer_low, outer_high)
        
        return [left_pos, center_pos, right_pos]

    # Generate interior points using Voronoi vertices
    def get_voronoi_interior_points(boundary_points, quality_factor):
        # Create Delaunay triangulation of boundary points
        tri = Delaunay(boundary_points)
        
        # Get Voronoi vertices from Delaunay triangulation
        vor = Voronoi(boundary_points)
        
        # Filter Voronoi vertices to those inside the triangle
        valid_points = []
        for point in vor.vertices:
            if is_inside_triangle(point, A, B, C):
                valid_points.append(point)
        
        # If not enough points, generate additional random interior points
        while len(valid_points) < 2:
            # Generate random barycentric coordinates
            u = np.random.random()
            v = np.random.random() * (1 - u)
            w = 1 - u - v
            point = u * A + v * B + w * C
            if is_inside_triangle(point, A, B, C):
                valid_points.append(point)
        
        # Select top candidates based on distance to boundary and other points
        scored_points = []
        for point in valid_points:
            # Calculate distance to boundary
            u, v, w = get_barycentric_coords(point, A, B, C)
            dist_to_boundary = min(u, v, w)
            
            # Calculate min distance to other points
            min_dist = float('inf')
            for p in boundary_points:
                dist = np.linalg.norm(point - p)
                if dist < min_dist:
                    min_dist = dist
            
            # Score combines distance to boundary and other points
            score = 0.7 * dist_to_boundary + 0.3 * min_dist
            scored_points.append((score, point))
        
        # Sort by score and select top points
        scored_points.sort(key=lambda x: x[0], reverse=True)
        interior_points = [p for _, p in scored_points[:4]]
        
        # Adjust count based on quality (more interior points when quality is poor)
        n_interior = max(2, min(4, int(4 - 2 * quality_factor)))
        return interior_points[:n_interior]

    # Calculate quality factor (0.0-1.0, 0=perfect)
    def calculate_quality_factor(current_min_area, target=0.0365):
        return max(0.0, min(1.0, 1.0 - current_min_area / target))

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
    def boundary_repulsion(point, A, B, C, quality_factor):
        u, v, w = get_barycentric_coords(point, A, B, C)
        
        # Calculate distance to each boundary (smaller value = closer to boundary)
        dist_to_AB = u
        dist_to_BC = v
        dist_to_CA = w
        
        # Apply repulsion force when near boundaries (stronger near boundaries)
        # Inverted formula: stronger repulsion for poor quality configurations
        repulsion_strength = 0.05 * (1.5 - 0.5 * quality_factor)
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

    # Calculate area gradient with improved weighting
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

    # Get adaptive triangle indices based on current min_area
    def get_adaptive_triangle_indices(points, ratio=1.15):
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
        # Only include triangles with area < ratio*min_area
        adaptive_indices = [idx for area, idx in zip(areas, indices) if area < ratio * min_area]
        
        # If none found (shouldn't happen), return smallest one
        if not adaptive_indices:
            sorted_indices = [idx for _, idx in sorted(zip(areas, indices))]
            return [sorted_indices[0]]
            
        return adaptive_indices

    # Periodic Voronoi cell reassignment to escape local optima
    def voronoi_reassignment(points, A, B, C):
        # Create Voronoi diagram
        vor = Voronoi(points)
        
        # Get new points at Voronoi vertices (centers of Voronoi cells)
        new_points = []
        for region in vor.regions:
            if not region or -1 in region:
                continue
            
            # Calculate centroid of Voronoi cell
n            vertices = np.array([vor.vertices[i] for i in region])
            centroid = np.mean(vertices, axis=0)
            
            # Ensure point is inside the triangle
            if is_inside_triangle(centroid, A, B, C):
                new_points.append(centroid)

        # If we don't have enough points, keep some original points
        if len(new_points) < 11:
            # Sort points by their Voronoi cell area (larger cells first)
            cell_areas = []
            for i, region in enumerate(vor.regions):
                if not region or -1 in region or i >= len(points):
                    continue
                vertices = np.array([vor.vertices[i] for i in region])
                # Calculate approximate area of Voronoi cell
                area = 0.5 * abs(np.dot(vertices[:,0], np.roll(vertices[:,1], 1)) - 
                               np.dot(vertices[:,1], np.roll(vertices[:,0], 1)))
                cell_areas.append((area, i))
            
            cell_areas.sort(reverse=True)
            selected_indices = set()
            for _, idx in cell_areas:
                if len(selected_indices) >= 11 - len(new_points):
                    break
                selected_indices.add(idx)
            
            # Add original points with largest cells
            for i in selected_indices:
                new_points.append(points[i])

        # If still not enough points, add random points
        while len(new_points) < 11:
            u = np.random.random()
            v = np.random.random() * (1 - u)
            w = 1 - u - v
            point = u * A + v * B + w * C
            if is_inside_triangle(point, A, B, C):
                new_points.append(point)

        # Return exactly 11 points
        return np.array(new_points[:11])

    # Multi-chain annealing implementation for robust optimization
    def run_annealing_chain(initial_points, base_step, T0, T_decay_base, step_decay_base, min_ratio, quality_factor):
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

        # Track gradient success rate for adaptive gradient usage
        gradient_success_history = []
        isotropic_success_history = []
        
        # Dynamic gradient usage based on quality (more exploration for poor quality)
        gradient_usage = 0.3 * quality_factor

        # Adaptive triangle ratio starts higher and decreases during optimization
        triangle_ratio = 1.15
        triangle_ratio_decay = (1.05 / 1.15) ** (1.0 / n_rounds)

        for round_idx in range(n_rounds):
            # Periodic Voronoi reassignment to escape local optima
            if round_idx > 0 and round_idx % 50 == 0:
                best = voronoi_reassignment(best, A, B, C)
                best_score = get_smallest_triangle_area(best)
                improvement_history = []
                stagnation_counter = 0

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
                    best[i] = boundary_repulsion(best[i], A, B, C, quality_factor)
                
                stagnation_counter = max(0, stagnation_counter - 5)
                improvement_history = improvement_history[-20:]

            T = T0 * (T_decay ** round_idx)
            current_step = base_step * (step_decay ** round_idx)
            
            # Update triangle ratio
            triangle_ratio = max(1.05, triangle_ratio * triangle_ratio_decay)

            # Get adaptive triangle indices based on current min_area
            triangle_indices = get_adaptive_triangle_indices(best, ratio=triangle_ratio)
            chosen_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
            
            # Dynamic gradient usage adjustment based on success history
            if len(gradient_success_history) > 5 and len(isotropic_success_history) > 5:
                gradient_success_rate = np.mean(gradient_success_history[-5:])
                isotropic_success_rate = np.mean(isotropic_success_history[-5:])
                
                # Adjust gradient usage based on relative performance
                if gradient_success_rate > isotropic_success_rate:
                    gradient_usage = min(0.9, gradient_usage * 1.1)
                else:
                    gradient_usage = max(0.2, gradient_usage * 0.9)

            # Create candidate solution
            candidate = best.copy()
            if np.random.rand() < gradient_usage:
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

                # Track gradient move success
                gradient_success_history.append(0)  # Will update after score calculation
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

                # Track isotropic move success
                isotropic_success_history.append(0)  # Will update after score calculation

            # Ensure all points stay inside triangle using boundary repulsion with fallback
            for i in range(len(candidate)):
                candidate[i] = boundary_repulsion(candidate[i], A, B, C, quality_factor)

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - best_score
            
            # Track improvements for adaptive cooling
            if delta > 0:
                improvement_history.append(delta)
                if len(improvement_history) > 50:
                    improvement_history.pop(0)

            # Update success history
            if len(gradient_success_history) > 0 and gradient_success_history[-1] == 0:
                gradient_success_history[-1] = 1 if delta > 0 else 0
            if len(isotropic_success_history) > 0 and isotropic_success_history[-1] == 0:
                isotropic_success_history[-1] = 1 if delta > 0 else 0

            # Keep success histories bounded
            if len(gradient_success_history) > 20:
                gradient_success_history.pop(0)
            if len(isotropic_success_history) > 20:
                isotropic_success_history.pop(0)

            # Acceptance criterion
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                best = candidate
                best_score = candidate_score

        return best, best_score

    # Initial boundary points
    A, B, C = get_unit_triangle()
    
    # Generate initial edge points with edge-specific spacing
    ab_spacings = get_edge_spacings('AB', 0.5)  # Use medium quality factor for initial spacing
    bc_spacings = get_edge_spacings('BC', 0.5)
    ca_spacings = get_edge_spacings('CA', 0.5)

    edge_points = []
    edge_points.extend(place_along_edge(A, B, ab_spacings))
    edge_points.extend(place_along_edge(B, C, bc_spacings))
    edge_points.extend(place_along_edge(C, A, ca_spacings))
    
    # Generate Voronoi-based interior points
    interior_points = get_voronoi_interior_points(np.array(edge_points), 0.5)
    points = np.array(edge_points + interior_points)

    # Calculate initial quality to adapt parameters
    initial_min_area = get_smallest_triangle_area(points)
    quality_factor = calculate_quality_factor(initial_min_area)

    # Run multiple annealing chains with logarithmically spaced parameters
    chains = []
    
    # Widen parameter ranges based on quality factor
    base_step_min = 0.015 * (1.0 + 0.5 * (1.0 - quality_factor))
    base_step_max = 0.09 * (1.0 + 0.5 * (1.0 - quality_factor))
    T0_min = 0.006 * (1.0 + 0.5 * (1.0 - quality_factor))
    T0_max = 0.014 * (1.0 + 0.5 * (1.0 - quality_factor))
    
    # Use logarithmic spacing for better parameter coverage
    chain_count = max(3, min(5, int(2 + 3 * quality_factor)))
    base_steps = np.logspace(np.log10(base_step_min), np.log10(base_step_max), chain_count)
    T0_values = np.logspace(np.log10(T0_min), np.log10(T0_max), chain_count)
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
            min_ratio=0.01,
            quality_factor=quality_factor
        )
        chains.append((chain, score))
    
    # Select the best chain result
    best_chain = max(chains, key=lambda x: x[1])
    return best_chain[0]