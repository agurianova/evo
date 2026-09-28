import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

np.random.seed(42)

# Global vulnerability tracking (persists across evaluations)
vulnerability_scores = {}

# Update vulnerability scores based on opponent improvements
def update_vulnerability_scores(points, improved_points):
    global vulnerability_scores
    
    # Get triangles from original configuration
    original_areas = {}
    n = len(points)
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = get_smallest_triangle_area(points[[i,j,k]])
                original_areas[(i,j,k)] = area
    
    # Check which triangles improved
    for (i,j,k), orig_area in original_areas.items():
        improved_area = get_smallest_triangle_area(improved_points[[i,j,k]])
        if improved_area > orig_area:
            # This triangle was successfully improved by opponent
            if (i,j,k) not in vulnerability_scores:
                vulnerability_scores[(i,j,k)] = 0
            vulnerability_scores[(i,j,k)] += 1

# Track improvements from opponents (would be called externally)
# In practice, this would be triggered when opponents submit improvements
def record_improvement(points, improved_points):
    update_vulnerability_scores(points, improved_points)


def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Function to place points along an edge with randomized spacing
    def place_along_edge(start, end, count):
        points = []
        # Create randomized spacing with ±10% variation (clamped to 0.05-0.95)
        positions = np.linspace(0.05, 0.95, count+2)[1:-1]  # Avoid vertices
        # Add random variation (±10% of spacing)
        spacing = 1.0 / (count + 1)
        variations = np.random.uniform(-0.1, 0.1, count) * spacing
        positions = np.clip(positions + variations, 0.05, 0.95)
        positions = np.sort(positions)
        
        for t in positions:
            point = (1 - t) * start + t * end
            points.append(point)
        return points
    
    # Create asymmetric distribution: 4 points on AB, 3 on BC, 2 on CA
    edge_points = []
    # AB edge: 4 points
    edge_points.extend(place_along_edge(A, B, 4))
    # BC edge: 3 points
    edge_points.extend(place_along_edge(B, C, 3))
    # CA edge: 2 points
    edge_points.extend(place_along_edge(C, A, 2))
    
    # Add interior points using Beta-distributed barycentric coordinates
    interior_points = []
    
    # Sample from Beta(2,2) which peaks at 0.5
    for _ in range(2):
        u = np.random.beta(2, 2)
        v = np.random.beta(2, 2) * (1 - u)
        w = 1 - u - v
        p = u * A + v * B + w * C
        interior_points.append(p)

    # Combine all points
    points = np.array(edge_points + interior_points)
    
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
    def calculate_area_gradient(points, triangle_indices, alpha=1.0):
        i, j, k = triangle_indices
        a, b, c = points[i], points[j], points[k]
        
        # Area = 0.5 * |(b-a) × (c-a)|
        grad_a = np.array([-(b[1] - c[1]), b[0] - c[0]]) * 0.5
        grad_b = np.array([-(c[1] - a[1]), c[0] - a[0]]) * 0.5
        grad_c = np.array([-(a[1] - b[1]), a[0] - b[0]]) * 0.5
        
        # Weight gradients by inverse distance with adaptive exponent alpha
        dist_ab = max(1e-6, np.linalg.norm(a - b))
        dist_ac = max(1e-6, np.linalg.norm(a - c))
        dist_bc = max(1e-6, np.linalg.norm(b - c))
        
        weight_a = 1.0 / (dist_ab**alpha + dist_ac**alpha)
        weight_b = 1.0 / (dist_ab**alpha + dist_bc**alpha)
        weight_c = 1.0 / (dist_ac**alpha + dist_bc**alpha)
        
        grad_a = grad_a * weight_a
        grad_b = grad_b * weight_b
        grad_c = grad_c * weight_c

        return grad_a, grad_b, grad_c

    # Get triangles adaptively based on current min_area and vulnerability
    def get_adaptive_triangle_indices(points, min_area_ratio=1.1):
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
        min_area = sorted_areas[0]
        threshold = min_area * min_area_ratio
        relevant_indices = [idx for area, idx in zip(areas, indices) if area <= threshold]
        
        # Apply vulnerability weighting to boost high-risk triangles
        weighted_indices = []
        for idx in relevant_indices:
            # Higher vulnerability score = higher selection probability
