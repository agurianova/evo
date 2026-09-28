from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

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

    def calculate_gradient(points, critical_points=None, epsilon=1e-5, triangle_cache=None):
        """Calculate numerical gradient only for specified critical points with caching"""
        if critical_points is None:
            critical_points = list(range(len(points)))
            
        # Initialize cache if not provided
        if triangle_cache is None:
            triangle_cache = {}
            # Precompute all triangle areas
            for i in range(len(points)):
                for j in range(i+1, len(points)):
                    for k in range(j+1, len(points)):
                        area = tri_area(points[i], points[j], points[k])
                        triangle_cache[(i, j, k)] = area
        
        # Get base score from cache
        min_area = min(triangle_cache.values())
        
        gradients = np.zeros_like(points)
        
        for i in critical_points:
            for dim in range(2):
                # Create a copy of the cache for this perturbation
                perturbed_cache = triangle_cache.copy()
                
                # Perturb point in positive direction
                points_plus = points.copy()
                points_plus[i, dim] += epsilon
                for j in range(len(points)):
                    points_plus[j] = project_to_triangle(points_plus[j])
                
                # Update only triangles involving the perturbed point
                for j in range(len(points)):
                    if j == i:
                        continue
                    for k in range(j+1, len(points)):
                        if k == i:
                            continue
                        # Update triangle (min(i,j,k), med, max)
                        idx = tuple(sorted([i, j, k]))
                        perturbed_cache[idx] = tri_area(points_plus[idx[0]], points_plus[idx[1]], points_plus[idx[2]])
                
                score_plus = min(perturbed_cache.values())
                
                # Perturb point in negative direction
                points_minus = points.copy()
                points_minus[i, dim] -= epsilon
                for j in range(len(points)):
                    points_minus[j] = project_to_triangle(points_minus[j])
                
                # Update only triangles involving the perturbed point
                for j in range(len(points)):
                    if j == i:
                        continue
                    for k in range(j+1, len(points)):
                        if k == i:
                            continue
                        idx = tuple(sorted([i, j, k]))
                        perturbed_cache[idx] = tri_area(points_minus[idx[0]], points_minus[idx[1]], points_minus[idx[2]])
                
                score_minus = min(perturbed_cache.values())
                
                # Central difference approximation
                gradients[i, dim] = (score_plus - score_minus) / (2 * epsilon)
        
        return gradients

    def improve(points: np.ndarray) -> np.ndarray:
        # Parameter dictionary for evolutionary optimization
        param_dict = {
            'theoretical_max': 0.0365,
            'gradient_blending_max': 0.9,
            'exponential_weight_base': 3.0,
            'exponential_weight_scale': 2.0,
            'orthogonal_dir_ratio': 0.7,
            'orthogonal_orth_ratio': 0.3,
            'stagnation_threshold_base': 50,
            'step_size_increase_factor': 1.15,
            'step_size_decrease_factor': 0.85,
            'min_threshold': 1.1,
            'exponential_weight_factor': 5.0,
            'initial_perturbation_base': 0.02,
            'initial_perturbation_scale': 0.06,
            'restart_count_base': 3,
            'restart_count_scale': 9,
            'threshold_k': 2.0,  # New parameter for threshold dynamics
            'threshold_c': 1.5   # New parameter for threshold dynamics
        }

        # Initial quality assessment to determine problem difficulty
        current_score = get_smallest_triangle_area(points)
        # Higher difficulty means harder to improve (closer to theoretical maximum)
        difficulty = 1.0 - (current_score / param_dict['theoretical_max'])
        
        # Adaptive parameters based on problem difficulty
        params = {
            'restart_count': max(3, min(12, int(param_dict['restart_count_base'] + param_dict['restart_count_scale'] * difficulty))),
            'initial_perturbation': param_dict['initial_perturbation_base'] + param_dict['initial_perturbation_scale'] * difficulty,
            'step_size_increase_factor': param_dict['step_size_increase_factor'],
            'step_size_decrease_factor': param_dict['step_size_decrease_factor'],
            'cooling_factor': 0.98,
            'exponential_weight_factor': param_dict['exponential_weight_factor']
        }

        best_overall = points.copy()
        best_score_overall = current_score
        
        # Multiple restarts with adaptive parameters
        for restart in range(params['restart_count']):
            # Perturb current best solution for restart
            min_perturbation = 0.02 * params['initial_perturbation']
            decay_rate = 0.9 - 0.1 * (1.0 - difficulty)
            perturbation = max(min_perturbation, params['initial_perturbation'] * (decay_rate ** restart))
            current = best_overall.copy()
            for i in range(11):
                current[i] += np.random.uniform(-perturbation, perturbation, 2)
                current[i] = project_to_triangle(current[i])
            
            current_score = get_smallest_triangle_area(current)
            best = current.copy()
            best_score = current_score
            
            step_size = 0.02
            initial_temp = 0.1
            max_iter = 500
            # Adaptive stagnation threshold based on difficulty
            adaptive_stagnation_threshold = max(20, int(param_dict['stagnation_threshold_base'] * (1.0 - difficulty)))
            max_no_improve = adaptive_stagnation_threshold
            no_improve_count = 0

            # Initialize triangle cache for this restart
            triangle_cache = {}
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = tri_area(current[i], current[j], current[k])
                        triangle_cache[(i, j, k)] = area
            
            for iter in range(max_iter):
                # Find ALL critical triangles with dynamic threshold
                min_area = min(triangle_cache.values())
                areas_triplets = [(area, triplet) for triplet, area in triangle_cache.items()]

                # SIMPLIFIED THRESHOLD DYNAMICS USING CONTINUOUS FUNCTION
                base_threshold = 1.5
                # Continuous threshold function: base * exp(-k*iteration/max_iter) * (1 + c*stagnation/max_no_improve)
                k_factor = param_dict['threshold_k'] * (0.8 + 0.4 * difficulty)
                c_factor = param_dict['threshold_c'] * (1.2 - 0.4 * difficulty)
                
                threshold_factor = base_threshold * np.exp(-k_factor * iter / max_iter) * \
                                  (1 + c_factor * no_improve_count / max_no_improve)
                threshold = threshold_factor * min_area

                critical_triplets = [(area, triplet) for area, triplet in areas_triplets 
                                    if area < threshold and area > 1e-10]
                
                if not critical_triplets:
                    break

                # Identify critical points (those in critical triangles)
                critical_points_set = set()
                for _, triplet in critical_triplets:
                    critical_points_set.update(triplet)
                critical_points = list(critical_points_set)

                # Calculate weighted displacement with improved prioritization
                displacement_vectors = np.zeros((11, 2))
                point_weights = np.zeros(11)
                
                # Exponential weighting factor adapted for difficulty
                exponential_weight_factor = param_dict['exponential_weight_base'] + \
                                          param_dict['exponential_weight_scale'] * (1.0 - difficulty)
                
                for area, triplet in critical_triplets:
                    i, j, k = triplet
                    # IMPROVED PRIORITIZATION: weight by both criticality and improvement potential
                    improvement_potential = 1.0 - (area / param_dict['theoretical_max'])
                    weight = np.exp(-exponential_weight_factor * (area - min_area) / (min_area + 1e-10)) * improvement_potential
                    
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

                # Normalize and apply displacements with adaptive orthogonal components
                candidate = current.copy()
                for idx in range(11):
                    if point_weights[idx] > 0:
                        direction = displacement_vectors[idx] / point_weights[idx]
                        
                        # ADAPTIVE ORTHOGONAL BLENDING BASED ON STAGNATION
                        stagnation_ratio = no_improve_count / max(1, max_no_improve)
                        dir_ratio = 0.5 + 0.4 * np.exp(-stagnation_ratio * 10)
                        orth_ratio = 1.0 - dir_ratio
