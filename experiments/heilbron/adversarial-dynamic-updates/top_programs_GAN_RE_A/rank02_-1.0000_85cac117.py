import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
from scipy.spatial import Voronoi

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Calculate centroid of the triangle
    centroid = (A + B + C) / 3
    
    # Generate Fibonacci sequence for irregular spacing
    def fibonacci_spacing(n):
        fib = [1, 1]
        while len(fib) < n:
            fib.append(fib[-1] + fib[-2])
        return np.array(fib[:n]) / fib[-1]
    
    # Adaptive edge point distribution (2-4 points per edge)
    def distribute_edge_points(start, end):
        # Randomly choose number of points (2-4)
        n_points = np.random.randint(2, 5)
        
        # Use Fibonacci sequence for irregular spacing
        t_values = fibonacci_spacing(n_points + 2)[1:-1]  # Skip first and last
        
        points = []
        for t in t_values:
            point = (1-t) * start + t * end
            points.append(point)
        return points
    
    # Place points along edges with adaptive distribution
    edge_points = []
    # AB edge
    edge_points.extend(distribute_edge_points(A, B))
    # BC edge
    edge_points.extend(distribute_edge_points(B, C))
    # CA edge
    edge_points.extend(distribute_edge_points(C, A))
    
    # Ensure we have exactly 8 edge points (since we need 11 total with 3 interior)
    while len(edge_points) > 8:
        # Remove random point if we have too many
        idx = np.random.randint(len(edge_points))
        edge_points.pop(idx)
    while len(edge_points) < 8:
        # Add point to the edge with fewest points
        counts = [len(edge_points[:3]), len(edge_points[3:6]), len(edge_points[6:])]  # Rough estimate
        edge_idx = np.argmin(counts)
        if edge_idx == 0:
            new_points = distribute_edge_points(A, B)
        elif edge_idx == 1:
            new_points = distribute_edge_points(B, C)
        else:
            new_points = distribute_edge_points(C, A)
        # Add one new point
        edge_points.append(new_points[0])

    # Function to calculate barycentric coordinates
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
        v = (d11 * d20 - d01 * d21) / (denom + 1e-10)
        w = (d00 * d21 - d01 * d20) / (denom + 1e-10)
        u = 1 - v - w
        return u, v, w

    # Soft boundary repulsion function with adaptive threshold
    def apply_boundary_repulsion(point, A, B, C, current_min_area=0.0):
        u, v, w = get_barycentric_coords(point, A, B, C)
        
        # Adaptive threshold based on current min_area
        difficulty_factor = max(0.0, min(1.0, 1.0 - current_min_area / 0.0365))
        threshold = 0.1 + 0.3 * (1.0 - difficulty_factor)
        
        # Calculate distance to each edge
        dist_to_AB = u
        dist_to_BC = v
        dist_to_CA = w
        
        # Apply repulsion force proportional to 1/(distance + epsilon)
        repulsion = np.zeros(2)
        epsilon = 0.01
        
        # Direction away from AB edge
        if dist_to_AB < threshold:
            normal_AB = np.array([0, 1])  # For flat-bottomed triangle
            repulsion += normal_AB * (1 / (dist_to_AB + epsilon))
        
        # Direction away from BC edge
        if dist_to_BC < threshold:
            # BC edge has slope -√3
            normal_BC = np.array([np.sqrt(3)/2, 0.5])
            repulsion += normal_BC * (1 / (dist_to_BC + epsilon))

        # Direction away from CA edge
        if dist_to_CA < threshold:
            # CA edge has slope √3
            normal_CA = np.array([-np.sqrt(3)/2, 0.5])
            repulsion += normal_CA * (1 / (dist_to_CA + epsilon))

        # Normalize and scale repulsion
        if np.linalg.norm(repulsion) > 1e-10:
            repulsion = repulsion / np.linalg.norm(repulsion) * 0.005
            
        return point + repulsion

    # Calculate area gradient for a triangle with improved weighting
    def calculate_area_gradient(points, i, j, k):
        a, b, c = points[i], points[j], points[k]
        
        # Area = 0.5 * |(b-a) × (c-a)|
        # Partial derivatives:
        # dA/da = -0.5 * ((b_y - c_y), (c_x - b_x))
        # dA/db = -0.5 * ((c_y - a_y), (a_x - c_x))
        # dA/dc = -0.5 * ((a_y - b_y), (b_x - a_x))
        
        grad_a = np.array([-(b[1] - c[1]), b[0] - c[0]]) * 0.5
        grad_b = np.array([-(c[1] - a[1]), c[0] - a[0]]) * 0.5
        grad_c = np.array([-(a[1] - b[1]), a[0] - b[0]]) * 0.5
        
        # Weight gradients by inverse distance sum (more stable than product)
        dist_ab = max(1e-10, np.linalg.norm(a - b))
        dist_ac = max(1e-10, np.linalg.norm(a - c))
        dist_bc = max(1e-10, np.linalg.norm(b - c))
        
        weight_a = 1.0 / (dist_ab + dist_ac)
        weight_b = 1.0 / (dist_ab + dist_bc)
        weight_c = 1.0 / (dist_ac + dist_bc)
        
        grad_a = grad_a * weight_a
        grad_b = grad_b * weight_b
        grad_c = grad_c * weight_c

        return grad_a, grad_b, grad_c

    # Function to get adaptive triangle indices based on current min_area
    def get_adaptive_triangle_indices(points, min_area):
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
            
        # Calculate difficulty factor
        difficulty_factor = max(0.0, min(1.0, 1.0 - min_area / 0.0365))
        # Include triangles up to (1.0 + 0.1 * difficulty_factor) * min_area
        threshold = (1.0 + 0.1 * difficulty_factor) * min_area
        
        # Get all triangles below threshold
        relevant_indices = [idx for area, idx in zip(areas, indices) if area <= threshold]
        
        # If none found (shouldn't happen), return top 3
        if not relevant_indices:
            sorted_indices = [idx for _, idx in sorted(zip(areas, indices))]
            return sorted_indices[:3]
        
        return relevant_indices

    # Place interior points using Voronoi diagram to find largest empty spaces
    def place_interior_points(edge_points, A, B, C):
        # Start with edge points
        all_points = np.array(edge_points)
        
        # Create a larger bounding box for Voronoi
        points_expanded = np.vstack([all_points, A, B, C])
        
        # Compute Voronoi diagram
        vor = Voronoi(points_expanded)
        
        # Find regions that are inside our triangle
        valid_regions = []
        for i, region in enumerate(vor.regions):
            if not region or -1 in region:
                continue
            
            # Check if the region is bounded and inside our triangle
            polygon = vor.vertices[region]
            center = np.mean(polygon, axis=0)
            
            if is_inside_triangle(center, A, B, C):
                # Calculate area of the Voronoi cell
                area = 0
                n = len(polygon)
                for j in range(n):
                    k = (j + 1) % n
