from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    # Precompute unit triangle area for barycentric calculations
    area_ABC_val = 0.5 * abs((B[0]-A[0])*(C[1]-A[1]) - (B[1]-A[1])*(C[0]-A[0]))

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)

        for iteration in range(50):
            candidate = best.copy()
            current_min_area = best_score

            # Find all triangles at or near current min_area
            n = 11
            critical_triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        p1, p2, p3 = candidate[i], candidate[j], candidate[k]
                        area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p2[1]-p1[1])*(p3[0]-p1[0]))
                        if area <= current_min_area + 1e-10:
                            critical_triangles.append((i, j, k))

            # Select points to perturb based on critical triangles
            if not critical_triangles:
                indices_to_perturb = [np.random.randint(0, 11)]
            else:
                tri = critical_triangles[np.random.randint(0, len(critical_triangles))]
                if np.random.rand() < 0.8:
                    indices_to_perturb = [tri[np.random.randint(0, 3)]]
                else:
                    if np.random.rand() < 0.5:
                        indices_to_perturb = list(np.random.choice(tri, 2, replace=False))
                    else:
                        indices_to_perturb = list(tri)

            # Adaptive step sizing
            base_step = 0.1 * np.sqrt(current_min_area)
            step_size = base_step * (1.0 - iteration / 50.0)

            for idx in indices_to_perturb:
                # Adjust step for multi-point moves
                per_point_step = step_size / np.sqrt(len(indices_to_perturb)) if len(indices_to_perturb) > 1 else step_size
                perturbation = np.random.normal(0, per_point_step, size=2)

                # Boundary adjustment using barycentric coordinates
                P = candidate[idx]
                area_PBC = 0.5 * abs((B[0]-P[0])*(C[1]-P[1]) - (B[1]-P[1])*(C[0]-P[0]))
                area_PCA = 0.5 * abs((C[0]-P[0])*(A[1]-P[1]) - (C[1]-P[1])*(A[0]-P[0]))
                area_PAB = 0.5 * abs((A[0]-P[0])*(B[1]-P[1]) - (A[1]-P[1])*(B[0]-P[0]))
                u, v, w = area_PBC / area_ABC_val, area_PCA / area_ABC_val, area_PAB / area_ABC_val
                min_bary = min(u, v, w)

                if min_bary < 0.1:
                    perturbation *= min(1.0, min_bary * 10.0)

                candidate[idx] = P + perturbation

            # Validate candidate configuration
            if not is_inside_triangle(candidate, A, B, C):
                continue

            score = get_smallest_triangle_area(candidate)
            if score > best_score:
                best = candidate
                best_score = score

        return best

    return improve