import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Function to calculate edge vulnerability from triangle_vulnerability
    def calculate_edge_vulnerabilities():
        edge_vulnerabilities = {
            'AB': [],
            'BC': [],
            'CA': []
        }
        
        # Classify triangles by which edge they're closest to
        for triangle, (success, total) in triangle_vulnerability.items():
            success_rate = success / total
            i, j, k = triangle
            
            # Calculate barycentric coordinates for triangle centroid
            centroid = (points[i] + points[j] + points[k]) / 3
            u, v, w = get_barycentric_coords(centroid, A, B, C)
            
            # Determine which edge the triangle is closest to
            if w < u and w < v:  # Closest to AB (w=0)
                edge_vulnerabilities['AB'].append(success_rate)
            elif u < v and u < w:  # Closest to BC (u=0)
                edge_vulnerabilities['BC'].append(success_rate)
            else:  # Closest to CA (v=0)
                edge_vulnerabilities['CA'].append(success_rate)
        
        # Calculate average vulnerability for each edge
        edge_scores = {}
        for edge, scores in edge_vulnerabilities.items():
            if scores:
                edge_scores[edge] = np.mean(scores)
            else:
                edge_scores[edge] = 0.0
        
        # Normalize scores to sum to 1.0
        total = sum(edge_scores.values())
        if total > 0:
            for edge in edge_scores:
                edge_scores[edge] /= total
        else:
            # Default equal distribution if no data
            for edge in edge_scores:
                edge_scores[edge] = 1.0 / 3.0
        
        return edge_scores

    # Function to place points along an edge with adaptive spacing
    def place_along_edge(start, end, count):
        points = []
        # Use randomized spacing with variation while maintaining order
        base_positions = np.linspace(0, 1, count + 2)[1:-1]
        noise = np.random.uniform(-0.1, 0.1, count)
        positions = np.clip(base_positions + noise * 0.1, 0.05, 0.95)
        positions.sort()  # Maintain order after perturbation
        
        for t in positions:
            point = (1 - t) * start + t * end
            points.append(point)
        return points
    
    # Create adaptive edge distribution based on vulnerability
    edge_points = []
    
    # Initialize vulnerability tracking
    triangle_vulnerability = {}
    
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
        
        # Adaptive strength based on boundary proximity and current min_area
        boundary_proximity = min(u, v, w)
        adaptive_strength = strength * (0.1 / max(boundary_proximity, 0.01))
        
        # Calculate repulsion vectors from each edge
        repulsion = np.zeros(2)
        
        # Repulsion from AB edge (where w=0)
        if w < 0.2:
            repulsion += adaptive_strength * (0.2 - w) * (C - A - v * (B - A))
        
        # Repulsion from BC edge (where u=0)
        if u < 0.2:
            repulsion += adaptive_strength * (0.2 - u) * (A - B - w * (C - B))

        # Repulsion from CA edge (where v=0)
        if v < 0.2:
            repulsion += adaptive_strength * (0.2 - v) * (B - C - u * (A - C))

        # Normalize repulsion to prevent large jumps
        if np.linalg.norm(repulsion) > 0:
            repulsion = repulsion / np.linalg.norm(repulsion) * min(0.02, np.linalg.norm(repulsion))
            
        return point + repulsion

    # Update vulnerability tracking for triangles
    def update_vulnerability(triangle_indices, was_improved):
        key = tuple(sorted(triangle_indices))
        if key not in triangle_vulnerability:
            triangle_vulnerability[key] = [0.1, 0.9]  # [success_count, total_count]
        
        triangle_vulnerability[key][1] += 1
        if was_improved:
            triangle_vulnerability[key][0] += 1

    # Get vulnerability score for a triangle (exponential prioritization)
    def get_vulnerability_score(triangle_indices):
        key = tuple(sorted(triangle_indices))
        if key in triangle_vulnerability:
            success_count, total_count = triangle_vulnerability[key]
            success_rate = success_count / total_count
            # Exponential scoring to prioritize highly vulnerable triangles
            return 1.0 + 2.0 * np.power(success_rate, 2)
        return 1.0  # Default weight

    # Calculate gradient of triangle area with respect to vertex positions
    def calculate_area_gradient(points, triangle_indices):
        i, j, k = triangle_indices
        a, b, c = points[i], points[j], points[k]
        
        # Area = 0.5 * |(b-a) × (c-a)|
        grad_a = np.array([-(b[1] - c[1]), b[0] - c[0]]) * 0.5
        grad_b = np.array([-(c[1] - a[1]), c[0] - a[0]]) * 0.5
        grad_c = np.array([-(a[1] - b[1]), a[0] - b[0]]) * 0.5
        
        # Weight gradients by inverse distance with adaptive exponent
        dist_ab = max(1e-6, np.linalg.norm(a - b))
        dist_ac = max(1e-6, np.linalg.norm(a - c))
        dist_bc = max(1e-6, np.linalg.norm(b - c))
        
        # Adaptive exponent based on optimization progress
        difficulty_factor = 1.0 - current_min_area / 0.0365
        alpha = 1.5 - 0.5 * min(1.0, mean_improvement / 1e-4)
        
        weight_a = 1.0 / (dist_ab ** alpha * dist_ac ** alpha)
        weight_b = 1.0 / (dist_ab ** alpha * dist_bc ** alpha)
        weight_c = 1.0 / (dist_ac ** alpha * dist_bc ** alpha)
        
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
        
        # Apply vulnerability weighting
        weighted_indices = []
        for idx in relevant_indices:
            vulnerability = get_vulnerability_score(idx)
            # Repeat index based on vulnerability score
            repeat_count = max(1, int(vulnerability * 2))
            weighted_indices.extend([idx] * repeat_count)
        
        # Always return at least 1 triangle
        return weighted_indices if weighted_indices else [sorted_indices[0]]

    # Multi-chain adaptive annealing
    def multi_chain_annealing(initial_points):
        current_min_area = get_smallest_triangle_area(initial_points)
        difficulty_factor = 1.0 - current_min_area / 0.0365
        
        # Calculate edge vulnerabilities for adaptive distribution
        edge_vulnerabilities = calculate_edge_vulnerabilities()
        
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
            boundary_focus=edge_vulnerabilities['AB'] * 0.7 + \
                        edge_vulnerabilities['BC'] * 0.2 + \
                        edge_vulnerabilities['CA'] * 0.1
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
            boundary_focus=edge_vulnerabilities['AB'] * 0.3 + \
                        edge_vulnerabilities['BC'] * 0.4 + \
                        edge_vulnerabilities['CA'] * 0.3
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
            boundary_focus=edge_vulnerabilities['AB'] * 0.2 + \
                        edge_vulnerabilities['BC'] * 0.3 + \
                        edge_vulnerabilities['CA'] * 0.5
        )
        chains.append(chain3)
        
        # Chain 4: Boundary-specialized approach (adaptive focus)
        chain4 = annealing_chain(
            initial_points.copy(),
            base_step=0.04 * (1 + difficulty_factor),
            T0=0.009 * (1 + difficulty_factor),
            T_decay=0.9976,
            step_decay=0.9986,
            min_area_ratio=1.0 + 0.2 * difficulty_factor,
            boundary_focus=max(edge_vulnerabilities.values()) * 0.8
        )
        chains.append(chain4)
        
        # Select the best result
        return max(chains, key=lambda x: get_smallest_triangle_area(x))

    # Single annealing chain with adaptive parameters
    def annealing_chain(points, base_step, T0, T_decay, step_decay, min_area_ratio, boundary_focus):
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        global current_min_area, mean_improvement
        current_min_area = best_score
        mean_improvement = 0.002070  # Initial estimate from metrics
        
        # Dynamic iteration count based on difficulty
        n_rounds = int(200 + 250 * (0.7 + 0.6 * (1 - (1.0 - best_score / 0.0365))))
        
        # Track improvement history for adaptive cooling
        improvement_history = []
        stagnation_counter = 0
        stagnation_threshold = 20
        
        # Identify boundary points (those close to edges)
        boundary_indices = []
        for i, point in enumerate(points):
            if distance_to_boundary(point, A, B, C) < 0.1:
                boundary_indices.append(i)
        
        # Stagnation type detection
        def detect_stagnation_type():
            if stagnation_counter < 15:
                return 'none'
            
            # 1. Check for local clustering
            n = len(best)
            distances = np.zeros((n, n))
            for i in range(n):
                for j in range(i+1, n):
                    distances[i,j] = distances[j,i] = np.linalg.norm(best[i] - best[j])
            
            close_threshold = 0.05
            neighbor_counts = np.sum(distances < close_threshold, axis=1)
            clustering_score = np.max(neighbor_counts) / (n / 3.0)
            
            # 2. Check for boundary confinement
            boundary_points = 0
            for i in range(n):
                u, v, w = get_barycentric_coords(best[i], A, B, C)
                if min(u, v, w) < 0.02:
                    boundary_points += 1
            boundary_ratio = boundary_points / n
            
            # 3. Check for global plateau
            score_variation = 0
            if len(improvement_history) >= 10:
                recent_improvements = improvement_history[-10:]
                score_variation = max(recent_improvements) - min(recent_improvements)
            
            if clustering_score > 1.7:
                return 'clustering'
            elif boundary_ratio > 0.85:
                return 'boundary'
            elif score_variation < 1e-8:
                return 'plateau'
            else:
                return 'general'

        for round_idx in range(n_rounds):
            # Adjust cooling rate based on recent progress
            if improvement_history and len(improvement_history) >= 10:
                recent_improvements = improvement_history[-10:]
                avg_improvement = np.mean(recent_improvements)
                mean_improvement = avg_improvement
                if avg_improvement < 1e-6:
                    T_decay = max(0.996, T_decay * 1.001)
                    step_decay = min(0.9995, step_decay * 1.0005)
                    stagnation_counter += 1
                else:
                    T_decay = min(0.9985, T_decay * 0.9998)
                    step_decay = max(0.997, step_decay * 0.9997)
                    stagnation_counter = max(0, stagnation_counter - 1)
            
            # Reset if stuck for too long with specialized recovery
            adaptive_stagnation_threshold = max(15, min(30, stagnation_threshold + 10 * (stagnation_counter / 5)))
            if stagnation_counter > adaptive_stagnation_threshold:
                stagnation_type = detect_stagnation_type()
                
                if stagnation_type == 'clustering':
                    # For local clustering: selectively reset points in dense regions
                    T_decay = min(0.999, T_decay * 1.05)
                    step_decay = max(0.995, step_decay * 0.95)
                    
                    # Identify dense regions and perturb points there
