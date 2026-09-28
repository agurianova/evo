from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import networkx as nx

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    side_length = np.linalg.norm(B - A)  # Precompute side length for barycentric scaling

    # Direction history tracking for prediction model
    direction_history = {}
    
    def get_direction_key(triplet_info):
        """Create hashable key for triangle characteristics to track direction success"""
        aspect_ratio, pos_category, size_category = triplet_info
        return (round(aspect_ratio, 2), pos_category, size_category)

    def update_direction_history(triplet_info, direction_idx, success):
        """Update historical success rate for a direction type"""
        key = get_direction_key(triplet_info)
        if key not in direction_history:
            direction_history[key] = [0.5, 0.5, 0.5]  # Initialize with neutral prior
        
        # Exponential smoothing for stability
        alpha = 0.2
        direction_history[key][direction_idx] = (
            alpha * success + (1 - alpha) * direction_history[key][direction_idx]
        )

    def predict_best_direction(triplet_info):
        """Predict best direction based on historical success rates"""
        key = get_direction_key(triplet_info)
        if key in direction_history:
            return np.argmax(direction_history[key])
        return None  # No history, test all directions

    # Precompute denominator for barycentric conversion (2 * area of ABC)
    denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
    
    # Helper functions for barycentric conversion
    def to_bary(p):
        u = ((B[1] - C[1]) * (p[0] - C[0]) + (C[0] - B[0]) * (p[1] - C[1])) / denom
        v = ((C[1] - A[1]) * (p[0] - C[0]) + (A[0] - C[0]) * (p[1] - C[1])) / denom
        return u, v
    
    def to_cart(u, v):
        w = 1 - u - v
        return u * A + v * B + w * C

    def calculate_betweenness_centrality(min_triplets, n):
        """Calculate betweenness centrality for points in the minimal triangle network"""
        G = nx.Graph()
        G.add_nodes_from(range(n))
        
        # Add edges between points that share minimal triangles
        for triplet in min_triplets:
            i, j, k = triplet
            G.add_edges_from([(i, j), (j, k), (k, i)])
        
        # Calculate betweenness centrality
        if len(G.edges) > 0:
            centrality = nx.betweenness_centrality(G)
            return np.array([centrality.get(i, 0) for i in range(n)])
        return np.zeros(n)

    def get_triangle_characteristics(points, i, j, k):
        """Extract characteristics for direction prediction"""
        p_i, p_j, p_k = points[i], points[j], points[k]
        
        # Calculate edge lengths
        edge_ij = p_j - p_i
        edge_jk = p_k - p_j
        edge_ki = p_i - p_k
        length_ij = np.linalg.norm(edge_ij)
        length_jk = np.linalg.norm(edge_jk)
        length_ki = np.linalg.norm(edge_ki)

        # Calculate aspect ratio
        perimeter = length_ij + length_jk + length_ki
        if perimeter > 0:
            aspect_ratio = (length_ij * length_jk * length_ki) / (perimeter ** 3)
        else:
            aspect_ratio = 1.0

        # Determine position category (near vertex, edge, or interior)
        u_i, v_i = to_bary(p_i)
        w_i = 1 - u_i - v_i
        min_coord_i = min(u_i, v_i, w_i)
        
        if min_coord_i < 0.1:
            pos_category = 'boundary'
        elif min_coord_i < 0.3:
            pos_category = 'near_boundary'
        else:
            pos_category = 'interior'

        # Determine size category
        area = 0.5 * abs((p_j[0] - p_i[0]) * (p_k[1] - p_i[1]) - (p_k[0] - p_i[0]) * (p_j[1] - p_i[1]))
        if area < 0.01:
            size_category = 'small'
        elif area < 0.02:
            size_category = 'medium'
        else:
            size_category = 'large'

        return aspect_ratio, pos_category, size_category

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Dynamically scale initial step based on current min area
        initial_step = 0.1 * np.sqrt(best_score) if best_score > 0 else 0.05
        step_size = initial_step
        stagnation_count = 0
        restart_failure_count = 0
        max_iterations = 500
        adaptive_stopping_threshold = 1e-7 * side_length
        min_step_size = 1e-8 * side_length
        tol = 1e-9
        n = 11
        
        # Adaptive distinctness threshold based on optimization progress
        distinctness_threshold = max(5e-7, 1e-6 * (1 + 0.3 * (0.0365 - best_score) / 0.0365))

        # Calculate betweenness centrality for initial configuration
        min_area = float('inf')
        min_triplets = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    x1, y1 = best[i]
                    x2, y2 = best[j]
                    x3, y3 = best[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area < min_area - tol:
                        min_area = area
                        min_triplets = [(i, j, k)]
                    elif abs(area - min_area) < tol:
                        min_triplets.append((i, j, k))
        betweenness = calculate_betweenness_centrality(min_triplets, n)
        
        for _ in range(max_iterations):
            # Find all minimal-area triangles
            min_area = float('inf')
            min_triplets = []
            
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = best[i]
                        x2, y2 = best[j]
                        x3, y3 = best[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area < min_area - tol:
                            min_area = area
                            min_triplets = [(i, j, k)]
                        elif abs(area - min_area) < tol:
                            min_triplets.append((i, j, k))
            
            # Update betweenness centrality
            betweenness = calculate_betweenness_centrality(min_triplets, n)
            
            # Count vertex frequencies in minimal triangles
            freq = [0] * n
            for triplet in min_triplets:
                for idx in triplet:
                    freq[idx] += 1
            
            # Identify all points in minimal triangles
            min_points = set()
            for triplet in min_triplets:
                min_points.update(triplet)
            min_points = list(min_points)
            
            # If no minimal triangles found (shouldn't happen), skip iteration
            if not min_points:
                continue
                
            # Compute geometrically-aware gradients for minimal triangles
            gradients = np.zeros((n, 2))
            for triplet in min_triplets:
                i, j, k = triplet
                A_pt, B_pt, C_pt = best[i], best[j], best[k]
                
                # Calculate triangle properties for geometric awareness
                edge_ij = B_pt - A_pt
                edge_jk = C_pt - B_pt
                edge_ki = A_pt - C_pt
                length_ij = np.linalg.norm(edge_ij)
                length_jk = np.linalg.norm(edge_jk)
                length_ki = np.linalg.norm(edge_ki)

                # Calculate aspect ratio (closer to 1 means more equilateral)
                perimeter = length_ij + length_jk + length_ki
                if perimeter > 0:
                    aspect_ratio = (length_ij * length_jk * length_ki) / (perimeter ** 3)
                else:
                    aspect_ratio = 1.0

                # Calculate angles using dot product
                if length_ki > 0 and length_ij > 0:
                    cos_angle_i = np.dot(-edge_ki, edge_ij) / (length_ki * length_ij)
                    angle_i = np.arccos(np.clip(cos_angle_i, -1.0, 1.0))
                else:
                    angle_i = np.pi/3
                    
                if length_ij > 0 and length_jk > 0:
                    cos_angle_j = np.dot(-edge_ij, edge_jk) / (length_ij * length_jk)
                    angle_j = np.arccos(np.clip(cos_angle_j, -1.0, 1.0))
                else:
                    angle_j = np.pi/3
                    
                if length_jk > 0 and length_ki > 0:
                    cos_angle_k = np.dot(-edge_jk, edge_ki) / (length_jk * length_ki)
                    angle_k = np.arccos(np.clip(cos_angle_k, -1.0, 1.0))
                else:
                    angle_k = np.pi/3

                # Calculate optimal expansion direction based on geometry
                # For very skinny triangles, expand along the longest edge's perpendicular
                longest_edge_idx = np.argmax([length_ij, length_jk, length_ki])
                if longest_edge_idx == 0:  # ij is longest
                    optimal_dir = np.array([-edge_ij[1], edge_ij[0]])
                elif longest_edge_idx == 1:  # jk is longest
                    optimal_dir = np.array([-edge_jk[1], edge_jk[0]])
                else:  # ki is longest
                    optimal_dir = np.array([-edge_ki[1], edge_ki[0]])

                if np.linalg.norm(optimal_dir) > 0:
                    optimal_dir = optimal_dir / np.linalg.norm(optimal_dir)
                    
                # Weight the direction by aspect ratio (more weight for skinny triangles)
                quality_ratio = min(1.0, min_area / 0.0365)
                # Sigmoid adaptation for smoother transitions near optimum
                sigmoid_factor = 1 / (1 + np.exp(-10 * (quality_ratio - 0.5)))
                geometry_weight = 1.0 + 2.0 * (1.0 - aspect_ratio) * sigmoid_factor
                optimal_dir = optimal_dir * geometry_weight

                # Calculate gradients with geometric awareness
                grad_i = 0.5 * optimal_dir
                grad_j = 0.5 * optimal_dir
                grad_k = 0.5 * optimal_dir

                # Normalize gradients
                norm_i = np.linalg.norm(grad_i)
                norm_j = np.linalg.norm(grad_j)
                norm_k = np.linalg.norm(grad_k)
                
                if norm_i > 0:
                    grad_i = grad_i / norm_i
                if norm_j > 0:
                    grad_j = grad_j / norm_j
                if norm_k > 0:
                    grad_k = grad_k / norm_k

                # Add to overall gradients
                gradients[i] += grad_i
                gradients[j] += grad_j
                gradients[k] += grad_k

            # Apply adaptive frequency-based weighting to gradients
            max_freq = max(freq) if freq else 1
            if max_freq > 0:
                # Make weighting factor adaptive based on current min_area
                quality_ratio = min(1.0, min_area / 0.0365)
                # Sigmoid adaptation for smoother transitions near optimum
                sigmoid_factor = 1 / (1 + np.exp(-10 * (quality_ratio - 0.5)))
                adaptive_weight_factor = 0.3 + 0.7 * (1.0 - quality_ratio) * sigmoid_factor
                
                for i in range(n):
                    if freq[i] > 0:
                        # Weight by frequency with adaptive factor
                        weight = 1 + adaptive_weight_factor * (freq[i] / max_freq)
                        # Incorporate betweenness centrality for high-impact points
                        weight *= (1 + 0.5 * betweenness[i])
                        gradients[i] *= weight

            # Normalize gradients
            for i in range(n):
                grad_norm = np.linalg.norm(gradients[i])
                if grad_norm > 0:
                    gradients[i] /= grad_norm
            
            # Identify connected components of minimal triangles for coordinated movement
            connected_components = []
            visited = set()

            for triplet in min_triplets:
                if triplet not in visited:
                    component = set()
                    queue = [triplet]
                    while queue:
                        current = queue.pop(0)
                        if current not in visited:
                            visited.add(current)
                            component.add(current)
                            # Find all triplets sharing points with current
                            for t in min_triplets:
                                if t not in visited and (set(current) & set(t)):
                                    queue.append(t)
                    connected_components.append(component)

            # Test directions with prediction model
            for triplet in min_triplets:
                i, j, k = triplet
                p_i, p_j, p_k = best[i], best[j], best[k]
                
                # Get triangle characteristics for direction prediction
                triplet_info = get_triangle_characteristics(best, i, j, k)
                
                # Predict best direction if history exists
                predicted_dir = predict_best_direction(triplet_info)
                
                # Calculate all three possible perpendicular directions
                edge_ij = p_j - p_i
                edge_jk = p_k - p_j
                edge_ki = p_i - p_k

                normal_ij = np.array([-edge_ij[1], edge_ij[0]])
                normal_jk = np.array([-edge_jk[1], edge_jk[0]])
                normal_ki = np.array([-edge_ki[1], edge_ki[0]])

                # Normalize
                if np.linalg.norm(normal_ij) > 0:
                    normal_ij = normal_ij / np.linalg.norm(normal_ij)
                if np.linalg.norm(normal_jk) > 0:
                    normal_jk = normal_jk / np.linalg.norm(normal_jk)
                if np.linalg.norm(normal_ki) > 0:
                    normal_ki = normal_ki / np.linalg.norm(normal_ki)

                # Evaluate potential improvement for each direction
                best_normal = normal_ij
                best_improvement = -np.inf
                
                # Order directions based on prediction
                direction_order = [0, 1, 2]
                if predicted_dir is not None:
                    # Move predicted direction to front
                    direction_order.remove(predicted_dir)
                    direction_order = [predicted_dir] + direction_order

                for idx, normal in enumerate([normal_ij, normal_jk, normal_ki]):
                    if idx not in direction_order:
                        continue
                        
                    if np.linalg.norm(normal) == 0:
                        continue
                        
                    # Scale movement based on current min_area (adaptive)
                    quality_ratio = min(1.0, min_area / 0.0365)
                    # Sigmoid adaptation for smoother transitions
                    sigmoid_factor = 1 / (1 + np.exp(-10 * (quality_ratio - 0.5)))
                    adaptive_factor = sigmoid_factor
                    
                    # Make movement distance geometry-aware
                    avg_edge_length = (length_ij + length_jk + length_ki) / 3
                    move_dist = step_size * 0.5 * np.sqrt(adaptive_factor) * (1 + 0.2 * (1 - aspect_ratio))
                    
                    # Calculate triangle centroid
                    centroid = (p_i + p_j + p_k) / 3
                    
                    # Move centroid in normal direction
                    centroid_new = centroid + normal * move_dist
                    
                    # Create candidate by moving all points relative to new centroid
                    candidate_rigid = best.copy()
                    candidate_rigid[i] = centroid_new + (p_i - centroid)
                    candidate_rigid[j] = centroid_new + (p_j - centroid)
                    candidate_rigid[k] = centroid_new + (p_k - centroid)
                    
                    # Check containment and distinctness
                    if not is_inside_triangle(candidate_rigid, A, B, C):
                        # Update direction history with failure
                        update_direction_history(triplet_info, idx, 0)
                        continue
                        
                    # Ensure distinctness
                    valid = True
                    for idx1 in range(n):
                        for idx2 in range(idx1+1, n):
                            if np.linalg.norm(candidate_rigid[idx1] - candidate_rigid[idx2]) < distinctness_threshold:
                                valid = False
                                break
                        if not valid:
                            break
                    
                    if not valid:
                        # Update direction history with failure
                        update_direction_history(triplet_info, idx, 0)
                        continue
                        
                    score_rigid = get_smallest_triangle_area(candidate_rigid)
                    improvement = score_rigid - best_score
                    
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_normal = normal
                        successful_direction = idx

                if best_improvement > 0:
                    # Update direction history with success
                    update_direction_history(triplet_info, successful_direction, 1)

                    # Use the best direction found
                    normal = best_normal
                    centroid = (p_i + p_j + p_k) / 3
                    move_dist = step_size * 0.5 * np.sqrt(adaptive_factor) * (1 + 0.2 * (1 - aspect_ratio))
                    centroid_new = centroid + normal * move_dist
                    
                    # Create candidate by moving all points relative to new centroid
                    candidate_rigid = best.copy()
                    candidate_rigid[i] = centroid_new + (p_i - centroid)
                    candidate_rigid[j] = centroid_new + (p_j - centroid)
                    candidate_rigid[k] = centroid_new + (p_k - centroid)
                    
                    # Check containment and distinctness
                    if is_inside_triangle(candidate_rigid, A, B, C):
                        # Ensure distinctness
                        valid = True
                        for idx1 in range(n):
                            for idx2 in range(idx1+1, n):
                                if np.linalg.norm(candidate_rigid[idx1] - candidate_rigid[idx2]) < distinctness_threshold:
                                    valid = False
                                    break
                            if not valid:
                                break
                        
                        if valid:
                            score_rigid = get_smallest_triangle_area(candidate_rigid)
                            if score_rigid > best_score:
                                best = candidate_rigid
                                best_score = score_rigid
                                stagnation_count = 0
                                restart_failure_count = 0
                                # Skip to next iteration since we found an improvement
                                continue

            # Process connected components for coordinated movement
            for component in connected_components:
                # Collect all points in this component
                component_points = set()
                for triplet in component:
                    component_points.update(triplet)
                
                # Calculate combined gradient for each point
                component_gradients = np.zeros((n, 2))
                for triplet in component:
                    i, j, k = triplet
                    p_i, p_j, p_k = best[i], best[j], best[k]
                    
                    # Calculate geometrically-aware gradient as before
                    edge_ij = p_j - p_i
                    edge_jk = p_k - p_j
                    edge_ki = p_i - p_k
                    length_ij = np.linalg.norm(edge_ij)
                    length_jk = np.linalg.norm(edge_jk)
                    length_ki = np.linalg.norm(edge_ki)

                    # Calculate aspect ratio
                    perimeter = length_ij + length_jk + length_ki
                    if perimeter > 0:
                        aspect_ratio = (length_ij * length_jk * length_ki) / (perimeter ** 3)
                    else:
                        aspect_ratio = 1.0

                    # Calculate optimal expansion direction based on geometry
                    longest_edge_idx = np.argmax([length_ij, length_jk, length_ki])
                    if longest_edge_idx == 0:  # ij is longest
                        optimal_dir = np.array([-edge_ij[1], edge_ij[0]])
                    elif longest_edge_idx == 1:  # jk is longest
                        optimal_dir = np.array([-edge_jk[1], edge_jk[0]])
                    else:  # ki is longest
                        optimal_dir = np.array([-edge_ki[1], edge_ki[0]])

                    if np.linalg.norm(optimal_dir) > 0:
                        optimal_dir = optimal_dir / np.linalg.norm(optimal_dir)
                        
                    # Weight the direction by aspect ratio
                    quality_ratio = min(1.0, min_area / 0.0365)
                    sigmoid_factor = 1 / (1 + np.exp(-10 * (quality_ratio - 0.5)))
                    geometry_weight = 1.0 + 2.0 * (1.0 - aspect_ratio) * sigmoid_factor
                    optimal_dir = optimal_dir * geometry_weight

                    # Calculate gradients with geometric awareness
                    grad_i = 0.5 * optimal_dir
                    grad_j = 0.5 * optimal_dir
                    grad_k = 0.5 * optimal_dir

                    # Normalize
                    norm_i = np.linalg.norm(grad_i)
                    norm_j = np.linalg.norm(grad_j)
                    norm_k = np.linalg.norm(grad_k)
                    
                    if norm_i > 0:
                        grad_i = grad_i / norm_i
                    if norm_j > 0:
                        grad_j = grad_j / norm_j
                    if norm_k > 0:
                        grad_k = grad_k / norm_k

                    # Add to component gradients
                    component_gradients[i] += grad_i
                    component_gradients[j] += grad_j
                    component_gradients[k] += grad_k
                
                # Normalize component gradients
                for i in range(n):
                    if i in component_points:
                        grad_norm = np.linalg.norm(component_gradients[i])
                        if grad_norm > 0:
                            component_gradients[i] /= grad_norm
                
                # Create candidate by moving all points in component
                candidate_component = best.copy()
                for i in component_points:
                    # Scale movement based on component size and quality
                    move_scale = 0.1 / len(component) * np.sqrt(adaptive_factor)
                    # Incorporate betweenness centrality
                    move_scale *= (1 + 0.3 * betweenness[i])
                    candidate_component[i] += component_gradients[i] * move_scale
                
                # Check containment and distinctness
                if is_inside_triangle(candidate_component, A, B, C):
                    # Ensure distinctness
                    valid = True
                    for idx1 in range(n):
                        for idx2 in range(idx1+1, n):
                            if np.linalg.norm(candidate_component[idx1] - candidate_component[idx2]) < distinctness_threshold:
                                valid = False
                                break
                        if not valid:
                            break
                    
                    if valid:
                        score_component = get_smallest_triangle_area(candidate_component)
                        if score_component > best_score:
                            best = candidate_component
                            best_score = score_component
                            stagnation_count = 0
                            restart_failure_count = 0
                            # Skip to next iteration since we found an improvement
                            continue

            # Create candidate by perturbing all minimal points
            candidate = best.copy()
            step_size_bary = max(min_step_size, step_size) / side_length
            
            # Make Cauchy scale adaptive based on recent success rate
            success_rate = max(0.1, 1.0 - stagnation_count / 50.0)
            cauchy_scale_factor = 1.5 - 0.5 * success_rate  # Larger scale when success rate is low
            
            # Make gradient strength adaptive based on current min_area
            quality_ratio = min(1.0, min_area / 0.0365)
            sigmoid_factor = 1 / (1 + np.exp(-10 * (quality_ratio - 0.5)))
            grad_strength = 0.2 + 0.3 * np.sqrt(adaptive_factor) * sigmoid_factor

            for idx in min_points:
                # Base perturbation: Cauchy distribution with gradient bias
                scale = step_size_bary * cauchy_scale_factor
                du_cauchy = np.random.standard_cauchy() * scale
                dv_cauchy = np.random.standard_cauchy() * scale
                
                # Add gradient direction if available
                grad = gradients[idx]
                du_grad = grad_strength * grad[0] * scale
                dv_grad = grad_strength * grad[1] * scale
                
                # Combine random and gradient-based movement
                du = du_cauchy + du_grad
                dv = dv_cauchy + dv_grad
                
                # Convert current point to barycentric
                u, v = to_bary(candidate[idx])
                
                # Apply perturbation in barycentric coordinates
                u_new, v_new = u + du, v + dv

                # Clamp to simplex [0,1] and adjust for u+v<=1
                u_new = max(0.0, min(1.0, u_new))
                v_new = max(0.0, min(1.0, v_new))
                if u_new + v_new > 1.0:
                    scale = 1.0 / (u_new + v_new)
                    u_new *= scale
                    v_new *= scale

                # Convert back to Cartesian
                new_point = to_cart(u_new, v_new)
                candidate[idx] = new_point
            
            # Ensure distinctness of points
            for i in range(n):
                for j in range(i+1, n):
                    if np.linalg.norm(candidate[i] - candidate[j]) < distinctness_threshold:
                        # Move point j slightly away from point i
                        direction = candidate[j] - candidate[i]
                        if np.linalg.norm(direction) > 0:
                            direction = direction / np.linalg.norm(direction)
                            candidate[j] += direction * distinctness_threshold
            
            # Check and evaluate candidate
            score = get_smallest_triangle_area(candidate)
            if score > best_score:
                best = candidate
                best_score = score
                stagnation_count = 0
                restart_failure_count = 0  # Reset failure count on ANY success
            else:
                stagnation_count += 1

            # Adaptive step decay (slower than before)
            step_size *= 0.99

            # Step size reset (tuned to fraction of initial)
            if stagnation_count >= 10:
                step_size = 0.1 * initial_step
                stagnation_count = 0

            # Global restart after prolonged stagnation
            if stagnation_count >= 30:
                # Generate restart candidate by perturbing all points with increasing step
                candidate_restart = best.copy()
                restart_failure_count += 1
                # CHANGED FROM LINEAR TO EXPONENTIAL GROWTH - FASTER ESCAPE FROM DEEP MINIMA
                step_multiplier = 1.2 ** restart_failure_count  # Exponential increase
                step_size_bary_restart = (0.5 * initial_step * step_multiplier) / side_length
                
                # Make gradient strength adaptive for restarts too
                quality_ratio = min(1.0, best_score / 0.0365)
                sigmoid_factor = 1 / (1 + np.exp(-10 * (quality_ratio - 0.5)))
                grad_strength_restart = 0.2 + 0.3 * np.sqrt(adaptive_factor) * sigmoid_factor
                
                for i in range(n):
                    u, v = to_bary(best[i])
                    # Use Cauchy distribution for restarts too
                    du = np.random.standard_cauchy() * step_size_bary_restart
                    dv = np.random.standard_cauchy() * step_size_bary_restart
                    
                    # Add gradient bias with adaptive strength
                    if freq[i] > 0:
                        grad = gradients[i]
                        du += grad_strength_restart * grad[0] * step_size_bary_restart
                        dv += grad_strength_restart * grad[1] * step_size_bary_restart
                    
                    u_new, v_new = u + du, v + dv
                    u_new = max(0.0, min(1.0, u_new))
                    v_new = max(0.0, min(1.0, v_new))
                    if u_new + v_new > 1.0:
                        scale = 1.0 / (u_new + v_new)
                        u_new *= scale
                        v_new *= scale
                    candidate_restart[i] = to_cart(u_new, v_new)
                
                # Ensure distinctness for restart candidate
                for i in range(n):
                    for j in range(i+1, n):
                        if np.linalg.norm(candidate_restart[i] - candidate_restart[j]) < distinctness_threshold:
                            direction = candidate_restart[j] - candidate_restart[i]
                            if np.linalg.norm(direction) > 0:
                                direction = direction / np.linalg.norm(direction)
                                candidate_restart[j] += direction * distinctness_threshold
                
                # Evaluate restart candidate
                score_restart = get_smallest_triangle_area(candidate_restart)
                if score_restart > best_score:
                    best = candidate_restart
                    best_score = score_restart
                    restart_failure_count = 0  # Reset on success
                
                # Reset search parameters regardless of restart success
                step_size = initial_step
                stagnation_count = 0

            # Adaptive stopping
            if step_size < adaptive_stopping_threshold:
                break

        return best

    return improve