# --- G's code (entrypoint renamed to _g_entrypoint) ---
import numpy as np
import random
from collections import deque
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def triangle_area(a, b, c):
    return 0.5 * abs((a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1])))

def compute_critical_points(config, current_min_area):
    n = config.shape[0]
    critical_triples = []
    tol = 1e-9
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = triangle_area(config[i], config[j], config[k])
                if abs(area - current_min_area) < tol:
                    critical_triples.append((i, j, k))
    critical_points = set()
    for triple in critical_triples:
        critical_points.update(triple)
    return list(critical_points)

def generate_symmetric_initial(A, B, C, num_points=11):
    rows = [5, 3, 2, 1]  # Total 11 points
    num_rows = len(rows)
    points = []
    side_length = np.linalg.norm(B - A)
    H_val = C[1]  # Height of triangle
    
    for i, k in enumerate(rows):
        y = i * (H_val / (num_rows - 1)) if num_rows > 1 else 0
        width = side_length * (1 - y / H_val)
        start_x = (side_length - width) / 2
        
        if k == 1:
            x = start_x + width / 2
            points.append([x, y])
        else:
            spacing = width / (k - 1)
            for j in range(k):
                x0 = start_x + j * spacing
                x = x0 + random.uniform(-1e-5, 1e-5)
                y_pert = y + random.uniform(-1e-5, 1e-5)
                points.append([x, y_pert])
    
    return np.array(points)

def generate_random_points_in_triangle(n, A, B, C):
    points = []
    for _ in range(n):
        r1, r2 = np.random.random(2)
        sqrt_r1 = np.sqrt(r1)
        point = (1 - sqrt_r1) * A + sqrt_r1 * (1 - r2) * B + sqrt_r1 * r2 * C
        points.append(point)
    return np.array(points)

def _g_entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    num_points = 11
    num_restarts = 50
    best_config = None
    best_min_area = -1

    for _ in range(num_restarts):
        # Generate initial configuration using symmetric pattern
        config = generate_symmetric_initial(A, B, C, num_points)
        min_area = get_smallest_triangle_area(config)
        
        # Fallback to random if symmetric initialization invalid
        if min_area <= 0:
            config = generate_random_points_in_triangle(num_points, A, B, C)
            min_area = get_smallest_triangle_area(config)

        current_config = config
        current_min_area = min_area
        step_size = 0.1
        min_step = 1e-6
        reduction_factor = 0.95
        max_no_improve = 1000
        steps_without_improvement = 0
        tabu = deque(maxlen=10)  # Tabu list for neutral move cycling

        # Initial tabu registration
        rounded_init = tuple((round(x, 4), round(y, 4)) for x, y in current_config)
        tabu.append(rounded_init)

        while step_size > min_step:
            for _ in range(max_no_improve):
                # Critical point bias: 80% chance for critical points
                critical_points = compute_critical_points(current_config, current_min_area)
                if critical_points and random.random() < 0.8:
                    idx = random.choice(critical_points)
                else:
                    idx = random.randint(0, num_points - 1)

                # 30% chance for two-point move
                if random.random() < 0.3 and num_points > 1:
                    idx2 = random.randint(0, num_points - 1)
                    while idx2 == idx:
                        idx2 = random.randint(0, num_points - 1)
                    angle = random.uniform(0, 2 * np.pi)
                    dx = step_size * 0.7 * np.cos(angle)
                    dy = step_size * 0.7 * np.sin(angle)
                    
                    new_point1 = current_config[idx] + np.array([dx, dy])
                    new_point2 = current_config[idx2] + np.array([dx, dy])
                    
                    if not (is_inside_triangle(new_point1, A, B, C) and 
                            is_inside_triangle(new_point2, A, B, C)):
                        steps_without_improvement += 1
                        continue

                    new_config = current_config.copy()
                    new_config[idx] = new_point1
                    new_config[idx2] = new_point2
                else:
                    angle = random.uniform(0, 2 * np.pi)
                    dx = step_size * np.cos(angle)
                    dy = step_size * np.sin(angle)
                    new_point = current_config[idx] + np.array([dx, dy])

                    if not is_inside_triangle(new_point, A, B, C):
                        steps_without_improvement += 1
                        continue

                    new_config = current_config.copy()
                    new_config[idx] = new_point

                new_min_area = get_smallest_triangle_area(new_config)
                if new_min_area <= 0:  # Invalid configuration
                    steps_without_improvement += 1
                    continue

                # Check tabu for neutral moves
                rounded_new = tuple((round(x, 4), round(y, 4)) for x, y in new_config)
                if new_min_area == current_min_area:
                    if rounded_new in tabu:
                        steps_without_improvement += 1
                        continue
                    else:
                        accept = True
                elif new_min_area > current_min_area:
                    accept = True
                else:
                    accept = False

                if accept:
                    current_config = new_config
                    current_min_area = new_min_area
                    tabu.append(rounded_new)
                    steps_without_improvement = 0
                else:
                    steps_without_improvement += 1

            if steps_without_improvement >= max_no_improve:
                step_size *= reduction_factor
                steps_without_improvement = 0
            else:
                break

            if step_size <= min_step:
                break

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = current_config

    return best_config

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