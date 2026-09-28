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
        
        # Compute initial solution quality for adaptive restart allocation
        initial_score = get_smallest_triangle_area(points)
        # Adaptive restart count: 3-10 based on problem hardness
        restarts = max(3, min(10, 3 + int(7 * (initial_score / THEORETICAL_MAX)))))

        for restart in range(restarts):
            T = 1.0
            initial_T = T
            step_size_base = 0.1 / (restart + 1)
            
            # Adaptive perturbation: decays geometrically per restart
            perturbation_scale = 0.01 * (0.5 ** restart)
            current = best.copy() + perturbation_scale * np.random.randn(*best.shape)
            
            # Project perturbed points back to triangle
            for idx in range(n_points):
                if not is_inside_triangle(current[idx], A, B, C):
                    current[idx] = project_point(current[idx], A, B, C)
            
            current_score = get_smallest_triangle_area(current)
            if current_score > best_score:
                best = current.copy()
                best_score = current_score
            
            # Adaptive triangle selection breadth based on current solution quality
            initial_ratio = 2.0 + 1.0 * (best_score / THEORETICAL_MAX)
            initial_ratio = min(initial_ratio, 3.0)

            n_steps = 0
            no_improve_count = 0

            while T > 1e-5 and n_steps < 1000 and no_improve_count < (500 + 100 * restart):
                n_steps += 1

                # Collect all triangles and sort by area
                triangles = []
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

                # Adaptive triangle selection threshold
                ratio_threshold = 1.0 + (initial_ratio - 1.0) * (T / initial_T)
                top_triangles = []
                for t in triangles:
                    if t[0] <= smallest_area * ratio_threshold:
                        top_triangles.append(t)
                    else:
                        break
                
                # Adaptive cap: scale with triangle difficulty
                ratio = smallest_area / THEORETICAL_MAX
                cap = max(3, min(50, int(20 * ratio)))
                top_triangles = top_triangles[:cap]

                # Accumulate gradients for top triangles with participation counting
                grad_accum = np.zeros((n_points, 2))
                count = np.zeros(n_points, dtype=int)
                for (area_val, i, j, k) in top_triangles:
                    count[i] += 1
                    count[j] += 1
                    count[k] += 1
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

                    grad_accum[i] += grad_v1
                    grad_accum[j] += grad_v2
                    grad_accum[k] += grad_v3

                # Normalize gradients by participation count
                for idx in range(n_points):
                    if count[idx] > 0:
                        grad_accum[idx] /= count[idx]

                # Compute gap to next smallest triangle for step size adaptation
                if len(triangles) > 1:
                    next_smallest_area = triangles[1][0]
                else:
                    next_smallest_area = THEORETICAL_MAX
                gap = next_smallest_area - smallest_area

                # Adaptive step size weighting based on solution quality
                w1 = 0.1 + 0.8 * (1 - best_score / THEORETICAL_MAX)
                w1 = max(0.01, min(0.99, w1))
                w2 = 1.0 - w1
                step_size = step_size_base * (w1 * T + w2 * (1-T)**2 * (gap / THEORETICAL_MAX))
                
                candidate = current.copy()
                for idx in range(n_points):
                    if np.linalg.norm(grad_accum[idx]) > 1e-5:
                        candidate[idx] += step_size * grad_accum[idx]

                # Project moved points back to triangle if outside
                for idx in range(n_points):
                    if np.linalg.norm(grad_accum[idx]) > 1e-5:
                        if not is_inside_triangle(candidate[idx], A, B, C):
                            candidate[idx] = project_point(candidate[idx], A, B, C)

                # Check constraints with adaptive threshold
                constraint_violated = False
                min_dist = float('inf')
                for i1 in range(n_points):
                    for j1 in range(i1 + 1, n_points):
                        d = np.linalg.norm(candidate[i1] - candidate[j1])
                        if d < min_dist:
                            min_dist = d
                
                # Adaptive distinctness threshold based on current min_area
                threshold = min(1e-4, max(1e-6, 0.01 * smallest_area))
                if min_dist < threshold:
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

                # Adaptive swap escape mechanism
                swap_threshold = max(100, min(500, 200 + 300 * (best_score / THEORETICAL_MAX)))
                swap_prob = min(0.3, 0.1 + 0.2 * (best_score / THEORETICAL_MAX))
                if no_improve_count > swap_threshold and np.random.rand() < swap_prob:
                    smallest_tri = triangles[0]
                    idx1 = np.random.choice([smallest_tri[1], smallest_tri[2], smallest_tri[3]])
                    
                    # Find larger triangle (area > 1.5x smallest)
                    larger_triangles = [tri for tri in triangles if tri[0] > 1.5 * smallest_tri[0]]
                    if larger_triangles:
                        chosen_tri = larger_triangles[np.random.randint(len(larger_triangles))]
                        idx2 = np.random.choice([chosen_tri[1], chosen_tri[2], chosen_tri[3]])
                    else:
                        idx2 = np.random.randint(n_points)
                        while idx2 == idx1:
                            idx2 = np.random.randint(n_points)

                    # Swap points
                    current[[idx1, idx2]] = current[[idx2, idx1]]

                    # Check distinctness with adaptive threshold
                    min_dist_swap = float('inf')
                    for i in range(n_points):
                        for j in range(i + 1, n_points):
                            d = np.linalg.norm(current[i] - current[j])
                            if d < min_dist_swap:
                                min_dist_swap = d
                    
                    threshold_swap = min(1e-4, max(1e-6, 0.01 * smallest_area))
                    if min_dist_swap < threshold_swap:
                        current[[idx1, idx2]] = current[[idx2, idx1]]
                    else:
                        current_score_swap = get_smallest_triangle_area(current)
                        if current_score_swap < 1e-10:
                            current[[idx1, idx2]] = current[[idx2, idx1]]
                        else:
                            current_score = current_score_swap
                            no_improve_count = 0

                # Adaptive temperature decay based on solution quality
                decay = 0.99 - 0.02 * (best_score / THEORETICAL_MAX)
                decay = max(0.9, min(0.99, decay))
                T *= decay

        return best

    return improve