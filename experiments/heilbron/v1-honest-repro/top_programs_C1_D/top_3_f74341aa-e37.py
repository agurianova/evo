from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        seed = hash(points.tobytes()) % (2**32)
        np.random.seed(seed)

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score

        decay_rate = 0.99
        initial_step = 0.05
        initial_temp = 0.001
        max_iter = 200

        def get_minimal_triangle_indices(pts):
            n = pts.shape[0]
            min_area2 = float('inf')
            best_triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area2 = abs((pts[i,0]*(pts[j,1]-pts[k,1]) + 
                                    pts[j,0]*(pts[k,1]-pts[i,1]) + 
                                    pts[k,0]*(pts[i,1]-pts[j,1])))
                        if area2 < min_area2 - 1e-10:
                            min_area2 = area2
                            best_triangles = [(i, j, k)]
                        elif abs(area2 - min_area2) <= 1e-10:
                            best_triangles.append((i, j, k))
            return best_triangles

        for iteration in range(max_iter):
            step_size = initial_step * (decay_rate ** iteration)
            temp = initial_temp * (decay_rate ** iteration)

            triangles = get_minimal_triangle_indices(current)
            if not triangles:
                continue
            tri = triangles[np.random.randint(len(triangles))]
            idx = tri[np.random.randint(3)]

            candidate = current.copy()
            candidate[idx] += np.random.normal(0, step_size, 2)

            if not is_inside_triangle(candidate, A, B, C):
                continue

            new_score = get_smallest_triangle_area(candidate)
            delta = new_score - current_score

            if delta > 0 or np.random.rand() < np.exp(delta / temp):
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate
                    best_score = new_score

        return best

    return improve