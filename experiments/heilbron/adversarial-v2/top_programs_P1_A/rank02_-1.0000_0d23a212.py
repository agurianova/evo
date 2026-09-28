import numpy as np
import cma
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from itertools import combinations
from sklearn.cluster import DBSCAN
from scipy.spatial import distance_matrix

np.random.seed(42)

def barycentric_penalty(points, A, B, C):
    """Calculate penalty for points outside the triangle using barycentric coordinates"""
    n = points.shape[0]
    total_penalty = 0.0
    
    for i in range(n):
        point = points[i]
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
            # Degenerate triangle, add large penalty
            return 1e10
            
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w
        
        # Penalty for negative coordinates or sum > 1
        penalty = 0.0
        if u < 0: penalty += abs(u)
        if v < 0: penalty += abs(v)
        if w < 0: penalty += abs(w)
        if u + v + w > 1: penalty += (u + v + w - 1)
        
        total_penalty += penalty
    
    return total_penalty

def collinearity_penalty(points, min_area_threshold=1e-5):
    """Calculate penalty for near-collinear points"""
    n = points.shape[0]
    total_penalty = 0.0
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                ax, ay = points[i]
                bx, by = points[j]
                cx, cy = points[k]
                area = 0.5 * abs((bx-ax)*(cy-ay) - (cx-ax)*(by-ay))
                
                # If area is very small, add penalty proportional to 1/area
                if area < min_area_threshold:
                    total_penalty += (min_area_threshold - area) ** 2
    
    return total_penalty

def barycentric_project(point, A, B, C):
    """Project point to triangle using barycentric coordinates"""
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
        return A.copy()
        
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    
    # Clamp to triangle
    if u < 0:
        u, v, w = 0, v/(v+w), w/(v+w)
    if v < 0:
        u, v, w = u/(u+w), 0, w/(u+w)
    if w < 0:
        u, v, w = u/(u+v), v/(u+v), 0
    if u + v + w > 1:
        total = u + v + w
        u, v, w = u/total, v/total, w/total
        
    return u * A + v * B + w * C

def calculate_boundary_distances(points, A, B, C):
    """Calculate distance from each point to the nearest triangle boundary"""
    distances = np.zeros(len(points))
    
    # Edge vectors
    AB = B - A
    BC = C - B
    CA = A - C
    
    # Edge lengths
    len_AB = np.linalg.norm(AB)
    len_BC = np.linalg.norm(BC)
    len_CA = np.linalg.norm(CA)
    
    for i, point in enumerate(points):
        # Distance to AB
        dist_AB = np.abs(np.cross(AB, point - A)) / len_AB
        # Distance to BC
        dist_BC = np.abs(np.cross(BC, point - B)) / len_BC
        # Distance to CA
        dist_CA = np.abs(np.cross(CA, point - C)) / len_CA
        
        distances[i] = min(dist_AB, dist_BC, dist_CA)
    
    return distances

def adaptive_boundary_penalty(points, A, B, C, target_distance=0.02):
    """Penalty that encourages points to be near boundary but doesn't prohibit interior points"""
    distances = calculate_boundary_distances(points, A, B, C)
    penalty = 0.0
    
    for d in distances:
        # Encourage points to be within target_distance of boundary
        if d > target_distance:
            penalty += (d - target_distance) ** 2
    
    return penalty

