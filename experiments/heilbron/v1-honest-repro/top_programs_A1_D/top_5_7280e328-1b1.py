from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def cartesian_to_barycentric(point, A, B, C):
    # Convert Cartesian coordinates to barycentric coordinates
    v0 = B - A
    v1 = C - A
    v2 = point - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    return np.array([u, v, w])

def barycentric_to_cartesian(bary, A, B, C):
    # Convert barycentric coordinates to Cartesian coordinates
    u, v, w = bary
    return u * A + v * B + w * C

def get_perpendicular_direction(p1, p2, p3):
    # Get outward perpendicular direction from p1 relative to edge p2-p3
    edge = p3 - p2
    normal = np.array([-edge[1], edge[0]])
    if np.dot(normal, p1 - (p2 + p3)/2) < 0:
        normal = -normal
    return normal / np.linalg.norm(normal)

def entrypoint():
    A, B, C = get_unit_triangle()
    rs = np.random.RandomState(42)

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        best = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_score = current_score

        # Fixed temperature based on domain size, not current score
        initial_temperature = 0.01
        temperature = initial_temperature
        cooling_rate = 0.999
        base_step = 0.1
        max_iterations = 10000
        stagnation_threshold = 1000
        stagnation_count = 0
        max_stagnation_resets = 3
        stagnation_resets = 0

        # Convert all points to barycentric coordinates for internal representation
        bary_points = np.array([cartesian_to_barycentric(p, A, B, C) for p in current])

        def triangle_area(a, b, c):
            return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

        def perturb(bary_point_set, cartesian_points, current_score_val):
            n = bary_point_set.shape[0]
            critical_set = set()
            critical_triangles = []
            
            # Identify critical triangles and points
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        a = triangle_area(cartesian_points[i], cartesian_points[j], cartesian_points[k])
                        if a <= current_score_val + 1e-10:
                            critical_set.update([i, j, k])
                            critical_triangles.append((i, j, k))

            if not critical_set:
                critical_set = set(range(n))

            # Always try targeted movement for bottleneck triangles first
            if critical_triangles and rs.rand() < 0.7:
                # Pick a random critical triangle
                i, j, k = critical_triangles[rs.randint(len(critical_triangles))]
                p1, p2, p3 = cartesian_points[i], cartesian_points[j], cartesian_points[k]
                
                # Compute outward perpendicular directions
                dir_i = get_perpendicular_direction(p1, p2, p3)
                dir_j = get_perpendicular_direction(p2, p1, p3)
                dir_k = get_perpendicular_direction(p3, p1, p2)
                
                # Create candidate by moving points in outward directions
                candidate_bary = bary_point_set.copy()
                step = 0.02 * (0.0365 - current_score_val)  # Scale by how far from target we are
                
                # Move each point in its outward direction
                new_p1 = p1 + dir_i * step
                new_p2 = p2 + dir_j * step
                new_p3 = p3 + dir_k * step
                
                # Convert back to barycentric if inside, otherwise use reflection
                if is_inside_triangle(new_p1, A, B, C):
                    candidate_bary[i] = cartesian_to_barycentric(new_p1, A, B, C)
                if is_inside_triangle(new_p2, A, B, C):
                    candidate_bary[j] = cartesian_to_barycentric(new_p2, A, B, C)
                if is_inside_triangle(new_p3, A, B, C):
                    candidate_bary[k] = cartesian_to_barycentric(new_p3, A, B, C)
                
                return candidate_bary

            # Fallback to random perturbation of critical points
            k_val = min(5, len(critical_set))  # Increased from 3 to 5
            critical_list = list(critical_set)
            indices = rs.choice(critical_list, size=k_val, replace=False)

            candidate_bary = bary_point_set.copy()
            step_size = base_step * temperature

            for idx in indices:
                # Generate perturbation in barycentric space (ensures we stay in triangle)
                perturbation = rs.normal(0, step_size, size=3)
                new_bary = candidate_bary[idx] + perturbation
                
                # Project back to simplex (u+v+w=1) and ensure non-negative
                new_bary = np.maximum(new_bary, 0)
                new_bary /= new_bary.sum()
                
                candidate_bary[idx] = new_bary

            return candidate_bary

        for iteration in range(max_iterations):
            # Convert current barycentric points to Cartesian for evaluation
            cartesian_current = np.array([barycentric_to_cartesian(b, A, B, C) for b in bary_points])
            
            # Generate candidate in barycentric space
            candidate_bary = perturb(bary_points, cartesian_current, current_score)
            
            # Convert to Cartesian for evaluation
            candidate_cartesian = np.array([barycentric_to_cartesian(b, A, B, C) for b in candidate_bary])
            candidate_score = get_smallest_triangle_area(candidate_cartesian)

            if candidate_score > best_score:
                best = candidate_cartesian.copy()
                best_score = candidate_score
                bary_points = candidate_bary.copy()
                stagnation_count = 0
            else:
                stagnation_count += 1

            if candidate_score > current_score:
                bary_points = candidate_bary.copy()
                current_score = candidate_score
            else:
                delta = candidate_score - current_score
                if rs.rand() < np.exp(delta / temperature):
                    bary_points = candidate_bary.copy()
                    current_score = candidate_score

            temperature *= cooling_rate

            # Stagnation recovery: reset temperature instead of terminating
            if stagnation_count >= stagnation_threshold:
                if stagnation_resets < max_stagnation_resets:
                    temperature = initial_temperature
                    stagnation_count = 0
                    stagnation_resets += 1
                # Don't break, continue searching

        # Convert final barycentric points to Cartesian
        final_points = np.array([barycentric_to_cartesian(b, A, B, C) for b in bary_points])
        return final_points

    return improve