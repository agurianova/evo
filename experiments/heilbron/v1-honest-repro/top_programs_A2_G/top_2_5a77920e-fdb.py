import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    h = C[1]  # Triangle height
    s = B[0]  # Triangle base length

    base_seed = 42
    best_points = None
    best_min_area = -1

    for trial in range(5):
        seed = base_seed + trial
        np.random.seed(seed)
        random.seed(seed)

        # Generate asymmetric interior grid (1,2,3,3,2 points per row from top to bottom)
        rows = [
            (1, 0.95),
            (2, 0.7),
            (3, 0.45),
            (3, 0.2),
            (2, 0.05)
        ]
        points = []
        for k, r in rows:
            y = r * h
            width = s * (1 - r)
            if k == 1:
                points.append([s / 2, y])
            else:
                for i in range(k):
                    x = (s - width) / 2 + i * (width / (k - 1))
                    points.append([x, y])
        points = np.array(points)

        # Perturb points with larger magnitude to break symmetries
        perturb_vectors = np.random.uniform(-0.02, 0.02, (11, 2))
        for i in range(11):
            candidate_pt = points[i] + perturb_vectors[i]
            if is_inside_triangle(candidate_pt, A, B, C):
                points[i] = candidate_pt
            else:
                candidate_pt2 = points[i] - perturb_vectors[i] * 0.5
                if is_inside_triangle(candidate_pt2, A, B, C):
                    points[i] = candidate_pt2

        # Enhanced hill-climbing with critical point targeting
        step_size = 0.1
        step_anneal = 0.99
        max_iter = 1000
        for iter in range(max_iter):
            # Precompute critical points from top 5 smallest triangles
            n = points.shape[0]
            triangles = []  # (area, i, j, k)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = points[i]
                        x2, y2 = points[j]
                        x3, y3 = points[k]
                        area_val = 0.5 * abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
                        triangles.append((area_val, i, j, k))
            triangles.sort(key=lambda x: x[0])
            current_min = triangles[0][0]
            top5 = triangles[:5]
            critical_points = set()
            for tri in top5:
                critical_points.add(tri[1])
                critical_points.add(tri[2])
                critical_points.add(tri[3])
            critical_points = list(critical_points)

            improved = False
            for idx in critical_points:
                best_candidate = None
                best_min = current_min
                for _ in range(100):  # Increased direction samples
                    angle = random.uniform(0, 2 * math.pi)
                    dx = step_size * math.cos(angle)
                    dy = step_size * math.sin(angle)
                    candidate_pts = points.copy()
                    candidate_pts[idx] = points[idx] + [dx, dy]

                    # Boundary handling
                    if not is_inside_triangle(candidate_pts[idx], A, B, C):
                        candidate_pts[idx] = points[idx] - [dx, dy]
                        if not is_inside_triangle(candidate_pts[idx], A, B, C):
                            continue

                    new_min = get_smallest_triangle_area(candidate_pts)
                    if new_min > best_min:
                        best_min = new_min
                        best_candidate = candidate_pts

                if best_candidate is not None and best_min > current_min:
                    points = best_candidate
                    current_min = best_min
                    improved = True

            if not improved:
                step_size *= step_anneal
                if step_size < 1e-5:
                    break

        # Evaluate final configuration for this trial
        trial_min = get_smallest_triangle_area(points)
        if trial_min > best_min_area:
            best_min_area = trial_min
            best_points = points.copy()

    return best_points