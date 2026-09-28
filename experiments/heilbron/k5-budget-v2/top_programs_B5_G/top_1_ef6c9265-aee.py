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

    # Boundary-aware mobility metric (mimicking Improver's strategy to identify vulnerabilities)
    def compute_mobility(point, all_points):
        # Distance to boundary
        def distance_to_boundary(p):
            area_PBC = 0.5 * abs((B[0]-p[0])*(C[1]-p[1]) - (B[1]-p[1])*(C[0]-p[0]))
            length_BC = np.linalg.norm(B - C)
            dist_BC = 2 * area_PBC / length_BC if length_BC > 1e-10 else float('inf')
            
            area_PAC = 0.5 * abs((A[0]-p[0])*(C[1]-p[1]) - (A[1]-p[1])*(C[0]-p[0]))
            length_AC = np.linalg.norm(A - C)
            dist_AC = 2 * area_PAC / length_AC if length_AC > 1e-10 else float('inf')
            
            area_PAB = 0.5 * abs((A[0]-p[0])*(B[1]-p[1]) - (A[1]-p[1])*(B[0]-p[0]))
            length_AB = np.linalg.norm(A - B)
            dist_AB = 2 * area_PAB / length_AB if length_AB > 1e-10 else float('inf')
            
            return min(dist_BC, dist_AC, dist_AB)

        dist_to_boundary = distance_to_boundary(point)
        
        # Distance to nearest point
        min_dist = float('inf')
        for other in all_points:
            if np.array_equal(other, point):
                continue
            dist = np.linalg.norm(point - other)
            if dist < min_dist:
                min_dist = dist
        
        # Adaptive boundary weights based on resistance level
        if len(resistance_history) > 0:
            avg_resistance = np.mean(resistance_history[-50:]) if len(resistance_history) >= 50 else 0.5
            if avg_resistance < 0.5:
                boundary_weight = 0.8
                point_weight = 0.2
            else:
                boundary_weight = 0.4
                point_weight = 0.6
        else:
            boundary_weight = 0.4
            point_weight = 0.6
            
        # Boundary-aware mobility
        return boundary_weight * dist_to_boundary + point_weight * min_dist

    # Compute resistance metric based on distribution of small triangles
    def compute_resistance_metric(triangles, min_area):
        if not triangles or min_area <= 0:
            return 1.0
        
        # Count triangles within 20% of minimum area
        tight_count = sum(1 for area in triangles if area <= min_area * 1.2)
        return min(1.0, tight_count / 5.0)

    # Optimize boundary position for maximum min_area
    def optimize_boundary_position(point, all_points, idx):
        original = point.copy()
        
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

        # Sample points along the closest edge with higher resolution
        p1, p2 = edges[closest_edge]
        
        # Adaptive resolution based on resistance
        if len(resistance_history) > 0:
            avg_resistance = np.mean(resistance_history[-50:]) if len(resistance_history) >= 50 else 0.5
            n_samples = 100 if avg_resistance < 0.5 else 50
        else:
            n_samples = 50
            
        best_position = original
        best_min_area = get_smallest_triangle_area(all_points)
        
        for t in np.linspace(0, 1, n_samples):
            candidate = p1 * (1 - t) + p2 * t
            
            # Calculate min area with this candidate position
            test_points = all_points.copy()
            test_points[idx] = candidate
            min_area = get_smallest_triangle_area(test_points)
            
            if min_area > best_min_area:
                best_min_area = min_area
                best_position = candidate

        return best_position

    # Generate dynamic asymmetric row patterns based on resistance level
    def generate_dynamic_row_patterns(resistance_history):
        # Literature-informed asymmetric patterns for 11 points
        asymmetric_patterns = [
            [4, 3, 2, 1, 1],
            [3, 3, 2, 2, 1],
            [4, 2, 2, 2, 1],
            [3, 3, 3, 1, 1],
            [4, 3, 1, 2, 1],
            [3, 4, 2, 1, 1],
            [5, 2, 2, 1, 1],
            [3, 2, 3, 2, 1],
            [4, 1, 3, 2, 1],
            [2, 3, 3, 2, 1],
            [3, 3, 1, 3, 1],
            [4, 2, 1, 3, 1]
        ]
        
        # Calculate pattern weights based on resistance history
        if len(resistance_history) < 50:
            return asymmetric_patterns[:4]  # Start with conservative patterns
        
        avg_resistance = np.mean(resistance_history[-50:])
        weights = []
        
        for i, pattern in enumerate(asymmetric_patterns):
            # Patterns with more asymmetry get higher weight when resistance is low
            asymmetry = sum(abs(pattern[j] - pattern[j+1]) for j in range(len(pattern)-1))
            base_weight = 0.5 + 0.5 * asymmetry / 10.0
            
            # When resistance is low, favor more asymmetric patterns
            if avg_resistance < 0.5:
                weight = base_weight * (1.5 - avg_resistance)
            else:
                weight = base_weight * (0.7 + avg_resistance)
            
            weights.append(weight)
        
        # Normalize weights
        total = sum(weights)
        weights = [w/total for w in weights]
        
        # Select top 4 patterns with highest weights
        pattern_indices = np.argsort(weights)[-4:][::-1]
        return [asymmetric_patterns[i] for i in pattern_indices]

    # Generate initial configuration with dynamic row pattern
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
                
                # Adaptive perturbation based on row position
                if v_coord < 0.2 or v_coord > 0.8:  # Near boundaries
                    perturbation = np.random.uniform(-0.08, 0.08, size=2) * scale
                else:  # Middle rows
                    perturbation = np.random.uniform(-0.12, 0.12, size=2) * scale
                
                P = P + perturbation
                points.append(P)
        return np.array(points)

    best_points = None
    best_min_area = -1
    best_resistance = -1

    # Multi-start optimization with opponent-aware scoring
    for pattern_idx in range(3):  # Run 3 independent starts with different patterns
        # Generate dynamic patterns based on previous resistance (simulating historical success)
        resistance_history = [0.5] * 50 if pattern_idx == 0 else [0.45, 0.48, 0.47, 0.51, 0.52] * 10
        row_patterns = generate_dynamic_row_patterns(resistance_history)
        
        # Select pattern with weighted randomness (skewed toward resistant patterns)
        pattern_weights = [0.6, 0.3, 0.1, 0.0]
        pattern = row_patterns[np.random.choice(4, p=pattern_weights)]
        
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
        mobility_history = []

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
            
            if not triangles:
                continue
            
            min_area = triangles[0][3]
            
            # Compute resistance metric for adaptive thresholding
            triangle_areas = [t[3] for t in triangles]
            resistance = compute_resistance_metric(triangle_areas, min_area)
            resistance_history.append(resistance)
            if len(resistance_history) > 100:
                resistance_history.pop(0)
            
            # Adaptive threshold: wider when resistance is low (vulnerable)
            avg_resistance = np.mean(resistance_history) if resistance_history else 0.5
            threshold = min_area * (0.05 + 0.15 * (1.0 - avg_resistance))
            critical_triangles = [t for t in triangles if t[3] <= min_area + threshold]

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
                # Adaptive weighting: when resistance is low, focus intensely on the smallest triangles
                if avg_resistance < 0.5:
                    weight = 1.0 / max(1e-10, (area_val - min_area + 1e-6)**2)
                else:
                    weight = 1.0 / max(1e-10, area_val - min_area + 1e-5)
                
                gradients[i] += weight * grad_a
                gradients[j] += weight * grad_b
                gradients[k] += weight * grad_c

            # Apply aggregated gradients
            for idx in range(11):
                if np.linalg.norm(gradients[idx]) > 1e-8:
                    # Scale by step size but preserve direction
                    candidate[idx] = points[idx] + step * gradients[idx] / np.linalg.norm(gradients[idx])

            # Voronoi-guided exploration for escaping shallow optima - triggered by low resistance
            if len(resistance_history) > 50 and np.mean(resistance_history[-50:]) < 0.5 and \
               (iter_idx % 150 == 0 or np.mean(np.diff(resistance_history[-50:])) < 0.0005):
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
                            
                            # Find most vulnerable point using boundary-aware mobility
                            vulnerabilities = []
                            for idx in range(11):
                                mobility = compute_mobility(points[idx], points)
                                # Higher vulnerability = lower mobility
                                vulnerabilities.append((1.0 / (mobility + 1e-5), idx))
                            
                            vulnerabilities.sort(reverse=True)  # Most vulnerable first
                            move_idx = vulnerabilities[0][1]  # Move the most vulnerable point
                            
                            # Project to triangle if needed
                            if is_inside_triangle(target_centroid, A, B, C):
                                candidate[move_idx] = target_centroid
                            else:
                                projected = project_to_triangle(target_centroid)
                                candidate[move_idx] = optimize_boundary_position(projected, candidate, move_idx)
                except Exception as e:
                    pass

            # Project candidate points to stay within triangle
            for idx in range(11):
                if not is_inside_triangle(candidate[idx], A, B, C):
                    projected = project_to_triangle(candidate[idx])
                    candidate[idx] = optimize_boundary_position(projected, candidate, idx)

            # Evaluate candidate
            new_min_area = get_smallest_triangle_area(candidate)
            delta = new_min_area - current_min_area
            
            # Systematic opponent simulation with adaptive perturbation strategy
            opponent_improvement = 0
            if iter_idx % 150 == 0:  # Reduced frequency to balance quality/resistance
                # Compute vulnerabilities for all points
                vulnerabilities = []
                for idx in range(11):
                    mobility = compute_mobility(points[idx], points)
                    # Higher vulnerability = lower mobility
                    vulnerabilities.append((1.0 / (mobility + 1e-5), idx))
                
                vulnerabilities.sort(reverse=True)  # Most vulnerable first
                top_vulnerable = [idx for _, idx in vulnerabilities[:3]]
                
                # Adaptive perturbation magnitudes based on vulnerability
                avg_mobility = np.mean([compute_mobility(p, candidate) for p in candidate])
                magnitudes = [0.02 * (1 + 1/(avg_mobility + 0.1)), 
                             0.04 * (1 + 1/(avg_mobility + 0.1)),
                             0.06 * (1 + 1/(avg_mobility + 0.1))]
                
                # Test adaptive perturbation strategy
                for magnitude in magnitudes:
                    for idx_to_move in top_vulnerable:
                        opp_candidate = candidate.copy()
                        
                        # Direction based on gradient (mimicking Improver's approach)
                        direction = np.random.uniform(-1, 1, size=2)
                        direction = direction / (np.linalg.norm(direction) + 1e-10)
                        opp_candidate[idx_to_move] += direction * magnitude
                        
                        # Project back to triangle
                        if not is_inside_triangle(opp_candidate[idx_to_move], A, B, C):
                            opp_candidate[idx_to_move] = project_to_triangle(opp_candidate[idx_to_move])
                            opp_candidate[idx_to_move] = optimize_boundary_position(
                                opp_candidate[idx_to_move], opp_candidate, idx_to_move)
                        
                        opp_min_area = get_smallest_triangle_area(opp_candidate)
                        improvement = opp_min_area - new_min_area
                        opponent_improvement = max(opponent_improvement, improvement)

                # Track mobility history for adaptive behavior
                avg_mobility = np.mean([compute_mobility(p, candidate) for p in candidate])
                mobility_history.append(avg_mobility)
                if len(mobility_history) > 100:
                    mobility_history.pop(0)

            # Adaptive resistance weighting based on vulnerability
            avg_resistance = np.mean(resistance_history[-50:]) if len(resistance_history) >= 50 else 0.5
            # Sigmoid-based weighting: when resistance < 0.5, increase resistance focus
            resistance_weight = 0.4 + 0.4 * (1 / (1 + np.exp(-5 * (0.5 - avg_resistance))))
            
            # Combined quality-resistance score with adaptive weighting
            resistance_score = max(0, 1.0 - min(0.5, opponent_improvement * 10))
            combined_score = (1 - resistance_weight) * new_min_area + resistance_weight * (new_min_area * resistance_score)
            
            # Current combined score for comparison
            current_resistance_score = 1.0
            if resistance_history:
                current_resistance_score = max(0, 1.0 - min(0.5, opponent_improvement * 10))
            current_combined = (1 - resistance_weight) * current_min_area + resistance_weight * (current_min_area * current_resistance_score)
            
            combined_delta = combined_score - current_combined

            # Adaptive cooling based on improvement history
            if len(min_area_history) > 100:
                recent_improvements = min_area_history[-100:]
                improvement_rate = (recent_improvements[-1] - recent_improvements[0]) / 100
                
                # Adjust cooling based on resistance trends
                resistance_trend = 0
                if len(resistance_history) > 100:
                    recent_resistance = resistance_history[-100:]
                    resistance_trend = (recent_resistance[-1] - recent_resistance[0]) / 100
                
                if improvement_rate < 1e-6 and resistance_trend < 0.001:  # Stagnation detected
                    T = max(0.001, T * 0.95)  # Slower cooling rate to prevent premature convergence
                else:
                    T = min(0.1, T * 1.008)  # Slower cooling for good progress

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