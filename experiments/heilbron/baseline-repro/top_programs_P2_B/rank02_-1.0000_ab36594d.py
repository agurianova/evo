from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()
    centroid = (A + B + C) / 3.0
    len_ab = np.linalg.norm(B - A)
    len_bc = np.linalg.norm(C - B)
    len_ca = np.linalg.norm(A - C)

    def improve(points):
        total_iters = 500
        initial_temp_value = 0.05
        initial_temp = initial_temp_value * np.log(2) / np.log(total_iters + 1)
        initial_step = 0.15
        restart_threshold = 40
        restart_duration = 50
        restart_step = 0.25
        tolerance = 1e-10

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        last_improvement_iter = 0
        restart_countdown = 0
        n = points.shape[0]

        for i_iter in range(total_iters):
            current_temp = initial_temp * np.log(total_iters + 1) / np.log(i_iter + 2)
            base_step = initial_step * (1 - i_iter / total_iters)
            if restart_countdown > 0:
                step_size = restart_step
                restart_countdown -= 1
            else:
                step_size = base_step

            top_triangles = []
            for i1 in range(n):
                for i2 in range(i1 + 1, n):
                    for i3 in range(i2 + 1, n):
                        x1, y1 = current[i1]
                        x2, y2 = current[i2]
                        x3, y3 = current[i3]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if len(top_triangles) < 5:
                            top_triangles.append((area, (i1, i2, i3)))
                            top_triangles.sort(key=lambda x: x[0])
                        else:
                            if area < top_triangles[-1][0]:
                                top_triangles[-1] = (area, (i1, i2, i3))
                                top_triangles.sort(key=lambda x: x[0])

            if not top_triangles:
                continue

            idx_choice = np.random.randint(0, len(top_triangles))
            min_tri = top_triangles[idx_choice][1]

            k = np.random.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
            indices_to_move = np.random.choice(min_tri, size=k, replace=False)

            candidate = current.copy()
            for idx in indices_to_move:
                # Geometry-aware directional move
                tri_points = list(min_tri)
                tri_points.remove(idx)
                p1, p2 = current[tri_points[0]], current[tri_points[1]]
                a = current[idx]
                base = p1 - p2
                perp = np.array([base[1], -base[0]])
                perp_norm = np.linalg.norm(perp)
                if perp_norm < 1e-10:
                    angle = np.random.uniform(0, 2 * np.pi)
                    dx = step_size * np.cos(angle)
                    dy = step_size * np.sin(angle)
                    move = np.array([dx, dy])
                else:
                    perp = perp / perp_norm
                    signed_area = 0.5 * ((p1[0] - a[0]) * (p2[1] - a[1]) - (p2[0] - a[0]) * (p1[1] - a[1]))
                    direction = perp if signed_area >= 0 else -perp
                    move = step_size * direction
                candidate[idx] = a + move

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
                        return proj_ab
                    elif d_bc <= d_ab and d_bc <= d_ca:
                        return proj_bc
                    else:
                        return proj_ca

                candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

                p = candidate[idx]
                area_abp = 0.5 * abs((B[0] - A[0]) * (p[1] - A[1]) - (B[1] - A[1]) * (p[0] - A[0]))
                area_bcp = 0.5 * abs((C[0] - B[0]) * (p[1] - B[1]) - (C[1] - B[1]) * (p[0] - B[0]))
                area_cap = 0.5 * abs((A[0] - C[0]) * (p[1] - C[1]) - (A[1] - C[1]) * (p[0] - C[0]))
                d_ab = (2 * area_abp) / len_ab
                d_bc = (2 * area_bcp) / len_bc
                d_ca = (2 * area_cap) / len_ca
                min_dist = min(d_ab, d_bc, d_ca)

                if min_dist < 0.0001:
                    dir_vec = centroid - p
                    dir_norm = np.linalg.norm(dir_vec)
                    if dir_norm > 1e-10:
                        step = min(0.001, dir_norm * 0.5)
                        p = p + (step / dir_norm) * dir_vec
                    candidate[idx] = p

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

            if i_iter - last_improvement_iter > restart_threshold and restart_countdown == 0:
                current = best.copy()
                current_score = best_score
                restart_countdown = restart_duration
                last_improvement_iter = i_iter

            if i_iter - last_improvement_iter > 400 and current_temp < 1e-5:
                break

        return best

    return improve