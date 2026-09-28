import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def signed_area(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])

def triangle_area(a, b, c):
    return 0.5 * abs(signed_area(a, b, c))

def distinct_points(points, min_dist=1e-5):
    n = points.shape[0]
    for i in range(n):
        for j in range(i+1, n):
            if np.linalg.norm(points[i] - points[j]) < min_dist:
                return False
    return True

def project_to_triangle(p, A, B, C):
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
        return A
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1 - v - w

    if u >= 0 and v >= 0 and w >= 0:
        return p

    d00 = np.dot(v0, v0)
    t = np.dot(v2, v0) / d00
    t = max(0, min(1, t))
    proj_AB = A + t * v0

    d11 = np.dot(v1, v1)
    t = np.dot(v2, v1) / d11
    t = max(0, min(1, t))
    proj_AC = A + t * v1

    v3 = p - B
    v4 = C - B
    d44 = np.dot(v4, v4)
    t = np.dot(v3, v4) / d44
    t = max(0, min(1, t))
    proj_BC = B + t * v4

    d_AB = np.linalg.norm(p - proj_AB)
    d_AC = np.linalg.norm(p - proj_AC)
    d_BC = np.linalg.norm(p - proj_BC)
    if d_AB <= d_AC and d_AB <= d_BC:
        return proj_AB
    elif d_AC <= d_AB and d_AC <= d_BC:
        return proj_AC
    else:
        return proj_BC

def critical_triangle_gradient_ascent(points, A, B, C, max_iter=500, initial_step=0.01, min_step=1e-5, step_factor=1.1, symmetric=False):
    current = points.copy()
    current_min = get_smallest_triangle_area(current)
    step = initial_step
    n_points = points.shape[0]
    
    # Precompute edge normals for boundary repulsion
    edges = [(A, B), (B, C), (C, A)]
    normals = []
    for (P1, P2) in edges:
        v = P2 - P1
        n = np.array([-v[1], v[0]])
        n_norm = np.linalg.norm(n)
        if n_norm > 1e-10:
            n = n / n_norm
        # Determine inward direction using third vertex
        if (np.allclose(P1, A) and np.allclose(P2, B)) or (np.allclose(P1, B) and np.allclose(P2, A)):
            third = C
        elif (np.allclose(P1, B) and np.allclose(P2, C)) or (np.allclose(P1, C) and np.allclose(P2, B)):
            third = A
        elif (np.allclose(P1, C) and np.allclose(P2, A)) or (np.allclose(P1, A) and np.allclose(P2, C)):
            third = B
        else:
            third = None
        if third is not None and np.dot(third - P1, n) < 0:
            n = -n
        normals.append(n)

    for _ in range(max_iter):
        epsilon = max(1e-6, 0.01 * current_min)  # Adaptive threshold
        critical_triangles = []
        for i in range(n_points):
            for j in range(i+1, n_points):
                for k in range(j+1, n_points):
                    area = triangle_area(current[i], current[j], current[k])
                    if area <= current_min + epsilon:
                        critical_triangles.append((i, j, k, area))

        if not critical_triangles:
            break

        grads = np.zeros_like(current)
        for (i, j, k, area) in critical_triangles:
            a, b, c = current[i], current[j], current[k]
            S = signed_area(a, b, c)
            sign_S = 1.0 if S >= 0 else -1.0
            grad_a = 0.5 * sign_S * np.array([b[1]-c[1], c[0]-b[0]])
            grad_b = 0.5 * sign_S * np.array([c[1]-a[1], a[0]-c[0]])
            grad_c = 0.5 * sign_S * np.array([a[1]-b[1], b[0]-a[0]])
            
            # Weight by 1/area to prioritize smallest triangles
            weight = 1.0 / (area + 1e-10)
            grads[i] += weight * grad_a
            grads[j] += weight * grad_b
            grads[k] += weight * grad_c

        # Enforce symmetry constraints if applicable
        if symmetric:
            if n_points > 5:
                grads[5, 0] = 0.0  # Axis point moves only vertically
            for i in range(5):
                j = 6 + i
                if j < n_points:
                    grads[j] = np.array([-grads[i, 0], grads[i, 1]])

        candidate = current + step * grads
        new_points = np.array([project_to_triangle(p, A, B, C) for p in candidate])
        
        # Apply boundary repulsion
        margin = 0.01
        repulsion_vectors = np.zeros_like(new_points)
        for idx, p in enumerate(new_points):
            for j in range(3):
                P1, P2 = edges[j]
                d = np.dot(p - P1, normals[j])
                if d < 0: d = 0
                if d < margin:
                    repulsion_vectors[idx] += (margin - d) * normals[j]
        new_points += repulsion_vectors

        if not distinct_points(new_points):
            new_min = current_min
        else:
            new_min = get_smallest_triangle_area(new_points)

        if new_min > current_min:
            current = new_points
            current_min = new_min
            step *= step_factor
        else:
            step *= 0.5

        if step < min_step:
            break

    return current, current_min

