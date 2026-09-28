from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Seed based on input for configuration-specific exploration
        seed = abs(hash(points.tobytes())) % (2**32)
        np.random.seed(seed)
        
        n = 11
        input_score = get_smallest_triangle_area(points)
        best = points.copy()
        best_score = input_score
        current = points.copy()
        current_score = input_score

        initial_step = 0.05
        initial_temp = 0.05  # Increased from 0.01

        for iteration in range(100):  # Increased from 50
            # Compute all triangles to identify bottleneck
            areas = []
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = current[i], current[j], current[k]
                        area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        areas.append(area_val)
                        triangles.append((i, j, k))
            
            min_area_val = min(areas)
            bottleneck_triangles = []
            for idx, area_val in enumerate(areas):
                if area_val <= min_area_val + 1e-7:
                    bottleneck_triangles.append(triangles[idx])

            critical_points = set()
            for tri in bottleneck_triangles:
                critical_points.update(tri)
            critical_points = list(critical_points)
            non_critical = [i for i in range(n) if i not in critical_points]
            
            if not critical_points:
                continue

            directions = np.zeros((n, 2))
            count_per_point = np.zeros(n)
            for tri in bottleneck_triangles:
                i, j, k = tri
                
                # For point i (opposite side j-k)
                base = current[k] - current[j]
                normal = np.array([-base[1], base[0]])
                v = current[i] - current[j]
                d = np.dot(v, normal)
                sign_d = 1.0 if d >= 0 else -1.0
                directions[i] += normal * sign_d
                count_per_point[i] += 1

                # For point j (opposite side i-k)
                base = current[k] - current[i]
                normal = np.array([-base[1], base[0]])
                v = current[j] - current[i]
                d = np.dot(v, normal)
                sign_d = 1.0 if d >= 0 else -1.0
                directions[j] += normal * sign_d
                count_per_point[j] += 1

                # For point k (opposite side i-j)
                base = current[j] - current[i]
                normal = np.array([-base[1], base[0]])
                v = current[k] - current[i]
                d = np.dot(v, normal)
                sign_d = 1.0 if d >= 0 else -1.0
                directions[k] += normal * sign_d
                count_per_point[k] += 1

            for i in critical_points:
                if count_per_point[i] > 0:
                    directions[i] /= count_per_point[i]
                norm = np.linalg.norm(directions[i])
                if norm > 1e-10:
                    directions[i] /= norm

            step = initial_step * (0.95 ** iteration)  # Slower decay from 0.9 to 0.95
            T = initial_temp * (0.98 ** iteration)  # Slower cooling from 0.95 to 0.98

            # Prepare displacement vectors for all points
            displacement = np.zeros((n, 2))
            
            # Critical points move
            for i in critical_points:
                displacement[i] = step * directions[i]

            # Occasionally perturb non-critical points (10% chance)
            if non_critical and np.random.rand() < 0.1:
                i = np.random.choice(non_critical)
                angle = np.random.uniform(0, 2*np.pi)
                direction = np.array([np.cos(angle), np.sin(angle)])
                displacement[i] = step * 0.5 * direction

            # Apply displacements with boundary safety
            candidate = current.copy()
            for i in range(n):
                if np.linalg.norm(displacement[i]) > 1e-10:
                    candidate[i] = current[i] + displacement[i]
                    # Boundary check and step reduction if outside
                    if not is_inside_triangle(candidate[i:i+1], A, B, C):
                        step_scale = 1.0
                        for _ in range(5):
                            step_scale *= 0.5
                            candidate[i] = current[i] + displacement[i] * step_scale
                            if is_inside_triangle(candidate[i:i+1], A, B, C):
                                break
                        # If still outside after reductions, revert to original
                        if not is_inside_triangle(candidate[i:i+1], A, B, C):
                            candidate[i] = current[i]

            candidate_score = get_smallest_triangle_area(candidate)

            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score

            if candidate_score > current_score:
                current = candidate
                current_score = candidate_score
            else:
                delta = candidate_score - current_score
                if T > 1e-10 and np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = candidate_score

        return best

    return improve