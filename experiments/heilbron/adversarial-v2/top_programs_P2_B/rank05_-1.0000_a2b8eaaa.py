from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import collections

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def tri_area(a, b, c):
        return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    def distance_to_line(p, a, b):
        ap = p - a
        ab = b - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
        t = max(0, min(1, t))
        projection = a + t * ab
        return np.linalg.norm(p - projection)

    def distance_to_boundary(point):
        d1 = distance_to_line(point, A, B)
        d2 = distance_to_line(point, B, C)
        d3 = distance_to_line(point, C, A)
        return min(d1, d2, d3)

    def boundary_influence(point):
        dist = distance_to_boundary(point)
        # Continuous scaling: 0.0 at centroid, 1.0 at boundary
        height = np.linalg.norm(C - (A+B)/2)
        return min(1.0, 3.0 * dist / height)

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
            # Use continuous boundary influence instead of binary push
            current_min_area = get_smallest_triangle_area(critical_for)
            normalized_min_area = current_min_area / 0.0365
            boundary_dist = distance_to_boundary(closest)
            height = np.linalg.norm(C - (A+B)/2)
            
            # More aggressive push with continuous scaling
            push_factor = 0.2 + 0.4 * normalized_min_area
            max_push = push_factor * current_min_area
            actual_push = min(max_push, boundary_dist * 0.7)
            
            return closest + actual_push * edge_normals[edge_idx]
        
        return closest

    def improve(points: np.ndarray) -> np.ndarray:
        # Base parameters
        base_params = {
            'step_size_increase_factor': 1.2,
            'step_size_decrease_factor': 0.8,
            'initial_perturbation': 0.07,
            'max_restart_count': 12,
            'bottleneck_history': 10
        }

        # Calculate initial difficulty metric
        current_min_area = get_smallest_triangle_area(points)
        
        # Dynamic difficulty tracker - maintains rolling history of min_area
        difficulty_history = collections.deque(maxlen=20)
        difficulty_history.append(current_min_area)
        
        def get_normalized_difficulty():
            # Use recent history to calculate current difficulty
            if len(difficulty_history) == 0:
                return current_min_area / 0.0365
            avg_recent = sum(difficulty_history) / len(difficulty_history)
            return avg_recent / 0.0365

        best_overall = points.copy()
        best_score_overall = current_min_area
        
        # Track bottleneck triangles across iterations
        bottleneck_counter = collections.defaultdict(int)
        bottleneck_history = []
        
        # Multiple restarts with decreasing perturbation to escape deep local optima
        for restart in range(base_params['max_restart_count']):
            # Dynamically adjust restart count based on difficulty
            normalized_difficulty = get_normalized_difficulty()
            restart_count = max(3, min(base_params['max_restart_count'], 
                                    int(3 + 12 * normalized_difficulty**2)))
            
            if restart >= restart_count:
                break

            # Perturb current best solution for restart (decreasing amount each time)
            perturbation = base_params['initial_perturbation'] * (0.5 ** restart)
            current = best_overall.copy()
            for i in range(11):
                current[i] += np.random.uniform(-perturbation, perturbation, 2)
                current[i] = project_to_triangle(current[i])
            
            current_score = get_smallest_triangle_area(current)
            best = current.copy()
            best_score = current_score
            
            step_size = 0.025
            initial_temp = 0.2
            max_iter = 700
            max_no_improve = 300
            no_improve_count = 0
            
            # Track critical triangle patterns across iterations
            iteration = 0
            
            while iteration < max_iter and no_improve_count < max_no_improve:
                # Update difficulty history
                difficulty_history.append(current_score)
                normalized_difficulty = get_normalized_difficulty()

                # Find ALL triangles and sort by area
                areas_triplets = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            area = tri_area(current[i], current[j], current[k])
                            areas_triplets.append((area, (i, j, k)))
                
                areas_triplets.sort(key=lambda x: x[0])
                min_area = areas_triplets[0][0]

                # Density-adaptive critical threshold
                # Find natural clusters in area distribution
                area_values = [area for area, _ in areas_triplets]
                gaps = [area_values[i+1] - area_values[i] for i in range(len(area_values)-1)]
                
                if gaps:
                    # Find largest gap below the top 25% of areas
                    max_gap_idx = 0
                    max_gap = 0
                    for i in range(min(len(gaps), int(len(gaps)*0.25))):
                        if gaps[i] > max_gap:
                            max_gap = gaps[i]
                            max_gap_idx = i
