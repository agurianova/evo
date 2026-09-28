from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def enforce_row_structure(points, row_counts=[3, 3, 3, 2]):
        """Enforce the expected row structure based on Constructor's pattern."""
        # Sort points by y-coordinate
        y_coords = points[:, 1]
        sorted_indices = np.argsort(y_coords)
        
        # Calculate expected row positions based on counts
        row_assignments = np.zeros(len(points), dtype=int)
        row_ys = np.zeros(len(row_counts))
        
        start_idx = 0
        for row_idx, count in enumerate(row_counts):
            end_idx = start_idx + count
            if end_idx > len(points):
                break
            # Points in this row
            row_points = sorted_indices[start_idx:end_idx]
            # Average y for this row
            row_ys[row_idx] = np.mean(y_coords[row_points])
            # Assign row index to these points
            for idx in row_points:
                row_assignments[idx] = row_idx
            start_idx = end_idx
        
        return row_assignments, row_ys

    def improve(points):
        np.random.seed(42)
        current = points.copy()
        best = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_score = current_score

        # Adaptive parameters
        temperature = 0.005
        initial_temperature = 0.005
        cooling_rate = 0.995
        step_size = 0.05
        initial_step_size = 0.05
        max_iter = 500
        TOL = 1e-10
        stagnation_counter = 0
        stagnation_threshold = 50
        
        # Track improvement history for adaptive step size
        improvement_history = []
        history_window = 50

        for it in range(max_iter):
            n = len(current)
            triangle_areas = []
            
            # Collect all triangle areas
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a = current[i]
                        b = current[j]
                        c = current[k]
                        area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                        triangle_areas.append((area_val, i, j, k))
            
            # Sort by area and take top 3 smallest
            triangle_areas.sort(key=lambda x: x[0])
            top_triangles = triangle_areas[:min(3, len(triangle_areas))]
            
            if not top_triangles:
                break
            
            # Initialize gradient accumulators for all points
            grads = np.zeros((n, 2))
            
            # Process each small triangle
            for area_val, i, j, k in top_triangles:
                a_pt = current[i]
                b_pt = current[j]
                c_pt = current[k]
                
                cross = (b_pt[0]-a_pt[0])*(c_pt[1]-a_pt[1]) - (c_pt[0]-a_pt[0])*(b_pt[1]-a_pt[1])
                sgn = np.sign(cross)
                
                grad_a = np.array([b_pt[1]-c_pt[1], c_pt[0]-b_pt[0]])
                grad_b = np.array([c_pt[1]-a_pt[1], a_pt[0]-c_pt[0]])
                grad_c = np.array([a_pt[1]-b_pt[1], b_pt[0]-a_pt[0]])
                
                if np.linalg.norm(grad_a) > 1e-8:
                    grad_a = grad_a / np.linalg.norm(grad_a)
                else:
                    grad_a = np.zeros(2)
                if np.linalg.norm(grad_b) > 1e-8:
                    grad_b = grad_b / np.linalg.norm(grad_b)
                else:
                    grad_b = np.zeros(2)
                if np.linalg.norm(grad_c) > 1e-8:
                    grad_c = grad_c / np.linalg.norm(grad_c)
                else:
                    grad_c = np.zeros(2)
                
                # Accumulate gradients
                grads[i] += sgn * grad_a
                grads[j] += sgn * grad_b
                grads[k] += sgn * grad_c
            
            # Normalize accumulated gradients
            for i in range(n):
                if np.linalg.norm(grads[i]) > 1e-8:
                    grads[i] = grads[i] / np.linalg.norm(grads[i])
            
            # Add row-based guidance to maintain structure
            row_assignments, row_ys = enforce_row_structure(current)
            for i in range(n):
                row_idx = row_assignments[i]
                if row_idx < len(row_ys):
                    # Gentle constraint to maintain y-coordinate within row
                    y_diff = current[i, 1] - row_ys[row_idx]
                    # Only apply if significantly off row
                    if abs(y_diff) > 0.01:
                        grads[i, 1] -= 0.2 * np.sign(y_diff)
            
            # Create candidate by moving all points
            candidate = current.copy()
            for i in range(n):
                candidate[i] += step_size * grads[i]
            
            # Project points back into triangle if needed
            for i in range(n):
                if not is_inside_triangle(candidate[i], A, B, C):
                    orig_pt = current[i]
                    v = candidate[i] - orig_pt
                    low, high = 0.0, 1.0
                    for _ in range(5):
                        mid = (low + high) / 2
                        test_pt = orig_pt + mid * v
                        if is_inside_triangle(test_pt, A, B, C):
                            low = mid
                        else:
                            high = mid
                    candidate[i] = orig_pt + low * v
            
            # Calculate new score
            new_score = get_smallest_triangle_area(candidate)
            if new_score < TOL:
                # Stagnation handling
                stagnation_counter += 1
                if stagnation_counter > stagnation_threshold:
                    temperature = initial_temperature
                    step_size = initial_step_size
                    stagnation_counter = 0
                temperature *= cooling_rate
                continue
            
            # Update improvement history
            delta = new_score - current_score
            improvement_history.append(delta > 0)
            if len(improvement_history) > history_window:
                improvement_history.pop(0)
            
            # Adaptive step size based on recent success rate
            if improvement_history:
                success_rate = sum(improvement_history) / len(improvement_history)
                if success_rate > 0.3:
                    step_size = min(step_size * 1.05, initial_step_size * 2.0)
                else:
                    step_size = max(step_size * 0.95, initial_step_size * 0.1)
            
            # Acceptance criteria
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current = candidate
                current_score = new_score
                stagnation_counter = 0
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
            else:
                stagnation_counter += 1
            
            # Stagnation recovery
            if stagnation_counter > stagnation_threshold:
                temperature = initial_temperature
                step_size = initial_step_size
                stagnation_counter = 0
            
            # Update temperature
            temperature *= cooling_rate

        return best

    return improve