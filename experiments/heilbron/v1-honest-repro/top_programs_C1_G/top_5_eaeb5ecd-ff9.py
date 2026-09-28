import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    np.random.seed(42)
    A, B, C = get_unit_triangle()
    
    # Define candidate patterns for n=11 (sum to 11)
    candidate_patterns = [
        [5, 3, 2, 1],
        [4, 3, 2, 2],
        [5, 4, 1, 1],
        [6, 3, 1, 1],
        [4, 4, 2, 1],
        [5, 2, 2, 2]
    ]
    
    # Evaluate all candidate patterns and select best initial configuration
    best_initial = None
    best_initial_score = -1
    for row_counts in candidate_patterns:
        total_rows = len(row_counts)
        points = []
        for row in range(total_rows):
            num_points = row_counts[row]
            v = (row + 0.5) / total_rows
            for i in range(num_points):
                u = (i + 0.5) / num_points * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                points.append(P)
        
        points = np.array(points)
        if is_inside_triangle(points, A, B, C):
            score = get_smallest_triangle_area(points)
            if score > best_initial_score:
                best_initial = points
                best_initial_score = score

    # If no valid pattern found (shouldn't happen), fall back to first pattern
    if best_initial is None:
        best_initial = np.array([ (1 - (row+0.5)/4 - (i+0.5)/row_counts[0]*(1-(row+0.5)/4))*A + 
                                 (i+0.5)/row_counts[0]*(1-(row+0.5)/4)*B + 
                                 (row+0.5)/4*C 
                                 for row in range(4) for i in range(row_counts[0]) ])

    points = best_initial
    best = points.copy()
    best_score = best_initial_score
    n = best.shape[0]
    total_rounds = 10000

    for round in range(total_rounds):
        # Exponential decay schedules (slower than linear)
        current_temp = 0.02 * np.exp(-round / 2000)
        current_step = 0.1 * np.exp(-round / 5000)

        # Identify critical points with relaxed tolerance
        critical_points = set()
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        (best[j,0] - best[i,0]) * (best[k,1] - best[i,1]) -
                        (best[k,0] - best[i,0]) * (best[j,1] - best[i,1])
                    )
                    if abs(area - best_score) < 1e-8:  # Relaxed from 1e-12
                        critical_points.update([i, j, k])

        # Determine number of points to perturb (1, 2, or 3)
        if np.random.rand() < 0.15:  # 15% chance for multi-point
            if np.random.rand() < 0.67:  # ~10% of total
                num_perturb = 2
            else:  # ~5% of total
                num_perturb = 3
        else:
            num_perturb = 1

        # Select points to perturb (prioritize critical points)
        if critical_points and len(critical_points) >= num_perturb:
            idxs = np.random.choice(list(critical_points), num_perturb, replace=False)
        else:
            idxs = np.random.choice(n, num_perturb, replace=False)

        # Generate candidate by perturbing selected points
        candidate = best.copy()
        for idx in idxs:
            candidate[idx] += np.random.normal(0, current_step, size=2)

        # Validate constraints
        if not is_inside_triangle(candidate, A, B, C):
            continue
        
        # Check distinctness
        duplicate = False
        for i in range(n):
            for j in range(i+1, n):
                if np.linalg.norm(candidate[i] - candidate[j]) < 1e-10:
                    duplicate = True
                    break
            if duplicate:
                break
        if duplicate:
            continue

        # Evaluate candidate
        new_score = get_smallest_triangle_area(candidate)

        # Acceptance criterion (simulated annealing)
        if new_score > best_score:
            best, best_score = candidate, new_score
        elif current_temp > 1e-5 and np.random.rand() < np.exp((new_score - best_score) / current_temp):
            best, best_score = candidate, new_score

    return best