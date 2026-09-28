import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import random

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Create initial points based on a structured hexagonal pattern with adaptive radii
    def create_initial_points():
        # Convert vertices to barycentric coordinates for easier placement
        # A=(1,0,0), B=(0,1,0), C=(0,0,1) in barycentric
        
        points = []
        
        # Calculate adaptive radii based on point count (n=11)
        # For 11 points: 1 center + 3 inner + 6 outer + 1 edge
        n = 11
        # Scale radii based on n, with empirical tuning for 11 points
        r1 = 0.18 + 0.02 * (n - 10)  # Scaled inner radius
        r2 = 0.38 + 0.02 * (n - 10)  # Scaled outer radius
        
        # Layer 0: Center point
        points.append((1/3, 1/3, 1/3))
        
        # Layer 1: 3 points
        for i in range(3):
            angle = 2 * np.pi * i / 3
            dx = r1 * np.cos(angle)
            dy = r1 * np.sin(angle)
            # Map to barycentric (approximation)
            bary_x = 1/3 + dx
            bary_y = 1/3 + dy * np.sqrt(3)/3
            bary_z = 1 - bary_x - bary_y
            # Ensure non-negative
            if bary_z < 0:
                excess = -bary_z/2
                bary_x += excess
                bary_y += excess
                bary_z = 0
            if bary_x < 0:
                excess = -bary_x/2
                bary_y += excess
                bary_z += excess
                bary_x = 0
            if bary_y < 0:
                excess = -bary_y/2
                bary_x += excess
                bary_z += excess
                bary_y = 0
            points.append((bary_x, bary_y, bary_z))
        
        # Layer 2: 6 points
        for i in range(6):
            angle = 2 * np.pi * i / 6
            dx = r2 * np.cos(angle)
            dy = r2 * np.sin(angle)
            bary_x = 1/3 + dx
            bary_y = 1/3 + dy * np.sqrt(3)/3
            bary_z = 1 - bary_x - bary_y
            if bary_z < 0:
                excess = -bary_z/2
                bary_x += excess
                bary_y += excess
                bary_z = 0
            if bary_x < 0:
                excess = -bary_x/2
                bary_y += excess
                bary_z += excess
                bary_x = 0
            if bary_y < 0:
                excess = -bary_y/2
                bary_x += excess
                bary_z += excess
                bary_y = 0
            points.append((bary_x, bary_y, bary_z))
        
        # We have 1+3+6=10 points, need one more
        # Add a point near the middle of the AB edge, but parameterized
        edge_position = 0.45 + 0.02 * (n - 10)
        points.append((edge_position, edge_position, 1 - 2*edge_position))
        
        # Convert to Cartesian coordinates
        cartesian_points = []
        for (u, v, w) in points[:11]:
            point = u * A + v * B + w * C
            cartesian_points.append(point)
        
        return np.array(cartesian_points)
    
    points = create_initial_points()
    
    # Simulated annealing parameters with adaptive cooling
    initial_temp = 0.025
    cooling_rate = 0.998  # Slower cooling for better exploration
    max_iter = 8000
    base_step = 0.04
    acceptance_target = 0.44
    plateau_threshold = 0.0001
    plateau_length = 500

    # Gradient calculation function
    def get_area_gradient(point_idx, triangle_indices, current_points):
        """Calculate direction to move point_idx to increase triangle area."""
        i, j, k = triangle_indices
        if point_idx == i:
            base1, base2 = j, k
        elif point_idx == j:
            base1, base2 = i, k
        else:  # point_idx == k
            base1, base2 = i, j
        
        # Vector for the base
        v = current_points[base2] - current_points[base1]
        # Normal vector (perpendicular to base)
        normal = np.array([-v[1], v[0]])
        norm_norm = np.linalg.norm(normal)
        if norm_norm < 1e-10:
            return np.array([0.0, 0.0])  # Degenerate triangle
        normal = normal / norm_norm
        
        # Determine direction: move away from the base line
        d = np.dot(normal, current_points[point_idx] - current_points[base1])
        direction = normal if d >= 0 else -normal
        
        return direction

    current = points.copy()
    current_score = get_smallest_triangle_area(current)
    best = current.copy()
    best_score = current_score
    
    # Adaptive step size parameters
    step_size = base_step
    successful = 0
    attempts = 0
    
    # Plateau tracking for reheating
    plateau_counter = 0
    prev_best_score = best_score
    
    for iter in range(max_iter):
        temp = initial_temp * (cooling_rate ** iter)
        
        # Find points that are part of small triangles
        triangles = []
        n = 11
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    # Compute area using the formula
                    area = 0.5 * abs(
                        (current[j,0] - current[i,0]) * (current[k,1] - current[i,1]) -
                        (current[j,1] - current[i,1]) * (current[k,0] - current[i,0])
                    )
                    triangles.append((area, i, j, k))
        
        # Sort by area (smallest first)
        triangles.sort()
        
        # Count how many times each point appears in the smallest triangles
        point_counts = [0] * 11
        for idx, (_, i, j, k) in enumerate(triangles[:15]):  # Increased from 5 to 15 for broader selection
            point_counts[i] += 1
            point_counts[j] += 1
            point_counts[k] += 1
        
        # Convert to probabilities for selection
        total = sum(point_counts)
        if total > 0:
            probabilities = [count/total for count in point_counts]
        else:
            probabilities = [1/11] * 11  # Uniform if no small triangles found
        
        # Determine number of points to perturb (1, 2, or 3)
        critical_points = set()
        for _, i, j, k in triangles[:5]:
            critical_points.update([i, j, k])
            
        n_perturb = 1
        if len(critical_points) >= 3 and np.random.rand() < 0.3:
            n_perturb = 3
        elif len(critical_points) >= 2 and np.random.rand() < 0.5:
            n_perturb = 2

        # Create candidate by perturbing points
        candidate = current.copy()
        
        if n_perturb == 1:
            # Select point to perturb based on probability
            point_idx = np.random.choice(11, p=probabilities)
            
            # Find the smallest triangle involving this point
            smallest_area = float('inf')
            smallest_triangle = None
            for area, i, j, k in triangles:
                if point_idx in (i, j, k) and area < smallest_area:
                    smallest_area = area
                    smallest_triangle = (i, j, k)

            # Use gradient-based movement if possible
            if smallest_triangle is not None:
                gradient_dir = get_area_gradient(point_idx, smallest_triangle, current)
                if np.linalg.norm(gradient_dir) > 1e-10:
                    candidate[point_idx] += gradient_dir * step_size
                else:
                    # Fallback to random perturbation if gradient is zero
                    displacement = np.random.normal(0, step_size, 2)
                    candidate[point_idx] += displacement
            else:
                # Fallback to random perturbation if no triangle found
                displacement = np.random.normal(0, step_size, 2)
                candidate[point_idx] += displacement
        else:
            # For multi-point perturbation, find the smallest critical triangle
            smallest_area = float('inf')
            smallest_triangle = None
            for area, i, j, k in triangles:
                if set([i, j, k]).issubset(critical_points) and area < smallest_area:
                    smallest_area = area
                    smallest_triangle = (i, j, k)

            if smallest_triangle is None:
                # Fallback to random selection if no critical triangle found
                point_indices = np.random.choice(list(critical_points), size=n_perturb, replace=False)
                for point_idx in point_indices:
                    displacement = np.random.normal(0, step_size, 2)
                    candidate[point_idx] += displacement
            else:
                # Perturb all points in the smallest critical triangle
                for point_idx in smallest_triangle:
                    gradient_dir = get_area_gradient(point_idx, smallest_triangle, current)
                    if np.linalg.norm(gradient_dir) > 1e-10:
                        candidate[point_idx] += gradient_dir * step_size
                    else:
                        displacement = np.random.normal(0, step_size, 2)
                        candidate[point_idx] += displacement

        # Boundary handling using barycentric coordinates
        if not is_inside_triangle(candidate, A, B, C):
            for point_idx in range(11):
                p = candidate[point_idx]
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
                    # Degenerate case, fallback to midpoint
                    bary_u = 0.5
                    bary_v = 0.5
                else:
                    bary_u = (d11 * d20 - d01 * d21) / denom
                    bary_v = (d00 * d21 - d01 * d20) / denom
                
                # Clamp to triangle
                if bary_u < 0: bary_u = 0
                if bary_v < 0: bary_v = 0
                if bary_u + bary_v > 1:
                    scale = 1 / (bary_u + bary_v)
                    bary_u *= scale
                    bary_v *= scale
                
                candidate[point_idx] = A + bary_u * v0 + bary_v * v1

        # Evaluate candidate
        candidate_score = get_smallest_triangle_area(candidate)
        delta = candidate_score - current_score
        
        # Simulated annealing acceptance
        if delta > 0 or random.random() < np.exp(delta / temp):
            current = candidate
            current_score = candidate_score
            successful += 1
            
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
        
        attempts += 1
        
        # Check for plateau for reheating
        if best_score - prev_best_score < plateau_threshold:
            plateau_counter += 1
            if plateau_counter >= plateau_length:
                # Reheat the system
                initial_temp *= 1.5
                plateau_counter = 0
        else:
            plateau_counter = 0
            prev_best_score = best_score

        # Adaptive step size adjustment
        if iter > 0 and iter % 100 == 0:
            acceptance_rate = successful / attempts
            if acceptance_rate > acceptance_target:
                step_size *= 1.05  # More conservative increase
            else:
                step_size *= 0.95  # More conservative decrease
            
            # Ensure step size stays within reasonable bounds
            step_size = max(0.001, min(step_size, 0.1))
            
            successful = 0
            attempts = 0
    
    # Final deepening phase to create a deeper local optimum
    deepening_steps = 2000  # Increased from 1000
    deepening_temp = 0.0005
    
    for _ in range(deepening_steps):
        # Select point to perturb
        point_idx = random.randint(0, 10)
        
        # Find smallest triangle involving this point
        smallest_area = float('inf')
        smallest_triangle = None
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = 0.5 * abs(
                        (best[j,0] - best[i,0]) * (best[k,1] - best[i,1]) -
                        (best[j,1] - best[i,1]) * (best[k,0] - best[i,0])
                    )
                    if point_idx in (i, j, k) and area < smallest_area:
                        smallest_area = area
                        smallest_triangle = (i, j, k)

        candidate = best.copy()
        
        # Use gradient-based movement if possible
        if smallest_triangle is not None:
            gradient_dir = get_area_gradient(point_idx, smallest_triangle, best)
            if np.linalg.norm(gradient_dir) > 1e-10:
                candidate[point_idx] += gradient_dir * (step_size * 0.1)
            else:
                # Fallback to small random perturbation
                displacement = np.random.normal(0, step_size * 0.1, 2)
                candidate[point_idx] += displacement
        else:
            # Fallback to small random perturbation
            displacement = np.random.normal(0, step_size * 0.1, 2)
            candidate[point_idx] += displacement
        
        if not is_inside_triangle(candidate, A, B, C):
            # Project back to triangle using barycentric coordinates
            p = candidate[point_idx]
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
                bary_u = 0.5
                bary_v = 0.5
            else:
                bary_u = (d11 * d20 - d01 * d21) / denom
                bary_v = (d00 * d21 - d01 * d20) / denom
            
            if bary_u < 0: bary_u = 0
            if bary_v < 0: bary_v = 0
            if bary_u + bary_v > 1:
                scale = 1 / (bary_u + bary_v)
                bary_u *= scale
                bary_v *= scale
            
            candidate[point_idx] = A + bary_u * v0 + bary_v * v1
        
        candidate_score = get_smallest_triangle_area(candidate)
        delta = candidate_score - best_score
        
        # Only accept if it doesn't decrease the minimum area too much
        # Tightened threshold from -0.00005 to -0.00001
        if delta >= -0.00001 or random.random() < np.exp(delta / deepening_temp):
            best = candidate
            best_score = candidate_score
    
    return best