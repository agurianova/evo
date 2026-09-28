from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        step_size = 0.05
        stagnation_count = 0
        max_iterations = 100
        tol = 1e-9
        
        for _ in range(max_iterations):
            # Find all minimal-area triangles
            min_area = float('inf')
            min_triplets = []
            n = 11
            
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = best[i]
                        x2, y2 = best[j]
                        x3, y3 = best[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area < min_area - tol:
                            min_area = area
                            min_triplets = [(i, j, k)]
                        elif abs(area - min_area) < tol:
                            min_triplets.append((i, j, k))
            
            # Collect all vertices from minimal triangles
            vertices = set()
            for triplet in min_triplets:
                vertices.update(triplet)
            vertices = list(vertices)
            
            # Randomly select one vertex to perturb
            idx = np.random.choice(vertices)
            
            candidate = best.copy()
            perturbation = np.random.normal(0, step_size, size=2)
            candidate[idx] += perturbation

            # Check containment
            if not is_inside_triangle(candidate, A, B, C):
                stagnation_count += 1
            else:
                score = get_smallest_triangle_area(candidate)
                if score > best_score:
                    best = candidate
                    best_score = score
                    stagnation_count = 0
                else:
                    stagnation_count += 1

            # Adaptive step decay and stagnation handling
            step_size *= 0.95
            if stagnation_count >= 10:
                step_size = 0.05
                stagnation_count = 0

        return best

    return improve