def asymmetric_initialization(A, B, C, n=11):
    candidates = []
    while len(candidates) < 1000:
        s, t = np.random.random(2)
        if s + t > 1:
            s, t = 1 - s, 1 - t
        p = (1 - s - t) * A + s * B + t * C
        candidates.append(p)
    candidates = np.array(candidates)
    
    points = [candidates[np.random.randint(len(candidates))]]
    for _ in range(n-1):
        dists = [min(np.linalg.norm(c - p) for p in points) for c in candidates]
        idx = np.argmax(dists)
        points.append(candidates[idx])
    return np.array(points)

def symmetric_initialization(A, B, C):
    symmetry_axis_x = (A[0] + B[0]) / 2.0
    candidates_left = []
    candidates_axis = []

    for _ in range(1000):
        s, t = np.random.random(2)
        if s + t > 1:
            s, t = 1 - s, 1 - t
        p = (1 - s - t) * A + s * B + t * C
        if p[0] < symmetry_axis_x - 1e-5:
            candidates_left.append(p)
        elif p[0] > symmetry_axis_x + 1e-5:
            continue
        else:
            candidates_axis.append(p)

    if not candidates_axis:
        y_vals = np.linspace(0, C[1], 100)
        candidates_axis = np.array([[symmetry_axis_x, y] for y in y_vals])
    else:
        candidates_axis = np.array(candidates_axis)

    if len(candidates_left) < 5:
        candidates_left = np.vstack([candidates_left, np.tile((A+B+C)/3, (5 - len(candidates_left), 1))])
    candidates_left = np.array(candidates_left)

    points_left = [candidates_left[np.random.randint(len(candidates_left))]]
    for _ in range(4):
        dists = [min(np.linalg.norm(c - p) for p in points_left) for c in candidates_left]
        idx = np.argmax(dists)
        points_left.append(candidates_left[idx])
    points_left = np.array(points_left)

    dists = [min(np.linalg.norm(c - p) for p in points_left) for c in candidates_axis]
    idx = np.argmax(dists)
    axis_point = candidates_axis[idx]

    return np.vstack([points_left, [axis_point]])

def get_full_points(base_points, A, B):
    left_points = base_points[:5]
    axis_point = base_points[5]
    mirror_x = (A[0] + B[0]) - left_points[:, 0]
    right_points = np.column_stack((mirror_x, left_points[:, 1]))
    return np.vstack([left_points, axis_point, right_points])

def entrypoint():
    np.random.seed(42)
    random.seed(42)
    A, B, C = get_unit_triangle()
    
    best_points = None
    best_min = -1
    no_improve_count = 0

    for restart in range(20):
        # Dynamic seeding for restart diversity
        np.random.seed(42 + restart)
        random.seed(42 + restart)
        
        if np.random.rand() < 0.5:  # Reduced symmetric bias from 70% to 50%
            base = symmetric_initialization(A, B, C)
            points = get_full_points(base, A, B)
            symmetric_flag = True
        else:
            points = asymmetric_initialization(A, B, C)
            symmetric_flag = False

        points, min_area = critical_triangle_gradient_ascent(
            points, A, B, C,
            max_iter=500,
            initial_step=0.001,  # Reduced step size
            min_step=1e-5,
            step_factor=1.05,     # Conservative step growth
            symmetric=symmetric_flag
        )

        if not is_inside_triangle(points, A, B, C) or not distinct_points(points):
            continue
            
        if min_area > best_min:
            best_min = min_area
            best_points = points.copy()
            no_improve_count = 0
        else:
            no_improve_count += 1

        # Early stopping after 5 non-improving restarts
        if no_improve_count >= 5:
            break

    if best_points is None:
        base = symmetric_initialization(A, B, C)
        best_points = get_full_points(base, A, B)

    return best_points