import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    base_seed = 42
    best_points = None
    best_min_area = -1

    # Precompute base step size for hexagonal lattice
    d0 = np.sqrt(2 / (11 * np.sqrt(3)))
    # Optimized search range and resolution for step size scaling
    deltas = np.logspace(np.log10(0.8), np.log10(1.2), 30)

    # Get triangle vertices and compute symmetry axis
    A, B, C = get_unit_triangle()
    min_y = min(A[1], B[1], C[1])
    base_points = [p for p in [A, B, C] if abs(p[1] - min_y) < 1e-10]
    if len(base_points) < 2:
        sorted_points = sorted([A, B, C], key=lambda p: p[1])
        base_points = sorted_points[:2]
    symmetry_x = (base_points[0][0] + base_points[1][0]) / 2

    def generate_symmetric_lattice_points(d):
        # Compute bounding box
        x_min = min(A[0], B[0], C[0])
        x_max = max(A[0], B[0], C[0])
        y_min = min(A[1], B[1], C[1])
        y_max = max(A[1], B[1], C[1])

        points_left = []
        y = y_min
        row = 0
        hex_height = (np.sqrt(3) / 2) * d

        while y <= y_max:
            x_start = x_min + (d / 2) * (row % 2)
            x = x_start
            while x <= symmetry_x:  # Only generate left half
                p = np.array([x, y])
                if is_inside_triangle(p.reshape(1, 2), A, B, C):
                    points_left.append(p)
                x += d
            y += hex_height
            row += 1

        # Create symmetric points (mirror left half)
        points = []
        for p in points_left:
            if abs(p[0] - symmetry_x) < 1e-5:
                points.append(p)
            else:
                points.append(p)
                points.append(np.array([2 * symmetry_x - p[0], p[1]]))
        return points

    def compute_symmetric_pairs(points, tol=1e-5):
        n = len(points)
        used = [False] * n
        axis_points = []
        pairs = []
        for i in range(n):
            if used[i]:
                continue
            x, y = points[i]
            if abs(x - symmetry_x) < tol:
                axis_points.append(i)
                used[i] = True
            else:
                found = False
                for j in range(i + 1, n):
                    if used[j]:
                        continue
                    xj, yj = points[j]
                    if abs(xj - (2 * symmetry_x - x)) < tol and abs(yj - y) < tol:
                        pairs.append((i, j))
                        used[i] = True
                        used[j] = True
                        found = True
                        break
                if not found:
                    axis_points.append(i)
                    used[i] = True
        return axis_points, pairs

    for restart in range(len(deltas)):
        np.random.seed(base_seed + restart)
        d = d0 * deltas[restart]
        lattice_points = generate_symmetric_lattice_points(d)

        # Skip if insufficient points
        if len(lattice_points) < 11:
            continue

        points = np.array(lattice_points[:11])
        axis_points, pairs = compute_symmetric_pairs(points)

        # Enhanced annealing parameters
        T0 = 0.1
        T = T0
        cooling_rate = 0.999
        total_iters = 10000

        for iter_idx in range(total_iters):
            current_min = get_smallest_triangle_area(points)
            idx = np.random.randint(11)

            # Determine move type (axis point or symmetric pair)
            if idx in axis_points:
                move_type = 'single'
                partner = None
            else:
                move_type = 'pair'
                partner = None
                for p1, p2 in pairs:
                    if idx == p1:
                        partner = p2
                        break
                    elif idx == p2:
                        partner = p1
                        break

            # Adaptive exploration directions
            num_directions = max(10, int(50 * (T / T0)))
            best_improvement = -np.inf
            best_candidate = None

            for _ in range(num_directions):
                theta = np.random.uniform(0, 2 * np.pi)
                magnitude = T
                dx = magnitude * np.cos(theta)
                dy = magnitude * np.sin(theta)

                candidate = points.copy()
                if move_type == 'single':
                    candidate[idx] += [dx, dy]
                    if not is_inside_triangle(candidate[idx:idx+1], A, B, C):
                        continue
                else:
                    candidate[idx] += [dx, dy]
                    candidate[partner] += [-dx, dy]
                    if not (is_inside_triangle(candidate[idx:idx+1], A, B, C) and 
                            is_inside_triangle(candidate[partner:partner+1], A, B, C)):
                        continue

                new_min = get_smallest_triangle_area(candidate)
                if new_min > best_improvement:
                    best_improvement = new_min
                    best_candidate = candidate

            if best_candidate is not None:
                delta = best_improvement - current_min
                if delta >= 0:
                    points = best_candidate
                else:
                    if np.random.rand() < np.exp(delta / T):
                        points = best_candidate

            T *= cooling_rate

        current_min_area = get_smallest_triangle_area(points)
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_points = points.copy()

    return best_points.astype(np.float32)