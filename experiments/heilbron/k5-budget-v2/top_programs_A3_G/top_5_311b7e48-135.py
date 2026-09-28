# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def _g_entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    base_length = B[0] - A[0]
    height = C[1]
    
    # Adaptive symmetric initialization
    rows = [4, 3, 2, 2]  # Points per row (bottom to top)
    
    # Compute optimal spacing via constraint resolution
    s = base_length / 3.0  # Initial guess for max row (4 points)
    for _ in range(5):
        y_vals = [i * s * np.sqrt(3) / 2 for i in range(len(rows))]
        widths = [base_length * (1 - y / height) for y in y_vals]
        max_s_per_row = []
        for i, k in enumerate(rows):
            if k > 1:
                max_s = widths[i] / (k - 1)
                max_s_per_row.append(max_s)
            else:
                max_s_per_row.append(float('inf'))
        s = min(max_s_per_row)

    points = []
    # Symmetric point generation
    for i, k in enumerate(rows):
        y = i * s * np.sqrt(3) / 2
        if y > height:
            y = height
        
        width = base_length * (1 - y / height)
        total_left_margin = (base_length - width) / 2
        
        if k % 2 == 1:
            num_left = (k - 1) // 2
            span = (k - 1) * s
            if span > width:
                span = width
            x0 = total_left_margin + (width - span) / 2
            
            # Left points
            for j in range(num_left):
                x = x0 + j * s
                points.append([x, y])
            # Midline point
            x_mid = x0 + num_left * s
            points.append([x_mid, y])
            # Right points (mirror of left)
            for j in range(num_left - 1, -1, -1):
                x = x0 + j * s
                x_mirror = base_length - x
                points.append([x_mirror, y])
        else:
            num_left = k // 2
            span = (k - 1) * s
            if span > width:
                span = width
            x0 = total_left_margin + (width - span) / 2
            
            # Left points
            for j in range(num_left):
                x = x0 + j * s
                points.append([x, y])
            # Right points (mirror of left)
            for j in range(num_left - 1, -1, -1):
                x = x0 + j * s
                x_mirror = base_length - x
                points.append([x_mirror, y])

    # Convert to numpy array
    current_points = np.array(points)
    current_min_area = get_smallest_triangle_area(current_points)
    best_points = current_points.copy()
    best_min_area = current_min_area

    # Enhanced simulated annealing
    T = 1.0
    alpha = 0.9999
    iterations = 50000

    # Precompute symmetric counterpart mapping
    counterpart = [3, 2, 1, 0, 6, 5, 4, 8, 7, 10, 9]
    pairs = [(0, 3), (1, 2), (4, 6), (7, 8), (9, 10)]

    for _ in range(iterations):
        # Geometry-aware step scaling
        step = T * base_length * 0.1
        
        # 80%: Single symmetric move (pair or midline), 20%: Multi-point move (two pairs)
        if random.random() < 0.8:
            idx = random.randint(0, 10)
            new_points = current_points.copy()
            
            if idx == 5:  # Midline point
                dx = random.uniform(-step, step)
                dy = random.uniform(-step, step)
                new_point = current_points[idx] + np.array([dx, dy])
                if not is_inside_triangle(new_point, A, B, C):
                    continue
                new_points[idx] = new_point
            else:  # Symmetric pair
                j = counterpart[idx]
                dx = random.uniform(-step, step)
                dy = random.uniform(-step, step)
                new_i = current_points[idx] + np.array([dx, dy])
                if not is_inside_triangle(new_i, A, B, C):
                    continue
                new_j = np.array([base_length - new_i[0], new_i[1]])
                new_points[idx] = new_i
                new_points[j] = new_j
        else:  # Multi-point: perturb two symmetric pairs (4 points)
            selected_pairs = random.sample(range(5), 2)
            new_points = current_points.copy()
            valid = True
            for pair_idx in selected_pairs:
                i, j = pairs[pair_idx]
                dx = random.uniform(-step, step)
                dy = random.uniform(-step, step)
                new_i = current_points[i] + np.array([dx, dy])
                if not is_inside_triangle(new_i, A, B, C):
                    valid = False
                    break
                new_j = np.array([base_length - new_i[0], new_i[1]])
                new_points[i] = new_i
                new_points[j] = new_j
            if not valid:
                continue

        # Resistance-aware constraint
        new_min_area = get_smallest_triangle_area(new_points)
        if new_min_area < 0.9 * current_min_area:
            continue

        # Annealing acceptance
        if new_min_area > current_min_area:
            current_points = new_points
            current_min_area = new_min_area
            if new_min_area > best_min_area:
                best_points = new_points
                best_min_area = new_min_area
        else:
            delta = new_min_area - current_min_area
            if random.random() < np.exp(delta / T):
                current_points = new_points
                current_min_area = new_min_area

        # Cool down
        T *= alpha

    return best_points

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def _d_entrypoint():
    A_tri, B_tri, C_tri = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        n_iterations = 200
        initial_temp = 0.00365
        initial_step = 0.05

        def get_min_area_and_triangle(pts):
            n = pts.shape[0]
            min_area = float('inf')
            best_triangle = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = 0.5 * abs((pts[j,0]-pts[i,0])*(pts[k,1]-pts[i,1]) - (pts[j,1]-pts[i,1])*(pts[k,0]-pts[i,0]))
                        if area < min_area:
                            min_area = area
                            best_triangle = (i, j, k)
            return min_area, best_triangle

        for iteration in range(n_iterations):
            current_score, (i, j, k) = get_min_area_and_triangle(current)
            T = initial_temp * (1 - iteration / n_iterations)
            step = initial_step * (0.9 ** (iteration // 10))

            p = np.random.choice([i, j, k])
            
            if p == i:
                side1, side2 = j, k
            elif p == j:
                side1, side2 = i, k
            else:
                side1, side2 = i, j

            vec_side = current[side2] - current[side1]
            n1 = np.array([-vec_side[1], vec_side[0]])
            vec_to_p = current[p] - current[side1]
            
            if np.dot(vec_to_p, n1) > 0:
                direction = n1
            else:
                direction = -n1

            norm_dir = np.linalg.norm(direction)
            if norm_dir < 1e-10:
                continue
            direction = direction / norm_dir

            candidate = current.copy()
            candidate[p] = current[p] + step * direction

            if not is_inside_triangle(candidate, A_tri, B_tri, C_tri):
                continue

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - current_score

            if delta > 0:
                current = candidate
            else:
                if T > 1e-10 and np.random.rand() < np.exp(delta / T):
                    current = candidate

        return current

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)