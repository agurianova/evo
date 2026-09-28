import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    def triangle_area(a, b, c):
        return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))

    A, B, C = get_unit_triangle()
    points = [A, B, C]

    # Greedy initialization (8 additional points)
    num_grid = 100
    for _ in range(8):
        best_min_area = -1
        best_point = None
        
        for i in range(num_grid + 1):
            u = i / num_grid
            for j in range(num_grid + 1 - i):
                v = j / num_grid
                w = 1 - u - v
                P = w * A + u * B + v * C
                
                # Skip if too close to existing points
                if any(np.linalg.norm(P - p) < 1e-5 for p in points):
                    continue
                
                # Compute min area with existing points
                min_area_candidate = float('inf')
                n = len(points)
                for i1 in range(n):
                    for i2 in range(i1 + 1, n):
                        area = triangle_area(points[i1], points[i2], P)
                        if area < min_area_candidate:
                            min_area_candidate = area
                
                if min_area_candidate > best_min_area:
                    best_min_area = min_area_candidate
                    best_point = P
        
        if best_point is not None:
            points.append(best_point)

    points = np.array(points)
    current_min_area = get_smallest_triangle_area(points)
    
    # Local search optimization
    step_size = 0.05
    min_step = 1e-6
    max_iter = 1000
    directions = np.array([
        [1, 0], [-1, 0], [0, 1], [0, -1],
        [1, 1], [-1, -1], [1, -1], [-1, 1]
    ])
    
    for _ in range(max_iter):
        improved = False
        for i in range(len(points)):
            for d in directions:
                new_point = points[i] + step_size * d
                
                # Validate new point
                if not is_inside_triangle(new_point, A, B, C):
                    continue
                if any(np.linalg.norm(new_point - points[j]) < 1e-5 for j in range(len(points)) if j != i):
                    continue

                # Test improvement
                new_points = points.copy()
                new_points[i] = new_point
                new_min_area = get_smallest_triangle_area(new_points)
                
                if new_min_area > current_min_area:
                    points = new_points
                    current_min_area = new_min_area
                    improved = True
        
        if not improved:
            if step_size <= min_step:
                break
            step_size *= 0.9

    return points