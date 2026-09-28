from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def find_smallest_triangles(pts, k=3):
        n = len(pts)
        triangles = []  # (indices, area)
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = pts[i], pts[j], pts[k]
                    area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                    triangles.append(((i, j, k), area))
        
        # Sort by area and take top k
        triangles.sort(key=lambda x: x[1])
        return [t[0] for t in triangles[:k]]

    def improve(points: np.ndarray) -> np.ndarray:
        rng = np.random.default_rng(seed=42)
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        T = 10 * current_score  # Increased initial temperature
        no_improve_count = 0
        max_no_improve = 500
        target = 0.0365

        for _ in range(2000):
            # Adaptive k based on current progress toward target
            adaptive_k = max(3, min(10, int(15 * (target - current_score) / target)))
            smallest_triangles = find_smallest_triangles(current, k=adaptive_k)
            
            # Count triangle membership for each point
            point_triangle_count = np.zeros(11, dtype=int)
            for triangle in smallest_triangles:
                for idx in triangle:
                    point_triangle_count[idx] += 1
            
            # Weighted selection of points based on triangle membership
            weights = point_triangle_count / (point_triangle_count.sum() + 1e-10)
            candidates = []
            
            # Try single-point moves
            for (i, j, k) in smallest_triangles:
                a, b, c = current[i], current[j], current[k]
                
                # Compute signed area for gradient direction
                signed_area = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                s = np.sign(signed_area)
                
                for idx in [i, j, k]:
                    # Compute gradient direction for current point
                    if idx == i:
                        grad_x = b[1] - c[1]
                        grad_y = c[0] - b[0]
                    elif idx == j:
                        grad_x = c[1] - a[1]
                        grad_y = a[0] - c[0]
                    else:  # idx == k
                        grad_x = a[1] - b[1]
                        grad_y = b[0] - a[0]
                    
                    direction = s * np.array([grad_x, grad_y])
                    norm = np.linalg.norm(direction)
                    if norm < 1e-10:
                        continue
                    direction = direction / norm
                    
                    # Adaptive step size
                    step_size = 0.3 * (1.0 - current_score / target) * T
                    step = step_size * direction
                    candidate_point = current[idx] + step
                    
                    if not is_inside_triangle(candidate_point, A, B, C):
                        continue
                    
                    too_close = False
                    for other_idx in range(11):
                        if other_idx == idx:
                            continue
                        if np.linalg.norm(candidate_point - current[other_idx]) < 1e-5:
                            too_close = True
                            break
                    if too_close:
                        continue
                    
                    candidate_config = current.copy()
                    candidate_config[idx] = candidate_point
                    candidate_score = get_smallest_triangle_area(candidate_config)
                    
                    if candidate_score < 1e-10:
                        continue
                    
                    candidates.append((candidate_config, candidate_score, 1))  # 1 indicates single-point move

            # Try multi-point moves if stuck
            if no_improve_count > max_no_improve // 2 and len(smallest_triangles) >= 2:
                # Pick a problematic triangle
                tri_idx = rng.integers(0, len(smallest_triangles))
                i, j, k = smallest_triangles[tri_idx]
                
                # Compute gradient directions for all three points
                a, b, c = current[i], current[j], current[k]
                signed_area = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                s = np.sign(signed_area)
                
                directions = []
                for idx, pt in zip([i, j, k], [a, b, c]):
                    if idx == i:
                        grad_x = b[1] - c[1]
                        grad_y = c[0] - b[0]
                    elif idx == j:
                        grad_x = c[1] - a[1]
                        grad_y = a[0] - c[0]
                    else:  # idx == k
                        grad_x = a[1] - b[1]
                        grad_y = b[0] - a[0]
                    
                    direction = s * np.array([grad_x, grad_y])
                    norm = np.linalg.norm(direction)
                    if norm < 1e-10:
                        directions.append(np.zeros(2))
                    else:
                        directions.append(direction / norm)
                
                # Create candidate moving 2 or 3 points
                num_to_move = rng.choice([2, 3])
                points_to_move = rng.choice([i, j, k], size=num_to_move, replace=False)
                
                candidate_config = current.copy()
                for idx in points_to_move:
                    pos = [i, j, k].index(idx)
                    step_size = 0.2 * (1.0 - current_score / target) * T
                    step = step_size * directions[pos]
                    candidate_config[idx] = current[idx] + step
                    
                    # Check constraints
                    if not is_inside_triangle(candidate_config[idx], A, B, C):
                        break
                    for other_idx in range(11):
                        if other_idx == idx:
                            continue
                        if np.linalg.norm(candidate_config[idx] - current[other_idx]) < 1e-5:
                            break
                else:  # Only execute if the loop didn't break
                    candidate_score = get_smallest_triangle_area(candidate_config)
                    if candidate_score > 1e-10:
                        candidates.append((candidate_config, candidate_score, num_to_move))

            if not candidates:
                T *= 0.999
                no_improve_count += 1
                continue

            # Select candidate with highest min_area
            candidate_config, candidate_score, move_type = max(candidates, key=lambda x: x[1])

            if candidate_score > current_score:
                current = candidate_config
                current_score = candidate_score
                no_improve_count = 0
                if current_score > best_score:
                    best = current
                    best_score = current_score
            else:
                delta = current_score - candidate_score
                if rng.random() < np.exp(-delta / T):
                    current = candidate_config
                    current_score = candidate_score
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            # Adaptive cooling: slow down when making progress
            if no_improve_count < 100:
                T *= 0.999  # Slower cooling when improving
            else:
                T *= 0.9985  # Slightly faster cooling when stuck

        return best

    return improve