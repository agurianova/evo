import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    def compute_triangle_gradient(points, i, j, k):
        """Compute gradients for points i,j,k to increase triangle area"""
        A = points[i]
        B = points[j]
        C = points[k]
        
        # Compute area sign
        f = (B[0]-A[0])*(C[1]-A[1]) - (C[0]-A[0])*(B[1]-A[1])
        sign_f = 1.0 if f >= 0 else -1.0
        
        # Compute gradients
        grad_A = 0.5 * sign_f * np.array([B[1]-C[1], C[0]-B[0]])
        grad_B = 0.5 * sign_f * np.array([C[1]-A[1], A[0]-C[0]])
        grad_C = 0.5 * sign_f * np.array([A[1]-B[1], B[0]-A[0]])
        
        # Normalize gradients
        for grad in [grad_A, grad_B, grad_C]:
            norm = np.linalg.norm(grad)
            if norm > 1e-8:
                grad /= norm
                
        return grad_A, grad_B, grad_C

    def adaptive_lattice_seeding(n, A, B, C):
        """Generate points with adaptive row structure and gradient-aware perturbations"""
        # Determine optimal row structure for n points
        rows = []
        total = 0
        row_count = 1
        
        # Find row structure that sums to at least n points
        while total < n:
            rows.append(min(row_count, n - total))
            total += row_count
n            row_count += 1
        
        # Reverse rows to have more points at bottom (like triangle packing)
        rows = rows[::-1]
        
        # Calculate row heights with optimization principles
        num_rows = len(rows)
        points = []
        
        # Use non-uniform spacing optimized for triangle packing
        for row_idx, num_in_row in enumerate(rows):
            # Calculate height position (more space at bottom)
            h = 0.1 + 0.8 * (row_idx / max(1, num_rows-1))**1.5
            
            for i in range(num_in_row):
                # Calculate horizontal position
                u = i / max(1, num_in_row-1)
                
                # Add gradient-aware perturbation
                perturbation = random.uniform(-0.02, 0.02)
                # Make perturbations aware of potential gradient attacks
                if row_idx > 0 and row_idx < num_rows-1:
                    perturbation *= 0.7  # Less perturbation in middle rows
                u = max(0, min(1, u + perturbation))
                
                # Barycentric coordinates
                alpha = u * (1 - h)
                beta = (1 - u) * (1 - h)
                gamma = h
                
                point = alpha * A + beta * B + gamma * C
                points.append(point)
                
                if len(points) >= n:
                    break
            if len(points) >= n:
                break
        
        return np.array(points)

    def get_problematic_triangles(points, k=10):
        """Return indices of k smallest triangles, weighted by proximity to minimum"""
        n = points.shape[0]
        triangle_areas = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                    (points[j,1]-points[i,1])*(points[k,0]-points[i,0]))
                    triangle_areas.append((area, (i, j, k)))
        
        # Sort by area
        triangle_areas.sort(key=lambda x: x[0])
        
        # Take top k, but weight selection toward smaller areas
        min_area = triangle_areas[0][0]
        max_area = triangle_areas[min(k*2, len(triangle_areas)-1)][0]
        
        # Create weighted list favoring smaller triangles
        weighted_triangles = []
        for area, indices in triangle_areas[:min(k*3, len(triangle_areas))]:
            # Weight proportional to how close to minimum
