import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

try:
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

np.random.seed(42)
random.seed(42)

def generate_grid(rows, A, B, C):
    base = np.linalg.norm(B - A)
    height = 2.0 / base
    total_rows = len(rows)
    points_list = []
    
    for i, n in enumerate(rows):
        y = (i + 0.5) / total_rows * height
        width = base * (total_rows - i) / total_rows
        left_x = (base - width) / 2.0
        
        if n == 1:
            x = base / 2.0
            points_list.append([x, y])
        else:
            dx = width / (n - 1)
            shift = dx / 2.0 if i % 2 == 1 else 0.0
            for j in range(n):
                x = left_x + j * dx + shift
                points_list.append([x, y])
                
    return np.array(points_list)

def generate_random_points(n, A, B, C):
    points = []
    for _ in range(n):
        a, b = sorted([random.random(), random.random()])
        c1, c2, c3 = a, b - a, 1 - b
n        point = c1 * A + c2 * B + c3 * C
        points.append(point)
    return np.array(points)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    base = np.linalg.norm(B - A)
    height = 2.0 / base

    # Literature-backed row structures (top to bottom)
    row_structures = [
        [2, 3, 3, 3],  # Standard solution
        [3, 2, 3, 3],  # 2 in second row
        [3, 3, 2, 3]   # 2 in third row
    ]
    best_points = None
    best_min_area = -1

    # 10 seeds for robust exploration
    for seed in range(10):
        np.random.seed(seed)
        random.seed(seed)

        # Generate 5 diverse initial configurations per seed
        configs = []
        
        # 1-3: Grid patterns with different row structures
        for rows in row_structures:
            grid = generate_grid(rows, A, B, C)
            configs.append(grid)

        # 4: Hexagonal grid (standard grid with alternating shifts)
        hex_grid = generate_grid([2, 3, 3, 3], A, B, C)
        configs.append(hex_grid)

        # 5: Random perturbation of standard grid
        base_grid = generate_grid([2, 3, 3, 3], A, B, C)
        perturbed = base_grid + np.random.uniform(-0.01, 0.01, size=base_grid.shape)
        configs.append(perturbed)

        for points in configs:
            # Ensure points are distinct and inside triangle
            points = np.clip(points, 0, None)  # Basic containment
            points = points[:11]  # Ensure exactly 11 points

            # Simulated Annealing
            current_min_area = get_smallest_triangle_area(points)
            n_points = len(points)
            T0 = 0.5
            cooling_rate = 0.999
            max_iter = 20000

            for iter in range(max_iter):
                T = T0 * (cooling_rate ** iter)
                idx = random.randrange(n_points)
                P_old = points[idx]

                # Convert to barycentric coordinates
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

                # Temperature-scaled step size
                step = 0.1 * T / T0
                da = random.uniform(-step, step)
                db = random.uniform(-step, step)
                a1 = a0 + da
                b1 = b0 + db
                c1 = 1 - a1 - b1

                # Reject moves outside triangle (preserve interior points)
                if a1 < 0 or b1 < 0 or c1 < 0:
                    continue

                # Convert back to Cartesian
                P_new = a1 * A + b1 * B + c1 * C

                new_points = np.copy(points)
                new_points[idx] = P_new
                new_min_area = get_smallest_triangle_area(new_points)

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

            # Track best configuration
            min_area_after_sa = get_smallest_triangle_area(points)
            if min_area_after_sa > best_min_area:
                best_min_area = min_area_after_sa
                best_points = points.copy()

    points = best_points

    # Final refinement with Nelder-Mead (derivative-free)
    if SCIPY_AVAILABLE:
        def objective(x):
            pts = x.reshape(11, 2)
            area = get_smallest_triangle_area(pts)
            return -area

        x0 = points.flatten()
        res = minimize(objective, x0, method='Nelder-Mead', 
                      options={'maxiter': 500, 'disp': False})
        if res.success:
            points = res.x.reshape(11, 2)

    return points