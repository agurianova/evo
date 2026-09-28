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
        cooling_rate = 0.995  # Faster cooling for better refinement
        
        best_found = points.copy()
        best_score = initial_min_area
        current = points.copy()
        current_score = best_score
        temperature = initial_temp
        
        # Track rounds without improvement for restarts
        rounds_without_improvement = 0
        max_stagnation_rounds = 100

        for round_idx in range(max_rounds):
            # Focus ONLY on the absolute worst triangles (top 5 smallest)
            n = len(current)
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = compute_triangle_area(current[i], current[j], current[k])
                        triangles.append((area, i, j, k))
            
            # Sort by area and take only top 5 smallest triangles
            triangles.sort(key=lambda x: x[0])
            relevant_triangles = triangles[:5]  # Focus on absolute worst
            
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

                # Use sqrt-stabilized weighting to prevent instability
                weight = 1.0 / np.sqrt(area - triangles[0][0] + 1e-4)
                displacement[i] += weight * dir_a
                displacement[j] += weight * dir_b
                displacement[k] += weight * dir_c
                
                point_weight[i] += weight
                point_weight[j] += weight
                point_weight[k] += weight

            # Apply displacements with magnitude preservation (NO UNIT NORMALIZATION)
            candidate = current.copy()
            step_length = 0.1 * current_score  # Linear scaling with current score

            for i in range(n):
                if point_weight[i] > 1e-10:
                    # Scale by weight and current score, no unit normalization
                    move_vector = displacement[i] * (step_length / point_weight[i])
                    
                    # Binary search for maximum valid step
                    low, high = 0.0, 1.0
                    for _ in range(10):
                        mid = (low + high) / 2
                        test_point = current[i] + mid * move_vector
                        if is_inside_triangle(test_point, A, B, C):
                            low = mid
                        else:
                            high = mid
                    
                    candidate[i] = current[i] + low * move_vector

            # Evaluate candidate
            new_score = get_smallest_triangle_area(candidate)

            # Acceptance criterion
            delta = new_score - current_score
            if delta > 0 or (temperature > 1e-8 and np.random.rand() < np.exp(delta / temperature)):
                current = candidate
                current_score = new_score
                
                if new_score > best_score:
                    best_score = new_score
                    best_found = candidate
                    rounds_without_improvement = 0
                else:
                    rounds_without_improvement += 1
            else:
                rounds_without_improvement += 1

            # Stagnation handling: restart if stuck
            if rounds_without_improvement >= max_stagnation_rounds:
                # Perturb best_found with larger steps
                perturbed = best_found.copy()
                for i in range(n):
                    if np.random.rand() < 0.3:  # Perturb 30% of points
                        angle = np.random.rand() * 2 * np.pi
                        radius = 0.05 * initial_min_area
                        dx = radius * np.cos(angle)
                        dy = radius * np.sin(angle)
                        test_point = best_found[i] + np.array([dx, dy])
                        if is_inside_triangle(test_point, A, B, C):
                            perturbed[i] = test_point
                
                current = perturbed
                current_score = get_smallest_triangle_area(current)
                temperature = initial_temp  # Reset temperature
                rounds_without_improvement = 0

            # Cooling
            temperature *= cooling_rate

        return best_found

    return improve