n                    # Use the gap to determine critical threshold
                    critical_threshold = area_values[max_gap_idx+1] * 1.05
                else:
                    critical_threshold = min_area * 1.1

                # Select all triangles below threshold
                critical_triplets = [(area, triplet) for area, triplet in areas_triplets 
                                    if area <= critical_threshold]
                
                # Ensure minimum number of critical triangles based on difficulty
                min_critical_count = max(5, int(8 * normalized_difficulty))
                if len(critical_triplets) < min_critical_count:
                    critical_triplets = areas_triplets[:min_critical_count]

                # Track bottleneck triangles for targeted improvement
                current_bottlenecks = set()
                for area, triplet in critical_triplets[:3]:  # Top 3 smallest
                    triplet_key = tuple(sorted(triplet))
                    current_bottlenecks.add(triplet_key)
                    
                bottleneck_history.append(current_bottlenecks)
                if len(bottleneck_history) > base_params['bottleneck_history']:
                    bottleneck_history.pop(0)
                
                # Count frequency of bottleneck triangles
                bottleneck_counter.clear()
                for bottlenecks in bottleneck_history:
                    for triplet in bottlenecks:
                        bottleneck_counter[triplet] += 1

                # Calculate weighted displacement with improved prioritization
                displacement_vectors = np.zeros((11, 2))
                point_weights = np.zeros(11)
                critical_points = set()
                
                # Adaptive weight exponent
                weight_exponent = 1.5 + 1.5 * normalized_difficulty
                
                # First pass: regular critical triangles
                for area, triplet in critical_triplets:
                    i, j, k = triplet
                    critical_points.update(triplet)
                    
                    # Exponential weighting
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

                # Second pass: targeted bottleneck triangles (persistent constraints)
                max_frequency = max(bottleneck_counter.values()) if bottleneck_counter else 1
                for triplet, frequency in bottleneck_counter.items():
                    if frequency < max_frequency * 0.7:  # Only target frequently bottlenecked triangles
                        continue
                        
                    i, j, k = triplet
                    # Higher weight for persistent bottlenecks
                    bottleneck_weight = 2.0 * (frequency / max_frequency)
                    
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
                            displacement_vectors[idx] += bottleneck_weight * normal
                            point_weights[idx] += bottleneck_weight

                # Normalize and apply displacements
                candidate = current.copy()
                for idx in range(11):
                    if point_weights[idx] > 0:
                        direction = displacement_vectors[idx] / point_weights[idx]
                        
                        # Boundary awareness - reduce movement near boundaries
                        boundary_factor = 1.0 - 0.4 * boundary_influence(current[idx])
                        
                        # Add some randomness to escape local minima
                        noise = np.random.normal(0, step_size/4, 2)
                        displacement = step_size * boundary_factor * direction + noise
                        candidate[idx] += displacement

                # Project all points back into triangle with boundary awareness
                for idx in range(11):
                    # Only apply inward push for points involved in critical triangles
                    is_critical = idx in critical_points
                    candidate[idx] = project_to_triangle(candidate[idx], 
                                                      critical_for=candidate if is_critical else None)

                candidate_score = get_smallest_triangle_area(candidate)
                
                # Simulated annealing acceptance
                cooling_factor = 0.95
                temp = initial_temp * (cooling_factor ** iteration)
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
                if no_improve_count > 75:
                    step_size *= base_params['step_size_increase_factor']
                elif no_improve_count < 10:
                    step_size *= base_params['step_size_decrease_factor']

                # Relaxed step size clamping
                step_size = max(5e-6, min(0.3, 0.5 * normalized_difficulty))

                iteration += 1

            # Update overall best if this restart found a better solution
            if best_score > best_score_overall:
                best_overall = best.copy()
                best_score_overall = best_score

        return best_overall

    return improve