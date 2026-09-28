import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

# Helper function for single triangle area (to identify critical triangles)
def triangle_area(a, b, c):
    return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))

def entrypoint() -> np.ndarray:
    base_seed = 42
    best_config = None
    best_min = -1

    for run in range(5):
        # Reset seeds for this run
        np.random.seed(base_seed + run)
        random.seed(base_seed + run)

        A, B, C = get_unit_triangle()
        
        # Generate 11 distinct points in triangle using barycentric coordinates with duplicate check
        points = []
        while len(points) < 11:
            u = random.random()
            v = random.random()
            if u + v > 1:
                u = 1 - u
                v = 1 - v
            w = 1 - u - v
            point = w * A + u * B + v * C
            
            # Check distinctness against existing points
            is_duplicate = False
            for p in points:
                if np.linalg.norm(point - p) < 1e-5:
                    is_duplicate = True
                    break
            if is_duplicate:
                continue
            
            points.append(point)
        points = np.array(points)
        
        # Initialize optimization parameters
        current_min = get_smallest_triangle_area(points)
        T = 0.001  # Initial temperature
        step_size = 0.05
        iterations = 1000

        for it in range(iterations):
            # Identify critical points (vertices of triangles at current minimum area)
            critical_points = set()
            n = len(points)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = triangle_area(points[i], points[j], points[k])
                        if area <= current_min + 1e-8:
                            critical_points.add(i)
                            critical_points.add(j)
                            critical_points.add(k)
            critical_points = list(critical_points)

            # Perform 11 perturbations per iteration
            for _ in range(11):
                # Choose point to perturb: 80% chance from critical points
                if critical_points and random.random() < 0.8:
                    idx = random.choice(critical_points)
                else:
                    idx = random.randint(0, 10)

                old_point = points[idx].copy()
                
                # Generate perturbation
                dx = random.uniform(-step_size, step_size)
                dy = random.uniform(-step_size, step_size)
                new_point = np.array([old_point[0] + dx, old_point[1] + dy])
                
                # Check containment
                if not is_inside_triangle([new_point], A, B, C):
                    continue
                
                # Apply perturbation temporarily
                points[idx] = new_point
                new_min = get_smallest_triangle_area(points)
                
                # Simulated annealing acceptance
                delta = new_min - current_min
                if delta > 0 or random.random() < np.exp(delta / T):
                    current_min = new_min
                else:
                    points[idx] = old_point

            # Decay temperature and step size
            T *= 0.995
            step_size *= 0.995

        # Evaluate final configuration for this run
        min_area = get_smallest_triangle_area(points)
        if min_area > best_min:
            best_min = min_area
            best_config = points.copy()

    return best_config