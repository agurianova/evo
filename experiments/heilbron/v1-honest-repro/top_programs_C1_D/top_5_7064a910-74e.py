from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def compute_triangle_area(a, b, c):
        return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))

    def improve(points: np.ndarray) -> np.ndarray:
        n_points = 11
        max_rounds = 500
        initial_min_area = get_smallest_triangle_area(points)
        initial_temp = 0.5 * initial_min_area  # Adapted to input quality
        cooling_rate = 0.995  # Faster cooling rate for better exploitation
        
        # Restart mechanism parameters
        restart_threshold = 100
        restart_perturbation = 0.05
        
        best_found = points.copy()
        best_score = initial_min_area
        current = points.copy()
        current_score = best_score
        temperature = initial_temp
        
        # Track iterations without improvement
        no_improve_count = 0

        for round_idx in range(max_rounds):
            # Find triangles near the minimum area
            n = len(current)
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = compute_triangle_area(current[i], current[j], current[k])
                        triangles.append((area, i, j, k))
            
            # Sort by area and select triangles within 50% of current min
            triangles.sort(key=lambda x: x[0])
            min_area = triangles[0][0]
            # Select triangles with area < 1.5 * min_area (adaptive count)
            relevant_triangles = [t for t in triangles if t[0] < min_area * 1.5]
            
            # Initialize displacement for each point with weights
            displacement = np.zeros((n, 2))
            point_weight = np.zeros(n)

            for (area, i, j, k) in relevant_triangles:
                a, b, c = current[i], current[j], current[k]
                f = (b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1])
                sign = 1 if f >= 0 else -1

                dir_a = np.array([b[1]-c[1], c[0]-b[0]]) * sign
                dir_b = np.array([c[1]-a[1], a[0]-c[0]]) * sign
                dir_c = np.array([a[1]-b[1], b[0]-a[0]]) * sign

                norm_a = np.linalg.norm(dir_a)
                if norm_a > 1e-10:
                    dir_a = dir_a / norm_a
                else:
                    dir_a = np.zeros(2)
                norm_b = np.linalg.norm(dir_b)
                if norm_b > 1e-10:
                    dir_b = dir_b / norm_b
                else:
                    dir_b = np.zeros(2)
                norm_c = np.linalg.norm(dir_c)
                if norm_c > 1e-10:
                    dir_c = dir_c / norm_c
                else:
                    dir_c = np.zeros(2)

                # Weight by inverse of relative area difference, capped for stability
                weight = 1.0 / np.sqrt(area - min_area + 1e-4)
                weight = min(weight, 100.0)  # Cap weight to prevent instability
                
                displacement[i] += weight * dir_a
                displacement[j] += weight * dir_b
                displacement[k] += weight * dir_c
                
                point_weight[i] += weight
                point_weight[j] += weight
                point_weight[k] += weight

            # Apply weights to displacement (no unit normalization)
            for i in range(n):
                if point_weight[i] > 1e-10:
                    displacement[i] = displacement[i] / point_weight[i]
                else:
                    displacement[i] = np.zeros(2)

            # Linear scaling for consistent step behavior
            step_length = 0.1 * current_score

            # Create candidate by moving points with boundary clipping
            candidate = current.copy()
            for i in range(n):
                if np.linalg.norm(displacement[i]) > 1e-10:
                    low, high = 0.0, 1.0  # Now using fractional step
                    # Increased from 5 to 10 iterations for better precision
                    for _ in range(10):
                        mid = (low + high) / 2
                        test_point = current[i] + mid * step_length * displacement[i]
                        if is_inside_triangle(test_point, A, B, C):
                            low = mid
                        else:
                            high = mid
                    t = low
                    candidate[i] = current[i] + t * step_length * displacement[i]

            # Check if candidate is valid
            new_score = get_smallest_triangle_area(candidate)

            delta = new_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best_score = new_score
                    best_found = candidate
                    no_improve_count = 0
                else:
                    no_improve_count += 1
            else:
                no_improve_count += 1

            # Restart mechanism if stuck in local optimum
            if no_improve_count >= restart_threshold:
                # Perturb best_found with larger steps
                current = best_found.copy()
                for i in range(n):
                    angle = np.random.uniform(0, 2 * np.pi)
                    r = np.random.uniform(0, restart_perturbation)
                    dx = r * np.cos(angle)
                    dy = r * np.sin(angle)
                    test_point = current[i] + np.array([dx, dy])
                    if is_inside_triangle(test_point, A, B, C):
                        current[i] = test_point
                
                # Reset temperature to initial value
                temperature = initial_temp
                no_improve_count = 0

            temperature *= cooling_rate

        return best_found

    return improve