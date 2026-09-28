from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    s = np.linalg.norm(B - A)

    def triangle_area(p1, p2, p3):
        return 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p2[1]-p1[1])*(p3[0]-p1[0]))

    def compute_distance_to_boundary(P):
        d_AB = abs((B[0]-A[0])*(P[1]-A[1]) - (B[1]-A[1])*(P[0]-A[0])) / s
        d_AC = abs((C[0]-A[0])*(P[1]-A[1]) - (C[1]-A[1])*(P[0]-A[0])) / s
        d_BC = abs((C[0]-B[0])*(P[1]-B[1]) - (C[1]-B[1])*(P[0]-B[0])) / s
        return min(d_AB, d_AC, d_BC)

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        T0 = 0.1 * best_score
        base_step = 0.05
        no_improve_streak = 0
        max_rounds = 200

        for _round in range(max_rounds):
            # Find smallest triangle in current configuration
            n = 11
            min_area_val = float('inf')
            min_triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = triangle_area(current[i], current[j], current[k])
                        if area < min_area_val - 1e-10:
                            min_area_val = area
                            min_triangles = [(i, j, k)]
                        elif abs(area - min_area_val) < 1e-10:
                            min_triangles.append((i, j, k))
            
            if not min_triangles:
                continue
                
            i, j, k = min_triangles[np.random.randint(0, len(min_triangles))]
            candidate = current.copy()
            
            # Perturb the three points with boundary-aware scaling
            for idx in [i, j, k]:
                d_min = compute_distance_to_boundary(candidate[idx])
                scale = min(1.0, d_min / base_step) if base_step > 0 else 1.0
                perturbation = np.random.normal(0, base_step * scale, size=2)
                candidate[idx] += perturbation

            # Validate candidate
            if not is_inside_triangle(candidate, A, B, C):
                continue
            
            score = get_smallest_triangle_area(candidate)
            if score <= 0:
                continue

            # Simulated annealing acceptance for current state
            delta_current = score - current_score
            T = T0 * np.exp(-_round / 100.0)
            if delta_current > 0 or np.random.rand() < np.exp(delta_current / T):
                current = candidate
                current_score = score

            # Update best solution
            if score > best_score:
                best = candidate.copy()
                best_score = score
                no_improve_streak = 0
            else:
                no_improve_streak += 1

            # Adaptive step size reduction
            if no_improve_streak >= 20:
                base_step *= 0.9
                no_improve_streak = 0

        return best

    return improve