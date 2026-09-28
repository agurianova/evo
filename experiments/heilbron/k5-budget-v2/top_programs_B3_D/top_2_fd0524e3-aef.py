from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import heapq

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        n_points = 11
        max_iter = 50
        base_step = 0.05
        initial_temp = 0.05
        
        # Adaptive annealing setup
        current_temp = initial_temp
        accept_history = []
        acceptance_window = 10
        min_acceptance = 5
        target_acceptance = 0.44
        cooling_factor_fast = 0.9
        cooling_factor_slow = 0.95

        for _round in range(max_iter):
            current = best.copy()
            step_size = base_step * (1 - _round / max_iter)
            
            # Find top 3 smallest triangles
            min_tris = []
            for i in range(n_points):
                for j in range(i+1, n_points):
                    for k in range(j+1, n_points):
                        x1, y1 = current[i]
                        x2, y2 = current[j]
                        x3, y3 = current[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1))
                        if len(min_tris) < 3:
                            heapq.heappush(min_tris, (-area, i, j, k))
                        else:
                            if area < -min_tris[0][0]:
                                heapq.heapreplace(min_tris, (-area, i, j, k))
            
            # Convert to triangle list
            triangles = [(i, j, k) for (_, i, j, k) in min_tris]
            
            # Accumulate displacements for all points in top triangles
            displacement = np.zeros((n_points, 2))
            count = np.zeros(n_points, dtype=int)
            
            for (i, j, k) in triangles:
                for idx in [i, j, k]:
                    others = [x for x in [i, j, k] if x != idx]
                    q, r = others
                    Q, R, P = current[q], current[r], current[idx]
                    
                    QR = R - Q
                    normal = np.array([-QR[1], QR[0]])
                    norm = np.linalg.norm(normal)
                    if norm > 1e-10:
                        normal /= norm
                    
                    QP = P - Q
                    direction = normal if np.dot(QP, normal) > 0 else -normal
                    displacement[idx] += step_size * direction
                    count[idx] += 1

            # Apply averaged displacements
            candidate = current.copy()
            for idx in range(n_points):
                if count[idx] > 0:
                    candidate[idx] = current[idx] + displacement[idx] / count[idx]

            # Validate containment
            if not is_inside_triangle(candidate, A, B, C):
                continue

            # Evaluate and accept via simulated annealing
            score = get_smallest_triangle_area(candidate)
            delta = score - best_score
            accepted = False
            if delta > 0 or (current_temp > 1e-5 and np.random.rand() < np.exp(delta / current_temp)):
                best, best_score = candidate, score
                accepted = True

            # Update annealing history and adapt temperature
            accept_history.append(accepted)
            if len(accept_history) > acceptance_window:
                accept_history.pop(0)

            if len(accept_history) >= min_acceptance:
                acceptance_rate = sum(accept_history) / len(accept_history)
                if acceptance_rate > target_acceptance:
                    current_temp *= cooling_factor_fast
                else:
                    current_temp *= cooling_factor_slow

        return best

    return improve