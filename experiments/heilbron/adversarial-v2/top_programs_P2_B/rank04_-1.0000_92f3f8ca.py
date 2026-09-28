from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def tri_area(a, b, c):
        return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    def project_to_triangle(point, critical_for=None):
        """Project point back into triangle with direction awareness for critical points"""
        if is_inside_triangle(point, A, B, C):
            return point.copy()
        
        # Try all three edges
        projections = []
        edges = [(A, B), (B, C), (C, A)]
        edge_normals = []
        
        # Precompute edge normals pointing inward
        for (p1, p2) in edges:
            v = p2 - p1
            normal = np.array([-v[1], v[0]])  # Perpendicular
            # Check direction - should point inward
            centroid = (A + B + C) / 3.0
            test_point = p1 + 0.5 * v
            if np.dot(normal, centroid - test_point) < 0:
                normal = -normal
            edge_normals.append(normal / np.linalg.norm(normal))

        for idx, (p1, p2) in enumerate(edges):
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
            projections.append((dist, b, idx))
        
        # Return closest projection
        _, closest, edge_idx = min(projections, key=lambda x: x[0])
        
        # For points critical for improvement, push inward slightly
        if critical_for is not None and len(critical_for) > 0:
            # ADAPTIVE CHANGE: Scale push by current min_area to maintain relative safety margin
            inward_push = 0.15 * current_min_area * edge_normals[edge_idx]
            return closest + inward_push
        
        return closest

    def calculate_gradient(points, epsilon=1e-5):
        """Calculate numerical gradient of minimum triangle area with respect to each point's position"""
        base_score = get_smallest_triangle_area(points)
        gradients = np.zeros_like(points)
        
        for i in range(len(points)):
            for dim in range(2):
                # Perturb point in positive direction
                points_plus = points.copy()
                points_plus[i, dim] += epsilon
                for j in range(len(points)):
                    # No special boundary handling during gradient calculation
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
        nonlocal current_min_area
        current_min_area = get_smallest_triangle_area(points)
        
        # Base parameters
        base_params = {
            'step_size_increase_factor': 1.1,
            'step_size_decrease_factor': 0.9,
            'initial_perturbation': 0.05,
            'max_restart_count': 6,
            'max_no_improve': 200
        }

        # Calculate normalized min_area to gauge problem difficulty
        normalized_min_area = current_min_area / 0.0365  # Relative to theoretical max

        # Adaptive parameters based on problem difficulty
        params = base_params.copy()
        
        # More restarts for harder problems (lower min_area)
        params['restart_count'] = max(2, min(base_params['max_restart_count'], 
                                          int(2 + 8 * (1 - normalized_min_area)**2)))
        
        # Scale initial perturbation based on problem difficulty
        params['initial_perturbation'] = base_params['initial_perturbation'] * (0.2 + 0.8 * (1 - normalized_min_area))

        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)
        
        # Track improvement rate across restarts
        improvement_history = []
        
        # Multiple restarts with decreasing perturbation to escape deep local optima
        for restart in range(params['restart_count']):
            # Perturb current best solution for restart (decreasing amount each time)
            perturbation = params['initial_perturbation'] * (0.5 ** restart)
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
            no_improve_count = 0
            
            # ADAPTIVE CHANGE: Make weight exponent difficulty-dependent
            weight_exponent = 3.0 * (1 + 0.7 * (1 - normalized_min_area))
            
            for iter in range(max_iter):
                # Find ALL critical triangles with adaptive threshold
                min_area = current_score
                areas_triplets = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            area = tri_area(current[i], current[j], current[k])
                            areas_triplets.append((area, (i, j, k)))
                
                # ADAPTIVE CHANGE: Dynamic percentile threshold based on area distribution
                areas_triplets.sort(key=lambda x: x[0])
                # Select top percentile of smallest triangles, adapting to problem difficulty
                percentile = max(10, min(20, int(15 + 5 * (1 - normalized_min_area))))
                threshold_index = max(1, int(len(areas_triplets) * percentile / 100))
                threshold = areas_triplets[threshold_index-1][0]
                
                critical_triplets = [(area, triplet) for area, triplet in areas_triplets 
                                    if area <= threshold and area > 1e-10]
                
                if not critical_triplets:
                    break

                # Calculate weighted displacement with improved prioritization
                displacement_vectors = np.zeros((11, 2))
                point_weights = np.zeros(11)
                critical_points = set()
                
                for area, triplet in critical_triplets:
                    i, j, k = triplet
                    critical_points.update(triplet)
                    
                    # ADAPTIVE CHANGE: Exponent now scales with problem difficulty
                    weight = np.exp(-weight_exponent * (area/min_area - 1))
                    
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

                # Normalize and apply displacements
                candidate = current.copy()
                for idx in range(11):
                    if point_weights[idx] > 0:
                        direction = displacement_vectors[idx] / point_weights[idx]
                        # Add some randomness to escape local minima
                        noise = np.random.normal(0, step_size/3, 2)
                        displacement = step_size * direction + noise
                        candidate[idx] += displacement

                # Project all points back into triangle with boundary awareness
                for idx in range(11):
                    # Only apply inward push for points involved in critical triangles
                    is_critical = idx in critical_points
                    candidate[idx] = project_to_triangle(candidate[idx], 
                                                      critical_for=[idx] if is_critical else None)

                # Calculate gradient for conflict resolution
                gradient = calculate_gradient(candidate, epsilon=1e-4)
                # Blend gradient direction with current displacement approach
                for idx in range(11):
                    if np.linalg.norm(gradient[idx]) > 1e-5:
                        # Normalize and blend gradient direction
                        grad_dir = gradient[idx] / np.linalg.norm(gradient[idx])
                        candidate[idx] += 0.3 * step_size * grad_dir
                        candidate[idx] = project_to_triangle(candidate[idx], 
                                                          critical_for=[idx] if idx in critical_points else None)

                candidate_score = get_smallest_triangle_area(candidate)
                
                # Simulated annealing acceptance
                temp = initial_temp * (0.98 ** iter)
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

                # Adaptive step size control with more aggressive factors
                if no_improve_count > 50:
                    step_size *= params['step_size_increase_factor']
                elif no_improve_count < 5:
                    step_size *= params['step_size_decrease_factor']

                # ADAPTIVE CHANGE: Dynamic clamping based on problem difficulty
                min_step = 5e-6
                max_step = 0.02 * (1 + normalized_min_area)
                step_size = max(min_step, min(step_size, max_step))

                # Stopping condition
                if no_improve_count >= params['max_no_improve']:
                    break

            # Track improvement for restart strategy
            if restart > 0:
                improvement = (best_score - best_score_overall) / best_score_overall if best_score_overall > 0 else 0
                improvement_history.append(improvement)

            # Update overall best if this restart found a better solution
            if best_score > best_score_overall:
                best_overall = best.copy()
                best_score_overall = best_score

        return best_overall

    return improve