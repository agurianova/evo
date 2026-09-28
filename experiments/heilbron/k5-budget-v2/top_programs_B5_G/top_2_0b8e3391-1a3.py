import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import scipy.spatial
import hashlib

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Helper for boundary-aware projection
    def project_to_triangle(point):
        v0 = B - A
        v1 = C - A
        v2 = point - A
        denom = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(denom) < 1e-10:
            return A
        u = (v2[0] * v1[1] - v1[0] * v2[1]) / denom
        v = (v0[0] * v2[1] - v2[0] * v0[1]) / denom
        w = 1 - u - v
        
        # Clamp negative coordinates
        if u < 0: u = 0
        if v < 0: v = 0
        if w < 0: w = 0
        
        total = u + v + w
        if total < 1e-10:
            return A
        
        u, v, w = u / total, v / total, w / total
        return w * A + u * B + v * C

    # Compute minimum perpendicular distance to any side of the triangle
    def distance_to_boundary(point):
        # Distance to side BC
        area_PBC = 0.5 * abs((B[0]-point[0])*(C[1]-point[1]) - (B[1]-point[1])*(C[0]-point[0]))
        length_BC = np.linalg.norm(B - C)
        dist_BC = 2 * area_PBC / length_BC if length_BC > 1e-10 else float('inf')
        
        # Distance to side AC
        area_PAC = 0.5 * abs((A[0]-point[0])*(C[1]-point[1]) - (A[1]-point[1])*(C[0]-point[0]))
        length_AC = np.linalg.norm(A - C)
        dist_AC = 2 * area_PAC / length_AC if length_AC > 1e-10 else float('inf')
        
        # Distance to side AB
        area_PAB = 0.5 * abs((A[0]-point[0])*(B[1]-point[1]) - (A[1]-point[1])*(B[0]-point[0]))
        length_AB = np.linalg.norm(A - B)
        dist_AB = 2 * area_PAB / length_AB if length_AB > 1e-10 else float('inf')
        
        return min(dist_BC, dist_AC, dist_AB)

    # Calculate boundary-aware mobility score
    def calculate_mobility(idx, points):
        dist_to_boundary = distance_to_boundary(points[idx])
        
        # Distance to nearest point
        min_dist = float('inf')
        for other_idx in range(11):
            if other_idx != idx:
                dist = np.linalg.norm(points[idx] - points[other_idx])
                if dist < min_dist:
                    min_dist = dist
        
        # Boundary-aware mobility
        if dist_to_boundary < 0.01:
            return 0.7 * dist_to_boundary + 0.3 * min_dist
        else:
            return 0.4 * dist_to_boundary + 0.6 * min_dist

    # Optimize boundary position for maximum min_area
    def optimize_boundary_position(point, all_points, idx):
        original = point.copy()
        
        # Try multiple positions along the boundary
        best_position = original
        best_min_area = get_smallest_triangle_area(all_points)
        
        # Check which edge the point is closest to
        edges = [(A, B), (B, C), (C, A)]
        min_dist = float('inf')
        closest_edge = 0
        
        for i, (p1, p2) in enumerate(edges):
            # Distance from point to edge
            edge_vec = p2 - p1
            point_vec = original - p1
            proj = np.dot(point_vec, edge_vec) / np.dot(edge_vec, edge_vec)
            proj = max(0, min(1, proj))
            closest_point = p1 + proj * edge_vec
            dist = np.linalg.norm(original - closest_point)
            if dist < min_dist:
                min_dist = dist
                closest_edge = i

        # Sample points along the closest edge
        p1, p2 = edges[closest_edge]
        for t in np.linspace(0, 1, 20):
            candidate = p1 * (1 - t) + p2 * t
            
            # Calculate min area with this candidate position
            test_points = all_points.copy()
            test_points[idx] = candidate
            min_area = get_smallest_triangle_area(test_points)
            
            if min_area > best_min_area:
                best_min_area = min_area
                best_position = candidate

        return best_position

    # Generate multiple initial configurations with different row patterns
    def generate_initial_config(row_pattern, seed):
        np.random.seed(seed)
        random.seed(seed)
        
        rows = len(row_pattern)
        total_height = 1.3161  # Height of unit-area equilateral triangle
        points = []
        for row in range(rows):
            num_points = row_pattern[row]
            v_coord = (row + 0.5) / rows
            scale = v_coord * total_height
            for i in range(num_points):
                u_coord = (i + 0.5) / num_points * (1 - v_coord)
                P = (1 - u_coord - v_coord) * A + u_coord * B + v_coord * C
                # Reduced perturbation to avoid excessive deviation
                perturbation = np.random.uniform(-0.05, 0.05, size=2) * scale
                P = P + perturbation
                points.append(P)
        return np.array(points)

    # Define promising row patterns
    row_patterns = [
        [4, 3, 2, 1, 1],  # Literature-proven for 11 points
        [3, 3, 2, 2, 1],  # Previous effective pattern
        [4, 2, 2, 2, 1],  # Alternative symmetric pattern
        [3, 3, 3, 1, 1]   # New pattern for better symmetry
    ]
    
    best_points = None
    best_min_area = -1
    best_resistance = -1

    # Multi-start optimization with opponent-aware scoring
    for pattern_idx, pattern in enumerate(row_patterns):
        points = generate_initial_config(pattern, seed=42 + pattern_idx)
        
        # Simulated annealing parameters
        n_iterations = 20000
        initial_temp = 0.1
        base_step = 0.1
        T = initial_temp
        current_min_area = get_smallest_triangle_area(points)
        
        # Track improvement history for adaptive cooling
        min_area_history = [current_min_area]
        resistance_history = []
        stagnation_counter = 0
        reheating_counter = 0

        for iter_idx in range(n_iterations):
            # Find all triangles and sort by area
            triangles = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        a, b, c = points[i], points[j], points[k]
                        s_val = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                        area_val = 0.5 * abs(s_val)
                        triangles.append((i, j, k, area_val))
            
            # Sort by area
            triangles.sort(key=lambda x: x[3])
            
            # Adaptive threshold based on resistance history
            min_area = triangles[0][3]
            if resistance_history:
                avg_resistance = np.mean(resistance_history[-10:])
                threshold_factor = 1.15 + 0.25 * (1.0 - avg_resistance)
            else:
                threshold_factor = 1.15  # Default value
            
            # Select triangles within threshold
            critical_triangles = [t for t in triangles if t[3] <= min_area * threshold_factor]

            # Temperature-scaled step
            step = base_step * (T / initial_temp)
            candidate = points.copy()
            
            # Calculate mobility scores for all points
            mobility_scores = np.array([calculate_mobility(idx, points) for idx in range(11)])
            
            # Aggregate gradients from all critical triangles
            gradients = np.zeros((11, 2))
            
            for (i, j, k, area_val) in critical_triangles:
                a, b, c = points[i], points[j], points[k]
                s_val = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                factor = 1.0 if s_val >= 0 else -1.0
                
                # Compute gradients (without normalization - preserving natural magnitude)
                grad_a = factor * np.array([b[1]-c[1], c[0]-b[0]])
                grad_b = factor * np.array([c[1]-a[1], a[0]-c[0]])
                grad_c = factor * np.array([a[1]-b[1], b[0]-a[0]])

                # Weight by proximity to minimum area
                weight = 1.0 / max(1e-10, area_val - min_area + 1e-5)
                
                gradients[i] += weight * grad_a
                gradients[j] += weight * grad_b
                gradients[k] += weight * grad_c

            # Normalize gradients and apply mobility weighting
            for idx in range(11):
                grad_norm = np.linalg.norm(gradients[idx])
                if grad_norm > 1e-8:
                    gradients[idx] = gradients[idx] / grad_norm * mobility_scores[idx]

            # Apply aggregated gradients
            for idx in range(11):
                if np.linalg.norm(gradients[idx]) > 1e-8:
                    candidate[idx] = points[idx] + step * gradients[idx]

            # Adaptive Voronoi-guided exploration for escaping shallow optima
            if iter_idx > 1000:
                # Trigger more frequently (every 250 iterations)
                exploration_triggered = (iter_idx % 250 == 0)
                
                # Also trigger early if stagnating
                if len(min_area_history) > 200:
                    recent_improvements = min_area_history[-200:]
                    improvement_rate = (recent_improvements[-1] - recent_improvements[0]) / 200
                    if improvement_rate < 1e-6:
                        exploration_triggered = True
                        stagnation_counter += 1
                        
                        # Reheat if stagnating for too long
                        if stagnation_counter > 100 and reheating_counter < 3:
                            T = initial_temp * 0.5  # Reheat to 50% of initial temperature
                            reheating_counter += 1
                            stagnation_counter = 0

                if exploration_triggered:
                    try:
                        # Compute Voronoi tessellation to identify low-density regions
                        padding = 0.1
                        boundary_points = [
                            [A[0]-padding, A[1]-padding],
                            [B[0]+padding, B[1]-padding],
                            [C[0], C[1]+padding],
                            [(A[0]+B[0])/2, (A[1]+B[1])/2 - padding],
                            [(A[0]+C[0])/2 - padding, (A[1]+C[1])/2 + padding/2],
                            [(B[0]+C[0])/2 + padding, (B[1]+C[1])/2 + padding/2]
                        ]
                        
                        all_points = np.vstack([points, boundary_points])
                        vor = scipy.spatial.Voronoi(all_points)
                        
                        # Find largest Voronoi regions (low-density areas)
                        region_sizes = []
                        for region_idx, region in enumerate(vor.regions):
                            if not region or -1 in region:
                                continue
                            polygon = [vor.vertices[i] for i in region]
                            if len(polygon) < 3:
                                continue
                            # Compute polygon area
                            area = 0
                            for i in range(len(polygon)):
                                j = (i + 1) % len(polygon)
                                area += polygon[i][0] * polygon[j][1] - polygon[j][0] * polygon[i][1]
                            area = abs(area) / 2
                            region_sizes.append((area, region_idx))
                        
                        region_sizes.sort(reverse=True)
                        
                        # Move points toward large regions
                        if region_sizes and len(region_sizes) > 2:
                            target_region_idx = region_sizes[0][1]
                            target_region = vor.regions[target_region_idx]
                            if target_region:
                                target_points = [vor.vertices[i] for i in target_region]
                                target_centroid = np.mean(target_points, axis=0)
                                
                                # Find the point in the smallest triangle to move
                                smallest_tri = triangles[0]
                                move_idx = smallest_tri[0]  # Move one vertex of the smallest triangle
                                
                                # Project to triangle if needed
                                if is_inside_triangle(target_centroid, A, B, C):
                                    candidate[move_idx] = target_centroid
                                else:
                                    projected = project_to_triangle(target_centroid)
                                    candidate[move_idx] = optimize_boundary_position(projected, candidate, move_idx)
                    except:
                        pass

            # Project candidate points to stay within triangle
            for idx in range(11):
                if not is_inside_triangle(candidate[idx], A, B, C):
                    projected = project_to_triangle(candidate[idx])
                    candidate[idx] = optimize_boundary_position(projected, candidate, idx)

            # Evaluate candidate
            new_min_area = get_smallest_triangle_area(candidate)
            delta = new_min_area - current_min_area
            
            # Enhanced opponent-aware resistance scoring
            resistance_score = 1.0
            # Simulate potential opponent improvements with multi-scale perturbations
            if iter_idx % 150 == 0:
                opponent_improvement = 0
                
                # Three perturbation scales to simulate different opponent strategies
                perturbation_scales = [
                    (3, 0.02),  # Small perturbations (subtle improvements)
                    (5, 0.05),  # Medium perturbations (balanced approach)
                    (2, 0.10)   # Large perturbations (aggressive exploration)
                ]
                
                # If we have resistance history, adapt scale selection
                if resistance_history:
                    avg_resistance = np.mean(resistance_history[-5:])
                    # If resistance is high, focus more on small perturbations
                    if avg_resistance > 0.6:
                        perturbation_scales[0] = (5, 0.02)
                        perturbation_scales[1] = (3, 0.05)
                    # If resistance is low, focus more on larger perturbations
                    elif avg_resistance < 0.4:
                        perturbation_scales[1] = (3, 0.05)
                        perturbation_scales[2] = (5, 0.10)

                for trial_count, scale in perturbation_scales:
                    for _ in range(trial_count):
                        opp_candidate = candidate.copy()
                        # Pick a random point involved in small triangles
                        small_tri_idx = np.random.randint(0, min(5, len(critical_triangles)))
                        i, j, k, _ = critical_triangles[small_tri_idx]
                        idx_to_move = np.random.choice([i, j, k])
                        
                        # Scale-appropriate move an opponent might try
                        opp_candidate[idx_to_move] += np.random.uniform(-scale, scale, size=2)
                        
                        # Project back to triangle
                        if not is_inside_triangle(opp_candidate[idx_to_move], A, B, C):
                            opp_candidate[idx_to_move] = project_to_triangle(opp_candidate[idx_to_move])
                            opp_candidate[idx_to_move] = optimize_boundary_position(
                                opp_candidate[idx_to_move], opp_candidate, idx_to_move)
                        
                        opp_min_area = get_smallest_triangle_area(opp_candidate)
                        opponent_improvement = max(opponent_improvement, opp_min_area - new_min_area)
                
                # More nuanced resistance scoring
                if opponent_improvement > 0:
                    # Non-linear penalty: small improvements are more concerning
                    resistance_score = 1.0 - min(0.8, np.sqrt(opponent_improvement) * 15)
                else:
                    # Reward configurations that make opponents worse
                    resistance_score = 1.0 + min(0.2, -opponent_improvement * 10)
                    
                resistance_history.append(resistance_score)

            # Combined quality-resistance score
            combined_score = 0.5 * new_min_area + 0.5 * (new_min_area * resistance_score)
            current_combined = 0.5 * current_min_area + 0.5 * (current_min_area * (resistance_history[-1] if resistance_history else 1.0))
            combined_delta = combined_score - current_combined

            # Adaptive cooling based on improvement history
            if len(min_area_history) > 100:
                recent_improvements = min_area_history[-100:]
                improvement_rate = (recent_improvements[-1] - recent_improvements[0]) / 100
                
                if improvement_rate < 1e-6:  # Stagnation detected
                    T = max(0.001, T * 0.9)  # Faster cooling
                else:
                    T = min(0.1, T * 1.01)  # Slower cooling for good progress

            # Metropolis acceptance with combined score
            if combined_delta > 0 or np.random.rand() < np.exp(combined_delta / T):
                points = candidate
                current_min_area = new_min_area

            # Track best overall (with resistance consideration)
            if current_min_area > best_min_area or \
               (abs(current_min_area - best_min_area) < 1e-6 and \
                (len(resistance_history) == 0 or resistance_history[-1] > best_resistance)):
                best_min_area = current_min_area
                best_points = points.copy()
                best_resistance = resistance_history[-1] if resistance_history else 1.0

            # Update history
            min_area_history.append(current_min_area)

    return best_points