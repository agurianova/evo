from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Seed RNG based on input configuration for diverse exploration
        seed = int(hashlib.sha256(points.tobytes()).hexdigest(), 16) % (2**32)
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

            step = initial_step * (0.95 ** iteration)  # Slower decay from 0.9
            T = initial_temp * (0.98 ** iteration)  # Slower decay from 0.95

            candidate = current.copy()
            # Apply moves with boundary projection
            for i in critical_points:
                candidate[i] = current[i] + step * directions[i]
                # Project point to boundary if outside
                if not is_inside_triangle(candidate[i], A, B, C):
                    step_reduction = 0.5
                    for _ in range(5):  # Try up to 5 reductions
                        candidate[i] = current[i] + step_reduction * step * directions[i]
                        if is_inside_triangle(candidate[i], A, B, C):
                            break
                        step_reduction *= 0.5
                    else:
                        candidate[i] = current[i]  # Revert if still outside

            # Final boundary check (safeguard)
            if not is_inside_triangle(candidate, A, B, C):
                continue

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