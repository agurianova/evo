import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

def entrypoint() -> np.ndarray:
    base_seed = 42
    best_points = None
    best_min_area = -1

    # Precompute base step size for hexagonal lattice
    d0 = np.sqrt(2 / (11 * np.sqrt(3)))
    # Widened scaling range with more steps to capture boundary-adapted step sizes
    deltas = np.logspace(np.log10(0.5), np.log10(1.5), 40)

    A, B, C = get_unit_triangle()
    # Precompute triangle geometry for boundary-adapted lattice
    points = [A, B, C]
    sorted_points = sorted(points, key=lambda p: p[1])
    base_points = sorted_points[:2]
    apex_pt = sorted_points[2]
    base_y = base_points[0][1]

    # Identify left/right base points
    base_points_sorted = sorted(base_points, key=lambda p: p[0])
    left_base_pt = base_points_sorted[0]
    right_base_pt = base_points_sorted[1]

    def generate_boundary_adapted_lattice_points(d):
        """Generate lattice points within triangle using boundary-adapted rows"""
        points_list = []
        y = base_y
        row = 0
        hex_height = (np.sqrt(3) / 2) * d

        # Handle degenerate triangle
        if abs(apex_pt[1] - base_y) < 1e-10:
            return []

        while y <= apex_pt[1] + 1e-5:
            # Compute x boundaries at current y
            t = (y - base_y) / (apex_pt[1] - base_y)
            x_left = left_base_pt[0] + t * (apex_pt[0] - left_base_pt[0])
            x_right = right_base_pt[0] + t * (apex_pt[0] - right_base_pt[0])

            # Hexagonal offset: shift every other row
            x_start = x_left + (d / 2) * (row % 2)
            x = x_start
            while x <= x_right + 1e-5:
                points_list.append(np.array([x, y]))
                x += d
            
            y += hex_height
            row += 1
        
        return points_list

    def farthest_point_sampling(candidates, n=11):
        """Select n points maximizing min-distance using greedy farthest-point sampling"""
        if len(candidates) <= n:
            return np.array(candidates)
        
        candidates = np.array(candidates)
        selected = []
        
        # Start with point closest to triangle centroid
        centroid = np.array([(A[0]+B[0]+C[0])/3, (A[1]+B[1]+C[1])/3])
        dists = np.linalg.norm(candidates - centroid, axis=1)
        idx0 = np.argmin(dists)
        selected.append(candidates[idx0])
        
        mask = np.ones(len(candidates), dtype=bool)
        mask[idx0] = False

        for _ in range(1, n):
            min_dists = np.zeros(len(candidates))
            for j in range(len(candidates)):
                if mask[j]:
                    d = np.min([np.linalg.norm(candidates[j] - p) for p in selected])
                    min_dists[j] = d
                else:
                    min_dists[j] = -np.inf
            
            idx = np.argmax(min_dists)
            selected.append(candidates[idx])
            mask[idx] = False

        return np.array(selected)

    for restart in range(len(deltas)):
        np.random.seed(base_seed + restart)
        d = d0 * deltas[restart]
        lattice_points = generate_boundary_adapted_lattice_points(d)

        if len(lattice_points) < 11:
            continue

        # Use farthest-point sampling for even dispersion
        points = farthest_point_sampling(lattice_points, 11)

        # Enhanced annealing parameters
        T0 = 0.1
        T = T0
        cooling_rate = 0.999
        total_iters = 10000

        for iter_idx in range(total_iters):
            current_min = get_smallest_triangle_area(points)

            # Compute critical points: points in triangles with area == current_min
            critical_points = set()
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                         (points[k,0]-points[i,0])*(points[j,1]-points[i,1]))
                        if abs(area - current_min) < 1e-10:
                            critical_points.update([i, j, k])

            # Moderate critical point weighting (3.0) prevents over-correction
            weights = np.ones(11)
            if critical_points:
                weights[list(critical_points)] = 3.0  # Reduced from 10.0
            weights /= weights.sum()
            idx = np.random.choice(11, p=weights)

            # Corrected exploration schedule: decreases with temperature
            num_directions = int(50 * (T / T0) + 10)  # Was increasing, now decreasing
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