n            score = vulnerability_scores.get(idx, 0)
            # Double the probability for high-risk areas
            repeat_count = 1 + min(1, score // 2)
            weighted_indices.extend([idx] * repeat_count)
        
        # Always return at least 1 triangle
        return weighted_indices if weighted_indices else [sorted_indices[0]]

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
            gradient_alpha=1.0,
            boundary_focus=0.3
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
            gradient_alpha=1.2,
            boundary_focus=0.5
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
            gradient_alpha=1.5,
            boundary_focus=0.5
        )
        chains.append(chain3)
        
        # Chain 4: Boundary-specialized chain (70% focus on edge points)
        chain4 = annealing_chain(
            initial_points.copy(),
            base_step=0.03 * (1 + 0.7 * difficulty_factor),
            T0=0.009 * (1 + 0.3 * difficulty_factor),
            T_decay=0.9982,
            step_decay=0.9987,
            min_area_ratio=1.08,
            gradient_alpha=1.0,
            boundary_focus=0.7  # 70% of perturbations on edge points
        )
        chains.append(chain4)
        
        # Select the best result
        return max(chains, key=lambda x: get_smallest_triangle_area(x))

    # Single annealing chain with adaptive parameters
    def annealing_chain(points, base_step, T0, T_decay, step_decay, min_area_ratio, gradient_alpha, boundary_focus):
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Dynamic iteration count based on difficulty
        n_rounds = int(200 + 250 * (0.7 + 0.6 * (1 - (1.0 - best_score / 0.0365))))
        
        # Track improvement history for adaptive cooling
        improvement_history = []
        stagnation_counter = 0
        stagnation_threshold = 20
        
        # Adaptive gradient exponent based on improvement rate
        alpha = gradient_alpha
        
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
            
            # Reset if stuck for too long
            adaptive_stagnation_threshold = max(15, min(30, stagnation_threshold + 10 * (stagnation_counter / 5)))
            if stagnation_counter > adaptive_stagnation_threshold:
                T_decay = 0.9975
                step_decay = 0.9985
                stagnation_counter = 0
                improvement_history = []
                
                # Reset with noise to escape local minima
                best = best + np.random.normal(0, 0.05, best.shape)
                # Project back to valid points
                for i in range(len(best)):
                    if not is_inside_triangle(best[i], A, B, C):
                        u, v, w = get_barycentric_coords(best[i], A, B, C)
                        u, v, w = max(0, u), max(0, v), max(0, w)
                        total = u + v + w
                        if total > 0:
                            u, v, w = u/total, v/total, w/total
                        best[i] = u * A + v * B + w * C

            T = T0 * (T_decay ** round_idx)
            current_step = base_step * (step_decay ** round_idx)
            
            # Update min_area_ratio adaptively based on optimization progress
            current_min_area_ratio = 1.0 + 0.3 * (1 - best_score / 0.0365)
            current_min_area_ratio = max(1.05, min(1.2, current_min_area_ratio))
            
            # Get relevant triangles adaptively
            triangle_indices = get_adaptive_triangle_indices(best, current_min_area_ratio)
            selected_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
            
            # Adaptive gradient exponent based on improvement rate
            if improvement_history:
                avg_improvement = np.mean(improvement_history[-5:]) if len(improvement_history) >= 5 else improvement_history[0]
                # alpha = 1.5 - 0.5 * min(1.0, avg_improvement / 1e-4)
                # Bound alpha to [0.5, 2.0]
                alpha = max(0.5, min(2.0, 1.5 - 0.5 * min(1.0, avg_improvement / 1e-4)))

            # Dynamic gradient ratio (increases as optimization progresses)
            gradient_ratio = 0.5 + 0.4 * (round_idx / n_rounds)
            
            if np.random.rand() < gradient_ratio:
                # Gradient-based perturbations
                grad_i, grad_j, grad_k = calculate_area_gradient(best, selected_triangle, alpha)
                
                # Determine if we're focusing on boundary points
                boundary_perturbation = np.random.rand() < boundary_focus
                
                # 60% chance to perturb one point, 40% to perturb all three
                if np.random.rand() < 0.6:
                    idx = selected_triangle[np.random.randint(3)]
                    candidate = best.copy()
                    
                    # If focusing on boundary and point is near boundary, adjust perturbation
                    if boundary_perturbation:
                        dist = distance_to_boundary(candidate[idx], A, B, C)
                        if dist < 0.1:  # Near boundary
                            # Smaller steps near boundary for precision
                            step_scale = 0.5 + 0.5 * dist
                            current_step *= step_scale

                    if idx == selected_triangle[0]:
                        candidate[idx] += grad_i * current_step
                    elif idx == selected_triangle[1]:
                        candidate[idx] += grad_j * current_step
                    else:
                        candidate[idx] += grad_k * current_step
                    
                    # Apply soft boundary repulsion instead of hard projection
                    for i in range(len(candidate)):
                        dist_to_boundary = distance_to_boundary(candidate[i], A, B, C)
                        if dist_to_boundary < 0.05:
                            candidate[i] = soft_boundary_repulsion(candidate[i], A, B, C)
                else:
                    candidate = best.copy()
                    # Apply boundary-focused scaling if needed
                    if boundary_perturbation:
                        for idx in selected_triangle:
                            dist = distance_to_boundary(candidate[idx], A, B, C)
                            if dist < 0.1:
                                step_scale = 0.5 + 0.5 * dist
                                current_step *= step_scale

                    candidate[selected_triangle[0]] += grad_i * current_step
                    candidate[selected_triangle[1]] += grad_j * current_step
                    candidate[selected_triangle[2]] += grad_k * current_step
                    
                    # Apply soft boundary repulsion
                    for i in range(len(candidate)):
                        dist_to_boundary = distance_to_boundary(candidate[i], A, B, C)
                        if dist_to_boundary < 0.05:
                            candidate[i] = soft_boundary_repulsion(candidate[i], A, B, C)
            else:
                # Isotropic perturbations (fallback)
                if np.random.rand() < 0.6:
                    idx = selected_triangle[np.random.randint(3)]
                    candidate = best.copy()
                    r = current_step * np.sqrt(np.random.rand())
                    theta = 2 * np.pi * np.random.rand()
                    perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                    
                    # Boundary-focused scaling
                    if np.random.rand() < boundary_focus:
                        dist = distance_to_boundary(candidate[idx], A, B, C)
                        if dist < 0.1:
                            perturbation *= (0.5 + 0.5 * dist)
                    
                    candidate[idx] += perturbation
                    
                    # Apply soft boundary repulsion
                    dist_to_boundary = distance_to_boundary(candidate[idx], A, B, C)
                    if dist_to_boundary < 0.05:
                        candidate[idx] = soft_boundary_repulsion(candidate[idx], A, B, C)
                else:
                    candidate = best.copy()
                    for idx in selected_triangle:
                        r = current_step * np.sqrt(np.random.rand())
                        theta = 2 * np.pi * np.random.rand()
                        perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                        
                        # Boundary-focused scaling
                        if np.random.rand() < boundary_focus:
                            dist = distance_to_boundary(candidate[idx], A, B, C)
                            if dist < 0.1:
                                perturbation *= (0.5 + 0.5 * dist)
                        
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

        return best

    # Apply multi-chain annealing to harden against opponent strategies
    final_points = multi_chain_annealing(points)
    
    return final_points