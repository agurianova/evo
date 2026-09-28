import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Calculate edge lengths for spacing constraints
    edge_length_AB = np.linalg.norm(B - A)
    edge_length_BC = np.linalg.norm(C - B)
    edge_length_CA = np.linalg.norm(A - C)
    
    # Function to place points along an edge with asymmetric spacing and minimum distance constraints
    def place_along_edge(start, end, count, min_spacing_ratio=0.15):
        points = []
        total_length = np.linalg.norm(end - start)
        min_spacing = min_spacing_ratio * total_length
        
        # Generate random spacing factors that sum to 1
        spacing_factors = np.random.uniform(0.85, 1.15, count + 1)
        spacing_factors = spacing_factors / np.sum(spacing_factors)
        
        # Ensure minimum spacing
        cumulative = 0
        for i in range(count):
            # Calculate next position with random spacing
            t = cumulative + spacing_factors[i]
            # Enforce minimum spacing
            if i > 0 and (t - cumulative) * total_length < min_spacing:
                t = cumulative + min_spacing / total_length
            
            point = (1 - t) * start + t * end
            points.append(point)
            cumulative = t
            
        return points
    
    # Create asymmetric distribution: 4 points on AB, 3 points on BC, 2 points on CA
    edge_points = []
    # AB edge: 4 points (most vulnerable edge)
    edge_points.extend(place_along_edge(A, B, 4))
    # BC edge: 3 points
    edge_points.extend(place_along_edge(B, C, 3))
    # CA edge: 2 points
    edge_points.extend(place_along_edge(C, A, 2))
    
    # Add interior points using Beta distribution for diversity
    interior_points = []
    
    # Sample 2 interior points using Beta(2,2) distribution (peaked at 0.5)
    for _ in range(2):
        u = np.random.beta(2, 2)
        v = np.random.beta(2, 2) * (1 - u)
        w = 1 - u - v
        # Ensure valid barycentric coordinates
        if w < 0:
            w = 0
            total = u + v
            u, v = u/total, v/total
        point = u * A + v * B + w * C
        interior_points.append(point)
    
    # Combine all points
    points = np.array(edge_points + interior_points)
    
    # Initialize triangle vulnerability tracking
    n = len(points)
    triangle_vulnerability = np.zeros((n, n, n))
    
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
        if abs(denom) < 1e-10:
            return 1/3, 1/3, 1/3
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1 - v - w
        return u, v, w

    # Calculate distance to boundary using barycentric coordinates
    def distance_to_boundary(point, A, B, C):
        u, v, w = get_barycentric_coords(point, A, B, C)
        return min(u, v, w)

    # Soft boundary repulsion (replaces hard projection)
    def soft_boundary_repulsion(point, A, B, C, strength=0.05):
        u, v, w = get_barycentric_coords(point, A, B, C)
        
        # Calculate repulsion vectors from each edge
        repulsion = np.zeros(2)
        
        # Repulsion from AB edge (where w=0)
        if w < 0.2:
            repulsion += strength * (0.2 - w) * (C - A - v * (B - A))
        
        # Repulsion from BC edge (where u=0)
        if u < 0.2:
            repulsion += strength * (0.2 - u) * (A - B - w * (C - B))

        # Repulsion from CA edge (where v=0)
        if v < 0.2:
            repulsion += strength * (0.2 - v) * (B - C - u * (A - C))

        # Normalize repulsion to prevent large jumps
        if np.linalg.norm(repulsion) > 0:
            repulsion = repulsion / np.linalg.norm(repulsion) * min(0.02, np.linalg.norm(repulsion))
            
        return point + repulsion

    # Calculate gradient of triangle area with respect to vertex positions
    def calculate_area_gradient(points, triangle_indices, alpha=1.5):
        i, j, k = triangle_indices
        a, b, c = points[i], points[j], points[k]
        
        # Area = 0.5 * |(b-a) × (c-a)|
        grad_a = np.array([-(b[1] - c[1]), b[0] - c[0]]) * 0.5
        grad_b = np.array([-(c[1] - a[1]), c[0] - a[0]]) * 0.5
        grad_c = np.array([-(a[1] - b[1]), a[0] - b[0]]) * 0.5
        
        # Weight gradients by inverse distance with parameterized exponent
        dist_ab = max(1e-6, np.linalg.norm(a - b))
        dist_ac = max(1e-6, np.linalg.norm(a - c))
        dist_bc = max(1e-6, np.linalg.norm(b - c))
        
        weight_a = 1.0 / (dist_ab ** alpha * dist_ac ** alpha)
        weight_b = 1.0 / (dist_ab ** alpha * dist_bc ** alpha)
        weight_c = 1.0 / (dist_ac ** alpha * dist_bc ** alpha)
        
        grad_a = grad_a * weight_a
        grad_b = grad_b * weight_b
        grad_c = grad_c * weight_c

        return grad_a, grad_b, grad_c

    # Get triangles adaptively based on current min_area
    def get_adaptive_triangle_indices(points, current_min_area, min_area_ratio=1.1):
        n = len(points)
        areas = []
        indices = []
        
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    a, b, c = points[i], points[j], points[k]
                    area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                    areas.append(area)
                    indices.append((i, j, k))
        
        if not areas:
            return [(0, 1, 2)]
        
        # Sort by area
        sorted_indices = [idx for _, idx in sorted(zip(areas, indices))]
        sorted_areas = [area for area, _ in sorted(zip(areas, indices))]
        
        # Get all triangles below min_area * min_area_ratio
        threshold = current_min_area * min_area_ratio
        relevant_indices = [idx for area, idx in zip(areas, indices) if area <= threshold]
        
        # Always return at least 1 triangle
        return relevant_indices if relevant_indices else [sorted_indices[0]]

    # Get triangle with vulnerability weighting
    def get_vulnerability_weighted_triangle(points, current_min_area, min_area_ratio=1.1):
        # Get relevant triangles
        relevant_indices = get_adaptive_triangle_indices(points, current_min_area, min_area_ratio)
        
        # Apply vulnerability weighting
        weights = []
        for idx in relevant_indices:
            i, j, k = idx
            # Higher vulnerability score means higher selection probability
            vulnerability = triangle_vulnerability[i, j, k] + 1.0
            weights.append(vulnerability)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(weights)] * len(weights)
        
        # Select based on weighted probability
        selected_idx = np.random.choice(len(relevant_indices), p=weights)
        return relevant_indices[selected_idx]

    # Update triangle vulnerability scores
    def update_vulnerability_scores(points, original_min_area):
        nonlocal triangle_vulnerability
        
        # Calculate current min area
        current_min_area = get_smallest_triangle_area(points)
        
        # If improvement occurred, update vulnerability scores
        if current_min_area > original_min_area:
            # Find the triangle that was improved
            n = len(points)
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a, b, c = points[i], points[j], points[k]
                        area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                        # If this triangle is now the minimum or was likely improved
                        if abs(area - current_min_area) < 1e-6:
                            # Increase vulnerability score with decay for older improvements
                            triangle_vulnerability[i, j, k] = triangle_vulnerability[i, j, k] * 0.9 + 1.0
                        
        # Apply exponential decay to all scores
        triangle_vulnerability *= 0.995

    # Multi-chain adaptive annealing
    def multi_chain_annealing(initial_points):
        current_min_area = get_smallest_triangle_area(initial_points)
        difficulty_factor = 1.0 - current_min_area / 0.0365
        
        # Create multiple annealing chains with different parameters
        chains = []
        
        # Chain 1: Conservative approach (smaller steps)
        chain1 = annealing_chain(
            initial_points.copy(),
            base_step=0.02 * (1 + 0.5 * difficulty_factor),
            T0=0.008 * (1 + 0.5 * difficulty_factor),
            T_decay=0.9975,
            step_decay=0.9985,
            min_area_ratio=1.05,
            boundary_focus=0.3,
            chain_id=1
        )
        chains.append(chain1)
        
        # Chain 2: Balanced approach
        chain2 = annealing_chain(
            initial_points.copy(),
            base_step=0.05 * (1 + difficulty_factor),
            T0=0.01 * (1 + difficulty_factor),
            T_decay=0.9978,
            step_decay=0.9988,
            min_area_ratio=1.1,
            boundary_focus=0.5,
            chain_id=2
        )
        chains.append(chain2)
        
        # Chain 3: Aggressive approach (larger steps for exploration)
        chain3 = annealing_chain(
            initial_points.copy(),
            base_step=0.08 * (1 + 1.5 * difficulty_factor),
            T0=0.012 * (1 + 1.5 * difficulty_factor),
            T_decay=0.998,
            step_decay=0.999,
            min_area_ratio=1.2,
            boundary_focus=0.4,
            chain_id=3
        )
        chains.append(chain3)
        
        # Chain 4: Boundary-specialized approach (70% edge focus)
        chain4 = annealing_chain(
            initial_points.copy(),
            base_step=0.04 * (1 + 0.8 * difficulty_factor),
            T0=0.009 * (1 + 0.8 * difficulty_factor),
            T_decay=0.997,
            step_decay=0.998,
            min_area_ratio=1.1,
            boundary_focus=0.7,
            chain_id=4
        )
        chains.append(chain4)
        
        # Select the best result
        return max(chains, key=lambda x: get_smallest_triangle_area(x))

    # Single annealing chain with adaptive parameters
    def annealing_chain(points, base_step, T0, T_decay, step_decay, min_area_ratio, boundary_focus, chain_id):
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        original_score = best_score
n        # Dynamic iteration count based on difficulty
        n_rounds = int(200 + 250 * (0.7 + 0.6 * (1 - (1.0 - best_score / 0.0365))))
        
        # Track improvement history for adaptive cooling
        improvement_history = []
        stagnation_counter = 0
        stagnation_threshold = 20
        
        # Dynamic gradient ratio (starts lower, increases as optimization progresses)
        gradient_ratio = 0.5
        
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
            
            # Reset if stuck for too long (with noise)
            adaptive_stagnation_threshold = max(15, min(30, stagnation_threshold + 10 * (stagnation_counter / 5)))
            if stagnation_counter > adaptive_stagnation_threshold:
                T_decay = 0.9975
                step_decay = 0.9985
                stagnation_counter = 0
                improvement_history = []
                
                # Reset with noise to escape local minima
                noise_scale = 0.01 * (1 + 0.5 * (stagnation_counter / adaptive_stagnation_threshold))
                best = best + np.random.normal(0, noise_scale, best.shape)
                
                # Project back to valid space
                for i in range(len(best)):
                    if not is_inside_triangle(best[i], A, B, C):
                        u, v, w = get_barycentric_coords(best[i], A, B, C)
                        u, v, w = max(0, u), max(0, v), max(0, w)
                        total = u + v + w
                        if total > 0:
                            u, v, w = u/total, v/total, w/total
                        best[i] = u * A + v * B + w * C
                
                best_score = get_smallest_triangle_area(best)

            T = T0 * (T_decay ** round_idx)
            current_step = base_step * (step_decay ** round_idx)
            
            # Get relevant triangles adaptively (with vulnerability weighting)
            current_min_area = get_smallest_triangle_area(best)
            # Dynamic min_area_ratio that narrows as optimization progresses
            adaptive_min_area_ratio = 1.0 + 0.3 * (1 - current_min_area / 0.0365)
            triangle_indices = get_vulnerability_weighted_triangle(best, current_min_area, adaptive_min_area_ratio)
            
            # Dynamic gradient ratio based on recent improvement rate
            if improvement_history and len(improvement_history) >= 5:
                recent_improvements = improvement_history[-5:]
                avg_improvement = np.mean(recent_improvements)
                gradient_ratio = 0.5 + 0.4 * min(1.0, avg_improvement / 1e-5)
            else:
                gradient_ratio = 0.5 + 0.4 * (round_idx / n_rounds)
            
            if np.random.rand() < gradient_ratio:
                # Gradient-based perturbations
                # Use parameterized alpha based on improvement rate
                alpha = 1.5 - 0.5 * (mean_improvement / 1e-4 if 'mean_improvement' in globals() else 0)
                alpha = max(0.5, min(2.0, alpha))
                
                grad_i, grad_j, grad_k = calculate_area_gradient(best, triangle_indices, alpha=alpha)
                
                # Determine point selection based on boundary focus
                i, j, k = triangle_indices
                edge_points_mask = np.zeros(len(best), dtype=bool)
                for idx in range(len(best)):
                    dist_to_boundary = distance_to_boundary(best[idx], A, B, C)
                    edge_points_mask[idx] = dist_to_boundary < 0.1
                
                # 60% chance to perturb one point, 40% to perturb all three
                if np.random.rand() < 0.6:
                    # Choose point with boundary focus consideration
                    if np.random.rand() < boundary_focus:
                        # Prefer edge points
                        edge_indices = [idx for idx in triangle_indices if edge_points_mask[idx]]
                        if edge_indices:
                            idx = np.random.choice(edge_indices)
                        else:
                            idx = triangle_indices[np.random.randint(3)]
                    else:
                        # Prefer interior points
                        interior_indices = [idx for idx in triangle_indices if not edge_points_mask[idx]]
                        if interior_indices:
                            idx = np.random.choice(interior_indices)
                        else:
                            idx = triangle_indices[np.random.randint(3)]
                    
                    candidate = best.copy()
                    
                    if idx == triangle_indices[0]:
                        candidate[idx] += grad_i * current_step
                    elif idx == triangle_indices[1]:
                        candidate[idx] += grad_j * current_step
                    else:
                        candidate[idx] += grad_k * current_step
                    
                    # Apply soft boundary repulsion instead of hard projection
                    dist_to_boundary = distance_to_boundary(candidate[idx], A, B, C)
                    if dist_to_boundary < 0.05:
                        candidate[idx] = soft_boundary_repulsion(candidate[idx], A, B, C)
                else:
                    candidate = best.copy()
                    candidate[triangle_indices[0]] += grad_i * current_step
                    candidate[triangle_indices[1]] += grad_j * current_step
                    candidate[triangle_indices[2]] += grad_k * current_step
                    
                    # Apply soft boundary repulsion
                    for i in range(len(candidate)):
                        dist_to_boundary = distance_to_boundary(candidate[i], A, B, C)
                        if dist_to_boundary < 0.05:
                            candidate[i] = soft_boundary_repulsion(candidate[i], A, B, C)
            else:
                # Isotropic perturbations (fallback)
                if np.random.rand() < 0.6:
                    # Choose point with boundary focus consideration
                    i, j, k = triangle_indices
                    edge_points_mask = np.zeros(len(best), dtype=bool)
                    for idx in range(len(best)):
                        dist_to_boundary = distance_to_boundary(best[idx], A, B, C)
                        edge_points_mask[idx] = dist_to_boundary < 0.1
                    
                    if np.random.rand() < boundary_focus:
                        # Prefer edge points
                        edge_indices = [idx for idx in triangle_indices if edge_points_mask[idx]]
                        if edge_indices:
                            idx = np.random.choice(edge_indices)
                        else:
                            idx = triangle_indices[np.random.randint(3)]
                    else:
                        # Prefer interior points
                        interior_indices = [idx for idx in triangle_indices if not edge_points_mask[idx]]
                        if interior_indices:
                            idx = np.random.choice(interior_indices)
                        else:
                            idx = triangle_indices[np.random.randint(3)]
                    
                    candidate = best.copy()
                    r = current_step * np.sqrt(np.random.rand())
                    theta = 2 * np.pi * np.random.rand()
                    perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                    candidate[idx] += perturbation
                    
                    # Apply soft boundary repulsion
                    dist_to_boundary = distance_to_boundary(candidate[idx], A, B, C)
                    if dist_to_boundary < 0.05:
                        candidate[idx] = soft_boundary_repulsion(candidate[idx], A, B, C)
                else:
                    candidate = best.copy()
                    for idx in triangle_indices:
                        r = current_step * np.sqrt(np.random.rand())
                        theta = 2 * np.pi * np.random.rand()
                        perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                        candidate[idx] += perturbation
                        
                        # Apply soft boundary repulsion
                        dist_to_boundary = distance_to_boundary(candidate[idx], A, B, C)
                        if dist_to_boundary < 0.05:
                            candidate[idx] = soft_boundary_repulsion(candidate[idx], A, B, C)
            
            # Ensure all points stay inside triangle (final check)
            for i in range(len(candidate)):
                if not is_inside_triangle(candidate[i], A, B, C):
                    # Fallback to barycentric projection if still outside
                    u, v, w = get_barycentric_coords(candidate[i], A, B, C)
                    u, v, w = max(0, u), max(0, v), max(0, w)
                    total = u + v + w
                    if total > 0:
                        u, v, w = u/total, v/total, w/total
                    candidate[i] = u * A + v * B + w * C

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - best_score
            
            # Track improvements for adaptive cooling
            if delta > 0:
                improvement_history.append(delta)
                if len(improvement_history) > 50:
                    improvement_history.pop(0)

            # Acceptance criterion
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                best = candidate
                best_score = candidate_score

        # Update vulnerability scores based on improvement
        update_vulnerability_scores(best, original_score)
        return best

    # Apply multi-chain annealing to harden against opponent strategies
    final_points = multi_chain_annealing(points)
    
    return final_points