n                    area += polygon[j, 0] * polygon[k, 1] - polygon[k, 0] * polygon[j, 1]
                area = abs(area) / 2
                valid_regions.append((i, area, center))
        
        # Sort by area (largest first)
        valid_regions.sort(key=lambda x: x[1], reverse=True)
        
        # Take top 3 largest regions (we need 3 interior points for 11 total)
        interior_points = []
        for i in range(min(3, len(valid_regions))):
            interior_points.append(valid_regions[i][2])
        
        # If we don't have enough points, add random points inside the triangle
        while len(interior_points) < 3:
            # Generate random point using barycentric coordinates
            u, v = np.random.rand(), np.random.rand()
            if u + v > 1:
                u, v = 1 - u, 1 - v
            w = 1 - u - v
            point = u * A + v * B + w * C
            interior_points.append(point)
        
        return interior_points

    # Get interior points using Voronoi method
    interior_points = place_interior_points(edge_points, A, B, C)
    
    # Convert to numpy array
    points = np.array(edge_points + interior_points)
    
    # Multi-chain annealing approach with adaptive parameters
    def multi_chain_annealing(points, n_chains=3):
        chains = []
        
        # Calculate initial min area to adapt parameters
        initial_min_area = get_smallest_triangle_area(points)
        difficulty_factor = max(0.1, 1.0 - initial_min_area / 0.0365)
        
        for chain_idx in range(n_chains):
            # Parameterize based on chain index and difficulty
            if chain_idx == 0:  # Conservative chain
                T0 = 0.008 * (0.5 + 0.5 * difficulty_factor)
                base_step = 0.01 + 0.01 * difficulty_factor
                T_decay = 0.9975
                step_decay = 0.9985
            elif chain_idx == 1:  # Balanced chain
                T0 = 0.01 * (0.7 + 0.3 * difficulty_factor)
                base_step = 0.01 + 0.04 * difficulty_factor
                T_decay = 0.9978
                step_decay = 0.9988
            else:  # Aggressive chain
                T0 = 0.012 * (0.8 + 0.2 * difficulty_factor)
                base_step = 0.01 + 0.07 * difficulty_factor
                T_decay = 0.998
                step_decay = 0.999

            current = points.copy()
            current_score = get_smallest_triangle_area(current)
            best = current.copy()
            best_score = current_score

            n_rounds = int(200 + 300 * difficulty_factor)
            
            # Track improvement history for adaptive cooling
            improvement_history = []
            stagnation_counter = 0
            stagnation_threshold = max(15, min(30, int(20 * (1 + 0.5 * difficulty_factor))))

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
                
                # Partial reset with noise injection if stuck for too long
                if stagnation_counter > stagnation_threshold:
                    # Partial reset instead of full reset
                    T_decay = (T_decay + 0.9975 + 0.0005 * chain_idx) / 2
                    step_decay = (step_decay + 0.9985 + 0.0003 * chain_idx) / 2
                    
                    # Add adaptive Gaussian noise
                    noise_scale = 0.005 * (1.0 + 0.5 * stagnation_counter / stagnation_threshold)
                    for i in range(len(best)):
                        best[i] += np.random.normal(0, noise_scale, size=2)
                        if not is_inside_triangle(best[i], A, B, C):
                            u, v, w = get_barycentric_coords(best[i], A, B, C)
                            u, v, w = max(0, u), max(0, v), max(0, w)
                            total = u + v + w
                            if total > 0:
                                u, v, w = u/total, v/total, w/total
                            else:
                                u, v, w = 1/3, 1/3, 1/3
                            best[i] = u * A + v * B + w * C
                    
                    stagnation_counter = max(0, stagnation_counter - 5)
                    improvement_history = improvement_history[-20:]

                T = T0 * (T_decay ** round_idx)
                current_step = base_step * (step_decay ** round_idx)
                
                # Get current min area for adaptive triangle selection
                current_min_area = get_smallest_triangle_area(current)
                
                # Get adaptive triangle indices
                triangle_indices = get_adaptive_triangle_indices(current, current_min_area)
                
                # Select a random triangle from the relevant ones
                if triangle_indices:
                    chosen_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
                else:
                    chosen_triangle = (0, 1, 2)

                # Calculate dynamic gradient ratio (50/50 → 90/10)
                progress = min(1.0, round_idx / n_rounds)
                gradient_ratio = 0.5 + 0.4 * progress
                
                candidate = current.copy()
                if np.random.rand() < gradient_ratio:
                    # Use gradient information for more targeted improvements
                    grad_i, grad_j, grad_k = calculate_area_gradient(current, *chosen_triangle)
                    
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
                    # Random perturbation (fallback)
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

                # Apply boundary repulsion with adaptive threshold
                for i in range(len(candidate)):
                    candidate[i] = apply_boundary_repulsion(candidate[i], A, B, C, current_min_area)

                # Ensure all points stay inside triangle
                for i in range(len(candidate)):
                    if not is_inside_triangle(candidate[i], A, B, C):
                        # Fallback to barycentric projection if repulsion failed
                        u, v, w = get_barycentric_coords(candidate[i], A, B, C)
                        u, v, w = max(0, u), max(0, v), max(0, w)
                        total = u + v + w
                        if total > 0:
                            u, v, w = u/total, v/total, w/total
                        else:
                            u, v, w = 1/3, 1/3, 1/3
                        candidate[i] = u * A + v * B + w * C

                candidate_score = get_smallest_triangle_area(candidate)
                
                # Track improvements for adaptive cooling
                if candidate_score > current_score:
                    improvement_history.append(candidate_score - current_score)
                    if len(improvement_history) > 50:
                        improvement_history.pop(0)

                # Acceptance criterion
                if candidate_score > best_score:
                    best = candidate.copy()
                    best_score = candidate_score
                
                delta = candidate_score - current_score
                if delta > 0 or np.random.rand() < np.exp(delta / (T + 1e-10)):
                    current = candidate
                    current_score = candidate_score

            chains.append((best, best_score))
        
        # Select the best chain result
        best_chain = max(chains, key=lambda x: x[1])
        return best_chain[0]

    # Apply multi-chain annealing to harden against opponent strategies
    points = multi_chain_annealing(points)

    return points