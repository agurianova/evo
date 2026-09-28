from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Seed RNG deterministically per input configuration
        seed = hash(points.tobytes()) % (2**32)
        rng = np.random.default_rng(seed)
        
        # Helper to get smallest triangles (indices) and min_area for a config
        def get_smallest_triangles(config):
            n = config.shape[0]
            min_area_val = float('inf')
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = config[i], config[j], config[k]
                        area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                        if area < min_area_val - 1e-10:
                            min_area_val = area
                            triangles = [(i, j, k)]
                        elif abs(area - min_area_val) <= 1e-10:
                            triangles.append((i, j, k))
            return triangles, min_area_val

        # Initialize with input configuration
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        
        # Simulated Annealing parameters
        base_step = 0.05
        T = 1.0
        cooling_rate = 0.995
        max_iter = 500
        max_no_improve = 100
        no_improve_count = 0

        for _ in range(max_iter):
            # Identify bottleneck: smallest triangles in current config
            smallest_triangles, _ = get_smallest_triangles(current)
            if not smallest_triangles:
                break
            
            # Select one smallest triangle randomly
            tri = smallest_triangles[rng.integers(0, len(smallest_triangles))]
            
            # Decide how many points to perturb (1,2,3)
            num_perturb = rng.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
            points_to_perturb = rng.choice(tri, size=num_perturb, replace=False)

            # Generate candidate by perturbing selected points
            candidate = current.copy()
            step = base_step * T
            for idx in points_to_perturb:
                pert = rng.normal(0, step, size=2)
                candidate[idx] += pert

            # Validate candidate
            if not is_inside_triangle(candidate, A, B, C):
                no_improve_count += 1
                T *= cooling_rate
                continue
            
            candidate_score = get_smallest_triangle_area(candidate)
            if candidate_score <= 0:  # Degenerate or coincident points
                no_improve_count += 1
                T *= cooling_rate
                continue

            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta >= 0 or rng.random() < np.exp(delta / T):
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

            # Cool down and check stopping condition
            T *= cooling_rate
            if no_improve_count >= max_no_improve:
                break

        return best

    return improve