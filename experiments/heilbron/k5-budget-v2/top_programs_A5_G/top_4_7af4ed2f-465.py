# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    main_seed = 42
    best_overall = None
    best_min_overall = -1

    for restart in range(5):
        # Set seed for this restart
        seed = main_seed + restart
        np.random.seed(seed)
        random.seed(seed)

        # Generate 4-row asymmetric grid [1,3,4,3] (top to bottom)
        rows = 4
        points_per_row = [1, 3, 4, 3]
        points = []
        for row in range(rows):
            num_points = points_per_row[row]
            v = (rows - row - 0.5) / rows  # Weight for C (top row: high v)
            for i in range(num_points):
                u = (i + 0.5) / num_points * (1 - v)  # Scale by row length
                P = (1 - u - v) * A + u * B + v * C
                # Increased perturbation to break symmetry
                perturbation = np.random.uniform(-0.05, 0.05, size=2)
                P = P + perturbation
                points.append(P)
        
        current = np.array(points)
        current_min = get_smallest_triangle_area(current)
        best_in_chain = current.copy()
        best_min_in_chain = current_min

        # Enhanced annealing parameters
        n_steps = 2000
        T_start = 0.1
        T_end = 0.0001

        for step in range(n_steps):
            # Track temperature (exponential decay)
            T = T_start * (T_end / T_start) ** (step / n_steps)
            
            # Identify ALL bottleneck triangles within tolerance
            min_triangle_indices_set = set()
            tol = 1e-5
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        a, b, c = current[i], current[j], current[k]
                        area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        if abs(area - current_min) < tol:
                            min_triangle_indices_set.add(i)
                            min_triangle_indices_set.add(j)
                            min_triangle_indices_set.add(k)

            if not min_triangle_indices_set:
                min_triangle_indices_set = {0, 1, 2}  # Fallback
            
            idx = random.choice(list(min_triangle_indices_set))
            
            # Adaptive step size (linear decay from 0.2 to 0.01)
            step_size = 0.2 - (0.2 - 0.01) * step / n_steps
            angle = random.uniform(0, 2 * np.pi)
            delta = np.array([step_size * np.cos(angle), step_size * np.sin(angle)])
            new_point = current[idx] + delta
            
            # Validate new point
            if not is_inside_triangle(new_point, A, B, C):
                continue
            
            dists = np.linalg.norm(current - new_point, axis=1)
            dists[idx] = 1e9
            if np.min(dists) < 1e-8:
                continue
            
            candidate = current.copy()
            candidate[idx] = new_point
            new_min = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            delta_area = new_min - current_min
            if delta_area > 0 or random.random() < np.exp(delta_area / T):
                current = candidate
                current_min = new_min

            # Track best in chain
            if current_min > best_min_in_chain:
                best_in_chain = current.copy()
                best_min_in_chain = current_min

        # Update overall best
        if best_overall is None or best_min_in_chain > best_min_overall:
            best_overall = best_in_chain
            best_min_overall = best_min_in_chain

    return best_overall

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