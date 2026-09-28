import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.stats import qmc

np.random.seed(42)
random.seed(42)

def generate_hexagonal_grid_in_triangle(triangle, n_points=11, jitter=0.02):
    """Generate points in hexagonal grid pattern inside the triangle with optional jitter."""
    A, B, C = triangle
    
    # Calculate triangle properties
    base = np.linalg.norm(B - A)
    height = np.linalg.norm(C - ((A + B) / 2))
    
    # Create a grid that fits inside the triangle
    points = []
    rows = 4  # Enough rows to get at least 11 points
    points_per_row = [1, 2, 3, 4, 3, 2, 1]  # Symmetric hexagonal pattern
    
    y_spacing = height / (rows + 1)
    total_points = 0
    
    for row in range(rows + 1):
        x_count = points_per_row[row]
        x_spacing = base / (x_count + 1)
        
        for col in range(x_count):
            # Calculate position in barycentric coordinates
            y_frac = (row + 1) / (rows + 2)
            x_frac = (col + 1) / (x_count + 1)
            
            # Convert to Cartesian
            x = A[0] + x_frac * (B[0] - A[0])
            y = A[1] + y_frac * (C[1] - A[1])
            
            # Add jitter
            x += np.random.uniform(-jitter, jitter) * base
            y += np.random.uniform(-jitter, jitter) * height
            
            # Convert to barycentric to ensure inside triangle
            v0 = B - A
            v1 = C - A
            v2 = np.array([x, y]) - A
            
            d00 = np.dot(v0, v0)
            d01 = np.dot(v0, v1)
            d11 = np.dot(v1, v1)
            d20 = np.dot(v2, v0)
            d21 = np.dot(v2, v1)
            denom = d00 * d11 - d01 * d01
            v = (d11 * d20 - d01 * d21) / denom
            w = (d00 * d21 - d01 * d20) / denom
            u = 1 - v - w
n
            if u < 0 or v < 0 or w < 0:
                # Project back to triangle if outside
                if u < 0:
                    u = 0
                    v = v / (v + w)
                    w = 1 - v
                elif v < 0:
                    v = 0
                    u = u / (u + w)
                    w = 1 - u
                elif w < 0:
                    w = 0
                    u = u / (u + v)
                    v = 1 - u
                
            point = u * A + v * B + w * C
            points.append(point)
            total_points += 1
            if total_points >= n_points:
                break
        if total_points >= n_points:
            break

    return np.array(points[:n_points])

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    n = 11
    max_restarts = 20
    max_iter = 1000
    
    # Use Sobol sequence for better restart coverage
    sampler = qmc.Sobol(d=2, scramble=False)
    sobol_points = sampler.random(n=max_restarts)

    best_points = None
    best_min_area = -1

    for restart in range(max_restarts):
        # Initialize with hexagonal grid for better starting point
        points = generate_hexagonal_grid_in_triangle(tri, n_points=n, jitter=0.05)
        
        # Simulated annealing parameters
        temperature = 0.001
        cooling_rate = 0.99
        initial_step = 0.05

        for iter in range(max_iter):
            current_min_area = get_smallest_triangle_area(points)
            
            # Consider triangles within 10% of min_area for candidate selection
            threshold = 1.1 * current_min_area
            
            best_improvement = -float('inf')
            best_idx = None
            best_new_point = None
            found_candidate = False

            # Find all triangles below threshold and collect their points
            candidate_points = set()
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        ax, ay = points[i]
                        bx, by = points[j]
                        cx, cy = points[k]
                        area = 0.5 * abs((bx-ax)*(cy-ay) - (cx-ax)*(by-ay))
                        if area <= threshold:
                            candidate_points.add(i)
                            candidate_points.add(j)
                            candidate_points.add(k)

            # If no candidates found (shouldn't happen), use all points
            if not candidate_points:
                candidate_points = set(range(n))

            # Current step size with decay
            step_size = initial_step * (cooling_rate ** iter)

            for idx in candidate_points:
                # For each candidate point, try to move it
                current_point = points[idx]
                
                # Try random direction for exploration
                direction = np.random.uniform(-1, 1, size=2)
                direction = direction / np.linalg.norm(direction) if np.linalg.norm(direction) > 1e-10 else np.array([1.0, 0.0])
                
                new_point = current_point + step_size * direction
                
                # Check if inside triangle
                if not is_inside_triangle(new_point, A, B, C):
                    # Try to project back to boundary if outside
                    v0 = B - A
                    v1 = C - A
                    v2 = new_point - A
                    
                    d00 = np.dot(v0, v0)
                    d01 = np.dot(v0, v1)
                    d11 = np.dot(v1, v1)
                    d20 = np.dot(v2, v0)
                    d21 = np.dot(v2, v1)
                    denom = d00 * d11 - d01 * d01
                    
                    v = (d11 * d20 - d01 * d21) / denom
                    w = (d00 * d21 - d01 * d20) / denom
                    u = 1 - v - w

                    if u < 0:
                        # Project to BC edge
                        bc = C - B
                        t = np.dot(new_point - B, bc) / np.dot(bc, bc)
                        t = max(0, min(1, t))
                        new_point = B + t * bc
                    elif v < 0:
                        # Project to AC edge
                        ac = C - A
                        t = np.dot(new_point - A, ac) / np.dot(ac, ac)
                        t = max(0, min(1, t))
                        new_point = A + t * ac
                    elif w < 0:
                        # Project to AB edge
                        ab = B - A
                        t = np.dot(new_point - A, ab) / np.dot(ab, ab)
                        t = max(0, min(1, t))
                        new_point = A + t * ab

                # Evaluate new configuration
                new_points = points.copy()
                new_points[idx] = new_point
                new_min_area = get_smallest_triangle_area(new_points)

                # Calculate improvement
                improvement = new_min_area - current_min_area
                
                # In simulated annealing, we might accept worsening moves
                if improvement > 0 or np.random.rand() < np.exp(improvement / temperature):
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_idx = idx
                        best_new_point = new_point
                        found_candidate = True

            # Apply the best move found
            if found_candidate:
                points[best_idx] = best_new_point

            # Cool down the temperature
            temperature *= cooling_rate

        # Evaluate final configuration
        final_min_area = get_smallest_triangle_area(points)
        if final_min_area > best_min_area:
            best_min_area = final_min_area
            best_points = points

    return best_points