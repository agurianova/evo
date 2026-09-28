import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    centroid = (A + B + C) / 3

    # Generate hexagonal lattice via triangular grid (m=4) with symmetric point removal
    s = np.linalg.norm(B - A)
    m = 4
    keep_points = []
    for i in range(0, m+1):
        for j in range(0, m+1 - i):
            if (i, j) not in [(1,0), (0,1), (3,1), (1,3)]:
                keep_points.append((i, j))

    points = []
    for (i, j) in keep_points:
        u = i / m
        v = j / m
        w = 1 - u - v
        P = w * A + u * B + v * C
        points.append(P)
    points = np.array(points)

    # Apply 2 iterations of Lloyd's relaxation (repulsion)
    for _ in range(2):
        new_points = []
        for i in range(11):
            P = points[i]
            repel = np.zeros(2)
            for j in range(11):
                if i == j:
                    continue
                diff = P - points[j]
                dist_sq = np.sum(diff**2)
                if dist_sq < 1e-10:
                    repel += np.random.uniform(-0.1, 0.1, 2)
                else:
                    repel += diff / dist_sq
            new_P = P + 0.05 * repel
            if not is_inside_triangle(new_P, A, B, C):
                new_P = (new_P + centroid) / 2
            new_points.append(new_P)
        points = np.array(new_points)

    current_points = points
    n = 11

    # Precompute all triangles and current areas for incremental updates
    triangles = []
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                triangles.append((i, j, k))
    num_tri = len(triangles)
    current_areas = np.zeros(num_tri)
    for idx, (i, j, k) in enumerate(triangles):
        area_val = 0.5 * abs(
            (current_points[j,0] - current_points[i,0]) * (current_points[k,1] - current_points[i,1]) -
            (current_points[j,1] - current_points[i,1]) * (current_points[k,0] - current_points[i,0])
        )
        current_areas[idx] = area_val
    current_min = np.min(current_areas)

    # Precompute point-to-triangle mappings
    point_to_triangles = [[] for _ in range(n)]
    for idx, (i, j, k) in enumerate(triangles):
        point_to_triangles[i].append(idx)
        point_to_triangles[j].append(idx)
        point_to_triangles[k].append(idx)

    # Initialize best_min for adaptive decay
    best_min = current_min
    consecutive_non_improvements = 0

    # Simulated annealing parameters
    T0 = 0.1
    cooling_rate = 0.999
    step_size = 0.2
    decay_base = 0.9995  # Base decay rate (adaptive modification below)
    max_iter = 10000
    T = T0

    for _ in range(max_iter):
        # Determine move type (single or two-point)
        use_two_points = random.random() < 0.1

        # Identify candidate points from bottleneck triangles
        smallest_triangles = []
        for idx, area_val in enumerate(current_areas):
            if area_val <= current_min + 1e-10:
                smallest_triangles.append(triangles[idx])
        
        candidate_points = set()
        for tri in smallest_triangles:
            candidate_points.update(tri)
        candidate_points = list(candidate_points)

        # Select points to move
        if use_two_points and len(candidate_points) >= 2:
            idx1, idx2 = random.sample(candidate_points, 2)
        else:
            idx1 = random.choice(candidate_points)
            idx2 = None

        # Compute movement directions
        directions = []
        for idx in [idx1, idx2]:
            if idx is None:
                continue
            tri_list = [tri for tri in smallest_triangles if idx in tri]
            if not tri_list:
                direction = np.random.uniform(-1, 1, 2)
                direction /= np.linalg.norm(direction)
            else:
                # Focus on the most critical triangle (smallest area)
                min_tri = None
                min_area_tri = float('inf')
                for tri in tri_list:
                    tri_idx = triangles.index(tri)
                    area_tri = current_areas[tri_idx]
                    if area_tri < min_area_tri:
                        min_area_tri = area_tri
                        min_tri = tri
                
                other_indices = [i for i in min_tri if i != idx]
                q, r = other_indices
                Q, R = current_points[q], current_points[r]
                v = R - Q
                n_vec = np.array([-v[1], v[0]])
                n_norm = np.linalg.norm(n_vec)
                if n_norm < 1e-10:
                    direction = np.random.uniform(-1, 1, 2)
                    direction /= np.linalg.norm(direction)
                else:
                    n_vec = n_vec / n_norm
                    w = current_points[idx] - Q
                    signed_dist = np.dot(w, n_vec)
                    if abs(signed_dist) < 1e-10:
                        direction = np.random.uniform(-1, 1, 2)
                        direction /= np.linalg.norm(direction)
                    else:
                        direction = n_vec * np.sign(signed_dist)
            directions.append(direction)
        
        # Generate new candidate positions
        new_positions = []
        for i, idx in enumerate([idx1, idx2]):
            if idx is None:
                continue
            new_pos = current_points[idx] + step_size * directions[i]
            if not is_inside_triangle(new_pos, A, B, C):
                new_pos = (new_pos + centroid) / 2
            new_positions.append((idx, new_pos))

        # Create new points array
        new_points = current_points.copy()
        for idx, new_pos in new_positions:
            new_points[idx] = new_pos

        # Check distinctness
        distinct = True
        for i in range(11):
            for j in range(i+1, 11):
                if np.linalg.norm(new_points[i] - new_points[j]) < 1e-5:
                    distinct = False
                    break
            if not distinct:
                break
        if not distinct:
            continue

        # Compute affected triangles for incremental area update
        moved_indices = [idx1]
        if idx2 is not None:
            moved_indices.append(idx2)
        affected_tri_indices = set()
        for idx in moved_indices:
            affected_tri_indices.update(point_to_triangles[idx])
        
        # Update areas only for affected triangles
        new_areas = current_areas.copy()
        for tri_idx in affected_tri_indices:
            i, j, k = triangles[tri_idx]
            area_val = 0.5 * abs(
                (new_points[j,0] - new_points[i,0]) * (new_points[k,1] - new_points[i,1]) -
                (new_points[j,1] - new_points[i,1]) * (new_points[k,0] - new_points[i,0])
            )
            new_areas[tri_idx] = area_val
        new_min = np.min(new_areas)

        # Simulated annealing acceptance
        delta = new_min - current_min
        accepted = False
        improved_best = False
        if delta > 0 or random.random() < np.exp(delta / T):
            current_points = new_points
            current_areas = new_areas
            current_min = new_min
            accepted = True
            if new_min > best_min:
                best_min = new_min
                improved_best = True

        # Update adaptive decay parameters
        if improved_best:
            consecutive_non_improvements = 0
        else:
            consecutive_non_improvements += 1

        # Adaptive step_size decay
        if consecutive_non_improvements > 100:
            decay = 0.999
        else:
            decay = 0.9999
        step_size *= decay

        # Update temperature
        T *= cooling_rate
        if step_size < 1e-5 or T < 1e-5:
            break

    return current_points