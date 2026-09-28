from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

class SolutionTracker:
    def __init__(self, max_history=5):
        self.history = []
        self.max_history = max_history
        
    def add_solution(self, points, score):
        self.history.append((points.copy(), score))
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
    def get_diversity_vector(self, current_points):
        if not self.history:
            return np.zeros_like(current_points)
        
        # Calculate average distance to previous solutions
        diversity_vector = np.zeros_like(current_points)
        for prev_points, _ in self.history:
            for i in range(len(current_points)):
                dist = np.linalg.norm(current_points[i] - prev_points[i])
                # Repulsion increases as distance decreases
                if dist < 0.05:  # Within repulsion radius
                    direction = current_points[i] - prev_points[i]
                    if np.linalg.norm(direction) > 1e-10:
                        direction = direction / np.linalg.norm(direction)
                        diversity_vector[i] += direction * (0.05 - dist)
        return diversity_vector

def entrypoint():
    A, B, C = get_unit_triangle()
    solution_tracker = SolutionTracker(max_history=3)

    def tri_area(a, b, c):
        return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    def project_to_triangle(point, critical_for=None, push_coeff=0.15):
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
            # Scale push by current min_area to maintain relative boundary safety
            current_min_area = get_smallest_triangle_area(critical_for)
            inward_push = push_coeff * current_min_area * edge_normals[edge_idx]
            return closest + inward_push
        
        return closest

    def improve(points: np.ndarray) -> np.ndarray:
        global RESISTANCE_HISTORY, QUALITY_HISTORY, GRADIENT_HISTORY, GRADIENT_HISTORY_WEIGHT
        
        # Initialize gradient history if needed
        if 'GRADIENT_HISTORY' not in globals() or GRADIENT_HISTORY is None or GRADIENT_HISTORY.shape != (11, 2):
            global GRADIENT_HISTORY
            global GRADIENT_HISTORY_WEIGHT
            GRADIENT_HISTORY = np.zeros((11, 2))
            GRADIENT_HISTORY_WEIGHT = 0.0

        # Initialize resistance history with continuous values
        if 'RESISTANCE_HISTORY' not in globals() or RESISTANCE_HISTORY is None:
            global RESISTANCE_HISTORY
            RESISTANCE_HISTORY = []
        
        if 'QUALITY_HISTORY' not in globals() or QUALITY_HISTORY is None:
            global QUALITY_HISTORY
            QUALITY_HISTORY = []

        # Base parameters
        base_params = {
            'step_size_increase_factor': 1.15,
            'step_size_decrease_factor': 0.85,
            'initial_perturbation': 0.1,
            'max_restart_count': 8,
        }

        # Calculate normalized min_area to gauge problem difficulty
        current_min_area = get_smallest_triangle_area(points)
        normalized_min_area = current_min_area / 0.0365  # Relative to theoretical max

        # Track resistance-quality history for adaptive scaling
        quality = min(normalized_min_area, 1.0)
        QUALITY_HISTORY.append(quality)
        
        # Calculate resistance-quality gap for adaptive scaling using continuous resistance values
        if RESISTANCE_HISTORY:
            avg_resistance = np.mean(RESISTANCE_HISTORY[-min(5, len(RESISTANCE_HISTORY)):])
            # Normalize resistance to [0,1] range based on theoretical max improvement
            normalized_resistance = min(1.0, avg_resistance / (0.0365 - current_min_area + 1e-8))
            resistance_excess = max(0, normalized_resistance)
        else:
            resistance_excess = 0.5
        
        # Adaptive parameters based on problem difficulty
        params = base_params.copy()
        
        # FIXED: Restart count formula with CORRECT scaling (increases with POOR quality)
        params['restart_count'] = max(2, min(base_params['max_restart_count'], 
                                          int(2 + 8 * (1 - normalized_min_area))))
        
        # FIXED: Increased perturbation base and CORRECT scaling (increases with POOR quality)
        params['initial_perturbation'] = 0.1 * (0.2 + 0.8 * (1 - normalized_min_area))

        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)
        
        # Calculate adaptive parameters that depend on problem difficulty
        boundary_push_coeff = 0.15 + 0.45 * (1 - normalized_min_area)  # Increased push for poor configs
        
        # FIXED: CORRECTED weight_exponent direction (increases with quality)
        weight_exponent = max(1.5, min(5.5, 1.5 + 2.5 * normalized_min_area))

        # Multiple restarts with decreasing perturbation to escape deep local optima
        for restart in range(params['restart_count']):
            # Perturb current best solution for restart (decreasing amount each time)
            perturbation = params['initial_perturbation'] * (0.5 ** restart)
            current = best_overall.copy()
            
            # Add diversity perturbation to encourage exploration of new regions
            diversity_vector = solution_tracker.get_diversity_vector(current)
            for i in range(11):
                current[i] += diversity_vector[i] * 0.3
                current[i] += np.random.uniform(-perturbation, perturbation, 2)
                current[i] = project_to_triangle(current[i], push_coeff=boundary_push_coeff)
            
            current_score = get_smallest_triangle_area(current)
            best = current.copy()
            best_score = current_score
            
            # Adaptive step size based on solution quality (LARGER for POOR configs)
            step_size = 0.005 + 0.025 * (1 - normalized_min_area)
            initial_temp = 0.1
            max_iter = 500
            max_no_improve = 200
            no_improve_count = 0
            
            # FIXED: Corrected reheating threshold to INCREASE with resistance
            reheating_threshold = max(50, int(100 * resistance_excess))
            
            for iter in range(max_iter):
                # Find ALL critical triangles using dynamic percentile approach
                min_area = current_score
                areas_triplets = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            area = tri_area(current[i], current[j], current[k])
                            areas_triplets.append((area, (i, j, k)))
                
                # Sort by area and select top critical triangles
                areas_triplets.sort(key=lambda x: x[0])
                
                # FIXED: Critical percentile INCREASES for RESISTANT configurations
                critical_percentile = max(0.05, min(0.5, 0.3 + 0.2 * resistance_excess))
                num_critical = max(3, int(critical_percentile * len(areas_triplets)))
                
                # Include near-critical points for tight local optima
                min_area_val = areas_triplets[0][0] if areas_triplets else 0
                # FIXED: Near-critical threshold now depends on resistance_excess
                near_critical_threshold = min_area_val * (1 + 0.1 + 0.3 * resistance_excess)
                critical_triplets = areas_triplets[:num_critical]
                
                # Add near-critical triangles to expand search focus
                for area, triplet in areas_triplets[num_critical:]:
                    if area <= near_critical_threshold and len(critical_triplets) < int(0.3 * len(areas_triplets)):
                        critical_triplets.append((area, triplet))
                    else:
                        break
                
                if not critical_triplets:
                    break

                # Enhanced critical point identification with neighbor inclusion
                critical_points_set = set()
                for _, triplet in critical_triplets:
                    i, j, k = triplet
                    critical_points_set.update([i, j, k])
                
                # Add neighbor points within adaptive distance for broader influence
                # FIXED: Slower decreasing neighbor distance
                adaptive_distance = 0.005 + 0.015 * (1 - normalized_min_area)
                for i in range(11):
                    if i in critical_points_set:
                        continue
                    for j in critical_points_set:
                        if np.linalg.norm(current[i] - current[j]) < adaptive_distance:
                            critical_points_set.add(i)
                            break

                # Calculate weighted displacement with side-effect penalty
                displacement_vectors = np.zeros((11, 2))
                point_weights = np.zeros(11)
                side_effect_penalty = np.zeros((11, 2))
                
                # First pass: Identify potential side effects on non-critical triangles
                non_critical_threshold = min_area_val * (1.2 + 0.3 * resistance_excess)
                for area, triplet in areas_triplets:
                    if area > non_critical_threshold:
                        continue
                    
                    i, j, k = triplet
                    # Skip if this is already a critical triplet
                    is_critical = False
                    for _, crit_triplet in critical_triplets:
                        if set(triplet) == set(crit_triplet):
                            is_critical = True
                            break
                    if is_critical:
                        continue

                    # For each point in the triplet, calculate direction that would degrade it
                    for idx in triplet:
                        others = [x for x in triplet if x != idx]
                        p0 = current[others[0]]
                        p1 = current[others[1]]
                        base_vector = p1 - p0
                        normal = np.array([-base_vector[1], base_vector[0]])
                        vec = current[idx] - p0
                        if np.dot(normal, vec) > 0:
                            normal = -normal
                        norm = np.linalg.norm(normal)
                        if norm > 1e-10:
                            normal = normal / norm
                            # Weight by how close to critical this triangle is
                            weight = 0.5 * np.exp(-2.0 * (area/min_area_val - 1))
                            side_effect_penalty[idx] += weight * normal

                # Second pass: Calculate improvement directions for critical triangles
                for area, triplet in critical_triplets:
                    i, j, k = triplet
                    
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
                            # Adaptive weighting based on problem difficulty
                            weight = np.exp(-weight_exponent * (area/min_area - 1))
                            displacement_vectors[idx] += weight * normal
                            point_weights[idx] += weight

                # Normalize and apply displacements with side-effect penalty
                candidate = current.copy()
                for idx in range(11):
                    if point_weights[idx] > 0:
                        # Balance improvement direction against side-effect penalties
                        improvement_direction = displacement_vectors[idx] / point_weights[idx]
                        penalty_magnitude = np.linalg.norm(side_effect_penalty[idx])
                        
                        # Adjust balance based on resistance - more cautious when resistance is high
                        side_effect_weight = 0.3 + 0.4 * resistance_excess
                        if penalty_magnitude > 1e-5:
                            side_effect_direction = side_effect_penalty[idx] / penalty_magnitude
                            direction = (1 - side_effect_weight) * improvement_direction - \
                                       side_effect_weight * side_effect_direction
                        else:
                            direction = improvement_direction

                        # Add resistance-aware gradient history biasing
                        if GRADIENT_HISTORY_WEIGHT > 0.01:
                            direction = 0.5 * direction + 0.5 * GRADIENT_HISTORY[idx]
                        
                        # Add some randomness to escape local minima
                        noise = np.random.normal(0, step_size/3, 2)
                        displacement = step_size * direction + noise
                        candidate[idx] += displacement

                # Project all points back into triangle with boundary awareness
                for idx in range(11):
                    # Only apply inward push for points involved in critical triangles
                    is_critical = idx in critical_points_set
                    candidate[idx] = project_to_triangle(candidate[idx], 
                                                      critical_for=candidate if is_critical else None,
                                                      push_coeff=boundary_push_coeff)

                candidate_score = get_smallest_triangle_area(candidate)
                
                # Calculate actual improvement for resistance tracking (continuous value)
                improvement = max(0.0, candidate_score - current_min_area)
                
                # Simulated annealing acceptance
                # FIXED: CORRECTED cooling exponent direction (decreases with quality)
                cooling_exponent = max(0.2, min(0.7, 0.7 - 0.5 * normalized_min_area))
                cooling_factor = 0.92 * (1 - 0.08 * (no_improve_count/max_no_improve)**cooling_exponent)
                temp = initial_temp * (cooling_factor ** iter)
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

                # Reheating mechanism when stuck in local optimum
                if no_improve_count > reheating_threshold:
                    temp = 0.75 * initial_temp
                    no_improve_count = 0

                # Update resistance history with actual improvement magnitude
                RESISTANCE_HISTORY.append(improvement)
                if len(RESISTANCE_HISTORY) > 10:  # Limit history size
                    RESISTANCE_HISTORY.pop(0)
                
                # Update gradient history with exponential decay
                decay_factor = 0.8
                if GRADIENT_HISTORY is None:
                    GRADIENT_HISTORY = displacement_vectors.copy()
                    GRADIENT_HISTORY_WEIGHT = 1.0
                else:
                    GRADIENT_HISTORY = decay_factor * GRADIENT_HISTORY + (1 - decay_factor) * displacement_vectors
                    GRADIENT_HISTORY_WEIGHT = decay_factor * GRADIENT_HISTORY_WEIGHT + (1 - decay_factor)

                # Stopping condition
                if no_improve_count >= max_no_improve:
                    break

            # Update overall best if this restart found a better solution
            if best_score > best_score_overall:
                best_overall = best.copy()
                best_score_overall = best_score
                solution_tracker.add_solution(best_overall, best_score_overall)

        return best_overall

    return improve