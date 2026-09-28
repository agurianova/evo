import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    best_points = None
    best_min_area = -1
    archive = []  # Archive of (points, min_area) for locally optimal configurations

    # Precomputed partitions for row pattern generation (y_i = x_i-1, sum y_i=6)
    PARTITIONS_Y = [
        [6,0,0,0,0],
        [5,1,0,0,0],
        [4,2,0,0,0],
        [4,1,1,0,0],
        [3,3,0,0,0],
        [3,2,1,0,0],
        [3,1,1,1,0],
        [2,2,2,0,0],
        [2,2,1,1,0],
        [2,1,1,1,1]
    ]

    for restart in range(5):
        # Use restart index to diversify seeds
        np.random.seed(42 + restart)
        random.seed(42 + restart)

        # Generate initial points: use archive for restarts > 0 with 70% probability
        if restart == 0 or len(archive) == 0 or random.random() >= 0.7:
            # Generate random non-increasing row pattern
            y = random.choice(PARTITIONS_Y)
            rows = [y_i + 1 for y_i in y]
            total_rows = len(rows)
            points = []
            for i, num_points in enumerate(rows):
                c_weight = (i + 0.5) / total_rows
                for j in range(num_points):
                    b_weight = (j + 0.5) / num_points * (1 - c_weight)
                    a_weight = 1 - c_weight - b_weight
                    
                    # Resampling loop for valid interior points (increased to 20 tries)
                    max_tries = 20
                    for _ in range(max_tries):
                        da = random.uniform(-0.05, 0.05)
                        db = random.uniform(-0.05, 0.05)
                        a1 = a_weight + da
                        b1 = b_weight + db
                        c1 = 1 - a1 - b1
                        if a1 >= 0 and b1 >= 0 and c1 >= 0:
                            break
                    else:
                        a1, b1, c1 = a_weight, b_weight, 1 - a_weight - b_weight
                    
                    P = a1 * A + b1 * B + c1 * C
                    points.append(P)
            points = np.array(points)
        else:
            # Seed from archive: select random configuration and perturb
            archived_points, _ = random.choice(archive)
            points = archived_points + np.random.uniform(-0.01, 0.01, size=(11, 2))
            # Project any points outside triangle back inside
n            for i in range(len(points)):
                p = points[i]
                if not is_inside_triangle(p, A, B, C):
                    # Convert to barycentric and resample
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
                        continue
                    b0 = (d11 * d20 - d01 * d21) / denom
                    c0 = (d00 * d21 - d01 * d20) / denom
                    a0 = 1 - b0 - c0

                    max_tries = 20
                    for _ in range(max_tries):
                        da = random.uniform(-0.05, 0.05)
                        db = random.uniform(-0.05, 0.05)
                        a1 = a0 + da
                        b1 = b0 + db
                        c1 = 1 - a1 - b1
                        if a1 >= 0 and b1 >= 0 and c1 >= 0:
                            break
                    else:
                        a1, b1, c1 = a0, b0, 1 - a0 - b0
                    
                    P = a1 * A + b1 * B + c1 * C
                    points[i] = P

        # Simulated annealing
        current_min_area = get_smallest_triangle_area(points)
        n_points = len(points)
        T0 = 0.1
        cooling_rate = 0.995
        max_iter = 10000

        for iter in range(max_iter):
            T = T0 * (cooling_rate ** iter)
            idx = random.randrange(n_points)
            P_old = points[idx]
            
            # Convert to barycentric
            v0 = B - A
            v1 = C - A
            v2 = P_old - A
            d00 = np.dot(v0, v0)
            d01 = np.dot(v0, v1)
            d11 = np.dot(v1, v1)
            d20 = np.dot(v2, v0)
            d21 = np.dot(v2, v1)
            denom = d00 * d11 - d01 * d01
            if abs(denom) < 1e-10:
                continue
            b0 = (d11 * d20 - d01 * d21) / denom
            c0 = (d00 * d21 - d01 * d20) / denom
            a0 = 1 - b0 - c0
            
            # Resampling loop for valid interior points (increased to 20 tries)
            max_tries = 20
            for _ in range(max_tries):
                da = random.uniform(-0.05, 0.05)
                db = random.uniform(-0.05, 0.05)
                a1 = a0 + da
                b1 = b0 + db
                c1 = 1 - a1 - b1
                if a1 >= 0 and b1 >= 0 and c1 >= 0:
                    break
            else:
                continue
            
            P_new = a1 * A + b1 * B + c1 * C
            
            new_points = np.copy(points)
            new_points[idx] = P_new
            new_min_area = get_smallest_triangle_area(new_points)
            
            # Acceptance criterion
            if new_min_area > current_min_area:
                points = new_points
                current_min_area = new_min_area
            else:
                delta = current_min_area - new_min_area
                if delta < 0:
                    continue
                if random.random() < math.exp(-delta / T):
                    points = new_points
                    current_min_area = new_min_area

        # Local refinement with adaptive step size
        initial_step = 0.01
        min_step = 1e-5
        step = initial_step
        n_points = len(points)
        while step >= min_step:
            improved = False
            for idx in range(n_points):
                P_old = points[idx]
                best_P = P_old
                best_area = get_smallest_triangle_area(points)
                for dx in [-step, 0, step]:
                    for dy in [-step, 0, step]:
                        if dx == 0 and dy == 0:
                            continue
                        P_new = P_old + np.array([dx, dy])
                        if not is_inside_triangle(P_new, A, B, C):
                            continue
                        new_points = np.copy(points)
                        new_points[idx] = P_new
                        new_area = get_smallest_triangle_area(new_points)
                        if new_area > best_area:
                            best_area = new_area
                            best_P = P_new
                            improved = True
                if improved:
                    points[idx] = best_P
            if not improved:
                step *= 0.5

        min_area = get_smallest_triangle_area(points)
        # Archive locally optimal configurations
        if min_area > 0:  # Valid configuration
            # Add to archive (keep max 20)
            archive.append((points.copy(), min_area))
            if len(archive) > 20:
                # Remove the one with smallest min_area
                archive.sort(key=lambda x: x[1])
                archive = archive[1:]

        if min_area > best_min_area:
            best_min_area = min_area
            best_points = points

    return best_points