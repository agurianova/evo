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

    # Calculate point mobility with boundary awareness
    def calculate_mobility(point_idx, points):
        point = points[point_idx]
        
        # Distance to boundary
        dist_to_boundary = float('inf')
        edges = [(A, B), (B, C), (C, A)]
        for p1, p2 in edges:
            edge_vec = p2 - p1
            point_vec = point - p1
            proj = np.dot(point_vec, edge_vec) / np.dot(edge_vec, edge_vec)
            proj = max(0, min(1, proj))
            closest_point = p1 + proj * edge_vec
            dist = np.linalg.norm(point - closest_point)
            dist_to_boundary = min(dist_to_boundary, dist)
        
        # Distance to nearest point
        min_dist = float('inf')
        for other_idx in range(11):
            if other_idx != point_idx:
                dist = np.linalg.norm(points[point_idx] - points[other_idx])
                if dist < min_dist:
                    min_dist = dist
        
        # Boundary-aware mobility: near boundaries, prioritize boundary distance
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
                # Larger perturbation to break symmetry
                perturbation = np.random.uniform(-0.15, 0.15, size=2) * scale
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
            
            # DYNAMIC THRESHOLD SELECTION - replaced fixed percentage threshold
            min_area = triangles[0][3]
            if len(min_area_history) > 10:
                recent_min_areas = min_area_history[-10:]
                improvement_rate = (recent_min_areas[-1] - recent_min_areas[0]) / 10
                # Higher improvement rate means we're making progress, focus on fewer triangles
                # Lower improvement rate means we're stuck, consider more triangles
                threshold_factor = 1.15 + 0.25 * (1.0 - min(1.0, max(0, improvement_rate * 1000)))
            else:
                threshold_factor = 1.01  # Default to 1% for early iterations

            threshold = min_area * threshold_factor
            critical_triangles = [t for t in triangles if t[3] <= threshold]

            # Temperature-scaled step
            step = base_step * (T / initial_temp)
            candidate = points.copy()
            
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

                # Weight by proximity to minimum area (more weight for smaller triangles)
                weight = 1.0 / max(1e-10, area_val - min_area + 1e-5)
                
                gradients[i] += weight * grad_a
                gradients[j] += weight * grad_b
                gradients[k] += weight * grad_c

            # Calculate mobilities for all points
            mobilities = [calculate_mobility(idx, points) for idx in range(11)]
            
            # Apply aggregated gradients with mobility weighting
            for idx in range(11):
                if np.linalg.norm(gradients[idx]) > 1e-8:
                    # Scale by step size but preserve direction, weighted by mobility
                    mobility_factor = mobilities[idx] / max(mobilities) if max(mobilities) > 0 else 1.0
                    candidate[idx] = points[idx] + step * gradients[idx] / np.linalg.norm(gradients[idx]) * (0.5 + 0.5 * mobility_factor)

            # INCREASED EXPLORATION FREQUENCY - changed from 500 to 250 and added adaptive triggering
            if iter_idx > 1000 and (iter_idx % 250 == 0 or (len(min_area_history) > 100 and (min_area_history[-1] - min_area_history[-100]) / 100 < 1e-6)):
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
            
            # ENHANCED RESISTANCE SIMULATION - multi-scale perturbation testing
            resistance_score = 1.0
            # Simulate potential opponent improvements with multi-scale perturbations
            if iter_idx % 200 == 0:
                opponent_improvement = 0
                # Test different perturbation scales to simulate various opponent strategies
                for perturbation_scale in [0.02, 0.05, 0.10]:
                    for _ in range(2):  # Run 2 trials per scale
                        opp_candidate = candidate.copy()
                        # Pick a random point involved in small triangles
                        small_tri_idx = np.random.randint(0, min(5, len(critical_triangles)))
                        i, j, k, _ = critical_triangles[small_tri_idx]
                        idx_to_move = np.random.choice([i, j, k])
                        
                        # Move with the current perturbation scale
                        opp_candidate[idx_to_move] += np.random.uniform(-perturbation_scale, perturbation_scale, size=2)
                        
                        # Project back to triangle
                        if not is_inside_triangle(opp_candidate[idx_to_move], A, B, C):
                            opp_candidate[idx_to_move] = project_to_triangle(opp_candidate[idx_to_move])
                            opp_candidate[idx_to_move] = optimize_boundary_position(
                                opp_candidate[idx_to_move], opp_candidate, idx_to_move)
                        
                        opp_min_area = get_smallest_triangle_area(opp_candidate)
                        opponent_improvement = max(opponent_improvement, opp_min_area - new_min_area)
                
                # Penalize configurations easily improved by opponents
                resistance_score = 1.0 - min(0.5, opponent_improvement * 10)
                resistance_history.append(resistance_score)

            # Combined quality-resistance score
            combined_score = 0.5 * new_min_area + 0.5 * (new_min_area * resistance_score)
            current_combined = 0.5 * current_min_area + 0.5 * (current_min_area * (resistance_history[-1] if resistance_history else 1.0))
            combined_delta = combined_score - current_combined

            # ADVANCED TEMPERATURE ADAPTATION - with reheating capability
            if len(min_area_history) > 100:
                recent_improvements = min_area_history[-100:]
                improvement_rate = (recent_improvements[-1] - recent_improvements[0]) / 100
                
                if improvement_rate < 1e-6:  # Stagnation detected
                    # Reheat if we've been stuck for a while
                    if len(min_area_history) > 500 and min_area_history[-100:].count(min_area_history[-1]) > 80:
                        T = initial_temp * 0.7  # Reheat to 70% of initial temperature
                    else:
                        T = max(0.001, T * 0.95)  # Faster cooling
                else:
                    # Adjust cooling rate based on resistance
                    if resistance_history and resistance_history[-1] > 0.5:
                        T = min(0.1, T * 1.01)  # Slower cooling for resistant configurations
                    else:
                        T = min(0.1, T * 1.005)  # Slightly slower cooling for non-resistant

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