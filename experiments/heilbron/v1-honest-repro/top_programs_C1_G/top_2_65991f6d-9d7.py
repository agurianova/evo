import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    np.random.seed(42)
    A, B, C = get_unit_triangle()
    
    # Generate asymmetric grid [5,3,2,1] (known Heilbronn pattern for n=11)
    row_counts = [5, 3, 2, 1]
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
    best = points.copy()
    best_score = get_smallest_triangle_area(best)
    n = best.shape[0]
    total_rounds = 10000

    for round in range(total_rounds):
        # Compute decay factor (1 at start, 0 at end)
        decay_factor = (total_rounds - round) / total_rounds
        current_temp = 0.002 * decay_factor
        current_step = 0.005 + 0.045 * decay_factor

        # Identify critical points (in minimal-area triangles)
        critical_points = set()
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        (best[j,0] - best[i,0]) * (best[k,1] - best[i,1]) -
                        (best[k,0] - best[i,0]) * (best[j,1] - best[i,1])
                    )
                    if abs(area - best_score) < 1e-12:
                        critical_points.update([i, j, k])

        # Select point to perturb (prioritize critical points)
        idx = np.random.choice(list(critical_points)) if critical_points else np.random.randint(0, n)

        # Generate candidate by perturbing selected point
        candidate = best.copy()
        candidate[idx] += np.random.normal(0, current_step, size=2)

        # Validate constraints
        if not is_inside_triangle(candidate, A, B, C):
            continue
        
        # Check distinctness for perturbed point
        duplicate = False
        for j in range(n):
            if j == idx: continue
            if np.linalg.norm(candidate[idx] - candidate[j]) < 1e-10:
                duplicate = True
                break
        if duplicate:
            continue

        # Evaluate candidate
        new_score = get_smallest_triangle_area(candidate)

        # Acceptance criterion (simulated annealing)
        if new_score > best_score:
            best, best_score = candidate, new_score
        elif current_temp > 0 and np.random.rand() < np.exp((new_score - best_score) / current_temp):
            best, best_score = candidate, new_score

    return best