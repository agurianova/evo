import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)


def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    row_counts = [4, 3, 2, 1, 1]
    total_rows = len(row_counts)
    points = []
    
    for row in range(total_rows):
        num_points = row_counts[row]
        v = (row + 0.5) / total_rows
        for i in range(num_points):
            u = (i + 0.5) / num_points * (1 - v)
            base_point = (1 - u - v) * A + u * B + v * C
            
            # Adaptive perturbation to ensure inside triangle and break collinearity
            candidate = None
            for _ in range(100):
                perturbation = np.random.uniform(-0.01, 0.01, 2)
                candidate = base_point + perturbation
                if is_inside_triangle(candidate, A, B, C):
                    break
            else:
                mag = 0.01
                while mag > 1e-6:
                    mag *= 0.5
                    perturbation = np.random.uniform(-mag, mag, 2)
                    candidate = base_point + perturbation
                    if is_inside_triangle(candidate, A, B, C):
                        break
            points.append(candidate)
    
    points = np.array(points)
    
    # Local search optimization to maximize min_area and build resistance
    step_size = 0.01
    max_iter = 1000
    for _ in range(max_iter):
        improved = False
        current_min = get_smallest_triangle_area(points)
        
        for i in range(len(points)):
            for _ in range(10):
                direction = np.random.randn(2)
                direction = direction / max(np.linalg.norm(direction), 1e-5)
                new_point = points[i] + step_size * direction
                
                if not is_inside_triangle(new_point, A, B, C):
                    continue
                
                # Save and test new position
                old_point = points[i].copy()
                points[i] = new_point
                new_min = get_smallest_triangle_area(points)
                
                if new_min > current_min:
                    current_min = new_min
                    improved = True
                else:
                    points[i] = old_point
        
        if not improved:
            step_size *= 0.9
            if step_size < 1e-5:
                break
    
    return points