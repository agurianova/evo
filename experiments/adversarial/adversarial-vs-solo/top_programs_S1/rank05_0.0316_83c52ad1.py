import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    base_seed = 42
    best_points = None
    best_min_area = -1

    # Precompute base step size for hexagonal lattice
    d0 = np.sqrt(2 / (11 * np.sqrt(3)))
    # Widen scaling range: [0.5, 1.5] (30 steps)
    deltas = np.logspace(np.log10(0.5), np.log10(1.5), 30)

    A, B, C = get_unit_triangle()

    # Helper function for farthest-point sampling
    def farthest_point_sampling(points, k):
        N = points.shape[0]
        if k >= N:
            return points
        selected_indices = [0]
        min_dists = np.linalg.norm(points - points[0], axis=1)
        for i in range(1, k):
            idx = np.argmax(min_dists)
            selected_indices.append(idx)
            dists = np.linalg.norm(points - points[idx], axis=1)
            min_dists = np.minimum(min_dists, dists)
        return points[selected_indices]

    # Helper function to generate random points inside the triangle
    def generate_random_points(n):
        points = []
        for i in range(n):
            r1, r2 = np.random.rand(2)
            sqrt_r1 = np.sqrt(r1)
            x = (1 - sqrt_r1) * A[0] + sqrt_r1 * (1 - r2) * B[0] + sqrt_r1 * r2 * C[0]
            y = (1 - sqrt_r1) * A[1] + sqrt_r1 * (1 - r2) * B[1] + sqrt_r1 * r2 * C[1]
            points.append([x, y])
        return np.array(points)

    # Helper function to generate lattice points with boundary constraints
    def generate_lattice_points(d, A, B, C):
        min_y = min(A[1], B[1], C[1])
        max_y = max(A[1], B[1], C[1])
        base_points = [p for p in [A, B, C] if abs(p[1] - min_y) < 1e-5]
        base_left = min(base_points, key=lambda p: p[0])
        base_right = max(base_points, key=lambda p: p[0])
        apex = max([A, B, C], key=lambda p: p[1])

        points = []
        y = min_y
        row = 0
        hex_height = (np.sqrt(3) / 2) * d

        while y <= max_y:
            if max_y > min_y:
                t = (y - min_y) / (max_y - min_y)
                left_x = base_left[0] + t * (apex[0] - base_left[0])
                right_x = base_right[0] + t * (apex[0] - base_right[0])
            else:
                left_x = base_left[0]
                right_x = base_right[0]

            x_start = left_x + (d / 2) * (row % 2)
            x = x_start
            while x <= right_x:
                points.append(np.array([x, y]))
                x += d

            y += hex_height
            row += 1

        return points

    # Total restarts: 30 hexagonal + 10 random = 40
    total_restarts = 40
    num_hex_restart = 30
    num_random_restart = total_restarts - num_hex_restart

    for restart_idx in range(total_restarts):
        np.random.seed(base_seed + restart_idx)
        if restart_idx < num_hex_restart:
            d = d0 * deltas[restart_idx]
            lattice_points = generate_lattice_points(d, A, B, C)
            if len(lattice_points) < 11:
                continue
            lattice_array = np.array(lattice_points)
            points = farthest_point_sampling(lattice_array, 11)
        else:
            points = generate_random_points(11)

        # Enhanced annealing parameters
        T0 = 0.1
        T = T0
        cooling_rate = 0.999
        total_iters = 10000

        for iter_idx in range(total_iters):
            current_min = get_smallest_triangle_area(points)

            # Compute critical points
            critical_points = set()
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                         (points[k,0]-points[i,0])*(points[j,1]-points[i,1]))
                        if abs(area - current_min) < 1e-10:
                            critical_points.update([i, j, k])

            # Biased point selection with reduced weight
            weights = np.ones(11)
            if critical_points:
                weights[list(critical_points)] = 3.0
            weights /= weights.sum()
            idx = np.random.choice(11, p=weights)

            # Corrected exploration schedule
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
                if not is_inside_triangle(candidate[idx:idx+1], A, B, C):
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