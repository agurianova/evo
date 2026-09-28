import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
from scipy.spatial import Delaunay, Voronoi
import scipy.spatial
import time

np.random.seed(42)

# Resistance history for adaptive parameter tuning
RESISTANCE_HISTORY = []

# Track opponent improvement patterns for resistance modeling
OPPONENT_IMPROVEMENT_HISTORY = []

# Edge-specific resistance profiles (updated during evolution)
EDGE_RESISTANCE_PROFILES = {
    'AB': np.array([0.5] * 100),
    'BC': np.array([0.5] * 100),
    'CA': np.array([0.5] * 100)
}

# Global resistance factor (updated externally)
RESISTANCE_FACTOR = 0.5

# Track resistance patterns across generations
def update_resistance_history(resistance_value):
    global RESISTANCE_HISTORY, RESISTANCE_FACTOR
    RESISTANCE_HISTORY.append(resistance_value)
    if len(RESISTANCE_HISTORY) > 50:
        RESISTANCE_HISTORY.pop(0)
    RESISTANCE_FACTOR = 1.0 - np.mean(RESISTANCE_HISTORY) if RESISTANCE_HISTORY else 0.5

# Update edge resistance profiles based on opponent failures
def update_edge_resistance_profiles(points, improved):
    global EDGE_RESISTANCE_PROFILES
    A, B, C = get_unit_triangle()
    
    # Map points to edges (0-1 parameterization)
    for i, point in enumerate(points):
        # Check AB edge
        if np.isclose(np.cross(B-A, point-A), 0) and min(A[0], B[0]) <= point[0] <= max(A[0], B[0]):
            t = (point[0] - A[0]) / (B[0] - A[0]) if B[0] != A[0] else (point[1] - A[1]) / (B[1] - A[1])
            idx = int(t * 99)
            EDGE_RESISTANCE_PROFILES['AB'][idx] = 0.9 * EDGE_RESISTANCE_PROFILES['AB'][idx] + 0.1 * (1.0 if improved else 0.0)
        
        # Check BC edge
        if np.isclose(np.cross(C-B, point-B), 0) and min(B[0], C[0]) <= point[0] <= max(B[0], C[0]):
            t = (point[0] - B[0]) / (C[0] - B[0]) if C[0] != B[0] else (point[1] - B[1]) / (C[1] - B[1])
            idx = int(t * 99)
            EDGE_RESISTANCE_PROFILES['BC'][idx] = 0.9 * EDGE_RESISTANCE_PROFILES['BC'][idx] + 0.1 * (1.0 if improved else 0.0)
        
        # Check CA edge
        if np.isclose(np.cross(A-C, point-C), 0) and min(C[0], A[0]) <= point[0] <= max(C[0], A[0]):
            t = (point[0] - C[0]) / (A[0] - C[0]) if A[0] != C[0] else (point[1] - C[1]) / (A[1] - C[1])
            idx = int(t * 99)
            EDGE_RESISTANCE_PROFILES['CA'][idx] = 0.9 * EDGE_RESISTANCE_PROFILES['CA'][idx] + 0.1 * (1.0 if improved else 0.0)

