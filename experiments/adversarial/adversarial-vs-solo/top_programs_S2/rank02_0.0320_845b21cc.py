import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    restarts = 20
    best_config = None
    best_min_area = -1

    # Precompute base geometry
    base_width = abs(B[0] - C[0])
    H = B[1]  # Base height (y-coordinate of base vertices)

    for restart in range(restarts):
        np.random.seed(restart * 1000)
        
        # Generate adaptive level distributions (5 levels, sum=11)
        base_extra = np.array([0, 1, 2, 2, 1])  # Hexagonal lattice pattern [1,2,3,3,2]
        probs_extra = base_extra + 1
        probs_extra = probs_extra / probs_extra.sum()
        extra_counts = np.random.multinomial(6, probs_extra, size=1)[0]
        level_counts = [1 + extra_counts[i] for i in range(5)]

        # Generate uniform height ratios
        base_gaps = np.array([0.2, 0.2, 0.2, 0.2])  # Uniform vertical spacing
        gaps = base_gaps + np.random.normal(0, 0.03, 4)
        gaps = np.maximum(gaps, 0.01)  # Avoid degenerate gaps
        gaps = gaps / gaps.sum()
        height_ratios = [0.0]
        for i in range(4):
            height_ratios.append(height_ratios[-1] + gaps[i])

        # Build initial configuration
        points = []
        for level in range(5):
            t = height_ratios[level]
            y = t * H
            width_at_level = base_width * t
            n = level_counts[level]
            if n == 1:
                points.append([0.0, y])
            else:
                step = width_at_level / (n - 1)
                for i in range(n):
                    # Enhanced symmetry-breaking perturbation
                    perturb = np.random.uniform(-0.05, 0.05) * width_at_level
                    x = -width_at_level/2 + i * step + perturb
                    points.append([x, y])
        
        points = np.array(points, dtype=np.float64)
        current_min_area = get_smallest_triangle_area(points)
        
        # Simulated Annealing parameters
        T = 0.5
        alpha = 0.995
        step_size = 0.07  # Moderated initial step
        min_bary = 1e-6
        max_iter = 5000
        min_iter = 100
        accepted_count = 0

        for iter in range(max_iter):
            # Compute all triangle areas for selection
            all_areas = []
            triangles = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        Ax, Ay = points[i]
                        Bx, By = points[j]
                        Cx, Cy = points[k]
                        area = 0.5 * abs((Bx - Ax) * (Cy - Ay) - (Cx - Ax) * (By - Ay))
                        all_areas.append(area)
                        triangles.append((i, j, k))

            # Linear rank-based probabilistic selection (P ∝ 1/rank)
            all_areas_np = np.array(all_areas)
            sorted_indices = np.argsort(all_areas_np)
            rank_arr = np.zeros(len(all_areas_np))
            rank_arr[sorted_indices] = np.arange(1, len(all_areas_np)+1)
            probs = 1.0 / rank_arr  # Linear bias for critical triangles
            probs /= probs.sum()
            tri_idx = np.random.choice(len(all_areas_np), p=probs)
            i, j, k = triangles[tri_idx]
            idx = np.random.choice([i, j, k])

            # Perturb selected point
            delta = np.random.normal(0, step_size, 2)
            new_point = points[idx] + delta

            # Project to triangle using barycentric coordinates
            denom = 2.0
            u_coord = ((B[1]-C[1])*new_point[0] + (C[0]-B[0])*new_point[1] + (B[0]*C[1]-C[0]*B[1])) / denom
            v_coord = ((C[1]-A[1])*new_point[0] + (A[0]-C[0])*new_point[1] + (C[0]*A[1]-A[0]*C[1])) / denom
            w_coord = 1 - u_coord - v_coord

            if u_coord < min_bary: u_coord = min_bary
            if v_coord < min_bary: v_coord = min_bary
            if w_coord < min_bary: w_coord = min_bary
            total = u_coord + v_coord + w_coord
            u_coord, v_coord, w_coord = u_coord/total, v_coord/total, w_coord/total
            new_point = u_coord * A + v_coord * B + w_coord * C

            new_points = points.copy()
            new_points[idx] = new_point
            new_min_area = get_smallest_triangle_area(new_points)

            # Simulated annealing acceptance
            acceptance_prob = np.exp((new_min_area - current_min_area) / T)
            if np.random.rand() < acceptance_prob:
                points = new_points
                current_min_area = new_min_area
                accepted_count += 1

            T *= alpha

            # Moderated step size adaptation
            if (iter+1) % min_iter == 0:
                acceptance_rate = accepted_count / min_iter
                if acceptance_rate > 0.5:
                    step_size *= 1.15  # Less aggressive expansion
                elif acceptance_rate < 0.2:
                    step_size *= 0.85  # Less aggressive contraction
                accepted_count = 0

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config.astype(np.float32)