n = len(best)
                    distances = np.zeros((n, n))
                    for i in range(n):
                        for j in range(i+1, n):
                            distances[i,j] = distances[j,i] = np.linalg.norm(best[i] - best[j])
                    
                    # Find points with many close neighbors
                    close_threshold = 0.05
                    neighbor_counts = np.sum(distances < close_threshold, axis=1)
                    dense_indices = np.where(neighbor_counts > n//3)[0]
                    
                    if len(dense_indices) > 0:
                        # Perturb points in dense regions
                        for idx in dense_indices:
                            r = 0.05 * np.sqrt(np.random.rand())
                            theta = 2 * np.pi * np.random.rand()
                            perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                            best[idx] += perturbation
                            if not is_inside_triangle(best[idx], A, B, C):
                                best[idx] = soft_boundary_repulsion(best[idx], A, B, C)

                elif stagnation_type == 'boundary':
                    # For boundary confinement: encourage interior movement
                    T_decay = min(0.999, T_decay * 1.03)
                    step_decay = max(0.997, step_decay * 0.97)
                    
                    # Adaptive boundary push
                    for i in range(len(best)):
                        u, v, w = get_barycentric_coords(best[i], A, B, C)
                        min_coord = min(u, v, w)
                        if min_coord < 0.05:
                            push_strength = 0.05 * (1 - min_coord) * (1.5 - (1.0 - current_min_area / 0.0365))
                            
                            if u < v and u < w:
                                best[i] += push_strength * (A - best[i])
                            elif v < u and v < w:
                                best[i] += push_strength * (B - best[i])
                            else:
                                best[i] += push_strength * (C - best[i])
                            
                            if not is_inside_triangle(best[i], A, B, C):
                                best[i] = soft_boundary_repulsion(best[i], A, B, C)

                else:
                    # General reset strategy with noise injection
                    T_decay = 0.9975
                    step_decay = 0.9985
                    stagnation_counter = 0
                    improvement_history = []
                    # Add small random noise to escape local minimum
                    noise = np.random.normal(0, 0.01 * (1 + 0.5 * (stagnation_counter / adaptive_stagnation_threshold)), best.shape)
                    best += noise
                    # Ensure points stay inside triangle
                    for i in range(len(best)):
                        if not is_inside_triangle(best[i], A, B, C):
                            best[i] = soft_boundary_repulsion(best[i], A, B, C)
                
                best_score = get_smallest_triangle_area(best)

            T = T0 * (T_decay ** round_idx)
            current_step = base_step * (step_decay ** round_idx)
            
            # Get relevant triangles adaptively
            triangle_indices = get_adaptive_triangle_indices(best, min_area_ratio)
            selected_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
            
            # Dynamic gradient ratio based on recent improvement rate
            gradient_ratio = 0.5
            if improvement_history and len(improvement_history) >= 5:
                recent_improvements = improvement_history[-5:]
                avg_improvement = np.mean(recent_improvements)
                # Increase gradient usage when making consistent progress
                gradient_ratio = 0.5 + min(0.45, avg_improvement * 1000)
            
            # Track if this move improved the configuration
            move_improved = False
            
            if np.random.rand() < gradient_ratio:
                # Gradient-based perturbations
                grad_i, grad_j, grad_k = calculate_area_gradient(best, selected_triangle)
                
                # Determine point selection based on boundary focus
                if np.random.rand() < boundary_focus and boundary_indices:
                    # Focus on boundary points
                    candidate_idx = [idx for idx in selected_triangle if idx in boundary_indices]
                    if not candidate_idx:
                        candidate_idx = selected_triangle
                else:
                    # Focus on interior points
                    candidate_idx = [idx for idx in selected_triangle if idx not in boundary_indices]
                    if not candidate_idx:
                        candidate_idx = selected_triangle
                
                # 60% chance to perturb one point, 40% to perturb all three
                if np.random.rand() < 0.6:
                    idx = candidate_idx[np.random.randint(len(candidate_idx))]
                    candidate = best.copy()
                    
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
                    for idx in candidate_idx:
                        if idx == selected_triangle[0]:
                            candidate[idx] += grad_i * current_step
                        elif idx == selected_triangle[1]:
                            candidate[idx] += grad_j * current_step
                        else:
                            candidate[idx] += grad_k * current_step
                    
                    # Apply soft boundary repulsion
                    for i in range(len(candidate)):
                        dist_to_boundary = distance_to_boundary(candidate[i], A, B, C)
                        if dist_to_boundary < 0.05:
                            candidate[i] = soft_boundary_repulsion(candidate[i], A, B, C)
            else:
                # Isotropic perturbations (fallback)
                if np.random.rand() < 0.6:
                    # Determine point selection based on boundary focus
                    if np.random.rand() < boundary_focus and boundary_indices:
                        # Focus on boundary points
                        candidate_idx = [idx for idx in selected_triangle if idx in boundary_indices]
                        if not candidate_idx:
                            candidate_idx = selected_triangle
                    else:
                        # Focus on interior points
                        candidate_idx = [idx for idx in selected_triangle if idx not in boundary_indices]
                        if not candidate_idx:
                            candidate_idx = selected_triangle
                    
                    idx = candidate_idx[np.random.randint(len(candidate_idx))]
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
                    # Determine points to perturb based on boundary focus
                    if np.random.rand() < boundary_focus and boundary_indices:
                        # Focus on boundary points
                        candidate_idx = [idx for idx in selected_triangle if idx in boundary_indices]
                        if not candidate_idx:
                            candidate_idx = selected_triangle
                    else:
                        # Focus on interior points
                        candidate_idx = [idx for idx in selected_triangle if idx not in boundary_indices]
                        if not candidate_idx:
                            candidate_idx = selected_triangle
                    
                    for idx in candidate_idx:
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
                move_improved = True
                if len(improvement_history) > 50:
                    improvement_history.pop(0)

            # Update vulnerability tracking
            update_vulnerability(selected_triangle, move_improved)

            # Acceptance criterion
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                best = candidate
                best_score = candidate_score
                current_min_area = best_score

        return best

    # Adaptive edge point distribution based on vulnerability
    edge_vulnerabilities = calculate_edge_vulnerabilities()
    total_vulnerability = sum(edge_vulnerabilities.values())
    
    # Total points to distribute: 9 on edges (2 interior)
    total_edge_points = 9
    # Calculate proportional distribution
    ab_points = max(3, min(5, int(round(total_edge_points * edge_vulnerabilities['AB'] / total_vulnerability))))
    bc_points = max(3, min(5, int(round(total_edge_points * edge_vulnerabilities['BC'] / total_vulnerability))))
    ca_points = total_edge_points - ab_points - bc_points
    
    # Ensure we have exactly 9 edge points
    while ab_points + bc_points + ca_points != total_edge_points:
        if ab_points + bc_points + ca_points < total_edge_points:
            # Add points to the most vulnerable edge
            if edge_vulnerabilities['AB'] >= edge_vulnerabilities['BC'] and edge_vulnerabilities['AB'] >= edge_vulnerabilities['CA']:
                ab_points += 1
            elif edge_vulnerabilities['BC'] >= edge_vulnerabilities['CA']:
                bc_points += 1
            else:
                ca_points += 1
        else:
            # Remove points from the least vulnerable edge
            if edge_vulnerabilities['AB'] <= edge_vulnerabilities['BC'] and edge_vulnerabilities['AB'] <= edge_vulnerabilities['CA']:
                ab_points = max(3, ab_points - 1)
            elif edge_vulnerabilities['BC'] <= edge_vulnerabilities['CA']:
                bc_points = max(3, bc_points - 1)
            else:
                ca_points = max(3, ca_points - 1)

    # Create adaptive edge distribution
    edge_points = []
    # AB edge
    edge_points.extend(place_along_edge(A, B, ab_points))
    # BC edge
    edge_points.extend(place_along_edge(B, C, bc_points))
    # CA edge
    edge_points.extend(place_along_edge(C, A, ca_points))
    
    # Add interior points with adaptive Beta distribution
    interior_points = []
    
    # Adaptive Beta parameters based on current min_area
    difficulty_factor = 0.5  # Initial difficulty
    alpha_param = 2.0 - 1.5 * difficulty_factor
    beta_param = 2.0 - 1.5 * difficulty_factor
    
    # Sample barycentric coordinates from adaptive Beta distribution
    for _ in range(2):
        u = np.random.beta(alpha_param, beta_param)
        v = np.random.beta(alpha_param, beta_param) * (1 - u)
        w = 1 - u - v
        point = u * A + v * B + w * C
        interior_points.append(point)

    # Combine all points
    points = np.array(edge_points + interior_points)
    
    # Apply multi-chain annealing to harden against opponent strategies
    final_points = multi_chain_annealing(points)
    
    return final_points