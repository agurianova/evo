# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def triangle_area(a, b, c):
    return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

def repulsion_initialization(n_points, A, B, C, steps=1000):
    # Generate random points inside triangle
    points = np.zeros((n_points, 2))
    for i in range(n_points):
        r1, r2 = np.random.random(), np.random.random()
        points[i] = (1 - np.sqrt(r1)) * A + np.sqrt(r1) * (1 - r2) * B + np.sqrt(r1) * r2 * C
    
    for _ in range(steps):
        forces = np.zeros((n_points, 2))
        # Repulsion between points
        for i in range(n_points):
            for j in range(i+1, n_points):
                vec = points[i] - points[j]
                dist_sq = np.sum(vec**2)
                if dist_sq < 1e-5:
                    force = np.random.uniform(-0.1, 0.1, 2)
                else:
                    force = vec / (dist_sq ** 1.5)  # F ~ 1/r^2
                forces[i] += force
                forces[j] -= force
        
        # Move points
        points += 0.01 * forces
        
        # Project back to triangle
        for i in range(n_points):
            p = points[i]
            while not is_inside_triangle(np.array([p]), A, B, C):
                centroid = (A + B + C) / 3
                direction = centroid - p
                direction = direction / (np.linalg.norm(direction) + 1e-8)
                p += 0.1 * direction
            points[i] = p
    
    return points

def multi_triangle_refinement(points, A, B, C, n_iter=100, k=3):
    for _ in range(n_iter):
        current_min = get_smallest_triangle_area(points)
        triangles = []
        
        # Collect all triangles
        for i in range(len(points)):
            for j in range(i+1, len(points)):
                for k in range(j+1, len(points)):
                    area = triangle_area(points[i], points[j], points[k])
                    triangles.append((area, i, j, k))
        
        # Sort and get top-k smallest
        triangles.sort(key=lambda x: x[0])
        top_triangles = triangles[:k]
        
        grads = np.zeros_like(points)
        for area, i, j, k in top_triangles:
            a, b, c = points[i], points[j], points[k]
            signed_area = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
            sign = 1.0 if signed_area > 0 else -1.0
            grad_a = sign * 0.5 * np.array([-(c[1]-b[1]), c[0]-b[0]])
            grad_b = sign * 0.5 * np.array([-(a[1]-c[1]), a[0]-c[0]])
            grad_c = sign * 0.5 * np.array([-(b[1]-a[1]), b[0]-a[0]])
            weight = 1.0 / (area + 1e-10)
            grads[i] += weight * grad_a
            grads[j] += weight * grad_b
            grads[k] += weight * grad_c
        
        new_points = points.copy()
        for i in range(len(points)):
            if np.linalg.norm(grads[i]) > 1e-5:
                grads[i] = grads[i] / np.linalg.norm(grads[i])
            new_points[i] = points[i] + 0.01 * grads[i]
            
            # Boundary projection
            if not is_inside_triangle(np.array([new_points[i]]), A, B, C):
                centroid = (A + B + C) / 3
                direction = centroid - new_points[i]
                direction = direction / (np.linalg.norm(direction) + 1e-8)
                new_points[i] = points[i] + 0.5 * 0.01 * direction
        
        new_min = get_smallest_triangle_area(new_points)
        if new_min >= current_min - 1e-10:
            points = new_points
    
    return points

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate initial configuration via repulsion
    points = repulsion_initialization(11, A, B, C)
    best_points = points.copy()
    best_min_area = get_smallest_triangle_area(points)
    
    # Annealing parameters
    initial_T = 0.1
    T = initial_T
    cooling_rate = 0.9995
    n_iter = 50000
    base_step = 0.2
    beta = 0.5  # Adversarial penalty weight
    
    # Track vulnerability for adaptive exploration
    vulnerability = np.zeros(11)
    reset_interval = 5000
    
    for iteration in range(n_iter):
        # Reset vulnerability periodically
        if iteration % reset_interval == 0 and iteration > 0:
            vulnerability = np.zeros(11)

        # Select point with adaptive step size
        idx = np.random.randint(0, 11)
        step = base_step * (1 + 0.1 * min(vulnerability[idx], 10))
        
        # Generate perturbation
        old_point = points[idx].copy()
        dx = np.random.uniform(-step, step)
        dy = np.random.uniform(-step, step)
        new_point = old_point + np.array([dx, dy])
        
        # Boundary handling
        if not is_inside_triangle(np.array([new_point]), A, B, C):
            centroid = (A + B + C) / 3
            direction = centroid - new_point
            direction = direction / (np.linalg.norm(direction) + 1e-8)
            new_point = old_point + 0.5 * step * direction
            if not is_inside_triangle(np.array([new_point]), A, B, C):
                continue
        
        candidate = points.copy()
        candidate[idx] = new_point
        base_min = get_smallest_triangle_area(candidate)
        
        # Simulate opponent: try improving one random point
        i_opponent = np.random.randint(0, 11)
        opp_point = candidate[i_opponent].copy()
        min_tri = None
        min_area = base_min
        for j in range(11):
            if j == i_opponent: continue
            for k in range(j+1, 11):
                if k == i_opponent: continue
                area = triangle_area(candidate[i_opponent], candidate[j], candidate[k])
                if area < min_area - 1e-10:
                    min_area = area
                    min_tri = (i_opponent, j, k)
        
        if min_tri:
            i, j, k = min_tri
            a, b, c = candidate[i], candidate[j], candidate[k]
            signed_area = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
            sign = 1.0 if signed_area > 0 else -1.0
            grad_a = sign * 0.5 * np.array([-(c[1]-b[1]), c[0]-b[0]])
            step_opp = 0.01 * grad_a / (np.linalg.norm(grad_a) + 1e-8)
            new_opp_point = opp_point + step_opp
            
            if is_inside_triangle(np.array([new_opp_point]), A, B, C):
                opp_candidate = candidate.copy()
                opp_candidate[i] = new_opp_point
                opp_min = get_smallest_triangle_area(opp_candidate)
                improvement = max(0, opp_min - base_min)
                if improvement > 0:
                    vulnerability[i_opponent] += 1
            else:
                improvement = 0
        else:
            improvement = 0
        
        # Adversarial objective
        objective = base_min - beta * improvement
        
        # Acceptance criterion
        current_min = get_smallest_triangle_area(points)
        delta = objective - current_min
        if delta > 0 or np.random.random() < np.exp(delta / T):
            points = candidate
            
        # Track best configuration
        current_min = get_smallest_triangle_area(points)
        if current_min > best_min_area:
            best_min_area = current_min
            best_points = points.copy()

        T *= cooling_rate

    # Final refinement
    refined_points = multi_triangle_refinement(best_points, A, B, C)
    return refined_points

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