# Simulate lightweight opponent attack to estimate resistance
def simulate_opponent_attack(configuration, num_trials=15):
    """Run lightweight opponent simulation to estimate how hard this configuration is to improve"""
    current_min_area = get_smallest_triangle_area(configuration)
    improvements = []
    
    # Lightweight annealing parameters for simulation
    base_step = 0.03
    T0 = 0.005
    T_decay = 0.998
    step_decay = 0.9985
    n_rounds = 80  # Limited rounds for speed
    
    for _ in range(num_trials):
        candidate = configuration.copy()
        best_score = current_min_area
        
        for round_idx in range(n_rounds):
            T = T0 * (T_decay ** round_idx)
            current_step = base_step * (step_decay ** round_idx)
            
            # Randomly select a triangle to work on
            n = len(candidate)
            i, j, k = np.random.choice(n, 3, replace=False)
            
            # Isotropic perturbation
            idx = np.random.choice([i, j, k])
            r = current_step * np.sqrt(np.random.rand())
            theta = 2 * np.pi * np.random.rand()
            perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
            candidate[idx] += perturbation
            
            # Ensure point stays inside triangle
            if not is_inside_triangle(candidate[idx], *get_unit_triangle()):
                # Simple projection back to triangle
                A, B, C = get_unit_triangle()
                # Find closest point on edges
                def closest_point_on_segment(p, a, b):
                    ap = p - a
                    ab = b - a
                    t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
                    t = max(0.0, min(1.0, t))
                    return a + t * ab
                
                p1 = closest_point_on_segment(candidate[idx], A, B)
                p2 = closest_point_on_segment(candidate[idx], B, C)
                p3 = closest_point_on_segment(candidate[idx], C, A)
                d1 = np.linalg.norm(candidate[idx] - p1)
                d2 = np.linalg.norm(candidate[idx] - p2)
                d3 = np.linalg.norm(candidate[idx] - p3)
                if d1 <= d2 and d1 <= d3:
                    candidate[idx] = p1
                elif d2 <= d1 and d2 <= d3:
                    candidate[idx] = p2
                else:
                    candidate[idx] = p3

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - best_score
            
            # Acceptance criterion
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                best_score = candidate_score
            
        improvements.append(max(0.0, best_score - current_min_area))
    
    # Return estimated resistance (1.0 - mean improvement)
    return 1.0 - np.mean(improvements)

