from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    # Precompute inward unit normals for the three edges
    edge_AB = B - A
    n_AB = np.array([-edge_AB[1], edge_AB[0]])
    if np.dot(n_AB, C - A) < 0:
        n_AB = -n_AB
    n_AB = n_AB / np.linalg.norm(n_AB)

    edge_BC = C - B
    n_BC = np.array([-edge_BC[1], edge_BC[0]])
    if np.dot(n_BC, A - B) < 0:
        n_BC = -n_BC
    n_BC = n_BC / np.linalg.norm(n_BC)

    edge_AC = C - A
    n_AC = np.array([-edge_AC[1], edge_AC[0]])
    if np.dot(n_AC, B - A) < 0:
        n_AC = -n_AC
    n_AC = n_AC / np.linalg.norm(n_AC)

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)

        step_size = 0.05
        temperature = 0.1
        no_improve_count = 0
        max_no_improve = 100
        max_iter = 500

        for iter in range(max_iter):
            if no_improve_count >= max_no_improve:
                break

            # Find top-3 smallest triangles
            n = len(best)
            critical_triangles = []  # (area, i, j, k)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area_val = 0.5 * abs((best[j,0]-best[i,0])*(best[k,1]-best[i,1]) - 
                                             (best[k,0]-best[i,0])*(best[j,1]-best[i,1]))
                        critical_triangles.append((area_val, i, j, k))
            critical_triangles = sorted(critical_triangles, key=lambda x: x[0])[:3]

            # Build set of critical points
            critical_points = set()
            for (_, i, j, k) in critical_triangles:
                critical_points.add(i)
                critical_points.add(j)
                critical_points.add(k)
            critical_points = list(critical_points)

            # Compute adaptive bias for critical points
            bias = max(0.5, 0.9 - 0.4 * (iter / max_iter))

            # Bias selection toward critical points
            if np.random.rand() < bias and len(critical_points) > 0:
                idx = np.random.choice(critical_points)
            else:
                idx = np.random.randint(0, 11)

            # Generate directed perturbation if in critical triangle
            if len(critical_points) > 0 and idx in critical_points:
                triangles_with_idx = []
                for tri in critical_triangles:
                    _, i, j, k = tri
                    if idx in (i, j, k):
                        triangles_with_idx.append(tri)
                if triangles_with_idx:
                    tri = triangles_with_idx[np.random.randint(0, len(triangles_with_idx))]
                    _, i, j, k = tri
                    other_pts = [p for p in [i, j, k] if p != idx]
                    if len(other_pts) == 2:
                        j_idx, k_idx = other_pts
                        P_i = best[idx]
                        P_j = best[j_idx]
                        P_k = best[k_idx]
                        f = (P_j[0]-P_i[0])*(P_k[1]-P_i[1]) - (P_k[0]-P_i[0])*(P_j[1]-P_i[1])
                        sign_f = 1.0 if f >= 0 else -1.0
                        grad = np.array([P_j[1] - P_k[1], P_k[0] - P_j[0]]) * sign_f
                        grad_norm = np.linalg.norm(grad)
                        if grad_norm > 1e-5:
                            direction = grad / grad_norm
                        else:
                            direction = np.random.normal(0, 1, size=2)
                            direction = direction / np.linalg.norm(direction)
                        perturbation = direction * step_size
                    else:
                        perturbation = np.random.normal(0, step_size, size=2)
                else:
                    perturbation = np.random.normal(0, step_size, size=2)
            else:
                perturbation = np.random.normal(0, step_size, size=2)

            candidate = best.copy()
            candidate[idx] += perturbation

            # Boundary reflection
            P = candidate[idx]
            for _ in range(3):
                d_ab = np.dot(P - A, n_AB)
                if d_ab < 0:
                    P = P - 2 * d_ab * n_AB
                d_bc = np.dot(P - B, n_BC)
                if d_bc < 0:
                    P = P - 2 * d_bc * n_BC
                d_ac = np.dot(P - A, n_AC)
                if d_ac < 0:
                    P = P - 2 * d_ac * n_AC
            candidate[idx] = P

            # Safeguard: move toward centroid if still outside
            if not is_inside_triangle(candidate[idx:idx+1], A, B, C):
                centroid = (A + B + C) / 3
                for _ in range(10):
                    candidate[idx] = 0.9 * candidate[idx] + 0.1 * centroid
                    if is_inside_triangle(candidate[idx:idx+1], A, B, C):
                        break

            # Skip if still outside
            if not is_inside_triangle(candidate, A, B, C):
                continue

            score = get_smallest_triangle_area(candidate)

            # Temperature decay
            temperature *= 0.99

            if score > best_score:
                best = candidate
                best_score = score
                no_improve_count = 0
            else:
                delta = score - best_score
                if np.random.rand() < np.exp(delta / temperature):
                    best = candidate
                    best_score = score
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            # Step size decay per iteration
            step_size *= 0.98

        return best

    return improve