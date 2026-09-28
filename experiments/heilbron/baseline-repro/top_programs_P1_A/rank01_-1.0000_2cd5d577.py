import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.spatial import distance_matrix

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    n_starts = 50
    best_config = None
    best_min_area = -1
    G = (A + B + C) / 3.0

    for start in range(n_starts):
        # Generate symmetric configuration: 6 outer points (scaled triangle), 5 inner points (rotated circle)
        s1 = 0.7
        outer_points = [
            G + s1 * (A - G),
            G + s1 * (B - G),
            G + s1 * (C - G),
            (G + s1*(A-G) + G + s1*(B-G)) / 2,
            (G + s1*(B-G) + G + s1*(C-G)) / 2,
            (G + s1*(C-G) + G + s1*(A-G)) / 2
        ]
        
        s2 = 0.2
        r = s2 * np.linalg.norm(A - G)
        angle0 = random.uniform(0, 60)
        angles = np.radians(angle0 + np.arange(5) * 72)
        inner_points = []
        for a in angles:
            dx = r * np.cos(a)
            dy = r * np.sin(a)
            inner_points.append(G + np.array([dx, dy]))
        
        points = np.array(outer_points + inner_points)

        # Validate configuration
        if not is_inside_triangle(points, A, B, C):
            continue

        current_min_area = get_smallest_triangle_area(points)
        
        # Initialize adaptive step size based on min distance
        dists = distance_matrix(points, points)
        np.fill_diagonal(dists, np.inf)
        min_dist = np.min(dists)
        step_size = max(0.001, min_dist * 0.1)
        no_improve_count = 0
        max_no_improve = 500
        max_steps = 10000
        step = 0

        while no_improve_count < max_no_improve and step < max_steps:
            step += 1

            # Identify smallest triangle
            min_area_val = float('inf')
            min_triangle = None
            n = len(points)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        p1, p2, p3 = points[i], points[j], points[k]
                        area = 0.5 * abs(p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1]))
                        if area < min_area_val:
                            min_area_val = area
                            min_triangle = (i, j, k)

            if min_triangle is None:
                break

            i, j, k = min_triangle
            idx_to_move = random.choice([i, j, k])

            # Boundary check: lock points within 1e-5 of boundary
            p = points[idx_to_move]
            sides = [(A, B), (B, C), (C, A)]
            min_dist_to_boundary = float('inf')
            for (a, b) in sides:
                ab = b - a
                ap = p - a
                cross = np.abs(ab[0]*ap[1] - ab[1]*ap[0])
                if np.linalg.norm(ab) > 1e-10:
                    d = cross / np.linalg.norm(ab)
                    if d < min_dist_to_boundary:
                        min_dist_to_boundary = d
            if min_dist_to_boundary < 1e-5:
                no_improve_count += 1
                continue

            # Compute area-increasing direction for selected point
            others = [i, j, k]
            others.remove(idx_to_move)
            p0 = p
            p1 = points[others[0]]
            p2 = points[others[1]]
            
            signed_area = 0.5 * ((p1[0]-p0[0])*(p2[1]-p0[1]) - (p1[1]-p0[1])*(p2[0]-p0[0]))
            grad_x = 0.5 * (p1[1] - p2[1])
            grad_y = 0.5 * (p2[0] - p1[0])
            if signed_area < 0:
                grad_x, grad_y = -grad_x, -grad_y
            
            direction = np.array([grad_x, grad_y])
            norm_dir = np.linalg.norm(direction)
            if norm_dir < 1e-10:
                no_improve_count += 1
                continue
            direction = direction / norm_dir * step_size

            new_point = p0 + direction
            if not is_inside_triangle(new_point, A, B, C):
                no_improve_count += 1
                continue

            # Evaluate new configuration
            new_points = points.copy()
            new_points[idx_to_move] = new_point
            new_min_area = get_smallest_triangle_area(new_points)

            if new_min_area > current_min_area:
                points = new_points
                current_min_area = new_min_area
                no_improve_count = 0
            else:
                no_improve_count += 1
                if no_improve_count % 50 == 0:
                    step_size *= 0.95
                    if step_size < 1e-5:
                        step_size = 1e-5

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config