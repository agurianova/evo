# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    base_seed = 42
    best_config = None
    best_min_area = -1

    def generate_initial_config():
        points = []
        num_candidates = 100
        
        for i in range(11):
            best_candidate = None
            best_metric = -1
            
            for _ in range(num_candidates):
                # Generate random point in triangle using barycentric coordinates
                u, v = np.random.rand(), np.random.rand()
                if u + v > 1:
                    u, v = 1 - u, 1 - v
                w = 1 - u - v
                candidate = w * A + u * B + v * C
                
                # Check distinctness
                if i > 0:
                    dists = np.linalg.norm(np.array(points) - candidate, axis=1)
                    if np.min(dists) < 1e-5:
                        continue
                
                # Evaluate candidate
                if i == 0:
                    metric = 1.0  # First point: arbitrary valid metric
                elif i == 1:
                    # Use distance to first point as proxy for future triangle area
                    metric = np.linalg.norm(points[0] - candidate)
                else:
                    # Form temporary set and compute min triangle area
                    temp_points = np.vstack([points, candidate])
                    metric = get_smallest_triangle_area(temp_points)
                
                if metric > best_metric:
                    best_metric = metric
                    best_candidate = candidate

            # Fallback if no valid candidate found (should rarely happen)
            if best_candidate is None:
                u, v = np.random.rand(), np.random.rand()
                if u + v > 1:
                    u, v = 1 - u, 1 - v
                w = 1 - u - v
                best_candidate = w * A + u * B + v * C
                
            points.append(best_candidate)
        
        return np.array(points)

    def hill_climb(points, steps=1000):
        def triangle_area(p1, p2, p3):
            return 0.5 * abs(p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1]))

        current_points = points.copy()
        current_min_area = get_smallest_triangle_area(current_points)
        initial_step = 0.05
        final_step = 0.001
        decay = (final_step / initial_step) ** (1.0 / steps)

        for step in range(steps):
            step_size = initial_step * (decay ** step)
            
            # Identify bottleneck: smallest triangle
            min_area_val = current_min_area
            min_triangle = None
            points_arr = np.array(current_points)
            n = len(points_arr)
            
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = triangle_area(points_arr[i], points_arr[j], points_arr[k])
                        if area < min_area_val + 1e-10:  # Allow floating point tolerance
                            min_area_val = area
                            min_triangle = (i, j, k)

            if min_triangle is None:
                idx1, idx2 = random.sample(range(n), 2)
            else:
                # Select two points from the bottleneck triangle
                idx1, idx2 = random.sample(min_triangle, 2)

            # Generate perturbations
            dir1 = np.random.uniform(-1, 1, 2)
            dir1 = dir1 / np.linalg.norm(dir1)
            dir2 = np.random.uniform(-1, 1, 2)
            dir2 = dir2 / np.linalg.norm(dir2)
            
            new_p1 = current_points[idx1] + dir1 * step_size
            new_p2 = current_points[idx2] + dir2 * step_size

            # Validate new points
            if not (is_inside_triangle(new_p1, A, B, C) and 
                    is_inside_triangle(new_p2, A, B, C)):
                continue

            new_points = current_points.copy()
            new_points[idx1] = new_p1
            new_points[idx2] = new_p2

            # Check distinctness
            all_dists = np.linalg.norm(new_points - new_p1, axis=1)
            all_dists[idx1] = np.inf
            if np.min(all_dists) < 1e-5:
                continue
            
            all_dists = np.linalg.norm(new_points - new_p2, axis=1)
            all_dists[idx2] = np.inf
            if np.min(all_dists) < 1e-5:
                continue

            # Evaluate new configuration
            new_min_area = get_smallest_triangle_area(new_points)
            if new_min_area > current_min_area:
                current_points = new_points
                current_min_area = new_min_area

        return current_points

    for trial in range(50):  # Increased from 10 to 50 trials
        np.random.seed(base_seed + trial)
        random.seed(base_seed + trial)
        
        initial = generate_initial_config()
        config = hill_climb(initial)
        min_area = get_smallest_triangle_area(config)
        
        if min_area > best_min_area:
            best_min_area = min_area
            best_config = config

    return best_config

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def _d_entrypoint():
    A, B, C = get_unit_triangle()

    def triangle_area(a, b, c):
        return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))

    def find_k_smallest_triangles(pts, k):
        n = pts.shape[0]
        triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k_idx in range(j+1, n):
                    area = triangle_area(pts[i], pts[j], pts[k_idx])
                    triangles.append((area, i, j, k_idx))
        triangles.sort(key=lambda x: x[0])
        return triangles[:k]

    def project_to_boundary(point, A, B, C):
        """Project a point to the closest point on the triangle boundary."""
        if is_inside_triangle(point, A, B, C):
            return point.copy()
        
        def point_to_line_distance(p, a, b):
            ab = b - a
            ap = p - a
            t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-12)
            t = max(0, min(1, t))
            projection = a + t * ab
            return projection, np.linalg.norm(p - projection)
        
        p_ab, d_ab = point_to_line_distance(point, A, B)
        p_bc, d_bc = point_to_line_distance(point, B, C)
        p_ca, d_ca = point_to_line_distance(point, C, A)
        
        if d_ab <= d_bc and d_ab <= d_ca:
            return p_ab
        elif d_bc <= d_ab and d_bc <= d_ca:
            return p_bc
        else:
            return p_ca

    def adaptive_triangle_selection(triangles, max_k=5):
        """Dynamically determine how many smallest triangles to consider based on area distribution."""
        if not triangles:
            return 1
        
        # Get the areas of the smallest triangles
        areas = [t[0] for t in triangles]
        
        # If we have fewer than max_k triangles, just use all
        if len(areas) <= max_k:
            return len(areas)
        
        # Analyze the distribution of the smallest areas
        # If the smallest areas are very close, we need to address multiple constraints
        smallest_area = areas[0]
        # Look at the ratio between the smallest and the k-th smallest area
        ratios = [areas[0] / areas[i] for i in range(1, min(max_k, len(areas)))]
        
        # If ratios are close to 1 (areas are similar), increase k
        avg_ratio = sum(ratios) / len(ratios) if ratios else 1.0
        if avg_ratio > 0.9:  # Areas are very similar
            return max_k
        elif avg_ratio > 0.7:  # Areas are somewhat similar
            return min(max_k, 3)
        else:  # Areas are distinct
            return 1

    def improve(points: np.ndarray) -> np.ndarray:
        # Make seed input-dependent to diversify exploration
        np.random.seed(hash(points.tobytes()) % (2**32))
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        initial_temp = 0.1  # Increased from 0.01 for better exploration
        cooling_rate = 0.999
        current_temp = initial_temp
        rounds = 750  # Increased from 500 for more thorough search

        for round in range(rounds):
            # Get up to 5 smallest triangles to analyze distribution
            candidate_triangles = find_k_smallest_triangles(current, 5)
            # Dynamically determine how many to actually use
            num_triangles = adaptive_triangle_selection(candidate_triangles, max_k=5)
            triangles = candidate_triangles[:num_triangles]
            
            # Track how many triangles each point is in for normalization
            point_triangle_count = {}
            point_gradients = {}
            for _, i, j, k in triangles:
                for idx in [i, j, k]:
                    point_triangle_count[idx] = point_triangle_count.get(idx, 0) + 1

            # Accumulate gradients for points that might be in multiple triangles
            for _, i, j, k in triangles:
                a, b, c = current[i], current[j], current[k]

                f = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                sign_f = 1.0 if f >= 0 else -1.0

                grad_a = np.array([b[1]-c[1], c[0]-b[0]]) * 0.5 * sign_f
                grad_b = np.array([c[1]-a[1], a[0]-c[0]]) * 0.5 * sign_f
                grad_c = np.array([a[1]-b[1], b[0]-a[0]]) * 0.5 * sign_f

                for idx, grad in [(i, grad_a), (j, grad_b), (k, grad_c)]:
                    if idx in point_gradients:
                        point_gradients[idx] += grad
                    else:
                        point_gradients[idx] = grad

            # Normalize gradients by triangle count to prevent overstepping
            for idx in point_gradients:
                point_gradients[idx] /= point_triangle_count[idx]

            # Adjusted step size: lower initial value with faster decay
            step_size_val = 0.01 * (0.99 ** round)

            def normalize_grad(grad, step_size):
                norm = np.linalg.norm(grad)
                if norm < 1e-8:
                    return np.zeros(2)
                return grad / norm * step_size

            candidate = current.copy()
            for idx, grad in point_gradients.items():
                delta = normalize_grad(grad, step_size_val)
                candidate[idx] += delta

            # Project each point to boundary if needed
            for idx in range(candidate.shape[0]):
                candidate[idx] = project_to_boundary(candidate[idx], A, B, C)

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - current_score

            if delta > 0 or np.random.rand() < np.exp(delta / current_temp):
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score

            current_temp *= cooling_rate

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)