import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import time

np.random.seed(42)

# Strategic initialization based on documented high-quality n=11 Heilbronn configurations
def strategic_initialization(A, B, C, n=11):
    points = []
    
    # Calculate centroid for reference
    centroid = (A + B + C) / 3
    
    # Vertex points (very slightly inside - 0.02 offset)
    for vertex in [A, B, C]:
        direction = centroid - vertex
        direction = direction / np.linalg.norm(direction)
        points.append(vertex + 0.02 * direction)

    # Edge points at 1/3 and 2/3 positions (with slight inward offset)
    for (v1, v2) in [(A, B), (B, C), (C, A)]:
        # 1/3 position
        p1 = v1 + 0.333 * (v2 - v1)
        # 2/3 position
        p2 = v1 + 0.667 * (v2 - v1)
        
        # Compute inward normal
        edge_vec = v2 - v1
        normal = np.array([-edge_vec[1], edge_vec[0]])
        normal = normal / np.linalg.norm(normal)
        
        # Point inward
        if np.dot(normal, centroid - p1) < 0:
            normal = -normal
        
        # Add points with slight inward offset (0.015)
        points.append(p1 + 0.015 * normal)
        points.append(p2 + 0.015 * normal)

    # Interior points - strategic triangular lattice pattern
    # Based on known high-quality configurations for n=11
    radii = [0.12, 0.24]  # Two concentric rings
    angles = [0, 2*np.pi/3, 4*np.pi/3]  # Triangular symmetry
    
    # First ring (3 points)
    for i in range(3):
        angle = angles[i]
        offset = np.array([radii[0] * np.cos(angle), radii[0] * np.sin(angle)])
        candidate = centroid + offset
        if is_inside_triangle(candidate, A, B, C):
            points.append(candidate)
        else:
            # Project toward centroid if outside
            direction = centroid - candidate
            direction = direction / np.linalg.norm(direction)
            points.append(candidate + 0.05 * direction)

    # Second ring (2 points - not full symmetry for n=11)
    for i in range(2):
        angle = angles[i] + np.pi/6  # Offset for better distribution
        offset = np.array([radii[1] * np.cos(angle), radii[1] * np.sin(angle)])
        candidate = centroid + offset
        if is_inside_triangle(candidate, A, B, C):
            points.append(candidate)
        else:
            # Project toward centroid if outside
            direction = centroid - candidate
            direction = direction / np.linalg.norm(direction)
            points.append(candidate + 0.05 * direction)

    # Ensure we have exactly n points
    if len(points) > n:
        points = points[:n]
    elif len(points) < n:
        # Add random points if needed (shouldn't happen for n=11)
        while len(points) < n:
            r = np.random.uniform(0.05, 0.2)
            theta = np.random.uniform(0, 2*np.pi)
            offset = np.array([r * np.cos(theta), r * np.sin(theta)])
            candidate = centroid + offset
            if is_inside_triangle(candidate, A, B, C):
                points.append(candidate)

    return np.array(points)

def triangle_area_signed(a, b, c):
    return 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))

def project_point_to_triangle(P, A, B, C):
    edges = [(A, B), (B, C), (C, A)]
    best_point = None
    best_dist = float('inf')
    for (V0, V1) in edges:
        v = V1 - V0
        w = P - V0
        c1 = np.dot(w, v)
        c2 = np.dot(v, v)
        if c2 == 0:
            continue
        b = c1 / c2
        if b < 0:
            proj = V0
        elif b > 1:
            proj = V1
        else:
            proj = V0 + b * v
        dist = np.linalg.norm(P - proj)
        if dist < best_dist:
            best_dist = dist
            best_point = proj
    
    # Add small inward bias toward centroid for robustness
    centroid = (A + B + C) / 3
    direction = centroid - best_point
    if np.linalg.norm(direction) > 0:
        direction = direction / np.linalg.norm(direction)
        # Apply small inward bias (0.005 units)
        best_point = best_point + 0.005 * direction
        
        # Verify still inside triangle
        if not is_inside_triangle(best_point, A, B, C):
            # If pushed outside, revert to boundary point
            best_point = proj
            
    return best_point

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    best_points = None
    best_score = -1
    
    # Increased restarts with more diverse seeds
    restart_seeds = [42, 87, 153, 219, 305]
    
    for restart, seed in enumerate(restart_seeds):
        np.random.seed(seed)
        points = strategic_initialization(A, B, C)
        
        # Simulated annealing parameters
        initial_temperature = 0.005
        temperature = initial_temperature
        cooling_rate = 0.995
        min_temperature = 1e-6
        initial_gradient_prob = 0.85  # Start with more exploration
        min_gradient_prob = 0.4      # End with more exploitation
        step_size = 0.02
        max_iter = 1800
        no_improve_count = 0
        
        # Track recent improvements for dynamic basin hopping
        improvement_window = 100
        improvements = [0] * improvement_window
