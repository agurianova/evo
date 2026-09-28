from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def find_smallest_triangles(pts, current_score):
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
        
        # Adaptive k: examine more triangles when farther from optimal
        target = 0.0365
        k = max(3, min(10, int(10 * (1.0 - current_score/target))))
        return [t[0] for t in triangles[:k]]

    def improve(points: np.ndarray) -> np.ndarray:
        rng = np.random.default_rng(seed=42)
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        T = 10 * current_score  # Initial temperature
        target = 0.0365
        no_improve_count = 0
        max_no_improve = 250
        
        for iteration in range(5000):  # Increased iterations
            # Get adaptive number of smallest triangles
            smallest_triangles = find_smallest_triangles(current, current_score)
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
                    
                    # Adaptive step size: smaller when closer to target
                    progress_factor = 1.0 - min(current_score / target, 0.99)
                    step = 0.3 * T * direction * progress_factor * 0.5
                    
                    # Ensure minimum step size for numerical stability
                    if np.linalg.norm(step) < 1e-6:
                        step = direction * 1e-6
                        
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
                    
                    candidates.append((candidate_config, candidate_score))

            # If stuck, try coordinated two-point moves
            if no_improve_count > max_no_improve and rng.random() < 0.3:
                for (i, j, k) in smallest_triangles[:2]:  # Focus on most critical triangles
                    # Pick two points to move
                    points_to_move = rng.choice([i, j, k], 2, replace=False)
                    idx1, idx2 = points_to_move[0], points_to_move[1]
                    
                    # Compute signed area for gradient direction
                    a, b, c = current[i], current[j], current[k]
                    signed_area = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    s = np.sign(signed_area)
                    
                    # Get gradients for both points
                    if idx1 == i:
                        grad_x1 = b[1] - c[1]
                        grad_y1 = c[0] - b[0]
                    elif idx1 == j:
                        grad_x1 = c[1] - a[1]
                        grad_y1 = a[0] - c[0]
                    else:  # idx1 == k
                        grad_x1 = a[1] - b[1]
                        grad_y1 = b[0] - a[0]
                    
                    if idx2 == i:
                        grad_x2 = b[1] - c[1]
                        grad_y2 = c[0] - b[0]
                    elif idx2 == j:
                        grad_x2 = c[1] - a[1]
                        grad_y2 = a[0] - c[0]
                    else:  # idx2 == k
                        grad_x2 = a[1] - b[1]
                        grad_y2 = b[0] - a[0]

                    # Move points in opposite directions to preserve shape
                    direction1 = s * np.array([grad_x1, grad_y1])
                    direction2 = -s * np.array([grad_x2, grad_y2])
                    
                    norm1 = np.linalg.norm(direction1)
                    norm2 = np.linalg.norm(direction2)
                    if norm1 < 1e-10 or norm2 < 1e-10:
                        continue
                    
                    direction1 = direction1 / norm1
                    direction2 = direction2 / norm2
                    
                    # Adaptive step size for coordinated move
                    progress_factor = 1.0 - min(current_score / target, 0.99)
                    step_size = 0.2 * T * progress_factor
                    
                    candidate_point1 = current[idx1] + direction1 * step_size
                    candidate_point2 = current[idx2] + direction2 * step_size

                    # Check constraints for both points
                    if (not is_inside_triangle(candidate_point1, A, B, C) or 
                        not is_inside_triangle(candidate_point2, A, B, C)):
                        continue

                    too_close = False
                    for other_idx in range(11):
                        if other_idx == idx1 or other_idx == idx2:
                            continue
                        if (np.linalg.norm(candidate_point1 - current[other_idx]) < 1e-5 or 
                            np.linalg.norm(candidate_point2 - current[other_idx]) < 1e-5):
                            too_close = True
                            break
                    if too_close:
                        continue

                    candidate_config = current.copy()
                    candidate_config[idx1] = candidate_point1
                    candidate_config[idx2] = candidate_point2
                    candidate_score = get_smallest_triangle_area(candidate_config)
                    
                    if candidate_score > 1e-10:
                        candidates.append((candidate_config, candidate_score))

            if not candidates:
                # Adaptive cooling: slow down when stuck
                if no_improve_count > 100:
                    T *= 0.9995
                else:
                    T *= 0.999
                
                # Restart if stuck for too long
                if no_improve_count > 500:
                    current = best.copy()
                    current_score = best_score
                    T = 10 * current_score
                    no_improve_count = 0
                
                continue

            # Select candidate with highest min_area
            candidate_config, candidate_score = max(candidates, key=lambda x: x[1])

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
                no_improve_count += 1

            # Adaptive cooling based on progress
            if no_improve_count > 100:
                T *= 0.9995
            else:
                T *= 0.999

            # Prevent temperature from getting too low too quickly
            if T < 0.01 * current_score:
                T = 0.01 * current_score

        return best

    return improve