# Detect stagnation type for targeted recovery
def detect_stagnation_type(points, improvement_history, stagnation_counter):
    """Analyze stagnation pattern to determine appropriate recovery strategy"""
    if stagnation_counter < 5:
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
    A, B, C = get_unit_triangle()
    for i in range(n):
        # Simple check: if any barycentric coordinate is very close to 0
        v0 = B - A
        v1 = C - A
        v2 = points[i] - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        if abs(denom) > 1e-10:
            v = (d11 * d20 - d01 * d21) / denom
            w = (d00 * d21 - d01 * d20) / denom
            u = 1.0 - v - w
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

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Function to place points along an edge with resistance-adaptive spacing
    def place_along_edge(start, end, edge_type, num_points=3):
        points = []
        
        # Use resistance profile to determine optimal spacing
        profile = EDGE_RESISTANCE_PROFILES[edge_type]
        profile_normalized = profile / np.sum(profile)
        
        # Sample positions based on resistance profile (higher resistance = more likely to place points)
        cumulative = np.cumsum(profile_normalized)
        positions = []
        
        # Place points at positions with highest resistance scores
        for _ in range(num_points):
            # Sample based on resistance profile
            r = np.random.rand()
            idx = np.searchsorted(cumulative, r)
            t = idx / 99.0
            positions.append(t)
        
        # Sort positions for even spacing
        positions.sort()
        
        # Add small random perturbations to avoid perfect symmetry
        for i in range(len(positions)):
            if i > 0 and i < len(positions) - 1:
                positions[i] += np.random.uniform(-0.03, 0.03)
                positions[i] = max(0.05, min(0.95, positions[i]))
        
        for t in positions:
            point = (1-t) * start + t * end
            points.append(point)
            
        return points

    # Calculate resistance factor (0.0-1.0, 0=perfect resistance)
    def calculate_resistance_factor(current_min_area, target=0.0365):
        # Base resistance on historical performance
        return RESISTANCE_FACTOR

    # Generate interior points using Voronoi triangulation with resistance-aware selection
    def get_voronoi_interior_points(edge_points, resistance_factor):
        # Create Delaunay triangulation of edge points
        points = np.array(edge_points)
        tri = Delaunay(points)
        
        # Get Voronoi diagram
        vor = Voronoi(points)
        
        # Collect Voronoi vertices inside the triangle
        voronoi_candidates = []
        for point in vor.vertices:
            if is_inside_triangle(point, A, B, C):
                voronoi_candidates.append(point)
        
        # Determine how many interior points to generate based on resistance
        n_interior = max(2, min(4, int(3 + 2 * resistance_factor)))
        
        # If we have no candidates, generate random points
        if not voronoi_candidates:
            additional_points = []
            for _ in range(n_interior):
                r1, r2 = np.random.rand(), np.random.rand()
                point = (1 - np.sqrt(r1)) * A + np.sqrt(r1) * (1 - r2) * B + np.sqrt(r1) * r2 * C
                if is_inside_triangle(point, A, B, C):
                    additional_points.append(point)
            return additional_points
        
        # Calculate resistance-aware score for each candidate
        resistance_scores = []
        for p in voronoi_candidates:
            # Create temporary configuration with this point added
            temp_points = np.vstack([points, p])
            
            # Calculate area impact
            area_impact = get_smallest_triangle_area(temp_points)
            
            # Simulate lightweight opponent attack to estimate resistance
            resistance_score = simulate_opponent_attack(temp_points, num_trials=10)
            
            # Combine area impact and resistance (weighted toward resistance)
            combined_score = 0.6 * area_impact + 0.4 * resistance_score
            resistance_scores.append(combined_score)

        # Select points with highest resistance-aware scores
        if len(voronoi_candidates) > n_interior:
            indices = np.argsort(resistance_scores)[-n_interior:]
            interior_points = [voronoi_candidates[i] for i in indices]
        else:
            interior_points = voronoi_candidates

        # If we don't have enough points, generate additional ones using resistance-aware scoring
        if len(interior_points) < n_interior:
            needed = n_interior - len(interior_points)
            additional_points = []
            
            # Generate additional points in regions with highest resistance potential
            for _ in range(needed):
                max_score = -np.inf
                candidate = None
                
                # Sample potential locations
                for _ in range(50):
                    # Random point inside triangle
                    r1, r2 = np.random.rand(), np.random.rand()
                    point = (1 - np.sqrt(r1)) * A + np.sqrt(r1) * (1 - r2) * B + np.sqrt(r1) * r2 * C
                    
                    if not is_inside_triangle(point, A, B, C):
                        continue
                    
                    # Create temporary configuration
                    temp_points = np.vstack([points, point])
                    
                    # Calculate resistance-aware score
                    area_impact = get_smallest_triangle_area(temp_points)
                    resistance_score = simulate_opponent_attack(temp_points, num_trials=5)
                    combined_score = 0.6 * area_impact + 0.4 * resistance_score
                    
                    if combined_score > max_score:
                        max_score = combined_score
                        candidate = point
                
                if candidate is not None:
                    additional_points.append(candidate)
            
            interior_points.extend(additional_points)

        return interior_points

    # Calculate k-NN density for adaptive weighting
    def calculate_knn_density(points, k=3):
        n = points.shape[0]
        densities = np.zeros(n)
        
        # For each point, find distances to all others
        for i in range(n):
            distances = np.linalg.norm(points - points[i], axis=1)
            distances = np.sort(distances)
            # Skip the point itself (distance 0)
            kth_distance = distances[k] if k < n else distances[-1]
            # Density proportional to 1/(volume of k-NN sphere)
            densities[i] = 1.0 / (kth_distance ** 2 + 1e-10)
            
        return densities

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
        
        # IMPLEMENTED ADAPTIVE DENSITY-BASED WEIGHTING (REPLACED FIXED WEIGHTING)
        densities = calculate_knn_density(points, k=3)
        density_i = densities[i]
        density_j = densities[j]
        density_k = densities[k]
        
        # Adaptive density-based exponent p
        max_density = max(density_i, density_j, density_k)
        min_density = min(density_i, density_j, density_k)
        density_ratio = min(1.0, max(0.0, (max_density - min_density) / (max_density + 1e-10)))
        p = 1.0 + 2.0 * (1.0 - density_ratio)  # p ranges from 1.0 (dense) to 3.0 (sparse)
        
        weight_a = 1.0 / (dist_ab**p + dist_ca**p)
        weight_b = 1.0 / (dist_ab**p + dist_bc**p)
        weight_c = 1.0 / (dist_bc**p + dist_ca**p)
        
        grad_a = grad_a * weight_a
        grad_b = grad_b * weight_b
        grad_c = grad_c * weight_c

        # PRESERVE GRADIENT MAGNITUDE (REMOVED NORMALIZATION)
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
        
        # Inverted repulsion strength: stronger when resistance is poor
        repulsion_strength = 0.08 * (1.5 - 0.5 * RESISTANCE_FACTOR)
        threshold = 0.05 + 0.1 * RESISTANCE_FACTOR  # Adaptive threshold
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

    # Multi-chain annealing implementation for resistance-aware optimization
    def run_annealing_chain(initial_points, base_step, T0, T_decay_base, step_decay_base, min_ratio):
        best = initial_points.copy()
        best_score = get_smallest_triangle_area(best)
        best_resistance = 0.5  # Initialize resistance score
        
        # Adaptive number of rounds based on resistance (increased from previous)
        n_rounds = int(500 + 300 * RESISTANCE_FACTOR)
        T_decay = T_decay_base
        step_decay = step_decay_base

        # Track improvement history for adaptive cooling
        improvement_history = []
        stagnation_counter = 0
        # Reduced threshold for faster recovery
        stagnation_threshold = max(5, min(15, int(10 * (1 + 0.5 * RESISTANCE_FACTOR))))

        # Track gradient success rate for adaptive gradient usage
        gradient_success_history = []
        isotropic_success_history = []
        
        # Dynamic gradient usage based on success rate
        gradient_usage = 0.4 + 0.5 * RESISTANCE_FACTOR  # More gradient usage for better resistance

        # Adaptive triangle ratio starts higher and decreases during optimization
        triangle_ratio = 1.15
        triangle_ratio_decay = (1.05 / 1.15) ** (1.0 / n_rounds)

        for round_idx in range(n_rounds):
            # Detect and handle stagnation with targeted recovery
            stagnation_type = detect_stagnation_type(best, improvement_history, stagnation_counter)
            
            if stagnation_counter > stagnation_threshold:
                # Apply targeted recovery based on stagnation type
                if stagnation_type == 'clustering':
                    # For local clustering: selectively reset points in dense regions
                    n = best.shape[0]
                    distances = np.zeros((n, n))
                    for i in range(n):
                        for j in range(i+1, n):
                            distances[i,j] = distances[j,i] = np.linalg.norm(best[i] - best[j])
                    
                    # Find points with many close neighbors
                    close_threshold = 0.04  # Adjust based on problem scale
                    neighbor_counts = np.sum(distances < close_threshold, axis=1)
                    dense_indices = np.where(neighbor_counts > n//3)[0]
                    
                    if len(dense_indices) > 0:
                        # Perturb points in dense regions
                        for idx in dense_indices:
                            r = 0.04 * np.sqrt(np.random.rand())
                            theta = 2 * np.pi * np.random.rand()
                            perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                            best[idx] += perturbation
                            best[idx] = boundary_repulsion(best[idx], A, B, C)

                elif stagnation_type == 'plateau':
                    # For global plateau: increase exploration more aggressively
                    T_decay = min(0.9985, T_decay * 1.1)
                    step_decay = max(0.996, step_decay * 0.9)
                    
                    # Add moderate noise to all points
                    noise_scale = 0.015 * (1 + 0.7 * min(2, stagnation_counter / stagnation_threshold))
                    for i in range(len(best)):
                        best[i] += np.random.normal(0, noise_scale, size=2)
                        best[i] = boundary_repulsion(best[i], A, B, C)

                elif stagnation_type == 'boundary':
                    # For boundary confinement: encourage interior movement
                    T_decay = min(0.999, T_decay * 1.03)
                    step_decay = max(0.997, step_decay * 0.97)
                    
                    # Adaptive boundary push
                    for i in range(len(best)):
                        u, v, w = get_barycentric_coords(best[i], A, B, C)
                        
                        # If near boundary, push slightly inward
                        min_coord = min(u, v, w)
                        if min_coord < 0.05:
                            # Push strength proportional to confinement severity
                            push_strength = 0.07 * (1 - min_coord) * (1.5 - RESISTANCE_FACTOR)
                            
                            # Push away from the nearest boundary
                            if u < v and u < w:
                                # Near BC boundary, push toward A
                                best[i] += push_strength * (A - best[i])
                            elif v < u and v < w:
                                # Near AC boundary, push toward B
                                best[i] += push_strength * (B - best[i])
                            else:
                                # Near AB boundary, push toward C
                                best[i] += push_strength * (C - best[i])
                            
                            best[i] = boundary_repulsion(best[i], A, B, C)

                # Reset counters after recovery
                stagnation_counter = max(0, stagnation_counter - 8)
                improvement_history = improvement_history[-20:]

            T = T0 * (T_decay ** round_idx)
            current_step = base_step * (step_decay ** round_idx)
            
            # Update triangle ratio
            triangle_ratio = max(1.05, triangle_ratio * triangle_ratio_decay)

            # Get adaptive triangle indices based on current min_area
            triangle_indices = get_adaptive_triangle_indices(best, ratio=triangle_ratio)
            
            # Select random triangle from adaptive set
            if triangle_indices:
                chosen_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
            else:
                # Fallback: select random triangle
                n = len(best)
                i, j, k = np.random.choice(n, 3, replace=False)
                chosen_triangle = (i, j, k)
            
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

            # Ensure all points stay inside triangle using boundary repulsion with fallback
            for i in range(len(candidate)):
                candidate[i] = boundary_repulsion(candidate[i], A, B, C)

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - best_score
            
            # Simulate lightweight opponent attack to estimate resistance improvement
            resistance_improvement = simulate_opponent_attack(candidate, num_trials=5) - simulate_opponent_attack(best, num_trials=5)
            
            # Enhanced acceptance criterion that considers resistance
            resistance_weight = 0.3 * (1.0 - RESISTANCE_FACTOR)  # Focus more on resistance when it's poor
            resistance_delta = resistance_weight * resistance_improvement
            
            # Total delta combines area improvement and resistance improvement
            total_delta = delta + 0.01 * resistance_delta

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

            # Acceptance criterion that prioritizes resistance when quality is high
            if total_delta > 0 or np.random.rand() < np.exp(total_delta / T):
                best = candidate
                best_score = candidate_score
                if resistance_improvement > 0:
                    best_resistance += resistance_improvement

            # Update stagnation counter
            if delta <= 0:
                stagnation_counter += 1
            else:
                stagnation_counter = max(0, stagnation_counter - 1)

        return best, best_score

    # Strategic Heilbronn configuration for n=11 with resistance-adaptive spacing
    edge_points = []
    # AB edge: resistance-adaptive spacing
    edge_points.extend(place_along_edge(A, B, 'AB'))
    # BC edge: resistance-adaptive spacing
    edge_points.extend(place_along_edge(B, C, 'BC'))
    # CA edge: resistance-adaptive spacing
    edge_points.extend(place_along_edge(C, A, 'CA'))
    
    # Add adaptive interior points using resistance-aware Voronoi approach
    interior_points = get_voronoi_interior_points(edge_points, RESISTANCE_FACTOR)
    points = np.array(edge_points + interior_points)

    # Run multiple annealing chains with resistance-aware parameter tuning
    chains = []
    
    # Widen parameter ranges based on resistance
    base_step_min = 0.015 * (1.8 - 0.3 * RESISTANCE_FACTOR)
    base_step_max = 0.10 * (1.8 - 0.3 * RESISTANCE_FACTOR)
    T0_min = 0.007 * (1.8 - 0.3 * RESISTANCE_FACTOR)
    T0_max = 0.016 * (1.8 - 0.3 * RESISTANCE_FACTOR)
    T_decay_min = 0.996 * (0.8 + 0.2 * RESISTANCE_FACTOR)
    T_decay_max = 0.9985 * (0.8 + 0.2 * RESISTANCE_FACTOR)
    step_decay_min = 0.997 * (0.8 + 0.2 * RESISTANCE_FACTOR)
    step_decay_max = 0.9995 * (0.8 + 0.2 * RESISTANCE_FACTOR)

    # Use logarithmic spacing for better parameter coverage
    chain_count = max(5, min(8, int(4 + 4 * RESISTANCE_FACTOR)))
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
            min_ratio=0.01
        )
        chains.append((chain, score))
    
    # Select the best chain result
    best_chain = max(chains, key=lambda x: x[1])
    return best_chain[0]