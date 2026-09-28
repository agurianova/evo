from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Seed randomness based on input for independent sequences per configuration
        seed = int.from_bytes(points.tobytes(), 'little') % (2**32)
        np.random.seed(seed)

        n = points.shape[0]
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        # Annealing parameters
        max_iter = 500
        initial_temp = 0.005
        cooling_rate = 0.995
        initial_step = 0.05
        degeneracy_tol = 1e-10
        critical_tol = 1e-8

        for iteration in range(max_iter):
            # Update temperature and step size
            temp = initial_temp * (cooling_rate ** iteration)
            step_size = initial_step * (temp / initial_temp)

            # Identify critical points (in minimal-area triangles)
            critical_points = set()
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        p1, p2, p3 = current[i], current[j], current[k]
                        area = 0.5 * abs(
                            (p2[0]-p1[0])*(p3[1]-p1[1]) - 
                            (p3[0]-p1[0])*(p2[1]-p1[1])
                        )
                        if area <= current_score + critical_tol:
                            critical_points.add(i)
                            critical_points.add(j)
                            critical_points.add(k)

            if not critical_points:
                critical_points = set(range(n))

            # Perturb a critical point
            idx = np.random.choice(list(critical_points))
            candidate = current.copy()
            candidate[idx] += np.random.normal(0, step_size, size=2)

            # Check containment and degeneracy
            if not is_inside_triangle(candidate, A, B, C):
                continue
            
            new_score = get_smallest_triangle_area(candidate)
            if new_score < degeneracy_tol:
                continue

            # Simulated annealing acceptance
            delta = new_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temp):
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate.copy()
                    best_score = new_score

        return best

    return improve