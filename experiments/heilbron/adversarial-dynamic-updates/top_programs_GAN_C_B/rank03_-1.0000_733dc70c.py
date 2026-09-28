from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A_big, B_big, C_big = get_unit_triangle()

    def find_small_triangles(pts, threshold_factor=1.5):
        n = pts.shape[0]
        min_area = float('inf')
        all_triangles = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    dx1 = pts[j,0] - pts[i,0]
                    dy1 = pts[j,1] - pts[i,1]
                    dx2 = pts[k,0] - pts[i,0]
                    dy2 = pts[k,1] - pts[i,1]
                    cross = dx1 * dy2 - dy1 * dx2
                    area = 0.5 * abs(cross)
                    if area < 1e-10:  # Skip degenerate
                        continue
                    if area < min_area:
                        min_area = area
                    all_triangles.append((area, i, j, k, cross))
        
        # If no valid triangles found (shouldn't happen with 11 distinct points)
        if min_area == float('inf'):
            return [], float('inf')
        
        # Filter triangles below threshold
        threshold = min_area * threshold_factor
        small_triangles = [t for t in all_triangles if t[0] <= threshold]
        
        # Calculate point pressure (how many small triangles each point is in)
        point_pressure = np.zeros(n)
        for _, i, j, k, _ in small_triangles:
            point_pressure[i] += 1
            point_pressure[j] += 1
            point_pressure[k] += 1
        
        # Normalize pressure to [0,1]
        max_pressure = np.max(point_pressure)
        if max_pressure > 0:
            point_pressure = point_pressure / max_pressure
        
        return small_triangles, min_area, point_pressure

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current_score = best_score

        max_rounds = 300
        base_temp = 0.001
        cooling_rate = 0.95
        base_noise_factor = 0.1
        base_early_stop = 20

        # Get initial min_area to set adaptive parameters
        _, min_area, _ = find_small_triangles(current)
        initial_step = 0.1 * min_area
        
        temp = base_temp
        last_improvement = 0

        for round_idx in range(max_rounds):
            small_triangles, min_area, point_pressure = find_small_triangles(current)
            
            # If no small triangles found (degenerate case), skip
            if not small_triangles:
                temp *= cooling_rate
                continue

            # Adaptive parameters based on current state
            step = initial_step * (temp / base_temp)
            noise_factor = base_noise_factor * (temp / base_temp)
            early_stop_patience = max(base_early_stop, int(100 * min_area))

            candidate = current.copy()
            move_made = False
            
            # Try up to 3 times with reduced step if degeneracy occurs
            for attempt in range(3):
                step_size = step * (0.5 ** attempt)
                
                # Move all points with pressure > 0
                for idx in range(len(current)):
                    if point_pressure[idx] > 0:
                        total_grad = np.zeros(2)
                        
                        # Sum gradients from all small triangles involving this point
n                        for _, i, j, k, cross in small_triangles:
                            if idx == i or idx == j or idx == k:
                                A_pt, B_pt, C_pt = current[i], current[j], current[k]
                                
                                grad_A = np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]])
                                grad_B = np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[0]])
                                grad_C = np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]])

                                if cross < 0:
                                    grad_A, grad_B, grad_C = -grad_A, -grad_B, -grad_C

                                if idx == i:
                                    # Scale gradient by min_area for natural step sizing
                                    total_grad += grad_A * min_area
                                elif idx == j:
                                    total_grad += grad_B * min_area
                                else:  # idx == k
                                    total_grad += grad_C * min_area

                        # Normalize and apply
                        norm = np.linalg.norm(total_grad)
                        if norm > 1e-10:
                            total_grad = total_grad / norm
                        else:
                            total_grad = np.random.randn(2)
                            total_grad = total_grad / np.linalg.norm(total_grad)

                        # Apply pressure-weighted movement with noise
                        noise = np.random.randn(2) * noise_factor * step_size
                        movement = step_size * point_pressure[idx] * total_grad + noise
                        candidate[idx] = current[idx] + movement
                        move_made = True

                # Check if we made any valid moves
                if not move_made:
                    break

                # Check constraints
                if is_inside_triangle(candidate, A_big, B_big, C_big):
                    score = get_smallest_triangle_area(candidate)
                    if score > 1e-10:  # Valid non-degenerate configuration
                        break

            # If no valid candidate after 3 attempts, skip this iteration
            if attempt == 2 and (not is_inside_triangle(candidate, A_big, B_big, C_big) or 
                                get_smallest_triangle_area(candidate) <= 1e-10):
                temp *= cooling_rate
                continue

            # Simulated annealing acceptance
            score = get_smallest_triangle_area(candidate)
            delta = score - current_score
            if delta > 0 or (temp > 1e-6 and np.random.rand() < np.exp(delta / temp)):
                current, current_score = candidate, score
                if score > best_score:
                    best, best_score = candidate, score
                    last_improvement = round_idx

            # Update temperature
            temp *= cooling_rate
            
            # Adaptive early stopping
            if round_idx - last_improvement > early_stop_patience:
                break

        return best

    return improve