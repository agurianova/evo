from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A_big, B_big, C_big = get_unit_triangle()

    def find_smallest_triangles(pts, k=3):
        n = pts.shape[0]
        triangles = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    dx1 = pts[j,0] - pts[i,0]
                    dy1 = pts[j,1] - pts[i,1]
                    dx2 = pts[k,0] - pts[i,0]
                    dy2 = pts[k,1] - pts[i,1]
                    cross = dx1 * dy2 - dy1 * dx2
                    area = 0.5 * abs(cross)
                    triangles.append((area, i, j, k, cross))
        
        triangles.sort(key=lambda x: x[0])
        return triangles[:k]

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current_score = best_score

        max_rounds = 300
        initial_temp = 0.0015
        cooling_rate = 0.95
        base_step = 0.15
        base_noise = 0.15
        early_stop_patience = 30

        temp = initial_temp
        last_improvement = 0
        
        # Track previous best for adaptive cooling
        previous_best_score = best_score
        
        # Track recent improvements for adaptive threshold
        improvement_history = []
        
        for round_idx in range(max_rounds):
            # Find all triangles
            all_triangles = []
            n = current.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        dx1 = current[j,0] - current[i,0]
                        dy1 = current[j,1] - current[i,1]
                        dx2 = current[k,0] - current[i,0]
                        dy2 = current[k,1] - current[i,1]
                        cross = dx1 * dy2 - dy1 * dx2
                        area = 0.5 * abs(cross)
                        all_triangles.append((area, i, j, k, cross))
            
            all_triangles.sort(key=lambda x: x[0])
            min_area = all_triangles[0][0]
            
            # TRACK improvement rate for adaptive threshold
            if round_idx > 0 and round_idx % 10 == 0:
                recent_improvement = best_score - previous_best_score
                improvement_history.append(recent_improvement)
                if len(improvement_history) > 5:
                    improvement_history.pop(0)
                
            # Calculate average improvement rate
            if len(improvement_history) > 0:
                avg_improvement = sum(improvement_history) / len(improvement_history)
                target_improvement_rate = 1e-5
                adaptive_factor = min(1.0, avg_improvement / target_improvement_rate)
                threshold_factor = 0.15 + 0.25 * adaptive_factor
            else:
                # Initial threshold factor
                threshold_factor = 0.15
            
            # DYNAMIC threshold based on actual improvement rate
            threshold = min_area * (1 + threshold_factor)
            
            # NEW STRATEGY: 20% of the time, focus exclusively on the smallest triangle
            focused_search = False
            if np.random.rand() < 0.2:
                # Only consider the single smallest triangle
                min_area, i, j, k, _ = all_triangles[0]
                points_to_move = {i, j, k}
                # Use larger step size for focused improvement
                base_step *= 1.5
                # Focus all gradient weight on this single triangle
                threshold = min_area * 1.01
                focused_search = True
            else:
                # Collect all points involved in small triangles
                points_to_move = set()
                for area, i, j, k, _ in all_triangles:
                    if area <= threshold:
                        points_to_move.update([i, j, k])
                    else:
                        break
                
                if not points_to_move:
                    points_to_move = {i for i in range(n)}  # Fallback to all points

            # PROGRESS-DEPENDENT gradient weighting exponent
            progress = min(1.0, round_idx / max_rounds)
            exponent = -1.0 - 6.0 * progress  # From -1.0 early to -7.0 late

            # LOGARITHMIC step size scaling to avoid tiny steps when min_area is small
            step_size = base_step * np.log1p(100 * min_area) * 0.01
            noise_factor = base_noise * (temp / initial_temp)
            
            candidate = current.copy()
            moved_any = False
            
            # Move points involved in small triangles with EXPONENTIAL weighting
            for idx in points_to_move:
                grads = []
                for area, i, j, k, cross in all_triangles:
                    if area > threshold:
                        break
                    if idx in (i, j, k):
                        # Calculate gradient for this triangle
                        if idx == i:
                            A_pt, B_pt, C_pt = current[i], current[j], current[k]
                            grad = np.array([B_pt[1] - C_pt[1], C_pt[0] - B_pt[0]])
                        elif idx == j:
                            A_pt, B_pt, C_pt = current[i], current[j], current[k]
                            grad = np.array([C_pt[1] - A_pt[1], A_pt[0] - C_pt[0]])
                        else:  # idx == k
                            A_pt, B_pt, C_pt = current[i], current[j], current[k]
                            grad = np.array([A_pt[1] - B_pt[1], B_pt[0] - A_pt[0]])
                        
                        if cross < 0:
                            grad = -grad
                        
                        # PROGRESS-DEPENDENT weighting to prioritize smallest triangles
                        area_importance = np.exp(exponent * (area - min_area) / (threshold - min_area + 1e-10))
                        grads.append(grad * area_importance)
                
                if grads:
                    total_grad = np.sum(grads, axis=0)
                    
                    norm = np.linalg.norm(total_grad)
                    if norm > 1e-10:
                        total_grad = total_grad / norm
                        
                        step = step_size * total_grad
                        noise = np.random.randn(2) * noise_factor * step_size
                        candidate[idx] = current[idx] + step + noise
                        moved_any = True

            # ENHANCED EXPLORATION: small probability to move other points
            if np.random.rand() < 0.1 and len(points_to_move) < n:
                non_moving_points = list(set(range(n)) - points_to_move)
                if non_moving_points:
                    idx = np.random.choice(non_moving_points)
                    # Apply smaller random move
                    step = np.random.randn(2) * (step_size * 0.3)
                    candidate[idx] = current[idx] + step
                    moved_any = True

            # If no points were moved (shouldn't happen), move a random point
            if not moved_any:
                idx = np.random.randint(0, n)
                step = np.random.randn(2) * base_step * min_area
                candidate[idx] = current[idx] + step

            # Boundary handling with projection
            for idx in range(n):
                if not is_inside_triangle(candidate[idx], A_big, B_big, C_big):
                    # Project point back into triangle using barycentric coordinates
                    v0 = B_big - A_big
                    v1 = C_big - A_big
                    v2 = candidate[idx] - A_big
                    d00 = np.dot(v0, v0)
                    d01 = np.dot(v0, v1)
                    d11 = np.dot(v1, v1)
                    d20 = np.dot(v2, v0)
                    d21 = np.dot(v2, v1)
                    denom = d00 * d11 - d01 * d01
                    
                    if abs(denom) > 1e-10:
                        v = (d11 * d20 - d01 * d21) / denom
                        w = (d00 * d21 - d01 * d20) / denom
                        u = 1 - v - w
                        
                        # Clamp to [0,1] and renormalize
                        u, v, w = max(0, u), max(0, v), max(0, w)
                        total = u + v + w
                        if total > 1e-10:
                            u, v, w = u/total, v/total, w/total
                            candidate[idx] = u * A_big + v * B_big + w * C_big

            score = get_smallest_triangle_area(candidate)
            if score <= 1e-10:  # Degenerate triangle
                # Try smaller step
                reduction_factor = 0.5
                for _ in range(5):
                    candidate = current.copy()
                    for idx in points_to_move:
                        step = (step_size * reduction_factor) * total_grad
                        noise = np.random.randn(2) * (noise_factor * reduction_factor) * step_size
                        candidate[idx] = current[idx] + step + noise
                    
                    # Re-project if needed
                    for idx in range(n):
                        if not is_inside_triangle(candidate[idx], A_big, B_big, C_big):
                            v0 = B_big - A_big
                            v1 = C_big - A_big
                            v2 = candidate[idx] - A_big
                            d00 = np.dot(v0, v0)
                            d01 = np.dot(v0, v1)
                            d11 = np.dot(v1, v1)
                            d20 = np.dot(v2, v0)
                            d21 = np.dot(v2, v1)
                            denom = d00 * d11 - d01 * d01
                            
                            if abs(denom) > 1e-10:
                                v = (d11 * d20 - d01 * d21) / denom
                                w = (d00 * d21 - d01 * d20) / denom
                                u = 1 - v - w
                                
                                u, v, w = max(0, u), max(0, v), max(0, w)
                                total = u + v + w
                                if total > 1e-10:
                                    u, v, w = u/total, v/total, w/total
                                    candidate[idx] = u * A_big + v * B_big + w * C_big
                    
                    score = get_smallest_triangle_area(candidate)
                    if score > 1e-10:
                        break
                    reduction_factor *= 0.5
                else:
                    temp *= cooling_rate
                    continue

            # ADAPTIVE early stopping based on min_area
            adaptive_patience = max(early_stop_patience, int(75 * (0.0365 / max(min_area, 1e-5))))
            
            delta = score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temp):
                current, current_score = candidate, score
                if score > best_score:
                    best, best_score = candidate, score
                    last_improvement = round_idx

            # ADAPTIVE cooling rate based on recent progress
            if round_idx > 10 and round_idx % 10 == 0:
                recent_improvement = best_score - previous_best_score
n                if recent_improvement > 1e-6:
                    # Significant progress, slow down cooling
                    adaptive_cooling = 0.98
                else:
                    # Stuck, cool faster to escape local optimum
                    adaptive_cooling = 0.92
                temp *= adaptive_cooling
                previous_best_score = best_score
            else:
                temp *= cooling_rate

            if round_idx - last_improvement > adaptive_patience:
                break

            # Reset base_step if we were in focused search mode
            if focused_search:
                base_step /= 1.5

        return best

    return improve