def generate_diverse_initial_points(n, A, B, C, method='hybrid', inner_scale=0.25, middle_scale=0.55, outer_scale=0.95, rotation=0.0):
    """Generate n diverse points inside the triangle using different strategies"""
    points = np.zeros((n, 2))
    
    # Calculate rotation matrix if needed
    rotation_rad = np.radians(rotation)
    cos_rot = np.cos(rotation_rad)
    sin_rot = np.sin(rotation_rad)
    rotation_matrix = np.array([[cos_rot, -sin_rot], [sin_rot, cos_rot]])
    
    if method == 'heilbronn':
        # Calculate triangle height for unit area
        height = (2 * 1.0) / np.linalg.norm(B - A)  # Area = 1 = (base * height)/2
        
        # Inner triangle (scaled down)
        inner_points = np.array([
            [0.5, 0.2 * height * inner_scale],
            [0.5 - 0.433 * inner_scale, 0.2 * height * inner_scale + 0.75 * height * inner_scale],
            [0.5 + 0.433 * inner_scale, 0.2 * height * inner_scale + 0.75 * height * inner_scale]
        ])
        
        # Middle ring (4 points)
        middle_points = np.array([
            [0.5, 0.2 * height * middle_scale],
            [0.5 - 0.433 * middle_scale, 0.2 * height * middle_scale + 0.75 * height * middle_scale],
            [0.5 + 0.433 * middle_scale, 0.2 * height * middle_scale + 0.75 * height * middle_scale],
            [0.5, 0.2 * height * middle_scale + height * middle_scale]
        ])
        
        # Outer ring (4 points)
        outer_points = np.array([
            [0.5, 0],
            [0, 0],
            [1, 0],
            [0.5, height]
        ]) * outer_scale
        
        # Combine and adjust to fit within unit triangle
        all_points = np.vstack([inner_points, middle_points, outer_points[:4]])
        
        # Apply rotation around triangle centroid
        centroid = np.array([0.5, height / 2])
        for i in range(len(all_points)):
            all_points[i] = centroid + np.dot(rotation_matrix, (all_points[i] - centroid))
        
        # Transform to match our triangle coordinates
        A_np = np.array(A)
        B_np = np.array(B)
        C_np = np.array(C)
        
        # Convert to barycentric and back to ensure inside triangle
        for i in range(11):
            x, y = all_points[i]
            all_points[i] = barycentric_project(np.array([x, y]), A_np, B_np, C_np)
        
        points = all_points
        
    else:
        # Keep existing methods but with barycentric projection
        if method == 'hybrid':
            # Mix of grid-based and random points
            grid_size = int(np.sqrt(n))
            count = 0
            
            # Grid points
            for i in range(grid_size):
                for j in range(grid_size):
                    if count >= n:
                        break
                    u = i / (grid_size - 1) if grid_size > 1 else 0.5
                    v = j / (grid_size - 1) * (1 - u) if grid_size > 1 else 0.5 * (1 - u)
                    w = 1 - u - v
                    points[count] = barycentric_project(u * A + v * B + w * C, A, B, C)
                    count += 1
            
            # Random points to fill remaining
            while count < n:
                r = np.random.rand(2)
                u, v = np.sort(r)
                bary = np.array([u, v - u, 1 - v])
                np.random.shuffle(bary)
                points[count] = barycentric_project(bary[0] * A + bary[1] * B + bary[2] * C, A, B, C)
                count += 1
                
        elif method == 'sobol':
            # Use Sobol sequence for low-discrepancy sampling
            try:
                from scipy.stats import qmc
                sampler = qmc.Sobol(d=2, scramble=False)
                samples = sampler.random(n=n)
                
                for i in range(n):
                    u, v = samples[i]
                    if u + v > 1:
                        u, v = 1 - u, 1 - v
                    w = 1 - u - v
                    points[i] = barycentric_project(u * A + v * B + w * C, A, B, C)
            except:
                # Fallback to random if Sobol not available
                for i in range(n):
                    r = np.random.rand(2)
                    u, v = np.sort(r)
                    bary = np.array([u, v - u, 1 - v])
                    np.random.shuffle(bary)
                    points[i] = barycentric_project(bary[0] * A + bary[1] * B + bary[2] * C, A, B, C)
                    
        else:  # 'random' or default
            # Generate random points using barycentric coordinates
            for i in range(n):
                r = np.random.rand(2)
                u, v = np.sort(r)
                bary = np.array([u, v - u, 1 - v])
                np.random.shuffle(bary)
                points[i] = barycentric_project(bary[0] * A + bary[1] * B + bary[2] * C, A, B, C)
    
    return points

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Generate multiple diverse starting points for multi-start optimization
    best_points = None
    best_min_area = -np.inf
    
    # Track progress of each initialization method
    method_progress = {method: [] for method in ['heilbronn', 'hybrid', 'sobol', 'random']}
    
    # Track min_area history for adaptive penalty decay
    min_area_history = []
    
    for method_idx, method in enumerate(['heilbronn', 'hybrid', 'sobol', 'random']):
        try:
            # Generate diverse initial points inside the triangle
            if method == 'heilbronn':
                # Use default scales for initial generation
                initial_points = generate_diverse_initial_points(11, A, B, C, method=method)
                # Add 4 extra parameters for scale factors and rotation
                initial_params = np.concatenate([initial_points.flatten(), np.array([0.0, 0.0, 0.0, 0.0])])
            else:
                initial_points = generate_diverse_initial_points(11, A, B, C, method=method)
                initial_params = initial_points.flatten()

            # Set up CMA-ES optimizer
            n_dim = 22 if method != 'heilbronn' else 26  # 11 points * 2 coordinates + 4 scale/rotation parameters
            popsize = max(80, int(8 + 6 * np.log(n_dim)))
            
            # Create function evaluation counter for adaptive penalties
            func_eval_count = [0]
            
            def objective(params, A, B, C):
                func_eval_count[0] += 1
                
                # Calculate adaptive decay rate based on recent progress
                # Track improvement rate for adaptive decay
                improvement_rate = 0.0
                if len(min_area_history) >= 50:
                    improvement_rate = (min_area_history[-1] - min_area_history[-50]) / 50
                
                # Adjust decay based on improvement rate
                decay_adjustment = 1.0 + 2.0 * max(0.0, 0.001 - improvement_rate)
                adaptive_decay_rate = 1500 * max(0.5, 1.0 - (best_min_area / 0.0365)) * decay_adjustment
                
                # Adaptive penalty weights - decay as optimization progresses
                decay_factor = max(0.05, np.exp(-func_eval_count[0] / adaptive_decay_rate))
                boundary_penalty_weight = 100.0 * decay_factor
                collinearity_penalty_weight = 50.0 * decay_factor
                
                # Reshape params to (11, 2) points
                if len(params) == 26:  # Heilbronn method with scale and rotation parameters
                    points = params[:22].reshape((11, 2))
                    
                    # Extract and transform scale parameters
                    inner_scale_param = params[22]
                    middle_scale_param = params[23]
                    outer_scale_param = params[24]
                    rotation_param = params[25]
                    
                    # ADAPTIVE RANGE EXPANSION: Expanded ranges based on current solution quality
                    progress = max(0.0, min(1.0, best_min_area / 0.0365))
                    inner_scale = 0.05 + (0.45 + 0.2 * progress) * (1 / (1 + np.exp(-inner_scale_param)))
                    middle_scale = 0.2 + (0.6 + 0.2 * progress) * (1 / (1 + np.exp(-middle_scale_param)))
                    outer_scale = 0.6 + (0.35 + 0.1 * progress) * (1 / (1 + np.exp(-outer_scale_param)))
                    
                    # IMPROVED ROTATION MAPPING: Full 360-degree coverage
                    rotation = 360.0 * (0.5 + np.arctan(rotation_param) / np.pi)
                    
                    # Regenerate points with new scales
                    points = generate_diverse_initial_points(11, A, B, C, method='heilbronn', 
                                                          inner_scale=inner_scale, 
                                                          middle_scale=middle_scale, 
                                                          outer_scale=outer_scale,
                                                          rotation=rotation)
                else:
                    points = params.reshape((11, 2))
                
                # Check for duplicate points
                duplicate_penalty = 0.0
                for i in range(11):
                    for j in range(i+1, 11):
                        dist = np.linalg.norm(points[i] - points[j])
                        if dist < 1e-8:
                            duplicate_penalty += 1.0 / (dist + 1e-12)
                
                # Calculate boundary penalty
                boundary_penalty = barycentric_penalty(points, A, B, C)
                
                # NEW SOFT BOUNDARY CONSTRAINT: Encourages boundary placement without forcing it
                soft_boundary_penalty = adaptive_boundary_penalty(points, A, B, C, target_distance=0.02)
                
                # Calculate collinearity penalty
                collinearity_penalty_val = collinearity_penalty(points)
                
                # Get smallest triangle area (we want to maximize this)
                min_area = get_smallest_triangle_area(points)
                
                # Track for adaptive decay
                min_area_history.append(min_area)
                if len(min_area_history) > 100:
                    min_area_history.pop(0)
                
                # Total objective: we want to maximize min_area while minimizing penalties
                # For minimization (as required by CMA-ES), return negative min_area + penalties
                return -min_area + boundary_penalty_weight * boundary_penalty + \
                       collinearity_penalty_weight * collinearity_penalty_val + \
                       10000.0 * duplicate_penalty + \
                       50.0 * decay_factor * soft_boundary_penalty

            # Instead of cma.fmin, use ask-and-tell interface for more control
            options = {
                'maxiter': 10000,
                'popsize': popsize,
                'verbose': -9,
                'seed': 42 + method_idx,
                'tolx': 1e-12,
                'tolfun': 1e-12
            }
            es = cma.CMAEvolutionStrategy(initial_params, 0.15, options)
            best_min_area_run = -np.inf
            no_improve_count = 0
            # Make stagnation threshold adaptive to optimization phase
            stagnation_threshold = max(50, min(300, es.countiter // 50))

            while not es.stop():
                # Get candidate solutions
                solutions = es.ask()
                
                # Evaluate each solution
                fitnesses = []
                min_areas = []
                for s in solutions:
                    # Extract points (handle different parameter lengths)
                    if len(s) == 26:
                        # ADAPTIVE RANGE EXPANSION: Use expanded ranges
                        progress = max(0.0, min(1.0, best_min_area / 0.0365))
                        inner_scale = 0.05 + (0.45 + 0.2 * progress) * (1 / (1 + np.exp(-s[22])))
                        middle_scale = 0.2 + (0.6 + 0.2 * progress) * (1 / (1 + np.exp(-s[23])))
                        outer_scale = 0.6 + (0.35 + 0.1 * progress) * (1 / (1 + np.exp(-s[24])))
                        rotation = 360.0 * (0.5 + np.arctan(s[25]) / np.pi)
                        
                        points = generate_diverse_initial_points(11, A, B, C, method='heilbronn', 
                                                              inner_scale=inner_scale, 
                                                              middle_scale=middle_scale, 
                                                              outer_scale=outer_scale,
                                                              rotation=rotation)
                    else:
                        points = s.reshape((11, 2))
                    
                    # Calculate min area (without penalties for tracking)
                    min_area = get_smallest_triangle_area(points)
                    min_areas.append(min_area)
                    
                    # Calculate objective with penalties
                    fitness = objective(s, A, B, C)
                    fitnesses.append(fitness)
                
                # Track best solution
                current_best_idx = np.argmin(fitnesses)
                current_best_min_area = min_areas[current_best_idx]
                
                if current_best_min_area > best_min_area_run:
                    best_min_area_run = current_best_min_area
                    no_improve_count = 0
                else:
                    no_improve_count += 1
                
                # Update method progress tracking
                method_progress[method].append(current_best_min_area)
                
                # Adaptive resource allocation: if this method is showing good progress, allocate more iterations
                if len(method_progress[method]) > 50:
                    recent_progress = method_progress[method][-1] - method_progress[method][-50]
                    if recent_progress > 0.0005:  # Significant progress
                        options['maxiter'] = min(15000, options['maxiter'] + 200)

                # Apply strategic perturbation if stuck in local optimum
                if no_improve_count > stagnation_threshold:
                    # Get the best solution
                    best_solution = solutions[current_best_idx]
                    
                    # Extract points (handle different parameter lengths)
                    if len(best_solution) == 26:
                        # ADAPTIVE RANGE EXPANSION: Use expanded ranges
                        progress = max(0.0, min(1.0, best_min_area / 0.0365))
                        inner_scale = 0.05 + (0.45 + 0.2 * progress) * (1 / (1 + np.exp(-best_solution[22])))
                        middle_scale = 0.2 + (0.6 + 0.2 * progress) * (1 / (1 + np.exp(-best_solution[23])))
                        outer_scale = 0.6 + (0.35 + 0.1 * progress) * (1 / (1 + np.exp(-best_solution[24])))
                        rotation = 360.0 * (0.5 + np.arctan(best_solution[25]) / np.pi)
                        
                        best_points_temp = generate_diverse_initial_points(11, A, B, C, method='heilbronn', 
                                                                        inner_scale=inner_scale, 
                                                                        middle_scale=middle_scale, 
                                                                        outer_scale=outer_scale,
                                                                        rotation=rotation)
                    else:
                        best_points_temp = best_solution.reshape((11, 2))
                    
                    # Identify points involved in small triangles
                    small_triangle_points = set()
                    triangles = []
                    for i, j, k in combinations(range(11), 3):
                        ax, ay = best_points_temp[i]
                        bx, by = best_points_temp[j]
                        cx, cy = best_points_temp[k]
                        area = 0.5 * abs((bx-ax)*(cy-ay) - (cx-ax)*(by-ay))
                        triangles.append((area, i, j, k))
                    
                    # Sort by area and take triangles within 15% of minimum area
                    triangles.sort(key=lambda x: x[0])
                    min_area = triangles[0][0]
                    threshold = min_area * 1.15
                    n_small = sum(1 for area, _, _, _ in triangles if area <= threshold)
                    n_small = max(1, n_small)
                    for _, i, j, k in triangles[:n_small]:
                        small_triangle_points.add(i)
                        small_triangle_points.add(j)
                        small_triangle_points.add(k)
                    
                    # Use DBSCAN to identify clusters of points in small triangles
                    small_triangle_points = list(small_triangle_points)
                    if len(small_triangle_points) >= 4:  # Need at least 4 points for meaningful clustering
                        points_array = best_points_temp[small_triangle_points]
                        # Scale coordinates to make DBSCAN distance meaningful
                        points_scaled = (points_array - np.mean(points_array, axis=0)) / (np.std(points_array, axis=0) + 1e-10)
                        
                        # ADAPTIVE EPS: Calculate using k-distance graph
                        k = max(2, min(len(points_scaled)-1, 4))
                        distances = []
                        for i in range(len(points_scaled)):
                            dists = np.linalg.norm(points_scaled - points_scaled[i], axis=1)
                            dists.sort()
                            distances.append(dists[k])
                        distances.sort()
                        # Use elbow point in k-distance graph as eps
                        elbow_idx = max(1, int(0.1 * len(distances)))
                        eps = distances[elbow_idx] * 1.2
                        
                        clustering = DBSCAN(eps=eps, min_samples=2).fit(points_scaled)
                        
                        # Create perturbed solution
                        perturbed_solution = best_solution.copy()
                        
                        # Perturb each cluster coherently
                        for cluster_id in set(clustering.labels_):
                            if cluster_id == -1:  # Skip noise points
                                continue
                                
                            cluster_indices = [small_triangle_points[i] for i in range(len(small_triangle_points)) 
                                              if clustering.labels_[i] == cluster_id]
                            
                            # Compute cluster centroid
                            centroid = np.mean(best_points_temp[cluster_indices], axis=0)
                            
                            # Adaptive perturbation magnitude based on stagnation
                            adaptive_perturbation = 0.04 * (1 + no_improve_count / stagnation_threshold)
                            magnitude = adaptive_perturbation / (np.sqrt(len(cluster_indices)) + 1e-6)
                            
                            # Perturb the entire cluster in the same direction
                            direction = np.random.normal(0, 1, size=2)
                            direction = direction / (np.linalg.norm(direction) + 1e-10)
                            
                            for idx in cluster_indices:
                                if len(perturbed_solution) == 26:
                                    # For Heilbronn method, we need to adjust the points directly
                                    # This is a bit tricky since the points are generated from parameters
                                    # Instead, we'll directly modify the generated points
                                    pass
                                else:
                                    perturbed_solution[idx*2:idx*2+2] += magnitude * direction
                        
                        # If we didn't use DBSCAN (or for Heilbronn method), do standard perturbation
                        if len(perturbed_solution) == 26 or len(set(clustering.labels_)) <= 1:
                            for idx in small_triangle_points:
                                adaptive_perturbation = 0.04 * (1 + no_improve_count / stagnation_threshold)
                                magnitude = adaptive_perturbation / (np.sqrt(1) + 1e-6)
                                perturbation = np.random.normal(0, magnitude, size=2)
                                if len(perturbed_solution) == 26:
                                    # For Heilbronn method, we can't directly modify points
                                    # Instead, we'll perturb the scale parameters
                                    perturbed_solution[22:] += np.random.normal(0, 0.1, size=4)
                                else:
                                    perturbed_solution[idx*2:idx*2+2] += perturbation
                    else:
                        # Not enough points for clustering, do standard perturbation
                        perturbed_solution = best_solution.copy()
                        for idx in small_triangle_points:
                            adaptive_perturbation = 0.04 * (1 + no_improve_count / stagnation_threshold)
                            magnitude = adaptive_perturbation / (np.sqrt(1) + 1e-6)
                            perturbation = np.random.normal(0, magnitude, size=2)
                            if len(perturbed_solution) == 26:
                                perturbed_solution[22:] += np.random.normal(0, 0.1, size=4)
                            else:
                                perturbed_solution[idx*2:idx*2+2] += perturbation
                    
                    # Project perturbed points back to triangle if needed
                    if len(perturbed_solution) == 26:
                        # ADAPTIVE RANGE EXPANSION: Use expanded ranges
                        progress = max(0.0, min(1.0, best_min_area / 0.0365))
                        inner_scale = 0.05 + (0.45 + 0.2 * progress) * (1 / (1 + np.exp(-perturbed_solution[22])))
                        middle_scale = 0.2 + (0.6 + 0.2 * progress) * (1 / (1 + np.exp(-perturbed_solution[23])))
                        outer_scale = 0.6 + (0.35 + 0.1 * progress) * (1 / (1 + np.exp(-perturbed_solution[24])))
                        rotation = 360.0 * (0.5 + np.arctan(perturbed_solution[25]) / np.pi)
                        
                        perturbed_points = generate_diverse_initial_points(11, A, B, C, method='heilbronn', 
                                                                        inner_scale=inner_scale, 
                                                                        middle_scale=middle_scale, 
                                                                        outer_scale=outer_scale,
                                                                        rotation=rotation)
                    else:
                        perturbed_points = perturbed_solution.reshape((11, 2))
                        
                        # Only project if necessary - let penalty handle it
                        for i in range(11):
                            if not is_inside_triangle(perturbed_points[i], A, B, C):
                                # Don't immediately project - let penalty handle it
                                pass
                        perturbed_solution = perturbed_points.flatten()
                    
                    # Evaluate perturbed solution
                    perturbed_min_area = get_smallest_triangle_area(perturbed_points)
                    perturbed_fitness = objective(perturbed_solution, A, B, C)
                    
                    # Replace worst solution with perturbed one if it's better
                    worst_idx = np.argmax(fitnesses)
                    if perturbed_fitness < fitnesses[worst_idx]:
                        solutions[worst_idx] = perturbed_solution
                        fitnesses[worst_idx] = perturbed_fitness
                        min_areas[worst_idx] = perturbed_min_area
                    
                    no_improve_count = 0  # Reset counter after perturbation

                # Update the optimizer
                es.tell(solutions, fitnesses)
                
                # Update adaptive stagnation threshold based on current iteration
                stagnation_threshold = max(50, min(300, es.countiter // 50))
                
                # Periodic display for debugging
                if es.countiter % 100 == 0:
                    print(f"Iteration {es.countiter}, Best min area: {best_min_area_run:.6f}")

            # Get the best solution from this run
            optimized_params = es.best.x
            
            # Extract points (handle different parameter lengths)
            if len(optimized_params) == 26:
                # ADAPTIVE RANGE EXPANSION: Use expanded ranges
                progress = max(0.0, min(1.0, best_min_area / 0.0365))
                inner_scale = 0.05 + (0.45 + 0.2 * progress) * (1 / (1 + np.exp(-optimized_params[22])))
                middle_scale = 0.2 + (0.6 + 0.2 * progress) * (1 / (1 + np.exp(-optimized_params[23])))
                outer_scale = 0.6 + (0.35 + 0.1 * progress) * (1 / (1 + np.exp(-optimized_params[24])))
                rotation = 360.0 * (0.5 + np.arctan(optimized_params[25]) / np.pi)
                
                optimized_points = generate_diverse_initial_points(11, A, B, C, method='heilbronn', 
                                                                  inner_scale=inner_scale, 
                                                                  middle_scale=middle_scale, 
                                                                  outer_scale=outer_scale,
                                                                  rotation=rotation)
            else:
                optimized_points = optimized_params.reshape((11, 2))
            
            # Calculate actual min area (without penalties)
            min_area = get_smallest_triangle_area(optimized_points)
            
            # Keep track of the best solution across all starts
            if min_area > best_min_area:
                best_min_area = min_area
                best_points = optimized_points.copy()
        except Exception as e:
            continue
    
    # Final validation
    if best_points is None or not is_inside_triangle(best_points, A, B, C):
        # Fallback: generate a grid-based configuration
        best_points = generate_diverse_initial_points(11, A, B, C, method='hybrid')
    
    # Additional safeguard: if points aren't distinct, perturb slightly
    for i in range(11):
        for j in range(i+1, 11):
            if np.allclose(best_points[i], best_points[j], atol=1e-8):
                best_points[j] += np.random.normal(0, 1e-6, size=2)
    
    return best_points