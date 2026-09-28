from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_triangle(point, A, B, C):
        """Project a point to the nearest location inside the triangle."""
        # If already inside, return as is
        if is_inside_triangle(point, A, B, C):
            return point
        
        # Check each edge
        edges = [(A, B), (B, C), (C, A)]
        min_dist = float('inf')
        closest_point = None
        
        for edge in edges:
            p1, p2 = edge
            # Vector from p1 to p2
            v = p2 - p1
            # Vector from p1 to point
            w = point - p1
            
            # Project w onto v
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 == 0:
                b = 0
            else:
                b = c1 / c2
            
            # Find closest point on the line segment
            if b <= 0:
                proj = p1
            elif b >= 1:
                proj = p2
            else:
                proj = p1 + b * v
            
            # Calculate distance
            dist = np.linalg.norm(point - proj)
            if dist < min_dist:
                min_dist = dist
                closest_point = proj
        
        return closest_point

    def distance_to_triangle_boundary(point, A, B, C):
        """Calculate distance from point to nearest triangle edge."""
        if is_inside_triangle(point, A, B, C):
            # Check each edge
            edges = [(A, B), (B, C), (C, A)]
            min_dist = float('inf')
            
            for edge in edges:
                p1, p2 = edge
                # Vector from p1 to p2
                v = p2 - p1
                # Vector from p1 to point
                w = point - p1
                
                # Project w onto v
                c1 = np.dot(w, v)
                c2 = np.dot(v, v)
                if c2 == 0:
                    b = 0
                else:
                    b = c1 / c2
                
                # Find closest point on the line segment
                if b <= 0:
                    proj = p1
                elif b >= 1:
                    proj = p2
                else:
                    proj = p1 + b * v
                
                # Calculate distance
                dist = np.linalg.norm(point - proj)
                min_dist = min(min_dist, dist)
            
            return min_dist
        else:
            # Point is outside, use projection distance
            projected = project_to_triangle(point, A, B, C)
            return np.linalg.norm(point - projected)

    def improve(points: np.ndarray) -> np.ndarray:
        def compute_min_area_and_triplets(coords, k=3):
            n = coords.shape[0]
            areas = []
            triplets = []
            
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = coords[i], coords[j], coords[k]
                        area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        areas.append(area_val)
                        triplets.append((i, j, k))
            
            # Sort by area and take top-k smallest
            sorted_indices = np.argsort(areas)
            top_k_areas = [areas[i] for i in sorted_indices[:k]]
            top_k_triplets = [triplets[i] for i in sorted_indices[:k]]
            
            return top_k_areas, top_k_triplets

        def compute_multi_gradient_for_point(coords, idx, min_area, area_gap):
            # Dynamically determine k based on area distribution
            k_val = max(3, min(10, int(0.01 / max(area_gap, 1e-5))))
            top_k_areas, top_k_triplets = compute_min_area_and_triplets(coords, k_val)
            
            # Filter triplets that include the point idx
            relevant_triplets = []
            for i, triplet in enumerate(top_k_triplets):
                if idx in triplet:
                    relevant_triplets.append((top_k_areas[i], triplet))
            
            if not relevant_triplets:
                # Enhanced exploration strategy using principal components
                centered = coords - np.mean(coords, axis=0)
                cov = np.cov(centered.T)
                try:
                    eigenvals, eigenvecs = np.linalg.eigh(cov)
                    # Move along direction of largest variance
                    return eigenvecs[:, -1] * 0.1
                except:
                    return np.random.normal(0, 0.1, size=2)

            # Compute weighted gradient from all relevant triplets with adaptive weighting
            total_weight = 0
            combined_grad = np.zeros(2)
            
            # Calculate spread factor for adaptive weighting
            area_range = top_k_areas[-1] - min_area + 1e-5
            spread_factor = 1.0 / max(0.1, min(10.0, area_gap / area_range))
            
            for area_val, triplet in relevant_triplets:
                # Find the position of idx in the triplet
                pos = triplet.index(idx)
                i, j, k = triplet
                a, b, c = coords[i], coords[j], coords[k]
                
                # Calculate area and gradient
                S = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                sign_S = 1 if S >= 0 else -1
                
                # Determine which point is idx and compute appropriate gradient
                if pos == 0:  # idx is point a
                    grad_x = (b[1] - c[1]) * sign_S
                    grad_y = (c[0] - b[0]) * sign_S
                elif pos == 1:  # idx is point b
                    grad_x = (c[1] - a[1]) * sign_S
                    grad_y = (a[0] - c[0]) * sign_S
                else:  # idx is point c
                    grad_x = (a[1] - b[1]) * sign_S
                    grad_y = (b[0] - a[0]) * sign_S
                
                grad = np.array([grad_x, grad_y])
                
                # Adaptive exponential weighting based on area spread
                weight = np.exp(-3.0 * spread_factor * (area_val - min_area) / max(area_gap, 1e-5))
                combined_grad += weight * grad
                total_weight += weight

            if total_weight > 0:
                combined_grad = combined_grad / total_weight
            
            # Phase-dependent gradient scaling
            grad_norm = np.linalg.norm(combined_grad)
            if grad_norm > 1e-8:
                # Scale based on optimization phase
                if round_idx < phase1_rounds:  # Exploration phase
                    scale = min(1.5, max(0.2, grad_norm))
                else:  # Refinement phase
                    scale = min(0.8, max(0.05, grad_norm))
                combined_grad = combined_grad / grad_norm * scale
            else:
                # Enhanced exploration strategy using principal components
                centered = coords - np.mean(coords, axis=0)
                cov = np.cov(centered.T)
                try:
                    eigenvals, eigenvecs = np.linalg.eigh(cov)
                    # Move along direction of largest variance
                    combined_grad = eigenvecs[:, -1] * 0.1
                except:
                    combined_grad = np.random.normal(0, 0.1, size=2)

            return combined_grad

        # Calculate initial area distribution to set dynamic parameters
        initial_min_area, _ = compute_min_area_and_triplets(points, 2)
        area_gap = initial_min_area[1] - initial_min_area[0] if len(initial_min_area) > 1 else 0.001
        
        # Dynamic temperature initialization based on area spread
        T0 = 0.01 * max(1.0, min(10.0, area_gap / 1e-4))
        
        max_rounds = 500
        initial_step = 0.05
        
        # Minimum iterations proportional to initial configuration quality
        min_iterations = max(100, int(200 * (initial_min_area[0] / 0.0365)))
        
        # Two-phase annealing schedule with dynamic phase transition
        phase1_rounds = int(max_rounds * 0.3)
        phase2_rounds = max_rounds - phase1_rounds
        
        # Slower cooling for phase 1 (exploration), faster for phase 2 (refinement)
        temp_alpha_phase1 = 0.9995
        temp_alpha_phase2 = 0.998
        step_alpha_phase1 = 0.999
        step_alpha_phase2 = 0.997

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score

        # For adaptive stopping
        no_improve_count = 0
        # Fixed stopping criteria issue by adding minimum iteration requirement
        max_no_improve = max(50, min(200, int(100 * (0.01 / max(area_gap, 1e-5)))))

        for round_idx in range(max_rounds):
            # Get top-k smallest triangles for reference
            top_k_areas, _ = compute_min_area_and_triplets(current, 3)
            current_score = top_k_areas[0]  # The smallest area
            area_gap = top_k_areas[1] - top_k_areas[0] if len(top_k_areas) > 1 else 0.001
            
            # Stabilized adaptive factor calculation with minimum threshold
            adaptive_factor = min(1.0, 0.1 / max(area_gap, 1e-5))
            bias = min(0.9, 0.8 + 0.1 * (round_idx / max_rounds) * adaptive_factor)
            
            # Dynamic cooling based on phase
            if round_idx < phase1_rounds:
                T = T0 * (temp_alpha_phase1 ** round_idx)
                step = initial_step * (step_alpha_phase1 ** round_idx)
            else:
                phase2_idx = round_idx - phase1_rounds
                T = T0 * (temp_alpha_phase1 ** phase1_rounds) * (temp_alpha_phase2 ** phase2_idx)
                step = initial_step * (step_alpha_phase1 ** phase1_rounds) * (step_alpha_phase2 ** phase2_idx)
            
            # Adaptive coordinated movement with improved calculation
            improvement_rate = (round_idx + 1) / max(1, no_improve_count + 1)
            coord_prob = 0.2 + 0.4 * min(1.0, area_gap / 0.005) * max(0.2, 1.0 - improvement_rate)
            coord_step_multiplier = 0.8
            
            # Coordinated movement with adaptive probability
            if np.random.rand() < coord_prob:
                _, top_triplets = compute_min_area_and_triplets(current, 1)
                triplet = top_triplets[0]
                
                # Move all three points in the smallest triangle
                candidate = current.copy()
                for idx in triplet:
                    dist_to_boundary = distance_to_triangle_boundary(candidate[idx], A, B, C)
                    
                    # Adaptive boundary factor with dynamic threshold
                    local_points = np.delete(current, idx, axis=0)
                    local_density = 1.0 / (np.mean([np.linalg.norm(candidate[idx] - p) for p in local_points]) + 1e-5)
                    adaptive_threshold = max(0.05, min(0.2, 0.1 * local_density))
                    boundary_factor = max(0.05, min(1.0, dist_to_boundary / adaptive_threshold))
                    
                    adapted_step = step * boundary_factor * coord_step_multiplier
                    
                    grad = compute_multi_gradient_for_point(current, idx, top_k_areas[0], area_gap)
                    candidate[idx] += grad * adapted_step
            else:
                # Point selection with adaptive bias
                if np.random.rand() < bias:
                    _, top_triplets = compute_min_area_and_triplets(current, 1)
                    triplet = top_triplets[0]
                    idx = np.random.choice(triplet)
                else:
                    idx = np.random.randint(0, 11)
                
                candidate = current.copy()
                
                # Distance to boundary for adaptive step size
                dist_to_boundary = distance_to_triangle_boundary(current[idx], A, B, C)
                
                # Adaptive boundary factor with dynamic threshold
                local_points = np.delete(current, idx, axis=0)
                local_density = 1.0 / (np.mean([np.linalg.norm(current[idx] - p) for p in local_points]) + 1e-5)
                adaptive_threshold = max(0.05, min(0.2, 0.1 * local_density))
                boundary_factor = max(0.05, min(1.0, dist_to_boundary / adaptive_threshold))
                
                adapted_step = step * boundary_factor

                # Multi-triangle gradient-based move
                grad = compute_multi_gradient_for_point(current, idx, top_k_areas[0], area_gap)
                candidate[idx] += grad * adapted_step

            # Project to triangle boundary if outside
            for i in range(11):
                if not is_inside_triangle(candidate[i], A, B, C):
                    candidate[i] = project_to_triangle(candidate[i], A, B, C)

            new_score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            if new_score > current_score:
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
                    no_improve_count = 0
                else:
                    no_improve_count += 1
            else:
                delta = current_score - new_score
                if np.random.rand() < np.exp(-delta / T):
                    current = candidate
                    current_score = new_score
                no_improve_count += 1

            # Dynamic phase transition based on improvement rate
            if no_improve_count > max(20, int(0.1 * round_idx)):
                # Slow improvement, extend exploration phase
                phase1_rounds = min(int(max_rounds * 0.5), round_idx + 100)
            else:
                # Good improvement, transition to refinement
                phase1_rounds = max(int(max_rounds * 0.2), round_idx - 100)
                
            # Adaptive stopping: terminate early if no progress but respect minimum iterations
            if round_idx > min_iterations and no_improve_count > max_no_improve:
                break

        return best

    return improve