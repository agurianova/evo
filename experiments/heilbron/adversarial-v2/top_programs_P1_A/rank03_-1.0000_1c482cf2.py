import numpy as np
import cma
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from itertools import combinations
from sklearn.cluster import DBSCAN

np.random.seed(42)

def barycentric_penalty(points, A, B, C, boundary_relaxation=0.0):
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
        if u < -boundary_relaxation: penalty += abs(u + boundary_relaxation)
        if v < -boundary_relaxation: penalty += abs(v + boundary_relaxation)
        if w < -boundary_relaxation: penalty += abs(w + boundary_relaxation)
        if u + v + w > 1 + boundary_relaxation: penalty += (u + v + w - 1 - boundary_relaxation)
        
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

def generate_diverse_initial_points(n, A, B, C, method='hybrid', 
                                    inner_scale=0.25, middle_scale=0.55, outer_scale=0.95,
                                    rotation_angle=0.0):
    """Generate n diverse points inside the triangle using different strategies"""
    points = np.zeros((n, 2))
    
    # Calculate triangle height for unit area
    height = (2 * 1.0) / np.linalg.norm(B - A)  # Area = 1 = (base * height)/2
    
    if method == 'heilbronn':
        # Create rotation matrix
        rot_matrix = np.array([
            [np.cos(rotation_angle), -np.sin(rotation_angle)],
            [np.sin(rotation_angle), np.cos(rotation_angle)]
        ])
        
        # Center of triangle
        center = (A + B + C) / 3
        
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
        
        # Apply rotation around center
        for i in range(len(all_points)):
            # Translate to origin, rotate, translate back
            vec = all_points[i] - center[:2]
            vec = rot_matrix @ vec
            all_points[i] = vec + center[:2]
        
        # Transform to match our triangle coordinates
        A_np = np.array(A)
        B_np = np.array(B)
        C_np = np.array(C)
        
        # Convert to barycentric and back to ensure inside triangle
        for i in range(11):
            x, y = all_points[i]
            all_points[i] = barycentric_project(np.array([x, y]), A_np, B_np, C_np)
        
        points = all_points
        
    elif method == 'hexagonal_lattice':
        # Generate hexagonal lattice points with adaptive spacing
        points = []
        
        # Calculate optimal spacing based on triangle dimensions
        base_length = np.linalg.norm(B - A)
        height = np.sqrt(3)/2 * base_length  # For equilateral triangle
        
        # Determine number of rows and points per row
        n_rows = int(np.sqrt(n * 2 / np.sqrt(3))) + 1
        points_per_row = [n_rows - i//2 for i in range(n_rows)]
        
        # Adjust total points to be 11
        total_points = sum(points_per_row)
        if total_points > n:
            # Remove extra points from the middle rows
            excess = total_points - n
            for i in range(1, n_rows-1):
                if excess <= 0: break
                points_per_row[i] -= 1
                excess -= 1

        # Generate hexagonal pattern
        y_spacing = height / (n_rows + 1)
        x_spacing = base_length / (max(points_per_row) + 1)
        
        for row in range(n_rows):
            num_in_row = points_per_row[row]
            y = (row + 1) * y_spacing
            
            # Start x position (centered)
            start_x = (base_length - (num_in_row - 1) * x_spacing) / 2
            
            for col in range(num_in_row):
                x = start_x + col * x_spacing
                # Convert to triangle coordinates (barycentric)
                bary_u = 1 - y/height
                bary_v = x/base_length * bary_u
                bary_w = bary_u - bary_v
                
                # Convert to Cartesian
                point = bary_u * A + bary_v * B + bary_w * C
                points.append(point)

        # Take only n points
        points = np.array(points[:n])
        
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
    
    # Try different initialization strategies
    initialization_methods = ['heilbronn', 'hexagonal_lattice', 'hybrid', 'sobol', 'random']
    
    # Track progress of each initialization method
    method_progress = {method: [] for method in initialization_methods}
    
    for method_idx, method in enumerate(initialization_methods):
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
            boundary_relaxation_phase = [True]  # Track if we're in boundary relaxation phase
            
            def objective(params, A, B, C):
                func_eval_count[0] += 1
                
                # Adaptive penalty weights - decay as optimization progresses
                improvement_rate = 0.01  # Default value
                if len(method_progress[method]) > 10:
                    improvement_rate = (method_progress[method][-1] - method_progress[method][-10]) / 10
                
                # Make decay rate adaptive based on improvement rate
                decay_factor = max(0.05, np.exp(-func_eval_count[0] / (3000 * max(0.1, improvement_rate))))
                boundary_penalty_weight = 100.0 * decay_factor
                collinearity_penalty_weight = 50.0 * decay_factor
                
                # Determine boundary relaxation (allow temporary boundary violations)
                boundary_relaxation = 0.0
                if boundary_relaxation_phase[0] and func_eval_count[0] < 5000:
                    # Allow temporary boundary violations with decreasing relaxation
                    # CHANGED: Exponential decay instead of linear to maintain boundary flexibility longer
                    boundary_relaxation = 0.12 * np.exp(-func_eval_count[0] / 10000)
                
                # Reshape params to (11, 2) points
                if len(params) == 26:  # Heilbronn method with scale parameters
                    points = params[:22].reshape((11, 2))
                    
                    # Extract and transform scale parameters
                    inner_scale_param = params[22]
                    middle_scale_param = params[23]
                    outer_scale_param = params[24]
                    rotation_param = params[25]
                    
                    # CHANGED: Wider parameter ranges to explore boundary regions
                    inner_scale = np.clip(inner_scale_param, 0.01, 0.8)
                    middle_scale = np.clip(middle_scale_param, 0.1, 0.9)
                    outer_scale = np.clip(outer_scale_param, 0.5, 1.1)
                    rotation_angle = rotation_param  # Radians, no clipping needed
                    
                    # Regenerate points with new scales
                    points = generate_diverse_initial_points(11, A, B, C, method='heilbronn', 
                                                          inner_scale=inner_scale, 
                                                          middle_scale=middle_scale, 
                                                          outer_scale=outer_scale,
                                                          rotation_angle=rotation_angle)
                else:
                    points = params.reshape((11, 2))
                
                # Check for duplicate points
                duplicate_penalty = 0.0
                for i in range(11):
                    for j in range(i+1, 11):
                        dist = np.linalg.norm(points[i] - points[j])
                        if dist < 1e-8:
                            duplicate_penalty += 1.0 / (dist + 1e-12)
                
                # Calculate boundary penalty with relaxation
                boundary_penalty = barycentric_penalty(points, A, B, C, boundary_relaxation)
                
                # Calculate collinearity penalty
                collinearity_penalty_val = collinearity_penalty(points)
                
                # Get smallest triangle area (we want to maximize this)
                min_area = get_smallest_triangle_area(points)
                
                # Total objective: we want to maximize min_area while minimizing penalties
                # For minimization (as required by CMA-ES), return negative min_area + penalties
                return -min_area + boundary_penalty_weight * boundary_penalty + \
                       collinearity_penalty_weight * collinearity_penalty_val + \
                       10000.0 * duplicate_penalty

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
            
            # CHANGED: Adaptive stagnation threshold with logarithmic growth instead of linear
            # Was: stagnation_threshold = min(300, max(50, int(es.countiter * 0.05)))
            stagnation_threshold = max(50, int(120 * np.log1p(es.countiter/150)))

            while not es.stop():
                # Get candidate solutions
                solutions = es.ask()
                
                # Evaluate each solution
                fitnesses = []
                min_areas = []
                for s in solutions:
                    # Extract points (handle different parameter lengths)
                    if len(s) == 26:
                        points = generate_diverse_initial_points(11, A, B, C, method='heilbronn', 
                                                              inner_scale=np.clip(s[22], 0.01, 0.8),
                                                              middle_scale=np.clip(s[23], 0.1, 0.9),
                                                              outer_scale=np.clip(s[24], 0.5, 1.1),
                                                              rotation_angle=s[25])
                    else:
                        points = s.reshape((11, 2))
                    
                    # Check if points are valid
                    if not is_inside_triangle(points, A, B, C):
                        fitnesses.append(1e10)  # Large penalty
                        min_areas.append(0.0)
                        continue
                        
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
                    # CHANGED: Relative threshold instead of fixed value
                    if recent_progress > 0.008 * best_min_area_run:
                        options['maxiter'] = min(15000, options['maxiter'] + 200)

                # Apply strategic perturbation if stuck in local optimum
                if no_improve_count > stagnation_threshold:
                    # Get the best solution
                    best_solution = solutions[current_best_idx]
                    
                    # Extract points (handle different parameter lengths)
                    if len(best_solution) == 26:
                        best_points_temp = generate_diverse_initial_points(11, A, B, C, method='heilbronn', 
                                                                        inner_scale=np.clip(best_solution[22], 0.01, 0.8),
                                                                        middle_scale=np.clip(best_solution[23], 0.1, 0.9),
                                                                        outer_scale=np.clip(best_solution[24], 0.5, 1.1),
                                                                        rotation_angle=best_solution[25])
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
                    
                    # Sort by area and take the smallest 25%
                    triangles.sort(key=lambda x: x[0])
                    n_small = max(1, len(triangles) // 4)
                    for _, i, j, k in triangles[:n_small]:
                        small_triangle_points.add(i)
                        small_triangle_points.add(j)
                        small_triangle_points.add(k)
                    
                    # CHANGED: Make DBSCAN eps adaptive to current point configuration
                    small_triangle_points = list(small_triangle_points)
                    if len(small_triangle_points) >= 4:  # Need at least 4 points for meaningful clustering
                        points_array = best_points_temp[small_triangle_points]
                        # Scale coordinates to make DBSCAN distance meaningful
                        points_scaled = (points_array - np.mean(points_array, axis=0)) / (np.std(points_array, axis=0) + 1e-10)
                        
                        # CHANGED: Adaptive eps calculation based on point distribution
                        # Calculate average minimum distance and maximum distance between points
                        all_dists = []
                        for i in range(len(points_scaled)):
                            for j in range(i+1, len(points_scaled)):
                                dist = np.linalg.norm(points_scaled[i] - points_scaled[j])
                                all_dists.append(dist)
                        if all_dists:
                            avg_min_dist = np.mean(np.sort(all_dists)[:max(1, len(all_dists)//5)])
                            max_dist = np.max(all_dists)
                            eps = 0.25 * (avg_min_dist / max_dist)
                        else:
                            eps = 0.3  # Fallback value
                        
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
                            
                            # CHANGED: Inverse linear scaling instead of inverse sqrt for cluster perturbation
                            magnitude = adaptive_perturbation / max(1, len(cluster_indices))
                            
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
                                # CHANGED: Inverse linear scaling instead of inverse sqrt
                                magnitude = adaptive_perturbation / max(1, len(small_triangle_points))
                                perturbation = np.random.normal(0, magnitude, size=2)
                                if len(perturbed_solution) == 26:
                                    # For Heilbronn method, perturb the scale parameters
                                    perturbed_solution[22:] += np.random.normal(0, 0.1, size=4)
                                else:
                                    perturbed_solution[idx*2:idx*2+2] += perturbation
                    else:
                        # Not enough points for clustering, do standard perturbation
                        perturbed_solution = best_solution.copy()
                        for idx in small_triangle_points:
                            adaptive_perturbation = 0.04 * (1 + no_improve_count / stagnation_threshold)
                            # CHANGED: Inverse linear scaling instead of inverse sqrt
                            magnitude = adaptive_perturbation / max(1, len(small_triangle_points))
                            perturbation = np.random.normal(0, magnitude, size=2)
                            if len(perturbed_solution) == 26:
                                perturbed_solution[22:] += np.random.normal(0, 0.1, size=4)
                            else:
                                perturbed_solution[idx*2:idx*2+2] += perturbation
                    
                    # Project perturbed points back to triangle if needed
                    if len(perturbed_solution) == 26:
                        perturbed_points = generate_diverse_initial_points(11, A, B, C, method='heilbronn', 
                                                                        inner_scale=np.clip(perturbed_solution[22], 0.01, 0.8),
                                                                        middle_scale=np.clip(perturbed_solution[23], 0.1, 0.9),
                                                                        outer_scale=np.clip(perturbed_solution[24], 0.5, 1.1),
                                                                        rotation_angle=perturbed_solution[25])
                    else:
                        perturbed_points = perturbed_solution.reshape((11, 2))
                        for i in range(11):
                            if not is_inside_triangle(perturbed_points[i], A, B, C):
                                perturbed_points[i] = barycentric_project(perturbed_points[i], A, B, C)
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
                
                # Periodic display for debugging
                if es.countiter % 100 == 0:
                    print(f"Iteration {es.countiter}, Best min area: {best_min_area_run:.6f}")

                # CHANGED: Update adaptive stagnation threshold with logarithmic growth
                stagnation_threshold = max(50, int(120 * np.log1p(es.countiter/150)))

            # Get the best solution from this run
            optimized_params = es.best.x
            
            # Extract points (handle different parameter lengths)
            if len(optimized_params) == 26:
                optimized_points = generate_diverse_initial_points(11, A, B, C, method='heilbronn', 
                                                                  inner_scale=np.clip(optimized_params[22], 0.01, 0.8),
                                                                  middle_scale=np.clip(optimized_params[23], 0.1, 0.9),
                                                                  outer_scale=np.clip(optimized_params[24], 0.5, 1.1),
                                                                  rotation_angle=optimized_params[25])
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