import numpy as np

# G's original point configuration
_G_POINTS = np.array([[1.0077079767641828, 0.4623088663955425], [0.8820315516855453, 0.8904721216517911], [1.2265234797090114, 0.153197710397766], [0.5389784947329167, 0.5850246885245033], [0.7232010815929202, 0.29158814922497517], [0.779777717377279, 0.2970100405265842], [0.48979189848462046, 0.5730686262789082], [0.7751812747920944, 1.1693104676763038], [0.8592914654191226, 0.030761665041107195], [0.757733772150756, 0.47289664286061417], [0.5211421104941416, 0.41567994968150984]], dtype=np.float64)

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def triangle_signed_area(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

def compute_area_gradient(a, b, c):
    """Compute gradients for points a, b, c to increase triangle area"""
    signed_area = triangle_signed_area(a, b, c)
    sign = 1.0 if signed_area >= 0 else -1.0
    
    # Gradients for absolute area
    grad_a = sign * np.array([b[1] - c[1], c[0] - b[0]])
    grad_b = sign * np.array([c[1] - a[1], a[0] - c[0]])
    grad_c = sign * np.array([a[1] - b[1], b[0] - a[0]])
    
    # Normalize gradients
    for grad in [grad_a, grad_b, grad_c]:
        norm = np.linalg.norm(grad)
        if norm > 1e-8:
            grad /= norm
    
    return grad_a, grad_b, grad_c
def project_to_triangle(point, A, B, C):
    """Project point to the closest point on the triangle boundary if outside"""
    if is_inside_triangle(point, A, B, C):
        return point
    
    # Find closest point on each edge
    def closest_point_on_segment(p, a, b):
        ap = p - a
        ab = b - a
        t = np.dot(ap, ab) / np.dot(ab, ab)
        t = max(0, min(1, t))
        return a + t * ab
    
    # Check all three edges
    p1 = closest_point_on_segment(point, A, B)
    p2 = closest_point_on_segment(point, B, C)
    p3 = closest_point_on_segment(point, C, A)
    
    # Find which is closest
    d1 = np.linalg.norm(point - p1)
    d2 = np.linalg.norm(point - p2)
    d3 = np.linalg.norm(point - p3)
    
    if d1 <= d2 and d1 <= d3:
        return p1
    elif d2 <= d1 and d2 <= d3:
        return p2
    else:
        return p3
def _d_entrypoint():
    np.random.seed(42)
    A, B, C = get_unit_triangle()
    
    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        T0 = 0.05  # Increased from 0.001 for better exploration
        initial_step = 0.05
        max_iter = 1000  # Increased from 500
        restart_after = 200  # Increased from 100
        
        T = T0
        step_size = initial_step
        last_improvement = 0

        for iteration in range(max_iter):
            # Restart mechanism when stuck
            if iteration - last_improvement > restart_after:
                T = T0
                step_size = initial_step
                current = best.copy()
                current_score = best_score
                last_improvement = iteration

            # Identify ALL minimal triangles (within tolerance)
            n = 11
            min_area_val = current_score
            min_triangles = []
            tolerance = 1e-9

            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        ax, ay = current[i]
                        bx, by = current[j]
                        cx, cy = current[k]
                        area = 0.5 * abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))
                        if abs(area - min_area_val) < tolerance:
                            min_triangles.append((i, j, k))

            # If no minimal triangles found (shouldn't happen), skip
            if not min_triangles:
                continue

            # Compute combined gradients for all points involved in minimal triangles
            gradients = np.zeros_like(current)
            point_count = np.zeros(n, dtype=int)
            
            for (i, j, k) in min_triangles:
                a, b, c = current[i], current[j], current[k]
                grad_a, grad_b, grad_c = compute_area_gradient(a, b, c)
                
                gradients[i] += grad_a
                gradients[j] += grad_b
                gradients[k] += grad_c
                
                point_count[i] += 1
                point_count[j] += 1
                point_count[k] += 1

            # Normalize by count to get average gradient
            for idx in range(n):
                if point_count[idx] > 0:
                    gradients[idx] /= point_count[idx]

            candidate = current.copy()
            # Move points in gradient direction
            for idx in range(n):
                if point_count[idx] > 0:  # Only move points involved in minimal triangles
                    candidate[idx] += step_size * gradients[idx]

            # Project outside points back to triangle using improved method
            for i in range(n):
                candidate[i] = project_to_triangle(candidate[i], A, B, C)

            candidate_score = get_smallest_triangle_area(candidate)
            if candidate_score <= 0:
                continue

            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate.copy()
                    best_score = candidate_score
                    last_improvement = iteration

            # Cool down
            T *= 0.995  # Slower cooling rate
            step_size *= 0.995  # Slower step decay

        return best

    return improve

def entrypoint():
    """D's improvement of G's points, as a valid G program."""
    improve_fn = _d_entrypoint()
    improved = improve_fn(_G_POINTS.copy())
    return np.asarray(improved, dtype=np.float64)