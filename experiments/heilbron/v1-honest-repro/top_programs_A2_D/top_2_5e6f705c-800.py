from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def find_k_smallest_triangles(pts, k=3):
        n = len(pts)
        triangle_areas = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = pts[i], pts[j], pts[k]
                    area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                    triangle_areas.append((area, (i, j, k)))
        
        triangle_areas.sort(key=lambda x: x[0])
        return [indices for _, indices in triangle_areas[:k]]

    def improve(points: np.ndarray) -> np.ndarray:
        rng = np.random.default_rng(seed=42)
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        # Fixed temperature scheduling issues:
        # 1. Start with higher initial temperature (10×current_score)
        # 2. Use slower decay rate (0.999 instead of 0.99)
        T0 = 10.0 * current_score
        T = T0
        decay_rate = 0.999

        # Target min_area we're aiming for (based on known optimum)
        target_min_area = 0.0365
        
        for _ in range(2000):
            # Consider top 3 smallest triangles instead of just one
            triangle_indices_list = find_k_smallest_triangles(current, k=3)
            
            candidates = []
            for triangle_indices in triangle_indices_list:
                i, j, k = triangle_indices
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
                    
                    # Scale step size by current temperature to maintain proportionality
                    step_size = 0.2 * np.sqrt(current_score) * (T / T0)
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
                    
                    candidates.append((candidate_config, candidate_score))

            if not candidates:
                T *= decay_rate
                continue

            # Select candidate with highest min_area
            candidate_config, candidate_score = max(candidates, key=lambda x: x[1])

            if candidate_score > current_score:
                current = candidate_config
                current_score = candidate_score
                if current_score > best_score:
                    best = current
                    best_score = current_score
                    
                    # Early termination if we're close to known optimum
                    if best_score > 0.95 * target_min_area:
                        return best
            else:
                delta = current_score - candidate_score
                if rng.random() < np.exp(-delta / T):
                    current = candidate_config
                    current_score = candidate_score

            T *= decay_rate

        return best

    return improve