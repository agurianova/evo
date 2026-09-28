import numpy as np
from itertools import combinations
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle

np.random.seed(42)

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

def entrypoint():
    A_tri, B_tri, C_tri = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        best = points.copy()
        best_score = get_smallest_triangle_area(points)
        current_score = best_score

        # ADAPTIVE MULTI-PHASE OPTIMIZATION (replaces fixed phase schedule)
        phase = 0
        step_sizes = [0.02, 0.005, 0.001]
        plateau_threshold = 1e-6
        plateau_window = 20
        improvement_history = np.zeros(plateau_window)
        history_idx = 0
        
        # Track recent improvements for adaptive temperature decay
        improvement_history_temp = []
        history_window = 50
        
        no_improve_count = 0
        temperature = 0.05
        min_temperature = 0.001
        
        # Track point involvement in small triangles for targeted perturbations
        point_involvement = np.zeros(11)

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
            
            # === REVAMPED: Dynamic Threshold Selection Strategy ===
            # Wider threshold to maintain exploration breadth
            areas = [t[0] for t in triangles]
            mean_area = np.mean(areas)
            std_dev = np.std(areas)
            
            # INCREASED THRESHOLD BREADTH: Base value raised to 0.0015, min threshold 0.0002
            if current_score <= 0.028:
                area_threshold_factor = 0.2 + 0.5 * (std_dev / mean_area)
                area_threshold_factor = min(max(area_threshold_factor, 0.05), 0.3)
                area_threshold = smallest_area * (1 + area_threshold_factor)
            else:
                # Absolute threshold with wider base value and minimum threshold
                base_threshold = 0.0015
                min_threshold = 0.0002
                area_threshold = smallest_area + max(base_threshold * (1 - current_score / 0.0365), min_threshold)
            
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
                # === REVAMPED: Smooth Gradient Weighting Strategy ===
                # Shifted transition point to 0.030 for better high-quality performance
                transition_point = 0.030
                transition_width = 0.008
                sigmoid = 1.0 / (1.0 + np.exp(-(current_score - transition_point) / transition_width))
                weight_log = 1.0 / (np.log(1 + 10 * abs_area) + 1e-10)
                weight_sqrt = 1.0 / np.sqrt(abs_area + 1e-10)
                weight = sigmoid * weight_log + (1 - sigmoid) * weight_sqrt
                
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

            # Scale gradients by point involvement count
            for i in range(11):
                if point_involvement[i] > 0:
                    # === REVAMPED: Quadratic Point Involvement Scaling ===
                    # Emphasize critical points more effectively
                    scale_factor = 0.2 + 0.05 * (point_involvement[i] ** 1.5)
                    gradients[i] *= scale_factor

            # === REVAMPED: Adaptive Phase Management ===
            # Check for improvement plateau to trigger phase transition
            improvement_history[history_idx] = current_score - best_score
            history_idx = (history_idx + 1) % plateau_window
            
            # Calculate recent average improvement
            valid_history = improvement_history[:history_idx] if history_idx < plateau_window else improvement_history
            avg_improvement = np.mean(valid_history) if len(valid_history) > 0 else 0
n            # Transition to next phase if plateau detected
            if phase < len(step_sizes) - 1 and avg_improvement < plateau_threshold:
                phase += 1

            # Use current phase's step size
            step_size = step_sizes[phase]

            # === REVAMPED: Robust Gradient Normalization ===
            # Cap exponent at 0.7 and add minimum magnitude threshold
            norm_exponent = min(0.7, 0.5 + 0.3 * (current_score / 0.0365))
            
            # Create candidate by moving all points
            candidate = current.copy()
            for i in range(11):
                if np.linalg.norm(gradients[i]) > 1e-4:  # Minimum magnitude threshold
                    # Adaptive normalization to retain magnitude sensitivity
                    norm = np.linalg.norm(gradients[i])
                    grad_dir = gradients[i] / (norm ** norm_exponent)
                    candidate[i] += step_size * grad_dir

            # Project any points outside the triangle back onto the boundary
            for i in range(11):
                if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                    candidate[i] = project_point_to_triangle(candidate[i], A_tri, B_tri, C_tri)

            new_score = get_smallest_triangle_area(candidate)

            # Track improvement for adaptive temperature
            improvement = new_score - current_score
            improvement_history_temp.append(improvement)
            if len(improvement_history_temp) > history_window:
                improvement_history_temp.pop(0)
            
            # ADAPTIVE TEMPERATURE DECAY based on recent improvement rate
            if len(improvement_history_temp) > 0:
                avg_improvement_temp = np.mean(improvement_history_temp)
                if avg_improvement_temp > 1e-6:  # Making good progress
                    temperature = max(min_temperature, temperature * 0.92)
                else:  # Stuck, maintain exploration longer
                    temperature = max(min_temperature, temperature * 0.9995)
            
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
                delta = new_score - current_score
                if delta < 0:
                    prob = np.exp(delta / temperature)
                    if np.random.random() < prob:
                        current = candidate.copy()
                        current_score = new_score
                        no_improve_count = 0
                    else:
                        no_improve_count += 1
                else:
                    no_improve_count += 1

            # === REVAMPED: Adaptive Global Perturbation Strategy ===
            # Lowered threshold and made more responsive to difficulty
            difficulty_metric = current_score / 0.0365
            base_threshold = 30
            coefficient = 1.5
            perturbation_threshold = base_threshold * (1 + coefficient * (1 - difficulty_metric))
            perturbation_threshold = max(30, min(perturbation_threshold, 150))

            # Targeted global perturbation to escape deep local minima
            if no_improve_count >= perturbation_threshold:
                # === REVAMPED: Inverse Involvement Scaling for Perturbations ===
                # Focus larger moves on most problematic points
                sorted_involvement = np.argsort(point_involvement)
                percentile = np.zeros(11)
                for idx, i in enumerate(sorted_involvement):
                    percentile[i] = idx / 10.0  # 0.0 to 1.0 percentile
                
                # Base perturbation scaled by inverse percentile (more for critical points)
                perturbation = np.zeros_like(current)
                for i in range(11):
                    # Inverse relationship: higher involvement = larger perturbation
                    scale = 0.02 * (1 + 1.5 * (1 - percentile[i]))
                    perturbation[i] = np.random.uniform(-scale, scale, size=2)
                
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

            # === REVAMPED: Strategic Large-Scale Perturbation ===
            # Made more adaptive based on point criticality
            if no_improve_count > 80 and np.random.random() < 0.15:
                # Sort points by involvement (highest first)
                sorted_indices = np.argsort(point_involvement)[::-1]
                num_to_perturb = max(2, min(5, int(4 * (1 - current_score / 0.0365) + 2)))
                perturb_indices = sorted_indices[:num_to_perturb]
                
                # Apply larger perturbations to strategic points with adaptive scaling
                for idx in perturb_indices:
                    # Scale based on how critical the point is
                    criticality = point_involvement[idx] / max(1, np.max(point_involvement))
                    base_scale = 0.04
                    adaptive_scale = base_scale * (1 + 1.5 * criticality)
                    direction = np.random.uniform(-1, 1, size=2)
                    direction = direction / (np.linalg.norm(direction) + 1e-10)
                    current[idx] += adaptive_scale * direction
                    
                    # Project back to triangle if needed
                    if not is_inside_triangle(current[idx], A_tri, B_tri, C_tri):
                        current[idx] = project_point_to_triangle(current[idx], A_tri, B_tri, C_tri)
                
                current_score = get_smallest_triangle_area(current)
                no_improve_count = 0

        return best

    return improve