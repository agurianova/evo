import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    base_seed = 42
    A, B, C = get_unit_triangle()
    min_y = min(A[1], B[1], C[1])
    max_y = max(A[1], B[1], C[1])
    base_points = sorted([p for p in [A, B, C] if abs(p[1] - min_y) < 1e-10], key=lambda p: p[0])
    base1, base2 = base_points[0], base_points[1]
    apex = [p for p in [A, B, C] if abs(p[1] - max_y) < 1e-10][0]
    symmetry_x = (base1[0] + base2[0]) / 2

    def get_left_x(y):
        if np.isclose(max_y, min_y):
            return symmetry_x
        return base1[0] + (apex[0] - base1[0]) * (y - min_y) / (max_y - min_y)

    def generate_lattice_points(d):
        points = []
        y = min_y
        row = 0
        hex_height = (np.sqrt(3) / 2) * d
        while y <= max_y:
            left_x = get_left_x(y)
            x_start = left_x + (d / 2) * (row % 2)
            x = x_start
            while x <= symmetry_x:
                points.append(np.array([x, y]))
                x += d
            y += hex_height
            row += 1
        
        full_points = []
        for p in points:
            full_points.append(p)
            if not np.isclose(p[0], symmetry_x):
                full_points.append(np.array([2 * symmetry_x - p[0], p[1]]))
        return full_points

    def select_k_points(points_list, k):
        if len(points_list) <= k:
            return points_list
        selected = [points_list[0]]
        candidates = points_list[1:]
        for _ in range(1, k):
            min_dists = []
            for c in candidates:
                dists = [np.linalg.norm(c - s) for s in selected]
                min_dists.append(min(dists))
            idx = np.argmax(min_dists)
            selected.append(candidates[idx])
            del candidates[idx]
        return selected

    def generate_random_points(n):
        points = []
        bbox = [
            min(A[0], B[0], C[0]),
            max(A[0], B[0], C[0]),
            min(A[1], B[1], C[1]),
            max(A[1], B[1], C[1])
        ]
        while len(points) < n:
            x = np.random.uniform(bbox[0], bbox[1])
            y = np.random.uniform(bbox[2], bbox[3])
            if is_inside_triangle(np.array([[x, y]]), A, B, C):
                points.append(np.array([x, y]))
        return points

    def generate_candidate_points(grid_size):
        points = []
        bbox = [
            min(A[0], B[0], C[0]),
            max(A[0], B[0], C[0]),
            min(A[1], B[1], C[1]),
            max(A[1], B[1], C[1])
        ]
        for i in range(grid_size):
            for j in range(grid_size):
                x = bbox[0] + (bbox[1] - bbox[0]) * i / (grid_size - 1)
                y = bbox[2] + (bbox[3] - bbox[2]) * j / (grid_size - 1)
                if is_inside_triangle(np.array([[x, y]]), A, B, C):
                    points.append(np.array([x, y]))
        return points

    d0 = np.sqrt(2 / (11 * np.sqrt(3)))
    deltas = np.logspace(np.log10(0.5), np.log10(1.5), 30)
    best_points = None
    best_min_area = -1

    for restart in range(len(deltas)):
        np.random.seed(base_seed + restart)
        d = d0 * deltas[restart]
        
        for init_strategy in ['hexagonal', 'random', '10+1']:
            if init_strategy == 'hexagonal':
                lattice_points = generate_lattice_points(d)
                if len(lattice_points) < 11:
                    continue
                points = np.array(select_k_points(lattice_points, 11))
            
            elif init_strategy == 'random':
                points = np.array(generate_random_points(11))
            
            else:  # '10+1'
                d0_10 = np.sqrt(2 / (10 * np.sqrt(3)))
                d_10 = d0_10 * deltas[restart]
                lattice_points_10 = generate_lattice_points(d_10)
                if len(lattice_points_10) < 10:
                    continue
                points_10 = np.array(select_k_points(lattice_points_10, 10))
                candidates = generate_candidate_points(5)
                best_candidate = None
                best_min_area_11 = -1
                for cand in candidates:
                    pts = np.vstack([points_10, cand])
                    min_area_val = get_smallest_triangle_area(pts)
                    if min_area_val > best_min_area_11:
                        best_min_area_11 = min_area_val
                        best_candidate = cand
                if best_candidate is None:
                    continue
                points = np.vstack([points_10, best_candidate])

            T0 = 0.1
            T = T0
            cooling_rate = 0.999
            total_iters = 10000

            for iter_idx in range(total_iters):
                current_min = get_smallest_triangle_area(points)

                critical_points = set()
                for i in range(11):
                    for j in range(i + 1, 11):
                        for k in range(j + 1, 11):
                            area = 0.5 * abs((points[j, 0] - points[i, 0]) * (points[k, 1] - points[i, 1]) - 
                                             (points[k, 0] - points[i, 0]) * (points[j, 1] - points[i, 1]))
                            if abs(area - current_min) < 1e-10:
                                critical_points.update([i, j, k])

                weights = np.ones(11)
                if critical_points:
                    weights[list(critical_points)] = 3.0
                weights /= weights.sum()
                idx = np.random.choice(11, p=weights)

                num_directions = int(50 * (T / T0) + 10)
                best_improvement = -np.inf
                best_candidate = None

                for _ in range(num_directions):
                    theta = np.random.uniform(0, 2 * np.pi)
                    magnitude = np.sqrt(T)
                    dx = magnitude * np.cos(theta)
                    dy = magnitude * np.sin(theta)

                    candidate = points.copy()
                    candidate[idx] += [dx, dy]
                    if not is_inside_triangle(candidate[idx:idx + 1], A, B, C):
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