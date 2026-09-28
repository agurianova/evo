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
        initial_temperature = 0.1  # Increased from 0.01
        cooling_rate = 0.95  # Changed from 0.99
        step_decay = 0.99
        min_step = 0.001
        stagnation_limit = 100
        tol = 1e-5
        num_restarts = 5
        restart_perturbation = 0.05  # Increased from 0.01

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
                previous_score = current_score  # Track for stagnation handling

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

                # === REPLACED DIRECTION COMPUTATION WITH FINITE DIFFERENCE GRADIENT ===
                step_size_fd = 0.001  # Finite difference step size

                # Evaluate in +x direction
                candidate_xp = current.copy()
                candidate_xp[point_idx] += [step_size_fd, 0]
                if is_inside_triangle(candidate_xp[point_idx], A, B, C):
                    score_xp = get_smallest_triangle_area(candidate_xp)
                else:
                    score_xp = -np.inf

                # Evaluate in -x direction
                candidate_xm = current.copy()
                candidate_xm[point_idx] += [-step_size_fd, 0]
                if is_inside_triangle(candidate_xm[point_idx], A, B, C):
                    score_xm = get_smallest_triangle_area(candidate_xm)
                else:
                    score_xm = -np.inf

                # Evaluate in +y direction
                candidate_yp = current.copy()
                candidate_yp[point_idx] += [0, step_size_fd]
                if is_inside_triangle(candidate_yp[point_idx], A, B, C):
                    score_yp = get_smallest_triangle_area(candidate_yp)
                else:
                    score_yp = -np.inf

                # Evaluate in -y direction
                candidate_ym = current.copy()
                candidate_ym[point_idx] += [0, -step_size_fd]
                if is_inside_triangle(candidate_ym[point_idx], A, B, C):
                    score_ym = get_smallest_triangle_area(candidate_ym)
                else:
                    score_ym = -np.inf

                # Compute gradients with boundary handling
                if score_xp == -np.inf and score_xm == -np.inf:
                    grad_x = 0.0
                elif score_xp == -np.inf:
                    grad_x = -1.0  # Push inward from right boundary
                elif score_xm == -np.inf:
                    grad_x = 1.0   # Push inward from left boundary
                else:
                    grad_x = (score_xp - score_xm) / (2 * step_size_fd)

                if score_yp == -np.inf and score_ym == -np.inf:
                    grad_y = 0.0
                elif score_yp == -np.inf:
                    grad_y = -1.0  # Push inward from top boundary
                elif score_ym == -np.inf:
                    grad_y = 1.0   # Push inward from bottom boundary
                else:
                    grad_y = (score_yp - score_ym) / (2 * step_size_fd)

                # Normalize gradient direction
                grad_norm = np.linalg.norm([grad_x, grad_y])
                if grad_norm > 1e-8:
                    direction = np.array([grad_x, grad_y]) / grad_norm
                else:
                    direction = np.zeros(2)

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

                # === STAGNATION COUNTER RESET ON ANY IMPROVEMENT ===
                if current_score > previous_score:
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