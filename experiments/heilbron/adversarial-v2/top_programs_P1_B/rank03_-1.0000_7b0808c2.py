from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_triangle(p):
        """Project point p to the closest point inside the triangle using barycentric coordinates."""
        v0 = B - A
        v1 = C - A
        v2 = p - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        if abs(denom) < 1e-10:
            return A
            
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        
        if v < 0:
            v = 0
            w = max(0, min(1, w))
        if w < 0:
            w = 0
            v = max(0, min(1, v))
        if v + w > 1:
            total = v + w
            v /= total
            w /= total
            
        return A + v * (B - A) + w * (C - A)

    def get_k_smallest_triangle_indices(pts, min_area, k=3):
        """Return indices of the k smallest triangles with adaptive k selection."""
        n = pts.shape[0]
        triangle_areas = []
        
        # Adaptive k selection based on min_area percentile
        # As min_area increases (better configuration), focus on fewer critical triangles
        adaptive_k = max(3, min(10, int(15 * (1 - min_area / 0.03))))
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    ax, ay = pts[i]
                    bx, by = pts[j]
                    cx, cy = pts[k]
                    area = 0.5 * abs((bx-ax)*(cy-ay) - (cx-ax)*(by-ay))
                    triangle_areas.append((area, (i, j, k)))
        
        triangle_areas.sort(key=lambda x: x[0])
        return [tri[1] for tri in triangle_areas[:adaptive_k]], adaptive_k

    def improve(points: np.ndarray) -> np.ndarray:
        n = points.shape[0]
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        # Adaptive parameters
        n_steps = 1000  # Increased max iterations with adaptive stopping
        initial_temp = 0.1
        initial_step = 0.01
        min_step = 0.001
        max_step = 0.05
        gradient_prob = 0.8
        multi_perturb_prob = 0.3
        multi_perturb_count = (2, 3)
        global_perturb_prob = 0.05  # Added probability for global perturbation

        step_size = initial_step
        temperature = initial_temp
        no_improve_count = 0
        improvement_history = []
        last_score = current_score

        for step in range(n_steps):
            # Adaptive cooling rate based on improvement history
            if len(improvement_history) > 10:
                improvement_rate = np.mean(improvement_history[-10:])
                cooling_rate = 0.9 + 0.05 * max(0, 1 - improvement_rate / 1e-5)
            else:
                cooling_rate = 0.95

            # Dynamic k selection based on current min_area
            triangle_indices, adaptive_k = get_k_smallest_triangle_indices(current, current_score)

            if np.random.rand() < gradient_prob:
                # Get top k smallest triangles
                
                # Initialize gradient accumulators for all points
                grads = np.zeros_like(current)
                
                for tri in triangle_indices:
                    i, j, k = tri
                    a, b, c = current[i], current[j], current[k]

                    f = (b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1])
                    sign_f = 1.0 if f >= 0 else -1.0

                    # Calculate area (without the 0.5 factor since we're using it for weighting)
                    area = 0.5 * abs(f)
                    
                    # Compute gradients with magnitude preservation
                    grad_a = 0.5 * sign_f * np.array([b[1]-c[1], c[0]-b[0]])
                    grad_b = 0.5 * sign_f * np.array([c[1]-a[1], a[0]-c[0]])
                    grad_c = 0.5 * sign_f * np.array([a[1]-b[1], b[0]-a[0]])

                    # Scale gradients by area sensitivity (1/area for smaller triangles to get larger updates)
                    if area > 1e-10:
                        scale = 1.0 / area
n                        grad_a *= scale
                        grad_b *= scale
                        grad_c *= scale

                    # Accumulate gradients for each point
                    grads[i] += grad_a
                    grads[j] += grad_b
                    grads[k] += grad_c

                # Apply gradients
                candidate = current.copy()
                for idx in range(n):
                    if np.linalg.norm(grads[idx]) > 1e-10:
                        # Normalize the accumulated gradient direction but preserve relative magnitude
                        grads[idx] = grads[idx] / (np.linalg.norm(grads[idx]) + 1e-10)
                        candidate[idx] += step_size * grads[idx]
            else:
                candidate = current.copy()
                
                # Determine how many points to perturb
                if np.random.rand() < global_perturb_prob:
                    # Global perturbation - perturb all points with smaller magnitude
                    for idx in range(n):
                        perturbation = np.random.normal(0, step_size * 0.5, size=2)
                        candidate[idx] += perturbation
                elif np.random.rand() < multi_perturb_prob:
                    num_points = np.random.randint(multi_perturb_count[0], multi_perturb_count[1] + 1)
                    indices = np.random.choice(n, num_points, replace=False)
                else:
                    indices = [np.random.randint(0, n)]
                    
                # Apply perturbations with step_size-proportional magnitude
                if np.random.rand() >= global_perturb_prob:
                    for idx in indices:
                        perturbation = np.random.normal(0, step_size, size=2)
                        candidate[idx] += perturbation

            # Project any out-of-bound points instead of rejecting the whole candidate
            for i in range(n):
                if not is_inside_triangle(candidate[i], A, B, C):
                    candidate[i] = project_to_triangle(candidate[i])

            candidate_score = get_smallest_triangle_area(candidate)

            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                no_improve_count = 0
                
                # Record improvement for adaptive cooling
                improvement = candidate_score - last_score
                improvement_history.append(improvement)
                if len(improvement_history) > 50:
                    improvement_history.pop(0)
                last_score = candidate_score
            else:
                no_improve_count += 1

            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current = candidate
                current_score = candidate_score

            # Adaptive step size reduction based on temperature
            if no_improve_count >= max(10, int(20 * temperature / initial_temp)):
                step_size = max(min_step, step_size * 0.95)
                no_improve_count = 0

            # Early stopping if improvement is negligible
            if step > 200 and len(improvement_history) > 20:
                avg_improvement = np.mean(improvement_history[-20:])
                if avg_improvement < 1e-8:
                    break

            temperature *= cooling_rate

        return best

    return improve