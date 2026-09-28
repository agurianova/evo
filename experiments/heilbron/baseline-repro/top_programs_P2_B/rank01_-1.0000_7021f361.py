from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()
    centroid = (A + B + C) / 3.0

    def project_to_segment(p, a, b):
        ap = p - a
        ab = b - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
        t = np.clip(t, 0.0, 1.0)
        return a + t * ab

    def project_to_triangle(p, A, B, C):
        if is_inside_triangle(p, A, B, C):
            return p
        proj_ab = project_to_segment(p, A, B)
        proj_bc = project_to_segment(p, B, C)
        proj_ca = project_to_segment(p, C, A)
        d_ab = np.linalg.norm(p - proj_ab)
        d_bc = np.linalg.norm(p - proj_bc)
        d_ca = np.linalg.norm(p - proj_ca)
        if d_ab <= d_bc and d_ab <= d_ca:
            p_proj = proj_ab
        elif d_bc <= d_ab and d_bc <= d_ca:
            p_proj = proj_bc
        else:
            p_proj = proj_ca
        return p_proj

    def improve(points):
        total_iters = 1000
        initial_step = 0.05
        restart_threshold_base = 150
        restart_duration_base = 100
        tolerance = 1e-10

        initial_min_area = get_smallest_triangle_area(points)
        initial_temp = max(0.001, 3.0 * (0.0365 - initial_min_area))

        best = points.copy()
        best_score = initial_min_area
        current = best.copy()
        current_score = best_score
        last_improvement_iter = 0
        restart_countdown = 0
        n = points.shape[0]

        for i_iter in range(total_iters):
            current_temp = initial_temp * (1 - i_iter / total_iters)
            base_step = initial_step * (1 - i_iter / total_iters)
            
            if restart_countdown > 0:
                step_size = 5 * base_step
                restart_countdown -= 1
            else:
                step_size = base_step

            factor = 1.15
            critical_threshold = current_score * factor

            triangles = []
            for i1 in range(n):
                for i2 in range(i1+1, n):
                    for i3 in range(i2+1, n):
                        x1, y1 = current[i1]
                        x2, y2 = current[i2]
                        x3, y3 = current[i3]
                        area = 0.5 * abs((x2-x1)*(y3-y1) - (x3-x1)*(y2-y1))
                        triangles.append((area, (i1, i2, i3)))
            
            critical_triangles = [tri for tri in triangles if tri[0] <= critical_threshold]
            if len(critical_triangles) > 10:
                critical_triangles = sorted(critical_triangles, key=lambda x: x[0])[:10]
            if not critical_triangles:
                critical_triangles = sorted(triangles, key=lambda x: x[0])[:3]

            candidate = current.copy()
            moved_indices = []

            # Gradient-based move removed (set probability to 0.0)
            if np.random.rand() < 0.0 and critical_triangles:
                tri = critical_triangles[0]
                min_tri = tri[1]
                idx_to_move = np.random.choice(min_tri)
                fixed_indices = [i for i in min_tri if i != idx_to_move]
                if len(fixed_indices) == 2:
                    p2 = current[fixed_indices[0]]
                    p3 = current[fixed_indices[1]]
                    p1 = current[idx_to_move]
                    edge = p3 - p2
                    normal = np.array([-edge[1], edge[0]])
                    norm_normal = np.linalg.norm(normal)
                    if norm_normal > 1e-10:
                        normal_unit = normal / norm_normal
n                        v = p1 - p2
                        height_sign = np.dot(v, normal_unit)
                        if height_sign == 0:
                            direction = normal_unit
                        else:
                            direction = normal_unit * (1.0 if height_sign > 0 else -1.0)
                        candidate[idx_to_move] = p1 + step_size * direction
                        moved_indices = [idx_to_move]
                    else:
                        angle = np.random.uniform(0, 2*np.pi)
                        dx = step_size * np.cos(angle)
                        dy = step_size * np.sin(angle)
                        candidate[idx_to_move] = p1 + np.array([dx, dy])
                        moved_indices = [idx_to_move]
                else:
                    idx_to_move = np.random.randint(n)
                    angle = np.random.uniform(0, 2*np.pi)
                    dx = step_size * np.cos(angle)
                    dy = step_size * np.sin(angle)
                    candidate[idx_to_move] = current[idx_to_move] + np.array([dx, dy])
                    moved_indices = [idx_to_move]
            else:
                if np.random.rand() < 0.1:
                    indices_to_move = [np.random.randint(n)]
                else:
                    tri = critical_triangles[np.random.randint(len(critical_triangles))]
                    min_tri = tri[1]
                    k = np.random.choice([1, 2, 3], p=[0.6, 0.3, 0.1])
                    indices_to_move = np.random.choice(min_tri, size=k, replace=False)
                for idx in indices_to_move:
                    angle = np.random.uniform(0, 2*np.pi)
                    dx = step_size * np.cos(angle)
                    dy = step_size * np.sin(angle)
                    candidate[idx] = current[idx] + np.array([dx, dy])
                moved_indices = indices_to_move

            for idx in moved_indices:
                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

            score = get_smallest_triangle_area(candidate)
            if score < tolerance:
                continue

            delta = score - current_score
            if delta > 0:
                accept = True
            else:
                if current_temp < 1e-10:
                    accept = False
                else:
                    p_accept = np.exp(delta / current_temp)
                    if np.random.rand() < p_accept:
                        accept = True
                    else:
                        accept = False

            if accept:
                current = candidate
                current_score = score

                if score > best_score:
                    best = candidate
                    best_score = score
                    last_improvement_iter = i_iter

            current_restart_threshold = max(50, restart_threshold_base * (1 - i_iter / total_iters))
            current_restart_duration = max(10, restart_duration_base * (1 - i_iter / total_iters))
            
            if i_iter - last_improvement_iter > current_restart_threshold and restart_countdown == 0:
                current = best.copy()
                current_score = best_score
                restart_countdown = int(current_restart_duration)
                last_improvement_iter = i_iter

        return best

    return improve