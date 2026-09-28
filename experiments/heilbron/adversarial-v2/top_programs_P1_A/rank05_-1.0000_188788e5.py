import numpy as np
from scipy.optimize import differential_evolution
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import math

np.random.seed(42)

# Soft-min function using log-sum-exp for smoother optimization landscape
def soft_min_area(points, beta=50):
    areas = []
    n = len(points)
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                p, q, r = points[i], points[j], points[k]
                area = 0.5 * abs((q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0]))
                areas.append(area)
    # Log-sum-exp for soft minimum
    areas = np.array(areas)
    return -np.log(np.sum(np.exp(-beta * areas))) / beta

def generate_grid_points(rows=4, perturbation=0.02):
    A, B, C = get_unit_triangle()
    points = []
    
    # Hexagonal grid pattern - known to work well for Heilbronn problems
    total_points = 0
    row = 0
    while total_points < 11:
        points_in_row = min(row + 1, 11 - total_points)
        spacing = 1.0 / (points_in_row + 1)
        
        for i in range(points_in_row):
            u = (i + 1) * spacing
            v = (row + 1) * spacing * math.sqrt(3)/2
            
            # Convert to barycentric coordinates for proper triangle containment
            w = 1 - u - v
            if w < 0:
                # Adjust to stay within triangle
                u = u * (1 - v)
                w = 1 - u - v
            
            # Convert to Cartesian
            P = u * A + v * B + w * C
            
            # Add small random perturbation
            P += np.random.uniform(-perturbation, perturbation, size=2)
            points.append(P)
            
            total_points += 1
            if total_points >= 11:
                break
        
        row += 1
    
    return np.array(points)

def entrypoint():
    A, B, C = get_unit_triangle()
    best_min_area = -1
    best_points = None
    
    # Generate multiple grid-based starting points with different perturbations
    for seed in range(10):  # Increased from 3 to 10 for better coverage
        np.random.seed(seed)
        
        # Generate grid points as starting configuration
        grid_points = generate_grid_points(perturbation=0.03)
        
        # Convert to barycentric coordinates for optimization
        barycentric_points = []
        for P in grid_points:
            # Solve for barycentric coordinates
            mat = np.array([A, B, C]).T
            mat = np.vstack([mat, [1, 1, 1]])
            rhs = np.append(P, 1)
            bary = np.linalg.solve(mat, rhs)
            u, v, w = bary
            barycentric_points.extend([u, v])  # w = 1-u-v is implicit
        
        x0 = np.array(barycentric_points)
        
        # Constraints to ensure points stay within triangle
        constraints = []
        for i in range(11):
            constraints.append({'type': 'ineq', 'fun': lambda x, i=i: x[2*i]})
            constraints.append({'type': 'ineq', 'fun': lambda x, i=i: x[2*i+1]})
            constraints.append({'type': 'ineq', 'fun': lambda x, i=i: 1 - x[2*i] - x[2*i+1]})

        # Use differential evolution for global optimization
        bounds = [(0, 1) for _ in range(22)]  # 11 points * 2 coordinates
        
        def objective(x):
            points = []
            for i in range(11):
                u, v = x[2*i], x[2*i+1]
                w = 1 - u - v
                P = u * A + v * B + w * C
                points.append(P)
            points = np.array(points)
            
            # Use soft-min for smoother optimization landscape
            return -soft_min_area(points, beta=50)

        res = differential_evolution(
            objective, 
n            bounds,
            constraints=constraints,
            maxiter=100,
            popsize=15,
            tol=1e-6,
            seed=seed
        )

        if res.success:
            points = []
            for i in range(11):
                u, v = res.x[2*i], res.x[2*i+1]
                w = 1 - u - v
                points.append(u * A + v * B + w * C)
            points = np.array(points)
            
            # Verify validity
            if not is_inside_triangle(points, A, B, C):
                continue
                
            min_area = get_smallest_triangle_area(points)
            
            # Quality threshold filtering - only accept reasonable solutions
            if min_area > 0.01 and min_area > best_min_area:
                best_min_area = min_area
                best_points = points

    # If no good solution found, try one more time with a different grid pattern
    if best_points is None or best_min_area < 0.01:
        np.random.seed(42)
        points = []
        rows = 5
        count = 0
        for row in range(rows):
            num_points = rows - row
            v = (row + 0.5) / rows
            for i in range(num_points):
                if count >= 11:
                    break
                u = (i + 0.5) / num_points * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                P += np.random.uniform(-0.01, 0.01, size=2)
                points.append(P)
                count += 1
            if count >= 11:
                break
        points = np.array(points)
        
        # Apply a final optimization pass
        barycentric_points = []
        for P in points:
            mat = np.array([A, B, C]).T
            mat = np.vstack([mat, [1, 1, 1]])
            rhs = np.append(P, 1)
            bary = np.linalg.solve(mat, rhs)
            u, v, w = bary
            barycentric_points.extend([u, v])
        
        x0 = np.array(barycentric_points)
        bounds = [(0, 1) for _ in range(22)]
        
        res = differential_evolution(
            lambda x: -get_smallest_triangle_area(convert_to_cartesian(x, A, B, C)),
            bounds,
            constraints=constraints,
            maxiter=50,
            popsize=10,
            seed=42
        )
        
        if res.success:
            points = convert_to_cartesian(res.x, A, B, C)
            if is_inside_triangle(points, A, B, C):
                min_area = get_smallest_triangle_area(points)
                if min_area > 0.01:
                    best_points = points

    # Final fallback - ensure we return a valid configuration
    if best_points is None:
        return generate_grid_points(perturbation=0.01)
        
    return best_points

def convert_to_cartesian(x, A, B, C):
    points = []
    for i in range(11):
        u, v = x[2*i], x[2*i+1]
        w = 1 - u - v
        points.append(u * A + v * B + w * C)
    return np.array(points)