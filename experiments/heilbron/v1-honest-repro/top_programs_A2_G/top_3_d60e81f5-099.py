import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def get_critical_points(points, threshold=0.01):
    """Return indices of points involved in triangles within threshold of min area"""
    n = len(points)
    min_area = get_smallest_triangle_area(points)
    critical_indices = set()
    
    # Find top 5 smallest triangles
    smallest_triangles = []
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Calculate triangle area
                area = 0.5 * abs(
                    points[i][0]*(points[j][1]-points[k][1]) +
                    points[j][0]*(points[k][1]-points[i][1]) +
                    points[k][0]*(points[i][1]-points[j][1])
                )
                smallest_triangles.append((area, i, j, k))
    
    smallest_triangles.sort(key=lambda x: x[0])
    top_5 = smallest_triangles[:5]
    
    # Collect all points in top 5 triangles
    for _, i, j, k in top_5:
        critical_indices.add(i)
        critical_indices.add(j)
        critical_indices.add(k)
        
    return list(critical_indices)

def hill_climb(points, max_iter=1000, step_size=0.1, step_anneal=0.99):
    tri = get_unit_triangle()
    A, B, C = tri
    h = C[1]
    s = B[0]

    for _ in range(max_iter):
        improved = False
        current_min = get_smallest_triangle_area(points)
        
        # Only consider points in critical triangles
        critical_indices = get_critical_points(points)
        
        for idx in critical_indices:
            best_candidate = None
            best_min = current_min
            
            # Test 100 random directions for better coverage
            for _ in range(100):
                angle = random.uniform(0, 2 * math.pi)
                dx = step_size * math.cos(angle)
                dy = step_size * math.sin(angle)
                candidate = points.copy()
                candidate[idx] = points[idx] + [dx, dy]

                # Boundary handling
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

    return points

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    h = C[1]
    s = B[0]

    # Best asymmetric pattern from lineage insights: (1,2,3,3,2 points)
    rows = [
        (1, 0.95),
        (2, 0.7),
        (3, 0.45),
        (3, 0.2),
        (2, 0.05)
    ]
    
    best_points = None
    best_min_area = -1

    # Run 5 independent trials with different seeds
    for trial in range(5):
        # Reset seed for each trial for reproducibility
        np.random.seed(42 + trial)
        random.seed(42 + trial)
        
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

        # Larger initial perturbation to break symmetries
        perturb_vectors = np.random.uniform(-0.02, 0.02, (11, 2))
        for i in range(11):
            candidate_pt = points[i] + perturb_vectors[i]
            if is_inside_triangle(candidate_pt, A, B, C):
                points[i] = candidate_pt
            else:
                candidate_pt2 = points[i] - perturb_vectors[i] * 0.5
                if is_inside_triangle(candidate_pt2, A, B, C):
                    points[i] = candidate_pt2

        # Hill climbing with optimized parameters
        points = hill_climb(points, step_size=0.1, step_anneal=0.99)

        # Track best configuration across trials
        min_area = get_smallest_triangle_area(points)
        if min_area > best_min_area:
            best_min_area = min_area
            best_points = points.copy()

    return best_points