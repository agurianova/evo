from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

THEORETICAL_MAX = 0.0365

def entrypoint():
    A, B, C = get_unit_triangle()

    def project_point(p, A, B, C):
        if is_inside_triangle(p, A, B, C):
            return p
        
        def project_onto_segment(p, a, b):
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
            t = max(0.0, min(1.0, t))
            return a + t * ab
        
        p_ab = project_onto_segment(p, A, B)
        p_bc = project_onto_segment(p, B, C)
        p_ca = project_onto_segment(p, C, A)
        
        d_ab = np.linalg.norm(p - p_ab)
        d_bc = np.linalg.norm(p - p_bc)
        d_ca = np.linalg.norm(p - p_ca)
        
        if d_ab <= d_bc and d_ab <= d_ca:
            return p_ab
        elif d_bc <= d_ab and d_bc <= d_ca:
            return p_bc
        else:
            return p_ca

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        n_points = points.shape[0]

        # Calculate adaptive restart count based on initial configuration quality
        initial_score = best_score
n        n_restarts = max(3, min(10, 5 + int(5 * (1 - initial_score / THEORETICAL_MAX))))

        # Helper for boundary handling: push points inward instead of hard projection
        def push_inward(p):
            if is_inside_triangle(p, A, B, C):
                return p
            p_proj = project_point(p, A, B, C)
            d = np.linalg.norm(p - p_proj)
            if d < 1e-4:
                return p_proj
            centroid = (A + B + C) / 3.0
            inward_dir = centroid - p_proj
            norm_dir = np.linalg.norm(inward_dir)
            if norm_dir < 1e-5:
                inward_dir = np.array([1.0, 0.0])
            else:
                inward_dir = inward_dir / norm_dir
            move = min(d * 0.5, 0.01)
            candidate_p = p_proj + move * inward_dir
            if not is_inside_triangle(candidate_p, A, B, C):
                candidate_p = project_point(candidate_p, A, B, C)
            return candidate_p

        for restart in range(n_restarts):
            initial_T = 0.5 * (restart + 1)
            T = initial_T
            step_size_base = 0.1 / (restart + 1)
            current = best.copy()
            current_score = best_score
            n_steps = 0
            no_improve_count = 0

            while T > 1e-5 and n_steps < 1000 and no_improve_count < (500 + 100 * restart):
                n_steps += 1

                # Collect all triangles and sort by area
                triangles = []  # (area, i, j, k)
                for i in range(n_points):
                    for j in range(i + 1, n_points):
                        for k in range(j + 1, n_points):
                            p1, p2, p3 = current[i], current[j], current[k]
                            area_val = 0.5 * abs((p2[0] - p1[0]) * (p3[1] - p1[1]) - 
                                              (p3[0] - p1[0]) * (p2[1] - p1[1]))
                            triangles.append((area_val, i, j, k))

                # Sort by area
                triangles.sort(key=lambda x: x[0])
                smallest_area = triangles[0][0]

                # Adaptive selection: decay threshold from 2.0 to 1.5 as T decreases
                ratio_threshold = 1.5 + 0.5 * (T / initial_T)
                top_triangles = []
                for t in triangles:
                    if t[0] <= smallest_area * ratio_threshold:
                        top_triangles.append(t)
                    else:
                        break
                
                # Adaptive cap: scale with triangle count
                cap = min(10, max(3, int(0.3 * len(triangles))))
                top_triangles = top_triangles[:cap]

                # Accumulate gradients with linear weighting by triangle importance
                grad_accum = np.zeros((n_points, 2))
                for (area_val, i, j, k) in top_triangles:
                    weight = smallest_area / area_val  # Linear weighting
                    v1, v2, v3 = current[i], current[j], current[k]
                    s0 = (v2[0] - v1[0]) * (v3[1] - v1[1]) - (v3[0] - v1[0]) * (v2[1] - v1[1])
                    d_s0_dv1 = np.array([v2[1] - v3[1], v3[0] - v2[0]])
                    d_s0_dv2 = np.array([v3[1] - v1[1], v1[0] - v3[0]])
                    d_s0_dv3 = np.array([v1[1] - v2[1], v2[0] - v1[0]])
                    
                    if s0 >= 0:
                        grad_v1 = d_s0_dv1
                        grad_v2 = d_s0_dv2
                        grad_v3 = d_s0_dv3
                    else:
                        grad_v1 = -d_s0_dv1
                        grad_v2 = -d_s0_dv2
                        grad_v3 = -d_s0_dv3

                    grad_accum[i] += weight * grad_v1
                    grad_accum[j] += weight * grad_v2
                    grad_accum[k] += weight * grad_v3

                # Dynamic step size with safe minimum
                gap = max(0.0, THEORETICAL_MAX - current_score)
                step_size = step_size_base * max(0.01, gap / THEORETICAL_MAX, 0.1 * (T / initial_T))
                candidate = current.copy()
                for idx in range(n_points):
                    if np.linalg.norm(grad_accum[idx]) > 1e-5:
                        candidate[idx] += step_size * grad_accum[idx]

                # Boundary handling: push inward instead of hard projection
                for idx in range(n_points):
                    if np.linalg.norm(grad_accum[idx]) > 1e-5:
                        if not is_inside_triangle(candidate[idx], A, B, C):
                            candidate[idx] = push_inward(candidate[idx])

                # Check constraints
                constraint_violated = False
                min_dist = float('inf')
                for i1 in range(n_points):
                    for j1 in range(i1 + 1, n_points):
                        d = np.linalg.norm(candidate[i1] - candidate[j1])
                        if d < min_dist:
                            min_dist = d
                if min_dist < 1e-4:
                    constraint_violated = True
                else:
                    candidate_score = get_smallest_triangle_area(candidate)
                    if candidate_score < 1e-10:
                        constraint_violated = True

                if constraint_violated:
                    no_improve_count += 1
                else:
                    delta = candidate_score - current_score
                    if delta > 0 or np.random.rand() < np.exp(delta / T):
                        current = candidate
                        current_score = candidate_score
                        if candidate_score > best_score:
                            best = candidate
                            best_score = candidate_score
                            no_improve_count = 0
                        else:
                            no_improve_count += 1
                    else:
                        no_improve_count += 1

                T *= 0.99

        return best

    return improve