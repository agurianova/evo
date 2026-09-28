from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        def get_min_triangle_indices(points):
            n = points.shape[0]
            min_area2 = float('inf')
            best_idx = (0, 1, 2)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area2 = abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                   (points[k,0]-points[i,0])*(points[j,1]-points[i,1]))
                        if area2 < min_area2:
                            min_area2 = area2
                            best_idx = (i, j, k)
            return best_idx

        def project_point(p):
            if is_inside_triangle(p, A, B, C):
                return p
            
            def closest_on_segment(a, b, p):
                ab = b - a
                ap = p - a
                t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
                t = max(0.0, min(1.0, t))
                return a + t * ab

            proj_ab = closest_on_segment(A, B, p)
            proj_bc = closest_on_segment(B, C, p)
            proj_ca = closest_on_segment(C, A, p)

            dist_ab = np.linalg.norm(p - proj_ab)
            dist_bc = np.linalg.norm(p - proj_bc)
            dist_ca = np.linalg.norm(p - proj_ca)

            if dist_ab <= dist_bc and dist_ab <= dist_ca:
                return proj_ab
            elif dist_bc <= dist_ab and dist_bc <= dist_ca:
                return proj_bc
            else:
                return proj_ca

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        step_size = 0.05
        min_step = 0.001
        temp = 0.001
        cooling_rate = 0.95
        steps_per_cool = 50
        no_improve_count = 0
        max_no_improve = 200
        max_iter = 1000

        for iter_count in range(max_iter):
            if iter_count % steps_per_cool == 0:
                temp *= cooling_rate

            if np.random.rand() < 0.7:
                i, j, k = get_min_triangle_indices(best)
                idx = np.random.choice([i, j, k])
            else:
                idx = np.random.randint(0, 11)

            candidate = best.copy()
            perturbation = np.random.normal(0, step_size, size=2)
            candidate[idx] += perturbation
            candidate[idx] = project_point(candidate[idx])

            score = get_smallest_triangle_area(candidate)
            delta = score - best_score

            if delta > 0 or np.random.rand() < np.exp(delta / (temp + 1e-10)):
                best = candidate
                best_score = score
                if delta > 0:
                    step_size = max(min_step, step_size * 0.95)
                no_improve_count = 0
            else:
                no_improve_count += 1

            if no_improve_count >= max_no_improve:
                break

        return best

    return improve