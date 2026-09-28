from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        np.random.seed(42)
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        
        # Helper for triplet area calculation
        def area3(a, b, c):
            return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

        # Configuration parameters
        max_iter = 200
        temp = 1.0
        cooling_rate = 0.995
        step_size = 0.1
        step_decay = 0.995
        no_improve_count = 0
        max_no_improve = 50

        for _ in range(max_iter):
            if no_improve_count >= max_no_improve:
                break

            # Find smallest triangle
            n = current.shape[0]
            min_area = float('inf')
            min_triangle = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area_val = area3(current[i], current[j], current[k])
                        if area_val < min_area:
                            min_area = area_val
                            min_triangle = (i, j, k)

            # Skip if degenerate
            if min_triangle is None:
                temp *= cooling_rate
                step_size *= step_decay
                continue

            # Select random vertex from smallest triangle
            idx = np.random.choice(min_triangle)
            apex = current[idx]
            others = [x for x in min_triangle if x != idx]
            base1, base2 = current[others[0]], current[others[1]]

            # Compute altitude direction
            base_vec = base2 - base1
            normal = np.array([-base_vec[1], base_vec[0]])
            norm = np.linalg.norm(normal)
            if norm < 1e-10:
                temp *= cooling_rate
                step_size *= step_decay
                continue
            normal = normal / norm

            # Determine direction to increase area
            signed_val = (base1[0]-apex[0])*(base2[1]-apex[1]) - (base1[1]-apex[1])*(base2[0]-apex[0])
            move_direction = normal if signed_val > 0 else -normal

            # Attempt bounded perturbation
            candidate_point = None
            base_step = step_size
            for attempt in range(3):
                perturbation = base_step * move_direction + 0.1 * base_step * np.random.randn(2)
                candidate_point = apex + perturbation
                if is_inside_triangle(candidate_point, A, B, C):
                    break
                base_step *= 0.5
            else:
                temp *= cooling_rate
                step_size *= step_decay
                continue

            # Check distinctness
            candidate = current.copy()
            candidate[idx] = candidate_point
            min_dist = float('inf')
            for i in range(11):
                for j in range(i+1, 11):
                    d = np.linalg.norm(candidate[i] - candidate[j])
                    if d < min_dist:
                        min_dist = d
            if min_dist < 1e-5:
                temp *= cooling_rate
                step_size *= step_decay
                continue

            # Evaluate candidate
            candidate_score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            if candidate_score > current_score:
                accept = True
            else:
                delta = candidate_score - current_score
                if np.random.rand() < np.exp(delta / temp):
                    accept = True
                else:
                    accept = False

            if accept:
                current = candidate
                current_score = candidate_score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Update search parameters
            temp *= cooling_rate
            step_size *= step_decay

        return current

    return improve