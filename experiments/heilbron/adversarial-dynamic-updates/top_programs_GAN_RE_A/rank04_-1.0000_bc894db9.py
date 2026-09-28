import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
from scipy.spatial import Delaunay, Voronoi
import scipy.spatial

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Function to place points along an edge with edge-specific adaptive spacing
    def place_along_edge(start, end, positions):
        points = []
        for t in positions:
            point = (1-t) * start + t * end
            points.append(point)
        return points
    
    # Generate parameterized edge spacing with edge-specific ranges
    def get_edge_spacings(quality_factor, edge_type):
        # Edge-specific base ranges that narrow as quality improves
        if edge_type == 'AB':
            outer_low = 0.08 + 0.04 * (1.0 - quality_factor)
            outer_high = 0.22 - 0.04 * (1.0 - quality_factor)
            center_low = 0.42 + 0.03 * (1.0 - quality_factor)
            center_high = 0.58 - 0.03 * (1.0 - quality_factor)
        elif edge_type == 'BC':
            outer_low = 0.12 + 0.06 * (1.0 - quality_factor)
            outer_high = 0.28 - 0.06 * (1.0 - quality_factor)
            center_low = 0.45 + 0.04 * (1.0 - quality_factor)
            center_high = 0.55 - 0.04 * (1.0 - quality_factor)
        else:  # 'CA'
            outer_low = 0.05 + 0.03 * (1.0 - quality_factor)
            outer_high = 0.18 - 0.03 * (1.0 - quality_factor)
            center_low = 0.40 + 0.05 * (1.0 - quality_factor)
            center_high = 0.60 - 0.05 * (1.0 - quality_factor)
        
        # Generate random positions within constrained ranges
        left_pos = np.random.uniform(outer_low, outer_high)
        center_pos = np.random.uniform(center_low, center_high)
        right_pos = 1.0 - np.random.uniform(outer_low, outer_high)
        
        return [left_pos, center_pos, right_pos]

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

    # Barycentric projection for boundary constraint satisfaction
    def barycentric_project(point, A, B, C):
        """Project a point back into the triangle using barycentric coordinates."""
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
            return (A + B + C) / 3
            
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w
        
        # Clip to [0,1] and renormalize if outside
        if u < 0:
            u = 0
            sum_vw = v + w
            if sum_vw > 0:
                v, w = v/sum_vw, w/sum_vw
            else:
                v, w = 0.5, 0.5
        if v < 0:
            v = 0
            sum_uw = u + w
            if sum_uw > 0:
                u, w = u/sum_uw, w/sum_uw
            else:
                u, w = 0.5, 0.5
        if w < 0:
            w = 0
            sum_uv = u + v
            if sum_uv > 0:
                u, v = u/sum_uv, v/sum_uv
            else:
                u, v = 0.5, 0.5
        
        # Ensure sum is 1 (numerical stability)
        total = u + v + w
        if total > 0:
            u, v, w = u/total, v/total, w/total
        else:
            u, v, w = 1/3, 1/3, 1/3
        
        return u * A + v * B + w * C

    # Adaptive boundary push based on confinement severity
    def adaptive_boundary_push(point, A, B, C, quality_factor):
        u, v, w = get_barycentric_coords(point, A, B, C)
        min_coord = min(u, v, w)
        
        # If not near boundary, return original point
        if min_coord >= 0.05:
            return point
        
        # Push strength proportional to confinement severity and quality
        push_strength = 0.05 * (1 - min_coord) * (1.5 - quality_factor)
        
        # Push away from the nearest boundary
        new_point = point.copy()
        if u < v and u < w:
            # Near BC boundary, push toward A
            new_point += push_strength * (A - point)
        elif v < u and v < w:
            # Near AC boundary, push toward B
            new_point += push_strength * (B - point)
        else:
            # Near AB boundary, push toward C
            new_point += push_strength * (C - point)
        
        return barycentric_project(new_point, A, B, C)

    # Generate interior points using Delaunay triangulation and Voronoi vertices
    def get_voronoi_interior_points(edge_points, quality_factor):
        # Create Delaunay triangulation of edge points
        points = np.array(edge_points)
        tri = Delaunoi(points)
        
        # Get Voronoi diagram
        vor = Voronoi(points)
        
        # Collect Voronoi vertices inside the triangle
        A, B, C = get_unit_triangle()
        candidate_points = []
        
        # Evaluate potential minimum triangle area for each candidate
        for i, point in enumerate(vor.vertices):
            if is_inside_triangle(point, A, B, C):
                # Temporarily add candidate point to evaluate impact
                test_points = np.vstack([points, point])
                min_area = get_smallest_triangle_area(test_points)
                candidate_points.append((point, min_area))
        
        # Determine how many interior points to generate based on quality
        n_interior = max(2, min(4, int(4 - 2 * quality_factor)))
        
        # If we have candidates, select those with highest potential min_area
        if candidate_points:
            # Sort by min_area (highest first)
            candidate_points.sort(key=lambda x: x[1], reverse=True)
            # Select top candidates
            selected_points = [p for p, _ in candidate_points[:n_interior]]
            return selected_points
        
        # Fallback: generate random points if no Voronoi vertices qualify
        interior_points = []
        for _ in range(n_interior):
            # Random point inside triangle
            r1, r2 = np.random.rand(), np.random.rand()
            point = (1 - np.sqrt(r1)) * A + np.sqrt(r1) * (1 - r2) * B + np.sqrt(r1) * r2 * C
            interior_points.append(point)
        
        return interior_points

    # Calculate quality factor (0.0-1.0, 0=perfect)
    def calculate_quality_factor(current_min_area, target=0.0365):
        return max(0.0, min(1.0, 1.0 - current_min_area / target))

    # Get current min_area to adapt parameters
    def get_current_min_area(points):
        try:
            return get_smallest_triangle_area(points)
        except:
            return 0.0

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
        
        # Density estimation for adaptive power-law weighting
        avg_dist = (dist_ab + dist_bc + dist_ca) / 3.0
        density_factor = min(1.0, max(0.2, 0.5 / (avg_dist + 1e-5)))
        p = 1.2 + 0.8 * density_factor  # p ranges from 1.2 (dense) to 2.0 (sparse)
        
        weight_a = 1.0 / (dist_ab**p + dist_ca**p)
        weight_b = 1.0 / (dist_ab**p + dist_bc**p)
        weight_c = 1.0 / (dist_bc**p + dist_ca**p)
        
        grad_a = grad_a * weight_a
        grad_b = grad_b * weight_b
        grad_c = grad_c * weight_c

        # Adaptive magnitude scaling
        max_grad = max(np.linalg.norm(grad_a), np.linalg.norm(grad_b), np.linalg.norm(grad_c), 1e-10)
        scaling_factor = 0.8 + 0.2 * density_factor
        
        if max_grad > 1e-10:
            grad_a = grad_a * (scaling_factor / max_grad)
            grad_b = grad_b * (scaling_factor / max_grad)
            grad_c = grad_c * (scaling_factor / max_grad)

        return grad_a, grad_b, grad_c

    # Triangle clustering analysis to identify critical regions
    def get_triangle_clusters(triangle_indices, points, min_area):
        # Build a weighted graph of triangles
        graph = {}
        weights = {}
        
        for i, tri1 in enumerate(triangle_indices):
            i1, j1, k1 = tri1
            a1, b1, c1 = points[i1], points[j1], points[k1]
            area1 = 0.5 * abs((b1[0] - a1[0]) * (c1[1] - a1[1]) - (c1[0] - a1[0]) * (b1[1] - a1[1]))
            
            # Weight by inverse area (higher weight for smaller triangles)
            weight1 = 1.0 / max(area1, min_area * 0.9)
            
            for j, tri2 in enumerate(triangle_indices):
                if i >= j:
                    continue
                
                i2, j2, k2 = tri2
                a2, b2, c2 = points[i2], points[j2], points[k2]
                area2 = 0.5 * abs((b2[0] - a2[0]) * (c2[1] - a2[1]) - (c2[0] - a2[0]) * (b2[1] - a2[1]))
                weight2 = 1.0 / max(area2, min_area * 0.9)
                
                # Count shared vertices
                shared = len(set(tri1) & set(tri2))
                if shared >= 1:  # Only need one shared vertex for adjacency
                    # Edge weight combines shared vertices and area weights
                    edge_weight = shared * (weight1 + weight2) / 2.0
                    
                    if i not in graph:
                        graph[i] = {}
                    if j not in graph:
                        graph[j] = {}
                    
                    graph[i][j] = edge_weight
                    graph[j][i] = edge_weight
                    
                    weights[(i, j)] = edge_weight
                    weights[(j, i)] = edge_weight
        
        # Find connected components (clusters) using weighted graph
        visited = set()
        clusters = []
        
        # Sort triangles by area (smallest first) to prioritize critical regions
        triangle_areas = []
        for i, tri in enumerate(triangle_indices):
            i1, j1, k1 = tri
            a1, b1, c1 = points[i1], points[j1], points[k1]
            area1 = 0.5 * abs((b1[0] - a1[0]) * (c1[1] - a1[1]) - (c1[0] - a1[0]) * (b1[1] - a1[1]))
            triangle_areas.append((i, area1))
        
        # Sort by area (smallest first)
        triangle_areas.sort(key=lambda x: x[1])
        
        for idx, _ in triangle_areas:
            if idx not in visited:
                cluster = []
                stack = [idx]
                visited.add(idx)
                
                while stack:
                    node = stack.pop()
                    cluster.append(node)
                    
                    if node in graph:
                        # Sort neighbors by edge weight (highest first)
                        neighbors = sorted(graph[node].items(), key=lambda x: x[1], reverse=True)
                        for neighbor, _ in neighbors:
                            if neighbor not in visited:
                                visited.add(neighbor)
                                stack.append(neighbor)
                
                clusters.append(cluster)
        
        # Sort clusters by average area (smallest first)
        cluster_metrics = []
        for i, cluster in enumerate(clusters):
            total_area = 0
            for idx in cluster:
                i1, j1, k1 = triangle_indices[idx]
                a1, b1, c1 = points[i1], points[j1], points[k1]
                area1 = 0.5 * abs((b1[0] - a1[0]) * (c1[1] - a1[1]) - (c1[0] - a1[0]) * (b1[1] - a1[1]))
                total_area += area1
            avg_area = total_area / len(cluster) if cluster else float('inf')
            cluster_metrics.append((i, avg_area, len(cluster)))
        
        # Sort by average area (smallest first) then by size (largest first)
        cluster_metrics.sort(key=lambda x: (x[1], -x[2]))
        sorted_clusters = [clusters[i] for i, _, _ in cluster_metrics]
        
        return sorted_clusters

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

    # Detect stagnation type for adaptive recovery
    def detect_stagnation_type(points, improvement_history, stagnation_counter):
        """Analyze stagnation pattern to determine appropriate recovery strategy"""
        if stagnation_counter < 15:
            return 'none'
        
        n = points.shape[0]
        # 1. Check for local clustering (high triangle density in small region)
        min_x, max_x = np.min(points[:,0]), np.max(points[:,0])
        min_y, max_y = np.min(points[:,1]), np.max(points[:,1])
        width, height = max_x - min_x, max_y - min_y
        
        # Calculate point density in quadrants
        x_mid, y_mid = (min_x + max_x)/2, (min_y + max_y)/2
        quadrant_counts = [0, 0, 0, 0]
        for i in range(n):
            x, y = points[i]
            if x < x_mid:
                if y < y_mid:
                    quadrant_counts[0] += 1
                else:
                    quadrant_counts[1] += 1
            else:
                if y < y_mid:
                    quadrant_counts[2] += 1
                else:
                    quadrant_counts[3] += 1
        
        max_quadrant = max(quadrant_counts)
        clustering_score = max_quadrant / (n / 4.0)
        
        # 2. Check for global plateau (minimal score variation)
        score_variation = 0
        if len(improvement_history) >= 10:
            recent_improvements = improvement_history[-10:]
            score_variation = max(recent_improvements) - min(recent_improvements)
        
        # 3. Check for boundary confinement (excessive boundary points)
        boundary_points = 0
        for i in range(n):
            u, v, w = get_barycentric_coords(points[i], A, B, C)
            if min(u, v, w) < 0.01:
                boundary_points += 1
        
        boundary_ratio = boundary_points / n
        
        # Determine stagnation type
        if clustering_score > 1.8 and boundary_ratio < 0.7:
            return 'clustering'
        elif score_variation < 1e-8 and clustering_score < 1.5:
            return 'plateau'
        elif boundary_ratio > 0.8:
            return 'boundary'
        else:
            return 'general'

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
        
        # Dynamic gradient usage based on success rate
        gradient_usage = 0.3 * quality_factor  # More exploration for poor quality

        # Adaptive triangle ratio starts higher and decreases during optimization
        triangle_ratio = 1.15
        triangle_ratio_decay = (1.05 / 1.15) ** (1.0 / n_rounds)

        # Reheating parameters
        reheating_counter = 0
        max_reheating = 3
        reheating_factor = 1.0

        for round_idx in range(n_rounds):
            # Periodic global restructuring via Voronoi cell reassignment
            if round_idx % 50 == 0 and round_idx > 0:
                # Create Delaunay triangulation
                tri = Delaunay(best)
                
                # Get Voronoi diagram
                vor = Voronoi(best)
                
                # Reassign points to different Voronoi regions
                new_points = np.zeros_like(best)
                for i in range(len(best)):
                    # Find which Voronoi region this point belongs to
                    region_idx = vor.point_region[i]
                    region = vor.regions[region_idx]
                    
                    # If the region is valid and not infinite
                    if -1 not in region and len(region) > 0:
                        # Choose a random vertex from this region
                        vertex_idx = np.random.choice(region)
                        new_point = vor.vertices[vertex_idx]
                        
                        # Only accept if inside triangle
                        if is_inside_triangle(new_point, A, B, C):
                            new_points[i] = new_point
                        else:
                            new_points[i] = best[i]
                    else:
                        new_points[i] = best[i]
                
                # Check if this restructuring improves the configuration
                new_score = get_smallest_triangle_area(new_points)
                if new_score > best_score:
                    best = new_points
                    best_score = new_score

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
            
            # Update adaptive stagnation threshold based on difficulty
            adaptive_stagnation_threshold = int(20 * (1 + 0.5 * min(1.0, 2 * stagnation_counter / n_rounds)))
            
            # Reset if stuck for too long, but with progressive strategy
            if stagnation_counter > adaptive_stagnation_threshold:
                # Detect stagnation type and apply appropriate recovery
                stagnation_type = detect_stagnation_type(best, improvement_history, stagnation_counter)
                
                if stagnation_type == 'clustering':
                    # For local clustering: selectively reset points in dense regions
                    T_decay = min(0.999, T_decay * 1.05)
                    step_decay = max(0.995, step_decay * 0.95)
                    
                    # Identify dense regions and perturb points there
                    n = best.shape[0]
                    distances = np.zeros((n, n))
                    for i in range(n):
                        for j in range(i+1, n):
                            distances[i,j] = distances[j,i] = np.linalg.norm(best[i] - best[j])
                    
                    # Find points with many close neighbors
                    close_threshold = 0.05  # Adjust based on problem scale
                    neighbor_counts = np.sum(distances < close_threshold, axis=1)
                    dense_indices = np.where(neighbor_counts > n//3)[0]
                    
                    if len(dense_indices) > 0:
                        # Perturb points in dense regions
                        for idx in dense_indices:
                            r = 0.05 * np.sqrt(np.random.rand())
                            theta = 2 * np.pi * np.random.rand()
                            perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                            best[idx] += perturbation
                            best[idx] = adaptive_boundary_push(best[idx], A, B, C, quality_factor)

                elif stagnation_type == 'plateau':
                    # For global plateau: increase exploration more aggressively
                    T_decay = min(0.9985, T_decay * 1.1)
                    step_decay = max(0.996, step_decay * 0.9)
                    
                    # Add moderate noise to all points
                    noise_scale = 0.01 * (1 + 0.5 * min(2, stagnation_counter / adaptive_stagnation_threshold))
                    for i in range(len(best)):
                        best[i] += np.random.normal(0, noise_scale, size=2)
                        best[i] = adaptive_boundary_push(best[i], A, B, C, quality_factor)

                elif stagnation_type == 'boundary':
                    # For boundary confinement: encourage interior movement
                    T_decay = min(0.999, T_decay * 1.03)
                    step_decay = max(0.997, step_decay * 0.97)
                    
                    # Adaptive boundary push for all points
                    for i in range(len(best)):
                        best[i] = adaptive_boundary_push(best[i], A, B, C, quality_factor)

                else:  # 'general' stagnation
                    # General case: moderate reset
                    T_decay = min(0.999, T_decay * 1.05)
                    step_decay = max(0.995, step_decay * 0.95)
                    stagnation_counter = max(0, stagnation_counter - 5)
                    
                    # Reset triangle ratio to encourage broader exploration
                    triangle_ratio = min(1.15, triangle_ratio * 1.05)

                # Apply reheating if stagnation persists
                if stagnation_counter > adaptive_stagnation_threshold * 1.5 and reheating_counter < max_reheating:
                    reheating_counter += 1
                    reheating_factor = 1.25 ** reheating_counter
                    T_decay = max(0.995, T_decay / reheating_factor)
                    step_decay = min(0.999, step_decay * reheating_factor)
                    stagnation_counter = max(0, stagnation_counter - 10)

            T = T0 * (T_decay ** round_idx) * reheating_factor
            current_step = base_step * (step_decay ** round_idx)
            
            # Update triangle ratio
            triangle_ratio = max(1.05, triangle_ratio * triangle_ratio_decay)

            # Get adaptive triangle indices based on current min_area
            triangle_indices = get_adaptive_triangle_indices(best, ratio=triangle_ratio)
            
            # Analyze triangle clusters to identify critical regions
            current_min_area = get_smallest_triangle_area(best)
            clusters = get_triangle_clusters(triangle_indices, best, current_min_area)
            
            # Select cluster with most critical triangles (smallest areas)
            if clusters:
                selected_cluster = clusters[0]
                selected_triangles = [triangle_indices[i] for i in selected_cluster]
                chosen_triangle = selected_triangles[np.random.randint(len(selected_triangles))]
            else:
                chosen_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
            
            # Dynamically adjust number of triangles to focus on based on current min_area
            focus_count = min(10, max(3, int(10 * current_min_area / 0.0365)))
            
            # Calculate gradient usage based on success history
            if len(gradient_success_history) > 5 and len(isotropic_success_history) > 5:
                gradient_success_rate = np.mean(gradient_success_history[-5:])
                isotropic_success_rate = np.mean(isotropic_success_history[-5:])
                
                # Calculate expected success rate (baseline)
                expected_success_rate = 0.1 * (1.0 + 0.5 * quality_factor)
                
                # Adjust gradient usage based on relative performance
                if gradient_success_rate > 0:
                    # Scale usage based on how much better gradient moves are performing
                    gradient_usage = max(0.3, 0.4 + 0.5 * min(1.0, gradient_success_rate / max(expected_success_rate, 1e-5)))
                else:
                    gradient_usage = max(0.3, gradient_usage * 0.9)
            
            # Randomly select one of the top triangles to work on
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

            # Ensure all points stay inside triangle using barycentric projection
            for i in range(len(candidate)):
                candidate[i] = barycentric_project(candidate[i], A, B, C)

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

    # Calculate initial quality to adapt parameters
    # Strategic Heilbronn configuration for n=11 with edge-specific spacing
    edge_points = []
    # AB edge: edge-specific spacing
    edge_points.extend(place_along_edge(A, B, get_edge_spacings(0.5, 'AB')))
    # BC edge: edge-specific spacing
    edge_points.extend(place_along_edge(B, C, get_edge_spacings(0.5, 'BC')))
    # CA edge: edge-specific spacing
    edge_points.extend(place_along_edge(C, A, get_edge_spacings(0.5, 'CA')))
    
    # Add adaptive interior points using Voronoi approach
    quality_factor = 0.5  # Initial estimate
    interior_points = get_voronoi_interior_points(edge_points, quality_factor)
    points = np.array(edge_points + interior_points)
    
    initial_min_area = get_smallest_triangle_area(points)
    # Scale parameters inversely with initial quality
    quality_factor = calculate_quality_factor(initial_min_area)

    # Run multiple annealing chains with logarithmically spaced parameters
    chains = []
    
    # Widen parameter ranges based on quality (more exploration for poor quality)
    base_step_min = 0.015 * (1.5 - 0.5 * quality_factor)
    base_step_max = 0.12 * (1.5 - 0.5 * quality_factor)  # Expanded from 0.09 to 0.12
    T0_min = 0.007 * (1.5 - 0.5 * quality_factor)
    T0_max = 0.015 * (1.5 - 0.5 * quality_factor)
    T_decay_min = 0.997 * (0.9 + 0.1 * quality_factor)
    T_decay_max = 0.999 * (0.9 + 0.1 * quality_factor)
    step_decay_min = 0.9975 * (0.9 + 0.1 * quality_factor)
    step_decay_max = 0.9998 * (0.9 + 0.1 * quality_factor)

    # Use logarithmic spacing for better parameter coverage
    chain_count = max(3, min(5, int(2 + 3 * quality_factor)))
    base_steps = np.logspace(np.log10(base_step_min), np.log10(base_step_max), chain_count)
    T0_values = np.logspace(np.log10(T0_min), np.log10(T0_max), chain_count)
    T_decay_values = np.logspace(np.log10(T_decay_min), np.log10(T_decay_max), chain_count)
    step_decay_values = np.logspace(np.log10(step_decay_min), np.log10(step_decay_max), chain_count)
    
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
    
    # Add ultra-precise chain for high-quality inputs
    if quality_factor < 0.2:
        ultra_chain, ultra_score = run_annealing_chain(
            points.copy(),
            base_step=0.005 + 0.005 * quality_factor,
            T0=0.005 * (0.3 + 0.7 * quality_factor),
            T_decay_base=0.9992,
            step_decay_base=0.9997,
            min_ratio=0.001,
            quality_factor=quality_factor
        )
        chains.append((ultra_chain, ultra_score))
    
    # Select the best chain result
    best_chain = max(chains, key=lambda x: x[1])
    return best_chain[0]