n        current_score = get_smallest_triangle_area(points)
        best_local_points = points.copy()
        best_local_score = current_score
        
        for iter in range(max_iter):
            # Calculate recent improvement rate
            improvement_rate = sum(improvements) / improvement_window
            
            # Dynamic basin hopping threshold based on improvement rate
            basin_hopping_threshold = 120 * (1 + 0.4 * (1 - improvement_rate))
            
            # Periodic basin hopping to escape local optima
            if no_improve_count >= basin_hopping_threshold:
                # Perturb 30% of points significantly
                n_perturb = max(1, len(points) // 3)
                indices = np.random.choice(len(points), n_perturb, replace=False)
                for idx in indices:
                    # Random direction with significant magnitude
                    direction = np.random.normal(0, 1, 2)
                    direction = direction / np.linalg.norm(direction)
                    points[idx] += 0.12 * direction
                    # Project back to triangle if needed
                    if not is_inside_triangle(points[idx], A, B, C):
                        points[idx] = project_point_to_triangle(points[idx], A, B, C)
                current_score = get_smallest_triangle_area(points)
                no_improve_count = 0
                # Reset improvement history
                improvements = [0] * improvement_window
                continue

            # Adaptive gradient probability based on temperature
            gradient_prob = initial_gradient_prob * (temperature / initial_temperature) + min_gradient_prob
            gradient_prob = min(max(gradient_prob, min_gradient_prob), initial_gradient_prob)

            # Decide move type: gradient-based or random
            if np.random.rand() < gradient_prob:
                # Gradient-based move (focus on critical triangles)
                min_area = current_score
                critical_triangles = []
                
                # Adaptive epsilon that decays with temperature
                epsilon = 1e-5 * (temperature / initial_temperature)
                
                # Find triangles within epsilon of min_area
                for i in range(len(points)):
                    for j in range(i+1, len(points)):
                        for k in range(j+1, len(points)):
                            area_signed = triangle_area_signed(points[i], points[j], points[k])
                            area_abs = abs(area_signed)
                            if area_abs < min_area + epsilon:
                                critical_triangles.append((i, j, k, area_signed))

                if critical_triangles:
                    grads = np.zeros_like(points)
                    for i, j, k, area_signed in critical_triangles:
                        sign = 1.0 if area_signed >= 0 else -1.0
                        
                        # Gradient contributions for each vertex
                        grads[i] += sign * np.array([
                            0.5 * (points[j,1] - points[k,1]),
                            0.5 * (points[k,0] - points[j,0])
                        ])
                        grads[j] += sign * np.array([
                            0.5 * (points[k,1] - points[i,1]),
                            0.5 * (points[i,0] - points[k,0])
                        ])
                        grads[k] += sign * np.array([
                            0.5 * (points[i,1] - points[j,1]),
                            0.5 * (points[j,0] - points[i,0])
                        ])

                    # Normalize gradients to prevent instability
                    for i in range(len(grads)):
                        norm = np.linalg.norm(grads[i])
                        if norm > 1e-8:
                            grads[i] = grads[i] / norm

                    # Create candidate by applying gradient
                    candidate = points + step_size * grads
                    
            else:
                # Random exploration move
                candidate = points.copy()
                idx = np.random.randint(0, len(points))
                # Larger perturbation for exploration
                perturbation = np.random.normal(0, 0.03, size=2)
                candidate[idx] += perturbation

            # Project points back to triangle if needed
            for i in range(len(candidate)):
                if not is_inside_triangle(candidate[i], A, B, C):
                    candidate[i] = project_point_to_triangle(candidate[i], A, B, C)

            # Evaluate candidate
            candidate_score = get_smallest_triangle_area(candidate)
            
            # Acceptance criterion (simulated annealing)
            if candidate_score > current_score:
                # Always accept improvements
                points = candidate
                current_score = candidate_score
                
                # Record improvement for dynamic basin hopping
                improvements.pop(0)
                improvements.append(1)
                
                # Adaptive step size: increase after improvements
                step_size = min(step_size * 1.05, 0.05)
                no_improve_count = 0
                
                # Track best solution
                if candidate_score > best_local_score:
                    best_local_points = candidate.copy()
                    best_local_score = candidate_score
            else:
                # Accept worsening moves with probability based on temperature
                delta = candidate_score - current_score
                if np.random.rand() < np.exp(delta / temperature):
                    points = candidate
                    current_score = candidate_score
                    
                    # Record improvement for dynamic basin hopping
                    improvements.pop(0)
                    improvements.append(1)
                else:
                    # Record lack of improvement
                    improvements.pop(0)
                    improvements.append(0)
                    
                # Adaptive step size: decrease after failures
                step_size = max(step_size * 0.95, 0.001)
                no_improve_count += 1

            # Cooling
            temperature *= cooling_rate
            
            # Early termination if temperature too low
            if temperature < min_temperature:
                break

        # Track best across restarts
        if best_local_score > best_score:
            best_points = best_local_points.copy()
            best_score = best_local_score

    return best_points