n                        # Blend direction with orthogonal component
                        orthogonal = np.array([-direction[1], direction[0]])
                        blended_direction = dir_ratio * direction + orth_ratio * orthogonal
                        blended_direction = blended_direction / (np.linalg.norm(blended_direction) + 1e-10)
                        
                        # Add some randomness
                        noise = np.random.normal(0, step_size/3, 2)
                        displacement = step_size * blended_direction + noise
                        candidate[idx] += displacement

                # Project all points back into triangle
                for idx in range(11):
                    candidate[idx] = project_to_triangle(candidate[idx])

                # MULTI-DIRECTIONAL STAGNATION RECOVERY
                if no_improve_count > adaptive_stagnation_threshold * 0.8:
                    best_candidate = candidate
                    best_candidate_score = get_smallest_triangle_area(candidate)
                    
                    # Try multiple random directions
                    for _ in range(4):
                        random_dir = np.random.normal(0, 0.5, 2)
                        random_dir = random_dir / (np.linalg.norm(random_dir) + 1e-10)
                        
                        multi_candidate = current.copy()
                        for idx in critical_points:
                            multi_candidate[idx] += step_size * 0.7 * random_dir
                            multi_candidate[idx] = project_to_triangle(multi_candidate[idx])
                        
                        multi_score = get_smallest_triangle_area(multi_candidate)
                        if multi_score > best_candidate_score:
                            best_candidate = multi_candidate
                            best_candidate_score = multi_score
                    
                    candidate = best_candidate

                # Calculate gradient only for critical points with caching
                gradient = calculate_gradient(candidate, critical_points=critical_points, 
                                            epsilon=1e-4, triangle_cache=triangle_cache)
                
                # Fixed gradient blending to prioritize gradient info for hard problems
                improvement_ratio = 1.0 - (best_score / param_dict['theoretical_max']) if param_dict['theoretical_max'] > 0 else 0
                blending_factor = 0.2 + 0.7 * (1.0 - difficulty) * min(1.0, no_improve_count / 200)
                blending_factor = max(0.1, min(param_dict['gradient_blending_max'], blending_factor))

                # Blend gradient direction with current displacement approach
                for idx in range(11):
                    if np.linalg.norm(gradient[idx]) > 1e-5:
                        grad_dir = gradient[idx] / np.linalg.norm(gradient[idx])
                        candidate[idx] += blending_factor * step_size * grad_dir
                        candidate[idx] = project_to_triangle(candidate[idx])

                # Update triangle cache with candidate configuration
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            triangle_cache[(i, j, k)] = tri_area(candidate[i], candidate[j], candidate[k])
                
                candidate_score = min(triangle_cache.values())
                
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

                # Adaptive step size control
                if no_improve_count > adaptive_stagnation_threshold / 2:
                    increase_factor = params['step_size_increase_factor'] + 0.15 * difficulty
                    step_size *= increase_factor
                elif no_improve_count < 5:
                    step_size *= params['step_size_decrease_factor']

                # MAKE STEP SIZE BOUNDS DIFFICULTY-DEPENDENT
                max_step_size = 0.15 + 0.1 * difficulty
                step_size = max(1e-5, min(step_size, max_step_size))

                # Stopping condition
                if no_improve_count >= max_no_improve:
                    break

            # Update overall best if this restart found a better solution
            if best_score > best_score_overall:
                best_overall = best.copy()
                best_score_overall = best_score

        return best_overall

    return improve