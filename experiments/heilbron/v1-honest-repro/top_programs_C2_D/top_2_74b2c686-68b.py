from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def triangle_area(a, b, c):
    return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        n = points.shape[0]
        max_iter = 200
        initial_step = 0.1
        initial_temperature = 0.01
        cooling_rate = 0.99
        step_decay = 0.99
        min_step = 0.001
        stagnation_limit = 100
        tol = 1e-5
        num_restarts = 5
        restart_perturbation = 0.01

        global_best = points.copy()
        global_best_score = get_smallest_triangle_area(global_best)

        for restart in range(num_restarts):
            # Start from global_best with perturbation
            start = global_best.copy()
            for i in range(n):
                for attempt in range(5):
                    pert = np.random.uniform(-restart_perturbation, restart_perturbation, size=2)
                    new_pt = global_best[i] + pert
                    if is_inside_triangle(new_pt, A, B, C):
                        start[i] = new_pt
                        break

            current = start.copy()
            current_score = get_smallest_triangle_area(current)
            chain_best = current.copy()
            chain_best_score = current_score

            step = initial_step
            temperature = initial_temperature
            stagnation_counter = 0

            for it in range(max_iter):
                # Find all minimal triangles within tolerance
                min_area = float('inf')
                triangles = []
                for i in range(n):
                    for j in range(i + 1, n):
                        for k in range(j + 1, n):
                            area = triangle_area(current[i], current[j], current[k])
                            if area < min_area - tol:
                                min_area = area
                                triangles = [(i, j, k, area)]
                            elif abs(area - min_area) <= tol:
                                triangles.append((i, j, k, area))

                if len(triangles) == 0:
                    continue

                # Build point frequency and triangle references
                point_count = [0] * n
                point_triangles = [[] for _ in range(n)]
                for (i, j, k, area) in triangles:
                    point_count[i] += 1
                    point_count[j] += 1
                    point_count[k] += 1
                    point_triangles[i].append((i, j, k, area))
                    point_triangles[j].append((i, j, k, area))
                    point_triangles[k].append((i, j, k, area))

                total = sum(point_count)
                if total == 0:
                    continue

                # Select point proportional to frequency in minimal triangles
                probs = [c / total for c in point_count]
                point_idx = np.random.choice(n, p=probs)

                # Compute average direction from all triangles containing this point
                total_dir = np.zeros(2)
                num_tri = 0
                for tri in point_triangles[point_idx]:
                    i, j, k, area = tri
                    pts = [current[i], current[j], current[k]]
                    idx_in_tri = [i, j, k].index(point_idx)
                    
                    if idx_in_tri == 0:
                        base = pts[2] - pts[1]
                        apex = pts[0]
                        ref_point = pts[1]
                    elif idx_in_tri == 1:
                        base = pts[2] - pts[0]
                        apex = pts[1]
                        ref_point = pts[0]
                    else:
                        base = pts[1] - pts[0]
                        apex = pts[2]
                        ref_point = pts[0]

                    perp = np.array([-base[1], base[0]])
                    norm = np.linalg.norm(perp)
                    if norm < 1e-8:
                        dir_vec = np.zeros(2)
                    else:
                        perp = perp / norm
                        proj = np.dot(apex - ref_point, perp)
                        dir_vec = perp * np.sign(proj)
                    total_dir += dir_vec
                    num_tri += 1

                direction = total_dir / num_tri if num_tri > 0 else np.zeros(2)

                # Generate move with temperature-scaled noise
                noise_scale = step * 0.2 * (temperature / initial_temperature)
                noise = np.random.normal(0, 1, size=2) * noise_scale
                move = direction * step + noise

                candidate = current.copy()
                candidate[point_idx] += move

                # Check containment for moved point
                if not is_inside_triangle(candidate[point_idx], A, B, C):
                    accept = False
                else:
                    candidate_score = get_smallest_triangle_area(candidate)
                    delta = candidate_score - current_score
                    if delta > 0:
                        accept = True
                    else:
                        if temperature > 1e-5:
                            prob = np.exp(delta / temperature)
                        else:
                            prob = 0.0
                        accept = np.random.rand() < prob

                if accept:
                    current = candidate
                    current_score = candidate_score

                # Update chain best
                if current_score > chain_best_score:
                    chain_best = current.copy()
                    chain_best_score = current_score
                    stagnation_counter = 0
                else:
                    stagnation_counter += 1

                # Update temperature and step
                temperature *= cooling_rate
                if not accept:
                    step = max(min_step, step * step_decay)

                # Early termination
                if stagnation_counter > stagnation_limit:
                    break

            # Update global best after chain
            if chain_best_score > global_best_score:
                global_best = chain_best.copy()
                global_best_score = chain_best_score

        return global_best

    return improve