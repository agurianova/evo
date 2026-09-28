import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area


def triangle_signed_area(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

def project_to_triangle(point, A, B, C):
    if is_inside_triangle(point, A, B, C):
        return point
    
    edges = [(A, B), (B, C), (C, A)]
    best_point = None
    min_dist = float('inf')
    
    for (P, Q) in edges:
        v = Q - P
        w = point - P
        c1 = np.dot(w, v)
        c2 = np.dot(v, v)
        if c2 < 1e-10:
            continue
        b = c1 / c2
        if b < 0:
            proj = P
        elif b > 1:
            proj = Q
        else:
            proj = P + b * v
        
        dist = np.linalg.norm(point - proj)
        if dist < min_dist:
            min_dist = dist
            best_point = proj
            
    return best_point

def generate_random_points_in_triangle(n, A, B, C):
    points = []
    for _ in range(n):
        u = np.random.rand()
        v = np.random.rand()
        if u + v > 1:
            u = 1 - u
            v = 1 - v
        w = 1 - u - v
        points.append(u * A + v * B + w * C)
    return np.array(points)

def farthest_point_sampling(n_points, A, B, C, n_candidates=1000):
    # Generate candidate points
    candidates = generate_random_points_in_triangle(n_candidates, A, B, C)
    
    # Select first point randomly
    selected_indices = [np.random.randint(0, n_candidates)]
    selected = [candidates[selected_indices[0]]]
    
    # Iteratively select points maximizing min distance to selected set
    for _ in range(1, n_points):
        min_dists = np.zeros(n_candidates)
        for i, cand in enumerate(candidates):
            min_dists[i] = min(np.linalg.norm(cand - s) for s in selected)
        next_idx = np.argmax(min_dists)
        selected.append(candidates[next_idx])
        selected_indices.append(next_idx)
    
    return np.array(selected)

def entrypoint() -> np.ndarray:
    best_points = None
    best_area = 0

    for seed in range(10):
        np.random.seed(seed)
        tri = get_unit_triangle()
        A, B, C = tri
        
        # Initialize with farthest-point sampling (Poisson-disk alternative)
        points = farthest_point_sampling(11, A, B, C, n_candidates=1000)

        # Local optimization with basin-hopping
        max_iter = 5000
        step_size = 0.1
        repulsion_strength = 0.01

        for iter in range(max_iter):
            current_min_area = get_smallest_triangle_area(points)
            
            # Adaptive k: scale with current min_area
            k = max(5, min(20, int(100 * current_min_area)))

            # Compute all triangle areas and get top-k smallest
            triangles = []
            n = 11
            for i in range(n):
                for j in range(i+1, n):
                    for l in range(j+1, n):
                        area_val = abs(triangle_signed_area(points[i], points[j], points[l]))
                        triangles.append((area_val, i, j, l))
            triangles.sort(key=lambda x: x[0])
            top_k = triangles[:k]

            # Compute gradient for area maximization
            area_grads = np.zeros((11, 2))
            for (area_val, i, j, l) in top_k:
                a, b, c = points[i], points[j], points[l]
                signed_area = triangle_signed_area(a, b, c)
                if abs(signed_area) < 1e-10:
                    continue
                sign = 1.0 if signed_area >= 0 else -1.0
                grad_a = sign * np.array([b[1] - c[1], c[0] - b[0]])
                grad_b = sign * np.array([c[1] - a[1], a[0] - c[0]])
                grad_c = sign * np.array([a[1] - b[1], b[0] - a[0]])
                area_grads[i] += grad_a
                area_grads[j] += grad_b
                area_grads[l] += grad_c

            # Compute repulsion gradient (inverse cube distance)
            repulsion_grads = np.zeros((11, 2))
            for i in range(11):
                for j in range(11):
                    if i == j:
                        continue
                    diff = points[i] - points[j]
                    dist = np.linalg.norm(diff)
                    if dist < 1e-5:
                        dist = 1e-5
                    repulsion_grads[i] += diff / (dist ** 3)

            # Combine gradients
            grads = area_grads + repulsion_strength * repulsion_grads

            # Normalize gradients to avoid numerical issues
            grad_norms = np.linalg.norm(grads, axis=1)
            max_norm = np.max(grad_norms)
            if max_norm > 0:
                grads = grads / max_norm

            current_min_area = get_smallest_triangle_area(points)
            step = step_size
            found = False
            
            # Backtracking line search
            for backtrack in range(10):
                new_points = points + step * grads
                for idx in range(11):
                    new_points[idx] = project_to_triangle(new_points[idx], A, B, C)
                new_min_area = get_smallest_triangle_area(new_points)
                
                if new_min_area > current_min_area:
                    points = new_points
                    step_size = min(step_size * 1.1, 0.5)
                    found = True
                    break
                else:
                    step *= 0.5

            if not found:
                step_size *= 0.9

            # Enhanced basin-hopping escape
            if iter % 50 == 0 and iter > 0:
                perturbation = np.random.uniform(-0.2, 0.2, size=(11, 2))
                new_points = points + perturbation
                for idx in range(11):
                    new_points[idx] = project_to_triangle(new_points[idx], A, B, C)
                new_min_area = get_smallest_triangle_area(new_points)
                if new_min_area > get_smallest_triangle_area(points):
                    points = new_points

        # Evaluate final configuration
        area = get_smallest_triangle_area(points)
        if area > best_area:
            best_area = area
            best_points = points.copy()

    return best_points