import random
import math
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    base_length = B[0] - A[0]  # Since A[0]=0, base_length = B[0]
    axis_x = (A[0] + B[0]) / 2.0
    centroid_y = C[1] / 3.0  # Centroid y-coordinate

    best_config = None
    best_min_area = -1.0

    num_restarts = 10
    initial_step = 0.05
    min_step = 1e-6
    no_improve_limit = 5000  # Increased from 1000
    max_iter = 100000

    # Helper to find critical triangles
    def get_critical_triangles(pts, min_area_val, tol=1e-5):
        n = pts.shape[0]
        critical = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs((pts[j,0]-pts[i,0])*(pts[k,1]-pts[i,1]) - 
                                    (pts[k,0]-pts[i,0])*(pts[j,1]-pts[i,1]))
                    if area <= min_area_val + tol:
                        critical.append((i, j, k))
        return critical

    for restart in range(num_restarts):
        # Generate symmetric initial configuration with centroid bias
        for _ in range(1000):
            # Base point on symmetry axis with centroid bias
            y0 = np.random.normal(loc=centroid_y, scale=0.1)
            y0 = max(0, min(C[1], y0))
            base = np.array([axis_x, y0])

            left_points = []
            for j in range(5):
                x = random.uniform(0, axis_x - 1e-5)
                # Maximum y for left half: line from A(0,0) to C
                max_y = ((C[1] - A[1]) / (C[0] - A[0])) * x
                y = random.uniform(0, max_y)
                left_points.append(np.array([x, y]))

            # Build full configuration: base + left + mirrored right
            points_list = [base]
            points_list.extend(left_points)
            for lp in left_points:
                points_list.append(np.array([base_length - lp[0], lp[1]]))
            points = np.array(points_list)

            min_area = get_smallest_triangle_area(points)
            if min_area > 1e-10:
                break
        
        step_size = initial_step
        no_improve_count = 0
        current_min_area = min_area

        for it in range(max_iter):
            # Compute critical triangles
            critical_triangles = get_critical_triangles(points, current_min_area, 1e-5)
            if not critical_triangles:
                # Fallback to random move if no critical triangles found (should not happen)
                i = random.randint(0, 5)
            else:
                # Count point occurrences in critical triangles
                point_count = np.zeros(11, dtype=int)
                for tri in critical_triangles:
                    for idx in tri:
                        point_count[idx] += 1
                
                # Select critical triangle and point to move
                tri = random.choice(critical_triangles)
                point_to_move = random.choice(tri)

                # Convert to left representation for symmetry handling
                if point_to_move == 0:
                    move_left_index = None
                    symmetry_break = False
                elif 1 <= point_to_move <= 5:
                    move_left_index = point_to_move
                    symmetry_break = (random.random() < 0.1)
                else:  # 6-10 (right points)
                    move_left_index = point_to_move - 5
                    symmetry_break = (random.random() < 0.1)

            # Generate new configuration
            new_points = points.copy()
            if 'move_left_index' in locals() and move_left_index is not None:
                # Move left point (or converted right point)
                angle = random.uniform(0, 2 * math.pi)
                r = step_size * math.sqrt(random.random())
                dx = r * math.cos(angle)
                dy = r * math.sin(angle)
                new_point = points[move_left_index] + np.array([dx, dy])
                
                if is_inside_triangle(new_point, A, B, C) and (new_point[0] < axis_x - 1e-5 or symmetry_break):
                    new_points[move_left_index] = new_point
                    if not symmetry_break:
                        # Mirror to right in symmetric move
                        new_points[move_left_index + 5] = np.array([base_length - new_point[0], new_point[1]])
                else:
                    no_improve_count += 1
                    continue
            else:
                # Base point move (y only)
                dy = step_size * (2 * random.random() - 1)
                new_y = points[0, 1] + dy
                new_y = max(0, min(C[1], new_y))
                new_point = np.array([axis_x, new_y])
                if not is_inside_triangle(new_point, A, B, C):
                    no_improve_count += 1
                    continue
                new_points[0] = new_point

            # Symmetry restoration after breaking
            if 'symmetry_break' in locals() and symmetry_break:
                # Force symmetry
                for i in range(1, 6):
                    new_points[i+5] = np.array([base_length - new_points[i,0], new_points[i,1]])
                # Short symmetric hill-climbing to recover
                short_steps = 100
                short_step = step_size * 0.5
                for _ in range(short_steps):
                    i = random.randint(0, 5)
                    test_points = new_points.copy()
                    if i == 0:
                        dy = short_step * (2 * random.random() - 1)
                        new_y = test_points[0, 1] + dy
                        new_y = max(0, min(C[1], new_y))
                        test_points[0] = np.array([axis_x, new_y])
                    else:
                        angle = random.uniform(0, 2 * math.pi)
                        r = short_step * math.sqrt(random.random())
                        dx = r * math.cos(angle)
                        dy = r * math.sin(angle)
                        new_pt = test_points[i] + np.array([dx, dy])
                        if is_inside_triangle(new_pt, A, B, C) and new_pt[0] < axis_x - 1e-5:
                            test_points[i] = new_pt
                            test_points[i+5] = np.array([base_length - new_pt[0], new_pt[1]])
                        else:
                            continue
                    test_min_area = get_smallest_triangle_area(test_points)
                    if test_min_area > get_smallest_triangle_area(new_points):
                        new_points = test_points

            new_min_area = get_smallest_triangle_area(new_points)

            if new_min_area > current_min_area:
                points = new_points
                current_min_area = new_min_area
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Step size adaptation
            if no_improve_count >= no_improve_limit:
                step_size *= 0.95  # Reduced from 0.9
                no_improve_count = 0
                if step_size < min_step:
                    break

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points

    return best_config