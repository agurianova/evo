import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    def project_to_triangle(point, A, B, C):
        v0 = B - A
        v1 = C - A
        v2 = point - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        if abs(denom) < 1e-10:
            return A
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w

        if u < 0:
            u = 0
            if v + w > 0:
                v, w = v / (v + w), w / (v + w)
            else:
                v, w = 0.5, 0.5
        if v < 0:
            v = 0
            if u + w > 0:
                u, w = u / (u + w), w / (u + w)
            else:
                u, w = 0.5, 0.5
        if w < 0:
            w = 0
            if u + v > 0:
                u, v = u / (u + v), v / (u + v)
            else:
                u, v = 0.5, 0.5
        
        u = 1.0 - v - w
        return u * A + v * B + w * C

    def compute_area(a, b, c):
        return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    # Generate hexagonal lattice points with alternating row offsets
    base = B[0] - A[0]
    height = C[1]
    points_list = []
    num_rows = 4
    for row_idx in range(num_rows):
        y = row_idx * (height / (num_rows - 1))
        num_in_row = 3 if row_idx < 3 else 2
        left_x = (base * y) / (2 * height)
        right_x = base - left_x
        width = right_x - left_x
        
        # Alternate row offset for hexagonal pattern
        offset = 0.0 if row_idx % 2 == 0 else width / (2 * num_in_row)
        
        step = width / num_in_row
        for j in range(num_in_row):
            x = left_x + offset + j * step
            points_list.append([x, y])

    points = np.array(points_list)
    valid = False
    for _ in range(100):
        perturbed = points.copy()
        for i in range(11):
            dx = random.uniform(-0.005, 0.005)  # Increased perturbation range
            dy = random.uniform(-0.005, 0.005)
            perturbed[i] = points[i] + [dx, dy]
            perturbed[i] = project_to_triangle(perturbed[i], A, B, C)
        min_area = get_smallest_triangle_area(perturbed)
        if min_area > 1e-8:
            points = perturbed
            valid = True
            break

    if not valid:
        points = []
        while len(points) < 11:
            s = random.random()
            t = random.random()
            if s + t > 1:
                s = 1 - s
                t = 1 - t
            point = A * (1 - s - t) + B * s + C * t
            point = np.array(point)
            distinct = True
            for p in points:
                if np.linalg.norm(p - point) < 1e-5:
                    distinct = False
                    break
            if distinct:
                points.append(point)
        points = np.array(points)

    # Coarse-to-fine multi-scale optimization
    phases = [
        {'step_size': 0.1, 'max_iter': 200},
        {'step_size': 0.05, 'max_iter': 300},
        {'step_size': 0.01, 'max_iter': 500},
        {'step_size': 0.005, 'max_iter': 1000}
    ]
    
    best_so_far = (points.copy(), get_smallest_triangle_area(points))
    
    for phase in phases:
        step_size = phase['step_size']
        max_iter_phase = phase['max_iter']
        no_improve_count = 0
        current_min = best_so_far[1]
        points = best_so_far[0].copy()

        for iteration in range(max_iter_phase):
            current_min = get_smallest_triangle_area(points)
            improved = False

            # Gradient-based single-point moves with robust calculation
            n = 11
            min_area_val = float('inf')
            smallest_triangles = []
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        area = compute_area(points[i], points[j], points[k])
                        if area < min_area_val:
                            min_area_val = area
                            smallest_triangles = [(i, j, k)]
                        elif area == min_area_val:
                            smallest_triangles.append((i, j, k))

            candidates = []
            eps = 1e-10
            for i, j, k in smallest_triangles[:5]:  # Focus on top 5 smallest triangles
                for idx in [i, j, k]:
                    p = points[idx]
                    if idx == i:
                        other1, other2 = points[j], points[k]
                    elif idx == j:
                        other1, other2 = points[i], points[k]
                    else:
                        other1, other2 = points[i], points[j]

                    v1 = other1 - p
                    v2 = other2 - p
                    cross = v1[0] * v2[1] - v1[1] * v2[0]
                    area_val = 0.5 * abs(cross)
                    
                    if area_val < eps:
                        grad = np.array([random.uniform(-1, 1), random.uniform(-1, 1)])
                    else:
                        grad = 0.5 * np.array([other2[1] - other1[1], other1[0] - other2[0]])
                        grad_norm = np.linalg.norm(grad)
                        if grad_norm < eps:
                            grad = np.array([random.uniform(-1, 1), random.uniform(-1, 1)])
                        else:
                            grad = grad / grad_norm

                    candidate_points = points.copy()
                    candidate_points[idx] = p + step_size * grad
                    candidate_points[idx] = project_to_triangle(candidate_points[idx], A, B, C)
                    new_min = get_smallest_triangle_area(candidate_points)
                    if new_min > min_area_val:
                        candidates.append((new_min, candidate_points))

            if candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                best_candidate = candidates[0][1]
                new_min_val = candidates[0][0]
                if new_min_val > current_min:
                    points = best_candidate
                    current_min = new_min_val
                    improved = True

            # Prioritize critical pairs for two-point moves
            critical_pairs = set()
            for i, j, k in smallest_triangles[:5]:
                critical_pairs.add((min(i, j), max(i, j)))
                critical_pairs.add((min(i, k), max(i, k)))
                critical_pairs.add((min(j, k), max(j, k)))
            
            critical_pairs = list(critical_pairs)
            random.shuffle(critical_pairs)
            selected_pairs = critical_pairs[:20]
            
            # Add some random pairs for exploration
            if len(selected_pairs) < 30:
                all_pairs = [(i, j) for i in range(11) for j in range(i + 1, 11)]
                random.shuffle(all_pairs)
                selected_pairs += [p for p in all_pairs if p not in critical_pairs][:30 - len(selected_pairs)]

            for i, j in selected_pairs:
                best_candidate = None
                best_min = current_min
                for _ in range(30):
                    # Bias angles toward gradient direction
                    if (i, j) in critical_pairs:
                        # Get gradient direction for critical pairs
                        angle1 = math.atan2(grad[1], grad[0]) + random.uniform(-0.5, 0.5)
                        angle2 = angle1 + math.pi + random.uniform(-0.5, 0.5)
                    else:
                        angle1 = random.uniform(0, 2 * math.pi)
                        angle2 = random.uniform(0, 2 * math.pi)
                    
                    candidate = points.copy()

                    dx1 = step_size * math.cos(angle1)
                    dy1 = step_size * math.sin(angle1)
                    candidate[i] = points[i] + [dx1, dy1]
                    candidate[i] = project_to_triangle(candidate[i], A, B, C)

                    dx2 = step_size * math.cos(angle2)
                    dy2 = step_size * math.sin(angle2)
                    candidate[j] = points[j] + [dx2, dy2]
                    candidate[j] = project_to_triangle(candidate[j], A, B, C)

                    new_min = get_smallest_triangle_area(candidate)
                    if new_min > best_min:
                        best_min = new_min
                        best_candidate = candidate

                if best_candidate is not None and best_min > current_min:
                    points = best_candidate
                    current_min = best_min
                    improved = True
                    break

            # Update best and check stagnation
            if current_min > best_so_far[1]:
                best_so_far = (points.copy(), current_min)
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Dynamic stagnation threshold
            improvement_rate = (current_min - best_so_far[1]) / (iteration + 1)
            stagnation_threshold = max(50, int(100 / (abs(improvement_rate) + 1e-5)))
            
            # Stagnation restart
            if no_improve_count >= stagnation_threshold:
                points = best_so_far[0].copy()
                for i in range(11):
                    points[i] += np.array([
                        random.uniform(-0.01, 0.01),
                        random.uniform(-0.01, 0.01)
                    ])
                    points[i] = project_to_triangle(points[i], A, B, C)
                current_min = get_smallest_triangle_area(points)
                no_improve_count = 0

            # Early termination if we've reached a good solution
            if best_so_far[1] >= 0.0365:
                break

    return best_so_far[0]