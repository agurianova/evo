import numpy as np
from itertools import combinations
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import scipy.optimize
from sklearn.cluster import DBSCAN

np.random.seed(42)

def calculate_normalized_distance_to_boundary(point, A, B, C):
    """Calculate normalized distance to triangle boundary (0=on boundary, 1=centroid)"""
    # Calculate distances to each edge
    def distance_to_edge(p, v1, v2):
        edge = v2 - v1
        w = p - v1
        proj = np.dot(w, edge) / (np.dot(edge, edge) + 1e-10)
        proj = np.clip(proj, 0, 1)
        closest = v1 + proj * edge
        return np.linalg.norm(p - closest)

    d1 = distance_to_edge(point, A, B)
    d2 = distance_to_edge(point, B, C)
    d3 = distance_to_edge(point, C, A)
    
    # Normalize by triangle height (approximate)
    height = np.linalg.norm(C - (A+B)/2)
    min_dist = min(d1, d2, d3)
    
    # Return normalized distance (0=boundary, 1=centroid)
    return 1.0 - min_dist / height

def project_point_to_triangle(p, A, B, C):
    """Project point p onto the triangle defined by A, B, C"""
    v0 = B - A
    v1 = C - A
    v2 = p - A
    
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-10:
        return A
    
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    
    if v < 0:
        v = 0
        w = max(0, min(1, w))
    if w < 0:
        w = 0
        v = max(0, min(1, v))
    if v + w > 1:
        total = v + w
        v /= total
        w /= total
        
    return A + v * v0 + w * v1

def nelder_mead_refinement(points, A_tri, B_tri, C_tri, maxiter=200):
    """Apply Nelder-Mead simplex method for local refinement"""
    n_points, _ = points.shape
    
    # Objective function for Nelder-Mead (we want to maximize min area)
    def objective(params):
        candidate = params.reshape((n_points, 2)).copy()
        
        # Project points back to triangle if needed
        for i in range(n_points):
            if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                candidate[i] = project_point_to_triangle(candidate[i], A_tri, B_tri, C_tri)
        
        # Calculate minimum triangle area (we want to maximize this, so return negative)
        min_area = get_smallest_triangle_area(candidate)
        return -min_area

    # Initial simplex: perturb the current best solution
    initial = points.flatten().copy()
    
    # Set adaptive step size based on current solution quality
    current_min_area = get_smallest_triangle_area(points)
    progress_ratio = current_min_area / 0.0365
    # Reduced decay rate to maintain exploration capability
    step_size = 0.004 * np.exp(-3.0 * progress_ratio) + 0.0005
    
    # Create initial simplex
    simplex = [initial]
    for i in range(len(initial)):
        perturbed = initial.copy()
        perturbed[i] += step_size
        simplex.append(perturbed)
    
    # Run Nelder-Mead
    result = scipy.optimize.minimize(
        objective,
        initial,
        method='Nelder-Mead',
        options={
            'maxiter': maxiter,
            'xatol': 1e-10,
            'fatol': 1e-10,
            'initial_simplex': simplex
        }
    )
    
    # Return the best solution
    best_points = result.x.reshape((n_points, 2))
    for i in range(n_points):
        if not is_inside_triangle(best_points[i], A_tri, B_tri, C_tri):
            best_points[i] = project_point_to_triangle(best_points[i], A_tri, B_tri, C_tri)
    
    return best_points

def identify_critical_clusters(points, top_triangles, min_cluster_size=2):
    """Use DBSCAN to identify clusters among points involved in small triangles"""
    # Get all points involved in top triangles
