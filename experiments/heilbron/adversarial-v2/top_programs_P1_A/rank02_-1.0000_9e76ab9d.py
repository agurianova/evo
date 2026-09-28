import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    def get_k_smallest_triangle_indices(points, k=3):
        n = points.shape[0]
        areas = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                    (points[j,1]-points[i,1])*(points[k,0]-points[i,0]))
                    areas.append((area, i, j, k))
        
        areas.sort(key=lambda x: x[0])
        return areas[:k]

    def hexagonal_lattice_points(n):
        """Generate n points in a hexagonal lattice inside the unit-area triangle."""
        A, B, C = get_unit_triangle()
        
        # Calculate triangle dimensions
        base = np.linalg.norm(B - A)
        height = np.linalg.norm(C - ((A + B) / 2))
        
        # Estimate lattice spacing
        area_per_point = (base * height / 2) / n
        spacing = np.sqrt(2 * area_per_point / np.sqrt(3))
        
        points = []
        rows = int(np.sqrt(n * 2 / np.sqrt(3))) + 1
        
        for row in range(rows):
            y = row * spacing * np.sqrt(3) / 2
            if y > height:
                break
            
            # Calculate number of points in this row
            points_in_row = n // rows
            if row < n % rows:
                points_in_row += 1
            
            # Calculate x offset for hexagonal pattern
            x_offset = (spacing / 2) * (row % 2)
            
            for col in range(points_in_row):
                x = col * spacing + x_offset
                
                # Convert to barycentric coordinates
                s = x / base
                t = y / height
                
                # Check if inside triangle
                if s + t > 1:
                    continue
                
                point = A + s*(B - A) + t*(C - A)
                points.append(point)
                
                if len(points) == n:
                    return np.array(points)
        
        # If we didn't get enough points, fill with random points
        while len(points) < n:
            s = random.random()
            t = random.random()
            if s + t > 1:
                s = 1 - s
                t = 1 - t
            point = A + s*(B - A) + t*(C - A)
            points.append(point)
            
        return np.array(points)

    tri = get_unit_triangle()
    A, B, C = tri
    
    # Generate initial points using hexagonal lattice
    points = hexagonal_lattice_points(11)
    
    # Optimization parameters
    max_iter = 1000
    initial_temp = 0.005
    cooling_rate = 0.99
    initial_step = 0.03
    min_step = 1e-5
    k_triangles = 3  # Consider top-k smallest triangles
    
    temperature = initial_temp
    step_size = initial_step
    best_points = points.copy()
    best_min_area = get_smallest_triangle_area(points)
    current_min_area = best_min_area
    
    for iter in range(max_iter):
        # Get top-k smallest triangles
        critical_triangles = get_k_smallest_triangle_indices(points, k=k_triangles)
        
        # Try moving points in critical triangles
        best_new_min = current_min_area
        best_move = None
        
        # Consider all points in top-k triangles
        candidate_points = set()
        for _, i, j, k in critical_triangles:
            candidate_points.add(i)
            candidate_points.add(j)
            candidate_points.add(k)
        
        candidate_points = list(candidate_points)
        
        # Try moving each candidate point
        for idx in candidate_points:
            # Get triangles involving this point
            triangles_with_idx = [(area, i, j, k) for area, i, j, k in critical_triangles 
                                 if i == idx or j == idx or k == idx]
            
            if not triangles_with_idx:
                continue

            # Average gradient direction across triangles
            total_grad = np.zeros(2)
            for area, i, j, k in triangles_with_idx:
                # Get the other two points
                if idx == i:
                    p1, p2 = points[j], points[k]
                elif idx == j:
                    p1, p2 = points[i], points[k]
                else:
                    p1, p2 = points[i], points[j]

                # Gradient direction for area increase
                dx = p1[1] - p2[1]
                dy = p2[0] - p1[0]
                norm = np.sqrt(dx*dx + dy*dy)
                if norm < 1e-10:
                    continue
                dx, dy = dx/norm, dy/norm
                
                total_grad += np.array([dx, dy])

            if np.linalg.norm(total_grad) > 1e-10:
                total_grad = total_grad / np.linalg.norm(total_grad)

            # Try multiple directions around the gradient
            directions = []
            for angle in range(0, 360, 45):  # 8 directions
                rad = np.radians(angle)
                dir_x = total_grad[0] * np.cos(rad) - total_grad[1] * np.sin(rad)
                dir_y = total_grad[0] * np.sin(rad) + total_grad[1] * np.cos(rad)
                directions.append(np.array([dir_x, dir_y]))

            for direction in directions:
                new_point = points[idx] + direction * step_size

                # Check if inside triangle
                if not is_inside_triangle(new_point, A, B, C):
                    # Try projecting back toward center
                    for t in [0.9, 0.8, 0.7, 0.6, 0.5]:
                        trial_point = points[idx] + direction * step_size * t
n                        if is_inside_triangle(trial_point, A, B, C):
                            new_point = trial_point
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

                if new_min_area > best_new_min:
                    best_new_min = new_min_area
                    best_move = (idx, direction * step_size)

        # Consider simultaneous moves on all points in critical triangles
        for _, i, j, k in critical_triangles[:1]:  # Just the smallest triangle for simultaneous moves
            # Calculate gradient for each point
            p1, p2, p3 = points[i], points[j], points[k]
            
            # Area = 0.5 * |(p2-p1) × (p3-p1)|
            f = (p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1])
            sign_f = 1.0 if f >= 0 else -1.0

            # Gradients for each point
            grad_i = 0.5 * sign_f * np.array([p2[1]-p3[1], p3[0]-p2[0]])
            grad_j = 0.5 * sign_f * np.array([p3[1]-p1[1], p1[0]-p3[0]])
            grad_k = 0.5 * sign_f * np.array([p1[1]-p2[1], p2[0]-p1[0]])

            # Normalize gradients
            for grad in [grad_i, grad_j, grad_k]:
                norm = np.linalg.norm(grad)
                if norm > 1e-10:
                    grad *= step_size / norm

            # Try simultaneous move
            new_points = points.copy()
            new_points[i] += grad_i
            new_points[j] += grad_j
            new_points[k] += grad_k

            # Check constraints
            valid = True
            for idx in [i, j, k]:
                if not is_inside_triangle(new_points[idx], A, B, C):
                    valid = False
                    break
                for other_idx in range(11):
                    if other_idx == idx:
                        continue
                    if np.linalg.norm(new_points[idx] - points[other_idx]) < 1e-5:
                        valid = False
                        break
                if not valid:
                    break

            if valid:
                new_min_area = get_smallest_triangle_area(new_points)
                if new_min_area > best_new_min:
                    best_new_min = new_min_area
                    best_move = (None, (i, j, k, grad_i, grad_j, grad_k))

        # Decide whether to accept the move
        if best_move is not None:
            delta = best_new_min - current_min_area
            
            # Simulated annealing acceptance
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                if best_move[0] is not None:  # Single-point move
                    idx, disp = best_move
                    points[idx] += disp
                else:  # Multi-point move
                    _, (i, j, k, grad_i, grad_j, grad_k) = best_move
                    points[i] += grad_i
                    points[j] += grad_j
                    points[k] += grad_k
                
                current_min_area = best_new_min
                
                # Track best solution
                if best_new_min > best_min_area:
                    best_min_area = best_new_min
                    best_points = points.copy()
                    # Reset step size on improvement
                    step_size = initial_step
            
        # Update temperature and step size
        temperature *= cooling_rate
        if best_move is None or (best_move is not None and delta <= 0):
            step_size = max(min_step, step_size * 0.95)

    return best_points