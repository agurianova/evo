# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
import numpy as np
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    n_points = 11
    n_restarts = 50
    max_iter = 2000
    best_points = None
    best_min_area = -1.0
    initial_temp = 0.001
    cooling_rate = 0.999

    for restart in range(n_restarts):
        # Uniform initialization using sqrt method
        points = []
        for _ in range(n_points):
            r1 = random.random()
            r2 = random.random()
            r1_sqrt = math.sqrt(r1)
            a = 1 - r1_sqrt
            b = r1_sqrt * (1 - r2)
            c = r1_sqrt * r2
            P = a * A + b * B + c * C
            points.append(P)
        points = np.array(points)

        current_min = get_smallest_triangle_area(points)
        step = 0.1
        temp = initial_temp

        for iter in range(max_iter):
            # Find smallest triangle (critical bottleneck)
            min_area_val = float('inf')
            best_tri = None
            for i in range(n_points):
                for j in range(i+1, n_points):
                    for k in range(j+1, n_points):
                        area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                                      (points[k,0]-points[i,0])*(points[j,1]-points[i,1]))
                        if area < min_area_val:
                            min_area_val = area
                            best_tri = (i, j, k)
            current_min = min_area_val

            # Target critical triangle points (80% single-point, 20% multi-point moves)
            if random.random() < 0.8:
                idx_to_move = [random.choice(best_tri)]
            else:
                num_to_move = random.choice([2, 3])
                idx_to_move = random.sample(best_tri, num_to_move)

            # Generate candidate move
            new_points = points.copy()
            valid_move = True
            for idx in idx_to_move:
                dx = random.uniform(-step, step)
                dy = random.uniform(-step, step)
                new_point = points[idx] + np.array([dx, dy])
                if not is_inside_triangle(new_point, A, B, C):
                    valid_move = False
                    break
                new_points[idx] = new_point

            # Evaluate and accept/reject
            if valid_move:
                new_min = get_smallest_triangle_area(new_points)
                delta = new_min - current_min
                if delta > 0 or random.random() < math.exp(delta / temp):
                    points = new_points
                    current_min = new_min

            # Adaptive schedule updates
            if iter % 50 == 0:
                step *= 0.95
                temp *= cooling_rate

        # Track best configuration
        if current_min > best_min_area:
            best_min_area = current_min
            best_points = points

    return best_points

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def _d_entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        rng = np.random.default_rng(seed=42)
        
        def find_k_smallest_triangles(pts, k=3):
            n = len(pts)
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = pts[i], pts[j], pts[k]
                        area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        triangles.append((area, (i, j, k)))
            triangles.sort(key=lambda x: x[0])
            return [t[1] for t in triangles[:k]]

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        # Initialize temperature to allow sufficient exploration
        T = 10.0 * current_score  # Increased from T = current_score

        for _ in range(2000):
            # Consider top 3 smallest triangles instead of just the smallest
            triangle_indices_list = find_k_smallest_triangles(current, k=3)
            
            candidates = []
            for indices in triangle_indices_list:
                i, j, k = indices
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
                    
                    # Make step size adaptive to current temperature
                    step = 0.2 * T * direction  # Changed from 0.2 * np.sqrt(current_score)
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
                T *= 0.999  # Slower decay from 0.99 to 0.999
                continue

            # Select candidate with highest min_area
            candidate_config, candidate_score = max(candidates, key=lambda x: x[1])

            if candidate_score > current_score:
                current = candidate_config
                current_score = candidate_score
                if current_score > best_score:
                    best = current
                    best_score = current_score
            else:
                delta = current_score - candidate_score
                if rng.random() < np.exp(-delta / T):
                    current = candidate_config
                    current_score = candidate_score

            T *= 0.999  # Slower decay

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)