n    critical_points_indices = set()
    for _, i, j, k, _ in top_triangles:
        critical_points_indices.add(i)
        critical_points_indices.add(j)
        critical_points_indices.add(k)
    
    critical_points_indices = list(critical_points_indices)
    if len(critical_points_indices) < min_cluster_size:
        return [critical_points_indices]  # Return all as one cluster if too few points

    # Extract the actual points
    critical_points = points[critical_points_indices]
    
    # Scale coordinates for meaningful DBSCAN distance
    points_scaled = (critical_points - np.mean(critical_points, axis=0)) / (np.std(critical_points, axis=0) + 1e-10)
    
    # Apply DBSCAN clustering
    clustering = DBSCAN(eps=0.4, min_samples=min_cluster_size).fit(points_scaled)
    
    # Group points by cluster
    clusters = {}
    for i, label in enumerate(clustering.labels_):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(critical_points_indices[i])
    
    # Return clusters, excluding noise points (-1 label)
    return [clusters[label] for label in clusters if label != -1] or [critical_points_indices]

def entrypoint():
    A_tri, B_tri, C_tri = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        best = points.copy()
        best_score = get_smallest_triangle_area(points)
        current_score = best_score

        # Multi-scale optimization parameters
        phase1_step = 0.02
        phase2_step = 0.005
        phase3_step = 0.001
        
        # Track recent improvements for adaptive behavior
        improvement_history = []
        history_window = 50
        improvement_rate = 0.0
        
        no_improve_count = 0
        
        # Track point involvement in small triangles for targeted perturbations
        point_involvement = np.zeros(11)
        point_gradient_magnitude = np.zeros(11)

        # Phase tracking
        phase = 1
        phase1_min_iter = 100
        phase2_min_iter = 200
        
        # Calculate triangle height for boundary distance normalization
        height = np.linalg.norm(C_tri - (A_tri + B_tri) / 2)

        for iteration in range(1000):
            # Find all triangles and their areas
            triangles = []
            for i, j, k in combinations(range(11), 3):
                ax, ay = current[i]
                bx, by = current[j]
                cx, cy = current[k]
                s_val = 0.5 * ((bx - ax) * (cy - ay) - (cx - ax) * (by - ay))
                abs_area = abs(s_val)
                triangles.append((abs_area, i, j, k, s_val))

            # Sort by area
            triangles.sort(key=lambda x: x[0])
            smallest_area = triangles[0][0]
            
            # Calculate area distribution statistics
            areas = [t[0] for t in triangles]
            # Use interquartile range instead of standard deviation for robustness
            q1 = np.percentile(areas, 25)
            q3 = np.percentile(areas, 75)
            iqr = q3 - q1
            iqr_factor = iqr / (q3 + 1e-10)  # Relative IQR

            # Adaptive factor with tunable parameters
            base_factor = 0.06  # Increased from 0.04
            sensitivity = 0.4   # Increased from 0.3
            area_threshold_factor = base_factor + sensitivity * iqr_factor
            area_threshold_factor = min(max(area_threshold_factor, 0.02), 0.45)
            area_threshold = smallest_area * (1 + area_threshold_factor)
            
            # Adaptive selection: all triangles within threshold of smallest area
            top_triangles = [t for t in triangles if t[0] <= area_threshold]

            # Track point involvement for targeted perturbations
            point_involvement = np.zeros(11)
            for _, i, j, k, _ in top_triangles:
                point_involvement[i] += 1
                point_involvement[j] += 1
                point_involvement[k] += 1
            
            # Initialize gradient accumulators for all points
            gradients = np.zeros_like(current)
            
            # Process each top triangle
            for abs_area, i, j, k, s_val in top_triangles:
                # Adaptive sigmoid transition parameters based on solution quality
                base_transition_point = 0.022
                transition_point_range = 0.01
                transition_point = base_transition_point + transition_point_range * (1 - current_score / 0.0365)
                
                base_steepness = 12.0
                steepness_range = 8.0
                steepness = base_steepness + steepness_range * (current_score / 0.0365)
                
                # Smooth sigmoid transition between weighting schemes
                weight_factor = 1.0 / (1.0 + np.exp(-steepness * (current_score - transition_point)))

                # Blend the two weighting schemes
                weight_sqrt = 1.0 / np.sqrt(abs_area + 1e-10)
                weight_log = 1.0 / (np.log(1 + 10 * abs_area) + 1e-10)
                weight = weight_factor * weight_sqrt + (1.0 - weight_factor) * weight_log
                
                A = current[i]
                B = current[j]
                C = current[k]

                sign_S = 1.0 if s_val >= 0 else -1.0

                # Compute gradients
                grad_A = sign_S * np.array([B[1] - C[1], C[0] - B[0]])
                grad_B = sign_S * np.array([C[1] - A[1], A[0] - C[0]])
                grad_C = sign_S * np.array([A[1] - B[1], B[0] - A[0]])

                # Accumulate weighted gradients
                gradients[i] += weight * grad_A
                gradients[j] += weight * grad_B
                gradients[k] += weight * grad_C

            # Calculate gradient magnitudes for all points
            for i in range(11):
                point_gradient_magnitude[i] = np.linalg.norm(gradients[i])
            
            # Normalize gradient magnitudes
            max_grad_mag = np.max(point_gradient_magnitude) if np.max(point_gradient_magnitude) > 0 else 1.0
            normalized_grad_mag = point_gradient_magnitude / max_grad_mag

            # Determine step size based on optimization phase
            if phase == 1:
                step_size = phase1_step
            elif phase == 2:
                step_size = phase2_step
            else:
                step_size = phase3_step

            # Create candidate by moving all points
            candidate = current.copy()
            for i in range(11):
                if np.linalg.norm(gradients[i]) > 1e-10:
                    # Enhanced gradient following with stronger directional exploitation
                    exp = 0.3 + 0.6 * (current_score / 0.0365)  # Changed from 0.5+0.3*progress
                    norm = np.linalg.norm(gradients[i])
                    grad_dir = gradients[i] / (norm ** exp)
                    candidate[i] += step_size * grad_dir

            # Project any points outside the triangle back onto the boundary
            for i in range(11):
                if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                    candidate[i] = project_point_to_triangle(candidate[i], A_tri, B_tri, C_tri)

            new_score = get_smallest_triangle_area(candidate)

            # Track improvement for adaptive behavior
            improvement = new_score - current_score
            improvement_history.append(improvement)
            if len(improvement_history) > history_window:
                improvement_history.pop(0)
            
            # Calculate moving average improvement rate
            if len(improvement_history) > 0:
                improvement_rate = np.mean(improvement_history)
            
            # Update best solution if improvement found
            if new_score > best_score:
                best = candidate.copy()
                best_score = new_score
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0
            elif new_score > current_score:
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Dynamic phase transitions based on improvement rate and solution quality
            # Adaptive scaling factors based on historical improvement rates
            base_phase1_to_2_factor = 0.0005  # Reduced from 0.001
            phase1_to_2_factor = base_phase1_to_2_factor * (1 + 0.5 * (1 - improvement_rate / 1e-3))
            phase1_to_2_threshold = max(1e-5, phase1_to_2_factor * (0.0365 - current_score))

            base_phase2_to_3_factor = 0.00005  # Reduced from 0.0001
            phase2_to_3_factor = base_phase2_to_3_factor * (1 + 0.5 * (1 - improvement_rate / 1e-3))
            phase2_to_3_threshold = max(1e-6, phase2_to_3_factor * (0.0365 - current_score))
            
            if phase == 1 and iteration > phase1_min_iter and improvement_rate < phase1_to_2_threshold:
                phase = 2
            elif phase == 2 and iteration > phase2_min_iter and improvement_rate < phase2_to_3_threshold:
                phase = 3

            # Dynamic global perturbation based on improvement rate
            base_threshold = 150
            scaling_factor = 3.0
            perturbation_threshold = base_threshold * (1 + scaling_factor * (1 - improvement_rate / 1e-3))
            perturbation_threshold = max(50, min(perturbation_threshold, 300))

            # Targeted global perturbation to escape deep local minima
            if no_improve_count >= perturbation_threshold:
                # Calculate normalized distance to boundary for each point
                dist_to_boundary = np.zeros(11)
                for i in range(11):
                    dist_to_boundary[i] = calculate_normalized_distance_to_boundary(current[i], A_tri, B_tri, C_tri)

                # Dynamic composite score weights based on optimization phase
                progress = current_score / 0.0365
                if phase == 1:
                    alpha = 0.55  # Increased beta weight
                    beta = 0.35  # Increased from 0.25
                    gamma = 0.10
                elif phase == 2:
                    alpha = 0.55
                    beta = 0.35
                    gamma = 0.10
                else:  # phase 3
                    alpha = 0.45 + 0.1 * progress
                    beta = 0.45 - 0.1 * progress
                    gamma = 0.10

                # Normalize weights to sum to 1
                total_weight = alpha + beta + gamma
                alpha /= total_weight
                beta /= total_weight
                gamma /= total_weight

                # Adaptive composite score with dynamic weights
                composite_score = (alpha * point_involvement + 
                                  beta * (1.0 - normalized_grad_mag) + 
                                  gamma * (1.0 - dist_to_boundary))

                # Normalize to [0,1]
                max_score = np.max(composite_score) if np.max(composite_score) > 0 else 1.0
                composite_score = composite_score / max_score

                # Enhanced perturbation scope targeting critical clusters
                # Increased from int(11*0.3) to int(11*0.4)
                n_perturb = max(2, min(5, int(11 * 0.4)))  
                
                # Use DBSCAN to identify clusters among critical points
                clusters = identify_critical_clusters(current, top_triangles)
                
                # Select the most critical cluster (with highest average composite score)
                best_cluster_idx = -1
                best_cluster_score = -np.inf
                for i, cluster in enumerate(clusters):
                    cluster_score = np.mean([composite_score[idx] for idx in cluster])
                    if cluster_score > best_cluster_score:
                        best_cluster_score = cluster_score
                        best_cluster_idx = i
                
                # If we found a good cluster, use it, otherwise use top composite scores
                if best_cluster_idx >= 0 and len(clusters[best_cluster_idx]) > 0:
                    indices = clusters[best_cluster_idx]
                else:
                    indices = np.argsort(composite_score)[::-1][:n_perturb]

                # Nonlinear perturbation scaling with tunable parameters
                progress = current_score / 0.0365
                base_scale = 0.035 * np.sqrt(1 - progress) + 0.015 * (1 + 0.5 * progress)
                
                perturbation = np.zeros_like(current)
                for i, idx in enumerate(indices):
                    # Higher scale for more critical points
                    # Enhanced boundary exploration with safeguards
                    boundary_factor = 0.3 + 0.7 * dist_to_boundary[idx]  # Changed from 0.5+0.5*dist
                    scale = base_scale * boundary_factor * (1 + 0.8 * composite_score[idx])
                    perturbation[idx] = np.random.uniform(-scale, scale, size=2)
                    
                    # Additional safeguard: ensure perturbation doesn't push point outside triangle
                    test_point = current[idx] + perturbation[idx]
                    if not is_inside_triangle(test_point, A_tri, B_tri, C_tri):
                        # Scale down perturbation until it's inside
                        for _ in range(5):
                            perturbation[idx] *= 0.8
                            test_point = current[idx] + perturbation[idx]
                            if is_inside_triangle(test_point, A_tri, B_tri, C_tri):
                                break
                
                candidate = current + perturbation
                
                # Project back to triangle
                for i in range(11):
                    if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                        candidate[i] = project_point_to_triangle(candidate[i], A_tri, B_tri, C_tri)
                
                new_score = get_smallest_triangle_area(candidate)
                
                if new_score > best_score:
                    best = candidate.copy()
                    best_score = new_score
                    
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0

        # Apply Nelder-Mead local search for final refinement
        refined_best = nelder_mead_refinement(best, A_tri, B_tri, C_tri)
        refined_score = get_smallest_triangle_area(refined_best)
        
        if refined_score > best_score:
            return refined_best
        return best

    return improve