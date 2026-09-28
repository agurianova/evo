import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    h = C[1]  # Triangle height
    s = B[0]  # Triangle base length

    best_overall = None
    best_min_area = -1

    for trial in range(5):
        # Set seed for this trial
        np.random.seed(42 + trial)
        random.seed(42 + trial)

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
            width = s * (1 - r)  # Width at current height
            if k == 1:
                points.append([s / 2, y])
            else:
                for i in range(k):
                    x = (s - width) / 2 + i * (width / (k - 1))
                    points.append([x, y])
        points = np.array(points)

        # Perturb points to break collinearity with robust boundary handling
        perturb_vectors = np.random.uniform(-0.02, 0.02, (11, 2))
        for i in range(11):
            candidate_pt = points[i] + perturb_vectors[i]
            if is_inside_triangle(candidate_pt, A, B, C):
                points[i] = candidate_pt
            else:
                candidate_pt2 = points[i] - perturb_vectors[i] * 0.5
                if is_inside_triangle(candidate_pt2, A, B, C):
                    points[i] = candidate_pt2

        # Enhanced hill-climbing with improved parameters
        step_size = 0.1
        step_anneal = 0.99
        max_iter = 1000
        for _ in range(max_iter):
            # Identify critical points: points in top 5 smallest triangles
            n = 11
            triangles = []  # list of (area, i, j, k)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = points[i]
                        x2, y2 = points[j]
                        x3, y3 = points[k]
                        area = 0.5 * abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
                        triangles.append((area, i, j, k))
            triangles.sort(key=lambda x: x[0])
            top5 = triangles[:5]
            critical_points = set()
            for tri in top5:
                _, i, j, k = tri
                critical_points.add(i)
                critical_points.add(j)
                critical_points.add(k)
            critical_points = list(critical_points)

            improved = False
            current_min = get_smallest_triangle_area(points)
            # Test only critical points
            for idx in critical_points:
                best_candidate = None
                best_min = current_min
                # Test 100 random directions
                for _ in range(100):
                    angle = random.uniform(0, 2 * math.pi)
                    dx = step_size * math.cos(angle)
                    dy = step_size * math.sin(angle)
                    candidate = points.copy()
                    candidate[idx] = points[idx] + [dx, dy]

                    # Boundary handling: try opposite direction if outside
                    if not is_inside_triangle(candidate[idx], A, B, C):
                        candidate[idx] = points[idx] - [dx, dy]
                        if not is_inside_triangle(candidate[idx], A, B, C):
                            continue

                    new_min = get_smallest_triangle_area(candidate)
                    if new_min > best_min:
                        best_min = new_min
                        best_candidate = candidate

                if best_candidate is not None and best_min > current_min:
                    points = best_candidate
                    current_min = best_min
                    improved = True

            if not improved:
                step_size *= step_anneal
                if step_size < 1e-5:
                    break

        # Evaluate this trial
        min_area_trial = get_smallest_triangle_area(points)
        if min_area_trial > best_min_area:
            best_min_area = min_area_trial
            best_overall = points.copy()

    return best_overall