n            weight = 1.0 / (area - min_area + 1e-10)
            weighted_triangles.append((weight, indices))
        
        # Normalize weights
        total_weight = sum(w for w, _ in weighted_triangles)
        if total_weight > 0:
            weighted_triangles = [(w/total_weight, idx) for w, idx in weighted_triangles]
        
        # Select k triangles with weighted random choice
        selected = []
        for _ in range(min(k, len(weighted_triangles))):
            r = random.random()
            cumulative = 0.0
            for weight, indices in weighted_triangles:
                cumulative += weight
                if r <= cumulative:
                    selected.append(indices)
                    break
        
        return selected[:k]

    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate initial points with adaptive seeding
    points = adaptive_lattice_seeding(11, A, B, C)
    
    # Ensure validity
    if not is_inside_triangle(points, A, B, C):
        points_list = []
        min_dist = 1e-5
        while len(points_list) < 11:
            s = random.random()
            t = random.random()
            if s + t > 1:
                s = 1 - s
                t = 1 - t
            point = A + s*(B - A) + t*(C - A)
            
            too_close = False
            for p in points_list:
                if np.linalg.norm(point - p) < min_dist:
                    too_close = True
                    break
            if not too_close:
                points_list.append(point)
        points = np.array(points_list)

    # Basin exploration parameters
    max_iter = 2000
    base_step_size = 0.03
    min_step = 1e-5
    exploration_rate = 0.15  # Probability of basin-shaking move
    basin_shake_magnitude = 0.08
    stagnation_threshold = 50
    restart_threshold = 150
    
    # Track optimization progress
    best_points = points.copy()
    best_min_area = get_smallest_triangle_area(points)
    current_min_area = best_min_area
    no_improve_count = 0
    stagnation_count = 0
    
    for iter in range(max_iter):
        # Determine step size based on progress
        step_size = base_step_size * (0.95 ** (no_improve_count / 20))
        step_size = max(min(step_size, 0.08), min_step)
        
        # Occasionally shake the basin to escape shallow local optima
        if stagnation_count > stagnation_threshold or random.random() < exploration_rate:
            # Perform basin shake - larger random perturbation
            idx = random.randint(0, 10)
            angle = random.uniform(0, 2*np.pi)
            magnitude = basin_shake_magnitude * (0.5 + 0.5 * random.random())
            direction = np.array([np.cos(angle), np.sin(angle)])
            new_point = points[idx] + direction * magnitude
            
            # Check validity
            if is_inside_triangle(new_point, A, B, C):
                # Check distinctness
                too_close = False
                for i in range(11):
                    if i == idx:
                        continue
                    if np.linalg.norm(new_point - points[i]) < 1e-5:
                        too_close = True
                        break
                if not too_close:
                    new_points = points.copy()
                    new_points[idx] = new_point
                    new_min_area = get_smallest_triangle_area(new_points)
                    
                    # Always accept basin shake (even if worse) to escape local optimum
                    points = new_points
                    current_min_area = new_min_area
                    no_improve_count = 0
                    stagnation_count = 0
                    continue

        # Get problematic triangles with weighted selection
        problematic_triangles = get_problematic_triangles(points, k=10)
        
        best_improvement = 0.0
        best_move = None
        
        # Try to improve each problematic triangle
        for triangle_indices in problematic_triangles:
            i, j, k = triangle_indices
            grad_i, grad_j, grad_k = compute_triangle_gradient(points, i, j, k)
            
            # Try moving each vertex in gradient direction
            for idx, grad in [(i, grad_i), (j, grad_j), (k, grad_k)]:
                # Scale gradient by step size
                disp = grad * step_size
                new_point = points[idx] + disp

                # Check if inside triangle
                if not is_inside_triangle(new_point, A, B, C):
                    # Try smaller step toward boundary
                    for scale in [0.75, 0.5, 0.25]:
                        test_point = points[idx] + disp * scale
                        if is_inside_triangle(test_point, A, B, C):
                            new_point = test_point
                            break
                    else:
                        continue

                # Check distinctness
                too_close = False
                for other_idx in range(11):
                    if other_idx == idx:
                        continue
                    if np.linalg.norm(new_point - points[other_idx]) < 1e-5:
                        too_close = True
                        break
                if too_close:
                    continue

                # Test new configuration
                new_points = points.copy()
                new_points[idx] = new_point
                new_min_area = get_smallest_triangle_area(new_points)

                # Calculate improvement
                improvement = new_min_area - current_min_area
                
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_move = (idx, disp, new_points.copy(), new_min_area)

        # Apply best move if found
        if best_improvement > 1e-8:
            idx, disp, new_points, new_min_area = best_move
            points = new_points
            current_min_area = new_min_area
            no_improve_count = 0
            stagnation_count = 0
            
            # Update best if improved
            if new_min_area > best_min_area:
                best_min_area = new_min_area
                best_points = points.copy()
        else:
            no_improve_count += 1
            stagnation_count += 1

        # Restart if stuck in local optimum
        if stagnation_count > restart_threshold:
            # Restart from best known position with small perturbation
            points = best_points.copy()
            idx = random.randint(0, 10)
            angle = random.uniform(0, 2*np.pi)
            points[idx] += np.array([np.cos(angle), np.sin(angle)]) * base_step_size * 0.5
            current_min_area = get_smallest_triangle_area(points)
            stagnation_count = 0
            no_improve_count = 0

        # Check for convergence
        if no_improve_count > 500 or step_size < min_step:
            break

    return best_points