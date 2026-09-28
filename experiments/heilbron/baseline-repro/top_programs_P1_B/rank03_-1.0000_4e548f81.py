from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from collections import deque

np.random.seed(42)

THEORETICAL_MAX = 0.0365

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Precompute inward bias parameters
    height = C[1]  # Triangle height (y-coordinate of C)
    INWARD_BIAS = 0.005 * height
    
    # Precompute inward normals for each segment (unit vectors)
    def compute_normal(start, end):
        direction = end - start
        norm_dir = np.linalg.norm(direction)
        if norm_dir < 1e-10:
            return np.array([0.0, 0.0])
        unit_dir = direction / norm_dir
        # 90-degree clockwise rotation for inward normal (assuming CCW triangle)
        return np.array([unit_dir[1], -unit_dir[0]])
    
    normal_AB = compute_normal(A, B)
    normal_BC = compute_normal(B, C)
    normal_CA = compute_normal(C, A)

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
            # Add inward bias for AB
            return p_ab + INWARD_BIAS * normal_AB
        elif d_bc <= d_ab and d_bc <= d_ca:
            # Add inward bias for BC
            return p_bc + INWARD_BIAS * normal_BC
        else:
            # Add inward bias for CA
            return p_ca + INWARD_BIAS * normal_CA

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        n_points = points.shape[0]

        for restart in range(5):
            T = 2.0 * (restart + 1)
            initial_T = T
            step_size_base = 0.1 / (restart + 1)
            
            current = best.copy()
            current += np.random.normal(0, 0.01, current.shape)
            for idx in range(n_points):
                if not is_inside_triangle(current[idx], A, B, C):
                    current[idx] = project_point(current[idx], A, B, C)
            
            current_score = get_smallest_triangle_area(current)
            if current_score > best_score:
                best = current.copy()
                best_score = current_score
            
            n_steps = 0
            no_improve_count = 0
            recent_accepts = deque(maxlen=100)  # Track recent move acceptances

            while T > 1e-5 and n_steps < 1000 and no_improve_count < (1000 + 200 * restart):
                n_steps += 1

                # Collect and sort triangles by area
                triangles = []
                for i in range(n_points):
                    for j in range(i + 1, n_points):
                        for k in range(j + 1, n_points):
                            p1, p2, p3 = current[i], current[j], current[k]
                            area_val = 0.5 * abs((p2[0] - p1[0]) * (p3[1] - p1[1]) - 
                                              (p3[0] - p1[0]) * (p2[1] - p1[1]))
                            triangles.append((area_val, i, j, k))
                triangles.sort(key=lambda x: x[0])
                smallest_area = triangles[0][0]

                # Adaptive triangle selection based on area gap
                if len(triangles) > 1:
                    gap = triangles[1][0] - triangles[0][0]
                    max_area = smallest_area + 5 * gap
n                else:
                    max_area = smallest_area
                
                top_triangles = []
                for t in triangles:
                    if t[0] <= max_area:
                        top_triangles.append(t)
                    else:
                        break

                # Adaptive exploration rate
                perturb_prob = 0.1 * (T / initial_T)
                moved = np.zeros(n_points, dtype=bool)

                if np.random.rand() < perturb_prob:
                    # Random perturbation
                    idx = np.random.randint(0, n_points)
                    candidate = current.copy()
                    candidate[idx] += np.random.normal(0, 0.01, 2)
                    moved[idx] = True
                    
                    if not is_inside_triangle(candidate[idx], A, B, C):
                        candidate[idx] = project_point(candidate[idx], A, B, C)
                else:
                    # Gradient step
                    grad_accum = np.zeros((n_points, 2))
                    min_area_val = triangles[0][0]
                    
                    for (area_val, i, j, k) in top_triangles:
                        # Exponential weighting prioritizes smallest triangles
                        weight = np.exp(-(area_val - min_area_val) / (T + 1e-10))
                        
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

                    step_size = step_size_base
                    candidate = current.copy()
                    for idx in range(n_points):
                        if np.linalg.norm(grad_accum[idx]) > 1e-5:
                            candidate[idx] += step_size * grad_accum[idx]
                            moved[idx] = True
                            if not is_inside_triangle(candidate[idx], A, B, C):
                                candidate[idx] = project_point(candidate[idx], A, B, C)

                # Optimized constraint checking (only moved points)
                constraint_violated = False
                min_dist = float('inf')
                for i in range(n_points):
                    if moved[i]:
                        for j in range(n_points):
                            if i != j:
                                d = np.linalg.norm(candidate[i] - candidate[j])
                                if d < min_dist:
                                    min_dist = d
                
                if min_dist < 1e-4:
                    constraint_violated = True
                else:
                    candidate_score = get_smallest_triangle_area(candidate)
                    if candidate_score < 1e-10:
                        constraint_violated = True

                if constraint_violated:
                    recent_accepts.append(False)
                    no_improve_count += 1
                else:
                    delta = candidate_score - current_score
                    accept = delta > 0 or np.random.rand() < np.exp(delta / (T + 1e-10))
                    if accept:
                        current = candidate
                        current_score = candidate_score
                        recent_accepts.append(True)
                        if candidate_score > best_score:
                            best = candidate
                            best_score = candidate_score
                            no_improve_count = 0
                        else:
                            no_improve_count += 1
                    else:
                        recent_accepts.append(False)
                        no_improve_count += 1

                # Adaptive cooling rate
                if len(recent_accepts) == 100:
                    acceptance_rate = sum(recent_accepts) / 100.0
                    if acceptance_rate > 0.6:
                        cooling_factor = 0.995
                    elif acceptance_rate < 0.2:
                        cooling_factor = 0.95
                    else:
                        cooling_factor = 0.99
                else:
                    cooling_factor = 0.99
                
                T *= cooling_factor

        return best

    return improve