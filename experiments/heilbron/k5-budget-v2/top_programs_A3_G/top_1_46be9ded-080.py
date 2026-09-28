# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    base_seed = 42
    n_chains = 30  # Increased from 15 to 30 for better exploration
    best_points = None
    best_min_area = -1

    def random_initialization(n=11):
        points = []
        max_attempts = 1000
        for i in range(n):
            attempt = 0
            while attempt < max_attempts:
                u = random.random()
                v = random.random()
                if u + v > 1:
                    u = 1 - u
                    v = 1 - v
                x = A[0] + u * (B[0] - A[0]) + v * (C[0] - A[0])
                y = A[1] + u * (B[1] - A[1]) + v * (C[1] - A[1])
                p = np.array([x, y])
                
                if any(np.linalg.norm(p - q) < 1e-5 for q in points):
                    attempt += 1
                    continue
                    
                if i >= 2:
                    collinear = False
                    for j in range(i):
                        for k in range(j+1, i):
                            area = 0.5 * abs(
                                points[j][0]*(points[k][1]-p[1]) + 
                                points[k][0]*(p[1]-points[j][1]) + 
                                p[0]*(points[j][1]-points[k][1])
                            )
                            if area < 1e-5:
                                collinear = True
                                break
                        if collinear:
                            break
                    if collinear:
                        attempt += 1
                        continue
                
                points.append(p)
                break
            
            if attempt == max_attempts and len(points) < n:
                last = points[-1]
                dx = random.uniform(-0.01, 0.01)
                dy = random.uniform(-0.01, 0.01)
                p = last + np.array([dx, dy])
                if is_inside_triangle(p, A, B, C) and not any(np.linalg.norm(p - q) < 1e-5 for q in points):
                    points.append(p)
        return np.array(points)
    
    def project_to_boundary(point, A, B, C):
        """Project a point outside the triangle to the nearest point on the boundary"""
        # If already inside, return as is
        if is_inside_triangle(point, A, B, C):
            return point
        
        # Calculate distances to each edge and find the closest point
        def point_to_line_dist(p, a, b):
            # Vector AB
            ab = b - a
            # Vector AP
            ap = p - a
            # Length of AB
            ab_length = np.linalg.norm(ab)
            if ab_length < 1e-10:  # Avoid division by zero
                return a, np.linalg.norm(p - a)
            # Unit vector in direction of AB
            ab_unit = ab / ab_length
            # Projection of AP onto AB
            proj = np.dot(ap, ab_unit)
            # Clamp projection to [0, ab_length]
            proj = max(0, min(ab_length, proj))
            # Nearest point on line
            nearest = a + proj * ab_unit
            return nearest, np.linalg.norm(p - nearest)
        
        # Check all three edges
        nearest_ab, dist_ab = point_to_line_dist(point, A, B)
        nearest_bc, dist_bc = point_to_line_dist(point, B, C)
        nearest_ca, dist_ca = point_to_line_dist(point, C, A)
        
        # Find the closest boundary point
        if dist_ab <= dist_bc and dist_ab <= dist_ca:
            return nearest_ab
        elif dist_bc <= dist_ab and dist_bc <= dist_ca:
            return nearest_bc
        else:
            return nearest_ca

    def literature_initialization(n=11):
        """Create a configuration based on known Heilbronn patterns for 11 points with strategic placement"""
        # Calculate triangle dimensions
        base = B[0] - A[0]
        height = C[1] - A[1]
        
        # Create points in a pattern known to be good for Heilbron
        points = []
        
        # Boundary points (vertices)
        points.append(A)
        points.append(B)
        points.append(C)
        
        # Points along edges using non-uniform spacing (golden ratio inspired)
        points.append(0.15 * A + 0.85 * B)
        points.append(0.35 * A + 0.65 * B)
        points.append(0.65 * A + 0.35 * B)
        points.append(0.85 * A + 0.15 * B)
        
        # Points along other edges (only two per edge to avoid overcrowding)
        points.append(0.2 * A + 0.8 * C)
        points.append(0.8 * A + 0.2 * C)
        points.append(0.2 * B + 0.8 * C)
        points.append(0.8 * B + 0.2 * C)
        
        # Strategic 11th point: golden ratio along median from A
        # Instead of two center points, we use a single strategic placement
        median_point = (B + C) / 2
        strategic_point = A + 0.618 * (median_point - A)  # Golden ratio placement
        points.append(strategic_point)
        
        # Add controlled perturbations to all points
        perturbed_points = []
        for i, p in enumerate(points[:n]):
            # Determine if point is on boundary
            is_boundary = (i < 10)  # First 10 points are on boundary
            
            if is_boundary:
                max_perturb = 0.025  # Smaller perturbations for boundary
            else:
                max_perturb = 0.015  # Even smaller for interior
            
            dx = random.uniform(-max_perturb, max_perturb)
            dy = random.uniform(-max_perturb, max_perturb)
            candidate = p + np.array([dx, dy])
            
            # Project to boundary if needed
            candidate = project_to_boundary(candidate, A, B, C)
            
            perturbed_points.append(candidate)
        
        return np.array(perturbed_points)

    def heuristic_initialization(n=11):
        points = literature_initialization(n-1)
        center = np.array([(A[0]+B[0]+C[0])/3, (A[1]+B[1]+C[1])/3])
        new_point = center
        attempt = 0
        while attempt < 100:
            dx = random.uniform(-0.015, 0.015)  # Smaller perturbations
            dy = random.uniform(-0.015, 0.015)
            candidate = center + np.array([dx, dy])
            
            # Project to boundary if needed
            candidate = project_to_boundary(candidate, A, B, C)
            
            if any(np.linalg.norm(candidate - p) < 1e-5 for p in points):
                attempt += 1
                continue

            collinear = False
            for i in range(len(points)):
                for j in range(i+1, len(points)):
                    area = 0.5 * abs(
                        points[i][0]*(points[j][1]-candidate[1]) + 
                        points[j][0]*(candidate[1]-points[i][1]) + 
                        candidate[0]*(points[i][1]-points[j][1])
                    )
                    if area < 1e-5:
                        collinear = True
                        break
                if collinear:
                    break
            
            if not collinear:
                new_point = candidate
                break
            attempt += 1
        
        if attempt == 100:
            new_point = random_initialization(1)[0]
        
        return np.vstack([points, new_point])

    def get_min_triangle_area_with_indices(points):
        n = len(points)
        min_area = float('inf')
        min_indices = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        points[i,0]*(points[j,1]-points[k,1]) + 
                        points[j,0]*(points[k,1]-points[i,1]) + 
                        points[k,0]*(points[i,1]-points[j,1])
                    )
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        return min_area, min_indices

    # Adaptive strategy weights based on historical success
    strategy_weights = [0.7, 0.2, 0.1]  # literature, heuristic, random
    
    for chain in range(n_chains):
        random.seed(base_seed + chain)
        np.random.seed(base_seed + chain)

        # Weighted selection of initialization method
        init_type = random.choices([0, 1, 2], weights=strategy_weights, k=1)[0]
        
        if init_type == 0:
            points = literature_initialization()
        elif init_type == 1:
            points = heuristic_initialization()
        else:
            points = random_initialization()

        if not is_inside_triangle(points, A, B, C):
            points = literature_initialization()

        current_points = points
        best_chain_points = current_points.copy()
        best_chain_min_area = get_smallest_triangle_area(current_points)

        initial_T = 0.1
        n_iter = 10000
        base_step = 0.03  # Smaller base step for finer control
        no_improve_count = 0
        max_no_improve = 1000  # For reheating

        for iter in range(n_iter):
            current_min_area, min_indices = get_min_triangle_area_with_indices(current_points)
            
            # Adaptive multi-point perturbation
            multi_point_prob = 0.7 * (1 - iter/n_iter)**0.5  # Decay probability of multi-point moves
            num_points_to_perturb = 1
            if random.random() < multi_point_prob:
                num_points_to_perturb = random.randint(2, min(3, len(min_indices)))
            
            # 15% chance of global perturbation (not related to smallest triangle)
            global_perturb_prob = 0.15
            if random.random() < global_perturb_prob:
                points_to_perturb = [random.randint(0, 10)]
            else:
                # Select points to perturb from the smallest triangle
                points_to_perturb = random.sample(min_indices, num_points_to_perturb)
            
            # Calculate adaptive step size - based on iteration count instead of current quality
            step_size = base_step * (1 - iter/n_iter)**0.3
            step_size = max(0.005, min(step_size, 0.05))  # Tighter bounds for stability
            
            # Create candidate configuration with perturbed points
            candidate_points = current_points.copy()
            valid_candidate = True
            
            for idx in points_to_perturb:
                dx = random.uniform(-step_size, step_size)
                dy = random.uniform(-step_size, step_size)
                new_point = current_points[idx] + np.array([dx, dy])
                
                # Project to boundary instead of rejecting
                new_point = project_to_boundary(new_point, A, B, C)
                
                # Check distinctness
                if any(np.linalg.norm(new_point - p) < 1e-5 for i, p in enumerate(candidate_points) if i != idx):
                    valid_candidate = False
                    break
                
                candidate_points[idx] = new_point
            
            if not valid_candidate:
                continue
                
            # Check collinearity for the perturbed points
            if num_points_to_perturb > 1 or global_perturb_prob:
                collinear = False
                for i in range(len(points_to_perturb)):
                    for j in range(i+1, len(points_to_perturb)):
                        idx1, idx2 = points_to_perturb[i], points_to_perturb[j]
                        for k in range(len(candidate_points)):
                            if k not in points_to_perturb:
                                area = 0.5 * abs(
                                    candidate_points[idx1,0]*(candidate_points[idx2,1]-candidate_points[k,1]) + 
                                    candidate_points[idx2,0]*(candidate_points[k,1]-candidate_points[idx1,1]) + 
                                    candidate_points[k,0]*(candidate_points[idx1,1]-candidate_points[idx2,1])
                                )
                                if area < 1e-5:
                                    collinear = True
                                    break
                        if collinear:
                            break
                    if collinear:
                        break
                if collinear:
                    continue
            
            new_min_area = get_smallest_triangle_area(candidate_points)

            if new_min_area > best_chain_min_area:
                best_chain_min_area = new_min_area
                best_chain_points = candidate_points.copy()
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Reheating mechanism when stuck
            if no_improve_count > max_no_improve:
                T = initial_T
                no_improve_count = 0
            else:
                T = initial_T * (0.999 ** iter)  # Slower cooling rate

            delta = new_min_area - current_min_area
            if delta > 0 or (T > 1e-5 and random.random() < np.exp(delta / T)):
                current_points = candidate_points

        if best_chain_min_area > best_min_area:
            best_min_area = best_chain_min_area
            best_points = best_chain_points.copy()

    return best_points

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib


def _d_entrypoint():
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
        # Create configuration-specific seed to avoid predictability
        config_hash = hashlib.md5(points.tobytes()).hexdigest()
        seed = int(config_hash[:8], 16) % (2**32 - 1)
        np.random.seed(seed)
        
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

        def compute_multi_gradient_for_point(coords, idx, relevant_triplets):
            if not relevant_triplets:
                return np.random.normal(0, 0.1, size=2)

            # Compute weighted gradient from all relevant triplets
            total_weight = 0
            combined_grad = np.zeros(2)
            
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
                
                # Weight by inverse area (smaller areas get higher weight)
                weight = 1.0 / (area_val + 1e-10)
                combined_grad += weight * grad
                total_weight += weight

            if total_weight > 0:
                combined_grad = combined_grad / total_weight
            else:
                combined_grad = np.random.normal(0, 0.1, size=2)

            return combined_grad

        max_rounds = 500
        initial_step = 0.05
        T0 = 0.02  # Increased from 0.01 for better exploration
        alpha = 0.9995  # Slower cooling rate for more exploration

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score

        # Adaptive stopping parameters
        plateau_threshold = 0.00001
        plateau_counter = 0
        max_plateau = 50
        restart_counter = 0
        max_restarts = 3
        min_score_bound = 0.005  # Conservative lower bound for min_area

        for round_idx in range(max_rounds):
            # Compute top-k smallest triangles (k is adaptive)
            top_k_areas, top_k_triplets = compute_min_area_and_triplets(current, 5)
            current_score = top_k_areas[0]  # The smallest area
            
            # Adaptive k for gradient computation based on area distribution
            if len(top_k_areas) > 1:
                area_gap = (top_k_areas[1] - top_k_areas[0]) / (top_k_areas[0] + 1e-10)
                k_adaptive = min(7, max(1, int(1 + 0.1 / max(area_gap, 1e-5))))
            else:
                k_adaptive = 1
            
            # Get the top k_adaptive smallest triangles
            top_areas = top_k_areas[:k_adaptive]
            top_triplets = top_k_triplets[:k_adaptive]

            # Point selection with adaptive bias
            if np.random.rand() < 0.9:
                # Select a random small triangle
                triangle_idx = np.random.randint(0, len(top_triplets))
                triplet = top_triplets[triangle_idx]
                
                # COORDINATED MULTI-POINT MOVEMENT
                # For each point in the triplet, compute gradient
                gradients = []
                for idx in triplet:
                    # Filter triplets that include the point idx
                    relevant_triplets = []
                    for i, t in enumerate(top_triplets):
                        if idx in t:
                            relevant_triplets.append((top_areas[i], t))
                    grad = compute_multi_gradient_for_point(current, idx, relevant_triplets)
                    gradients.append(grad)
                
                # Slower step size decay
                step = initial_step * (0.998 ** round_idx)
                
                # Scale step by distance to boundary with increased threshold
                dist_to_boundary = min(distance_to_triangle_boundary(current[idx], A, B, C) for idx in triplet)
                # Increased threshold from 0.2 to 0.3 and added adaptive scaling
                boundary_factor = max(0.1, min(1.0, dist_to_boundary / 0.3)) * (1.0 + 5.0 * current_score)
                adapted_step = step * boundary_factor

                # Create candidate by moving all three points
                candidate = current.copy()
                # Calculate gradient magnitudes for relative weighting
                grad_magnitudes = [np.linalg.norm(g) for g in gradients]
                max_grad_mag = max(grad_magnitudes) if grad_magnitudes else 1.0
                
                for i, idx in enumerate(triplet):
                    grad_mag = grad_magnitudes[i]
                    # Weight steps by relative gradient magnitude (points with smaller gradients move more)
                    movement_weight = 1.0 + 0.5 * (max_grad_mag - grad_mag) / (max_grad_mag + 1e-8)
                    movement = gradients[i] * (adapted_step * movement_weight)
                    candidate[idx] += movement
                
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
                    # Reset plateau counter on improvement
                    plateau_counter = 0
                else:
                    delta = current_score - new_score
                    T = T0 * (alpha ** round_idx)
                    if np.random.rand() < np.exp(-delta / T):
                        current = candidate
                        current_score = new_score
                    
                    # Check for plateau
                    if current_score - best_score < plateau_threshold:
                        plateau_counter += 1
                    else:
                        plateau_counter = 0
            else:
                # Fallback to single-point movement
                idx = np.random.randint(0, 11)
                
                # Filter triplets that include the point idx
                relevant_triplets = []
                for i, t in enumerate(top_triplets):
                    if idx in t:
                        relevant_triplets.append((top_areas[i], t))
                
                grad = compute_multi_gradient_for_point(current, idx, relevant_triplets)
                
                # Slower step size decay
                step = initial_step * (0.998 ** round_idx)
                
                # Scale step by distance to boundary with increased threshold
                dist_to_boundary = distance_to_triangle_boundary(current[idx], A, B, C)
                boundary_factor = max(0.1, min(1.0, dist_to_boundary / 0.3)) * (1.0 + 5.0 * current_score)
                adapted_step = step * boundary_factor

                candidate = current.copy()
                
                grad_magnitude = np.linalg.norm(grad)
                if grad_magnitude > 1e-8:
                    movement = grad * (adapted_step * min(1.0, grad_magnitude))
                    candidate[idx] += movement
                
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
                    plateau_counter = 0
                else:
                    delta = current_score - new_score
                    T = T0 * (alpha ** round_idx)
                    if np.random.rand() < np.exp(-delta / T):
                        current = candidate
                        current_score = new_score
                    
                    if current_score - best_score < plateau_threshold:
                        plateau_counter += 1
                    else:
                        plateau_counter = 0

            # Adaptive restart mechanism after plateau
            if plateau_counter > max_plateau and restart_counter < max_restarts:
                # Calculate perturbation magnitude based on current progress
                perturbation_scale = 0.01 * (1.0 - current_score / min_score_bound)
                perturbation_scale = max(0.001, min(0.05, perturbation_scale))
                
                # Restart from best solution with controlled perturbation
                current = best.copy()
                for i in range(11):
                    if np.random.rand() < 0.7:  # Perturb 70% of points
                        current[i] += np.random.normal(0, perturbation_scale, size=2)
                        
                # Project any outside points back to triangle
                for i in range(11):
                    if not is_inside_triangle(current[i], A, B, C):
                        current[i] = project_to_triangle(current[i], A, B, C)
                
                current_score = get_smallest_triangle_area(current)
                plateau_counter = 0
                restart_counter += 1

            # Adaptive stopping
            if restart_counter >= max_restarts and plateau_counter > max_plateau:
                break

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)