from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

# Global experience replay buffer (within entrypoint closure)
EXPERIENCE_BUFFER_SIZE = 25
experience_buffer = []


def entrypoint():
    A, B, C = get_unit_triangle()

    def tri_area(a, b, c):
        return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    def project_to_triangle(point):
        """Project point back into triangle using closest boundary point"""
        if is_inside_triangle(point, A, B, C):
            return point.copy()
        
        # Try all three edges
        projections = []
        edges = [(A, B), (B, C), (C, A)]
        
        for (p1, p2) in edges:
            v = p2 - p1
            w = point - p1
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 == 0:
                b = p1
            else:
                b = max(0, min(1, c1/c2))
                b = p1 + b * v
            
            dist = np.linalg.norm(point - b)
            projections.append((dist, b))
        
        # Return closest projection
        _, closest = min(projections, key=lambda x: x[0])
        return closest

    def calculate_gradient(points, critical_points=None, epsilon=1e-5):
        """Calculate numerical gradient only for specified critical points"""
        if critical_points is None:
            critical_points = list(range(len(points)))
            
        base_score = get_smallest_triangle_area(points)
        gradients = np.zeros_like(points)
        
        for i in critical_points:
            for dim in range(2):
                # Perturb point in positive direction
                points_plus = points.copy()
                points_plus[i, dim] += epsilon
                for j in range(len(points)):
                    points_plus[j] = project_to_triangle(points_plus[j])
                score_plus = get_smallest_triangle_area(points_plus)
                
                # Perturb point in negative direction
                points_minus = points.copy()
                points_minus[i, dim] -= epsilon
                for j in range(len(points)):
                    points_minus[j] = project_to_triangle(points_minus[j])
                score_minus = get_smallest_triangle_area(points_minus)
                
                # Central difference approximation
                gradients[i, dim] = (score_plus - score_minus) / (2 * epsilon)
        
        return gradients

    def improve(points: np.ndarray) -> np.ndarray:
        # Create parameter configuration dictionary for evolutionary optimization
        param_config = {
            'theoretical_max': 0.0365,
            'base_threshold': 1.5,
            'min_threshold': 1.1,
            'base_widen_factor': 0.05,
            'widen_difficulty_factor': 0.3,
            'base_reduction': 0.05,
            'min_blending': 0.1,
            'max_blending': 0.9,
            'stagnation_threshold': 200,
            'restart_base': 3,
            'restart_scale': 9,
            'initial_perturbation_base': 0.02,
            'initial_perturbation_scale': 0.06,
            'step_size_increase_base': 1.15,
            'step_size_increase_difficulty_factor': 0.15,
            'step_size_decrease_factor': 0.85,
            'cooling_factor': 0.98,
            'exponential_weight_base': 3.0,
            'exponential_weight_scale': 2.0,
            'orthogonal_direction_ratio': 0.7,
            'orthogonal_component_ratio': 0.3,
            'orthogonal_random_scale': 0.1,
            'max_step_size_base': 0.15,
            'max_step_size_difficulty_factor': 0.1,
            'stagnation_widen_threshold': 50,
            'stagnation_narrow_threshold': 5,
            'max_no_improve': 200,
            'max_iter': 500,
            'experience_kernel_width': 0.05,
            'experience_similarity_threshold': 0.12,
            'progress_window_size': 20,
            'local_search_iterations': 200,
            'local_search_step_size': 0.001
        }

        # Initial quality assessment to determine problem difficulty
        current_score = get_smallest_triangle_area(points)
        # Higher difficulty means harder to improve (closer to theoretical maximum)
        difficulty = 1.0 - (current_score / param_config['theoretical_max'])
        
        # Track progress window for improvement rate calculation
        progress_window = []
        
        # Use weighted experience replay with multiple similar experiences
        global experience_buffer
        if len(experience_buffer) > 0:
            # Find relevant experiences within difficulty threshold
            relevant_experiences = []
            for exp in experience_buffer:
                diff_diff = abs(exp[0] - difficulty)
                if diff_diff < param_config['experience_similarity_threshold']:
                    # Gaussian kernel weighting based on difficulty proximity
                    weight = np.exp(-(diff_diff ** 2) / (2 * param_config['experience_kernel_width'] ** 2))
                    relevant_experiences.append((exp, weight))
            
            if relevant_experiences:
                total_weight = sum(weight for _, weight in relevant_experiences)
                if total_weight > 0:
                    # Weighted average of relevant experiences
                    weighted_exp = {
                        'exponential_weight_factor': 0,
                        'orthogonal_direction_ratio': 0,
                        'orthogonal_component_ratio': 0
                    }
                    
                    for (exp, weight) in relevant_experiences:
                        _, params, _ = exp
                        w = weight / total_weight
                        weighted_exp['exponential_weight_factor'] += w * params['exponential_weight_factor']
                        weighted_exp['orthogonal_direction_ratio'] += w * params['orthogonal_direction_ratio']
                        weighted_exp['orthogonal_component_ratio'] += w * params['orthogonal_component_ratio']

                    # Adjust parameters toward weighted experience
                    param_config['exponential_weight_scale'] *= 1.0 + 0.2 * weighted_exp['exponential_weight_factor']
                    param_config['orthogonal_direction_ratio'] *= 0.9 + 0.2 * weighted_exp['orthogonal_direction_ratio']
                    param_config['orthogonal_component_ratio'] *= 1.1 - 0.2 * weighted_exp['orthogonal_component_ratio']

        # Adaptive parameters based on problem difficulty
        params = {
            'restart_count': max(3, min(12, int(param_config['restart_base'] + param_config['restart_scale'] * difficulty))),
            'initial_perturbation': param_config['initial_perturbation_base'] + 
                                  param_config['initial_perturbation_scale'] * (1.0 - difficulty),
            'step_size_increase_factor': param_config['step_size_increase_base'] + 
                                      param_config['step_size_increase_difficulty_factor'] * difficulty,
            'step_size_decrease_factor': param_config['step_size_decrease_factor'],
            'cooling_factor': param_config['cooling_factor'],
            'base_threshold': param_config['base_threshold'],
            'min_threshold': param_config['min_threshold'],
            # FIXED: Reversed relationship to INCREASE weighting with difficulty
            'exponential_weight_factor': param_config['exponential_weight_base'] + 
                                       param_config['exponential_weight_scale'] * difficulty,
            # DYNAMIC ORTHOGONAL RATIO BASED ON DIFFICULTY
            'orthogonal_ratio': 0.5 + 0.3 * difficulty
        }

        best_overall = points.copy()
        best_score_overall = current_score
        
        # Multiple restarts with adaptive parameters
        for restart in range(params['restart_count']):
            # Perturb current best solution for restart using Levy flight distribution
            # Levy flights provide heavy-tailed distribution for better exploration
            levy_scale = params['initial_perturbation']
            perturbation = levy_scale * np.random.standard_cauchy(2) * (0.9 ** restart)
            current = best_overall.copy()
            for i in range(11):
                current[i] += perturbation
                current[i] = project_to_triangle(current[i])
            
            current_score = get_smallest_triangle_area(current)
            best = current.copy()
            best_score = current_score
            
            step_size = 0.02
            initial_temp = 0.1
            max_iter = param_config['max_iter']
            max_no_improve = param_config['max_no_improve']
            no_improve_count = 0
            
            # Reset progress window for each restart
            progress_window = []
            
            for iter in range(max_iter):
                # Find ALL critical triangles with percentile-based threshold
                min_area = current_score
                areas_triplets = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            area = tri_area(current[i], current[j], current[k])
                            areas_triplets.append((area, (i, j, k)))
                
                # Sort areas for percentile calculation
                areas_triplets.sort(key=lambda x: x[0])
                areas = [area for area, _ in areas_triplets]
                
                # Calculate median area for percentile-based threshold
                n = len(areas)
                median_area = areas[n//2] if n > 0 else min_area
                
                # NEW: Percentile-based threshold - select triangles below (min_area + 0.2*(median_area - min_area))
                # This adapts to the actual area distribution rather than using arbitrary scaling factors
                threshold = min_area + 0.2 * (median_area - min_area)
                
                # NEW: Calculate improvement velocity for adaptive thresholding
                progress_window.append(current_score)
                if len(progress_window) > param_config['progress_window_size']:
                    progress_window.pop(0)
                
                # Calculate improvement velocity (delta min_area per iteration)
                if len(progress_window) >= 2:
                    min_window = min(progress_window)
                    max_window = max(progress_window)
                    window_iterations = len(progress_window)
                    
                    # Compute velocity as normalized improvement rate
                    improvement_velocity = (max_window - min_window) / window_iterations
                    # Normalize by theoretical max for consistent scaling
                    improvement_velocity /= param_config['theoretical_max']
                else:
                    improvement_velocity = 0.0

                # ADJUST THRESHOLD BASED ON IMPROVEMENT VELOCITY
                # If making good progress, narrow threshold to focus on smallest triangles
                # If stuck, widen threshold to explore more broadly
                velocity_factor = 1.0 - min(0.8, 5 * improvement_velocity)
                threshold = threshold * velocity_factor

                critical_triplets = [(area, triplet) for area, triplet in areas_triplets 
                                    if area < threshold and area > 1e-10]
                
                if not critical_triplets:
                    break

                # Identify critical points (those in critical triangles)
                critical_points_set = set()
                for _, triplet in critical_triplets:
                    critical_points_set.update(triplet)
                critical_points = list(critical_points_set)

                # Calculate weighted displacement with exponential prioritization and orthogonal components
                displacement_vectors = np.zeros((11, 2))
                point_weights = np.zeros(11)
                
                for area, triplet in critical_triplets:
                    i, j, k = triplet
                    # Exponential weighting for better prioritization of critical triangles
                    weight = np.exp(-params['exponential_weight_factor'] * (area - min_area) / (min_area + 1e-10))
                    
                    # For each point in the triplet, calculate direction to move
                    for idx in triplet:
                        others = [x for x in triplet if x != idx]
                        p0 = current[others[0]]
                        p1 = current[others[1]]
                        base_vector = p1 - p0
                        normal = np.array([-base_vector[1], base_vector[0]])
                        vec = current[idx] - p0
                        if np.dot(normal, vec) < 0:
                            normal = -normal
                        norm = np.linalg.norm(normal)
                        if norm > 1e-10:
                            normal = normal / norm
                            displacement_vectors[idx] += weight * normal
                            point_weights[idx] += weight

                # Normalize and apply displacements with orthogonal components
                candidate = current.copy()
                for idx in range(11):
                    if point_weights[idx] > 0:
                        direction = displacement_vectors[idx] / point_weights[idx]
                        
                        # DYNAMIC ORTHOGONAL RATIO BASED ON DIFFICULTY
                        orthogonal_ratio = params['orthogonal_ratio']
                        
                        # Add orthogonal random component
                        orthogonal = np.array([-direction[1], direction[0]])
                        random_component = np.random.normal(0, 0.3 * (1.0 - difficulty), 2)
                        orthogonal_component = orthogonal * (0.2 + 0.3 * (1.0 - difficulty))
                        
                        # Blended direction with dynamic orthogonal ratio
                        blended_direction = (orthogonal_ratio * direction + 
                                           (1 - orthogonal_ratio) * orthogonal_component + 
                                           0.1 * random_component)
                        blended_direction = blended_direction / np.linalg.norm(blended_direction)
                        
                        # Add some randomness to escape local minima
                        noise = np.random.normal(0, step_size/3, 2)
                        displacement = step_size * blended_direction + noise
                        candidate[idx] += displacement

                # Project all points back into triangle
                for idx in range(11):
                    candidate[idx] = project_to_triangle(candidate[idx])

                # Calculate gradient only for critical points to save computation
                gradient = calculate_gradient(candidate, critical_points=critical_points, epsilon=1e-4)
                
                # ENHANCED GRADIENT BLENDING BASED ON IMPROVEMENT VELOCITY
                # Direct relationship with observed progress
                blending_factor = 0.3 + 0.6 * min(1.0, 20 * improvement_velocity)
                blending_factor = max(param_config['min_blending'], min(param_config['max_blending'], blending_factor))

                # Blend gradient direction with current displacement approach
                for idx in range(11):
                    if np.linalg.norm(gradient[idx]) > 1e-5:
                        # Normalize and blend gradient direction
                        grad_dir = gradient[idx] / np.linalg.norm(gradient[idx])
                        candidate[idx] += blending_factor * step_size * grad_dir
                        candidate[idx] = project_to_triangle(candidate[idx])

                candidate_score = get_smallest_triangle_area(candidate)
                
                # Simulated annealing acceptance
                temp = initial_temp * (params['cooling_factor'] ** iter)
                if candidate_score > current_score:
                    accept = True
                else:
                    delta = current_score - candidate_score
                    if np.random.rand() < np.exp(-delta / temp):
                        accept = True
                    else:
                        accept = False

                if accept:
                    current = candidate
                    current_score = candidate_score
                    if candidate_score > best_score:
                        best = candidate
                        best_score = candidate_score
                        no_improve_count = 0
                    else:
                        # Reset counter if current solution improved (uphill move)
                        if candidate_score > current_score:
                            no_improve_count = 0
                        else:
                            no_improve_count += 1
                else:
                    no_improve_count += 1

                # PROGRESS-BASED STEP SIZE CONTROL WITHOUT OSCILLATIONS
                if improvement_velocity > 0.0001:
                    step_size *= 1.05  # Increase step size when making progress
                else:
                    step_size *= 0.95  # Decrease step size when stuck

                # MAKE STEP SIZE BOUNDS DIFFICULTY-DEPENDENT
                max_step_size = param_config['max_step_size_base'] + \
                              param_config['max_step_size_difficulty_factor'] * difficulty
                step_size = max(1e-5, min(step_size, max_step_size))

                # Stopping condition
                if no_improve_count >= max_no_improve:
                    break

            # Update overall best if this restart found a better solution
            if best_score > best_score_overall:
                best_overall = best.copy()
                best_score_overall = best_score

        # DEDICATED LOCAL SEARCH PHASE FOR FINAL REFINEMENT
        # This phase uses smaller step sizes and exhaustive analysis to squeeze out final improvements
        local_search_points = best_overall.copy()
        local_search_score = best_score_overall
        local_step_size = param_config['local_search_step_size']
        
        for local_iter in range(param_config['local_search_iterations']):
            # Find ALL triangles for exhaustive analysis
            min_area = get_smallest_triangle_area(local_search_points)
            areas_triplets = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = tri_area(local_search_points[i], local_search_points[j], local_search_points[k])
                        areas_triplets.append((area, (i, j, k)))
            
            # Sort to get smallest triangles
            areas_triplets.sort(key=lambda x: x[0])
            critical_triplets = areas_triplets[:max(3, min(10, len(areas_triplets)//5))]
            
            # Identify critical points
            critical_points_set = set()
            for _, triplet in critical_triplets:
                critical_points_set.update(triplet)
            critical_points = list(critical_points_set)

            # Calculate displacement vectors
n            displacement_vectors = np.zeros((11, 2))
            point_weights = np.zeros(11)
            
            for area, triplet in critical_triplets:
                i, j, k = triplet
                weight = 1.0 / (area + 1e-10)
                
                for idx in triplet:
                    others = [x for x in triplet if x != idx]
                    p0 = local_search_points[others[0]]
                    p1 = local_search_points[others[1]]
                    base_vector = p1 - p0
                    normal = np.array([-base_vector[1], base_vector[0]])
                    vec = local_search_points[idx] - p0
                    if np.dot(normal, vec) < 0:
                        normal = -normal
                    norm = np.linalg.norm(normal)
                    if norm > 1e-10:
                        normal = normal / norm
                        displacement_vectors[idx] += weight * normal
                        point_weights[idx] += weight

            # Apply small displacements for refinement
            candidate = local_search_points.copy()
            for idx in range(11):
                if point_weights[idx] > 0:
                    direction = displacement_vectors[idx] / point_weights[idx]
                    direction = direction / np.linalg.norm(direction)
                    candidate[idx] += local_step_size * direction
                    candidate[idx] = project_to_triangle(candidate[idx])

            candidate_score = get_smallest_triangle_area(candidate)
            
            if candidate_score > local_search_score:
                local_search_points = candidate
                local_search_score = candidate_score

        # Update best overall with local search results
        if local_search_score > best_score_overall:
            best_overall = local_search_points.copy()
            best_score_overall = local_search_score

        # Store experience for future reference
        improvement = best_score_overall - current_score
        if improvement > 0:
            # Store (difficulty, params, improvement) tuple
            experience_buffer.append((difficulty, {
                'exponential_weight_factor': params['exponential_weight_factor'],
                'orthogonal_direction_ratio': params['orthogonal_ratio'],
                'orthogonal_component_ratio': 1 - params['orthogonal_ratio']
            }, improvement))
            
            # Keep buffer size limited
            if len(experience_buffer) > EXPERIENCE_BUFFER_SIZE:
                experience_buffer.pop(0)

        return best_overall

    return improve