import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    centroid = (A + B + C) / 3

    # Generate 11 points via barycentric grid with repulsion
    points_bary = []
    for i in range(0, 4):
        for j in range(0, 4 - i):
            u = i / 3.0
            v = j / 3.0
            points_bary.append((u, v))
    points_bary.append((1/6, 1/6))  # Add extra point

    # Convert to Cartesian coordinates
    points = []
    for (u, v) in points_bary:
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
    current_min = get_smallest_triangle_area(current_points)

    # Simulated annealing parameters
    T0 = 0.1
    cooling_rate = 0.999
    step_size = 0.2
    decay = 0.9995
    max_iter = 10000
    T = T0

    for _ in range(max_iter):
        # Determine move type (single or two-point)
        use_two_points = random.random() < 0.1

        # Identify bottleneck triangles and candidate points
        min_area_val = get_smallest_triangle_area(current_points)
        smallest_triangles = []
        for i in range(11):
            for j in range(i+1, 11):
                for k in range(j+1, 11):
                    area = 0.5 * abs(
                        (current_points[j,0]-current_points[i,0])*(current_points[k,1]-current_points[i,1]) - 
                        (current_points[j,1]-current_points[i,1])*(current_points[k,0]-current_points[i,0])
                    )
                    if area <= min_area_val + 1e-10:
                        smallest_triangles.append((i, j, k))
        
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
                tri = random.choice(tri_list)
                other_indices = [i for i in tri if i != idx]
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

        # Validate new configuration
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

        # Evaluate new configuration
        new_min = get_smallest_triangle_area(new_points)
        delta = new_min - current_min

        # Simulated annealing acceptance
        if delta > 0 or random.random() < np.exp(delta / T):
            current_points = new_points
            current_min = new_min

        # Update parameters
        T *= cooling_rate
        step_size *= decay
        if step_size < 1e-5 or T < 1e-5:
            break

    return current_points