import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.stats import qmc

np.random.seed(42)
random.seed(42)

def triangle_area(p, q, r):
    return 0.5 * abs((q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0]))

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    side_length = np.linalg.norm(B - A)
    n_starts = 100
    best_config = None
    best_min_area = -1

    # Define adversarial validation function
    def is_resistant(config, n_tests=5, perturbation_mag=0.001 * side_length):
        current_min = get_smallest_triangle_area(config)
        for _ in range(n_tests):
            idx = random.randint(0, 10)
            angle = random.uniform(0, 2 * np.pi)
            dx = perturbation_mag * np.cos(angle)
            dy = perturbation_mag * np.sin(angle)
            new_config = config.copy()
            new_config[idx] += np.array([dx, dy])
            if not is_inside_triangle(new_config[idx], A, B, C):
                continue
            new_min = get_smallest_triangle_area(new_config)
            if new_min > current_min:
                return False
        return True

    for start in range(n_starts):
        # Generate 20 candidate points using Sobol
        sobol = qmc.Sobol(d=2, scramble=True, seed=start)
        sample = sobol.random(n=20)
        r1 = sample[:, 0]
        r2 = sample[:, 1]
        u = 1 - np.sqrt(r1)
        v = r2 * np.sqrt(r1)
        candidates = A + u[:, None] * (B - A) + v[:, None] * (C - A)

        # Farthest-point traversal to select 11 points
        selected = []
        remaining = list(range(20))
        # Start with random point
        idx0 = random.choice(remaining)
        selected.append(idx0)
        remaining.remove(idx0)
        
        for _ in range(10):
            max_min_dist = -1
            next_idx = None
            for i in remaining:
                min_dist = float('inf')
                for j in selected:
                    d = np.linalg.norm(candidates[i] - candidates[j])
                    if d < min_dist:
                        min_dist = d
                if min_dist > max_min_dist:
                    max_min_dist = min_dist
                    next_idx = i
            selected.append(next_idx)
            remaining.remove(next_idx)
        
        points = candidates[selected].copy()

        # Apply tiny asymmetric perturbation (1% of side length)
        perturbation_mag = 0.01 * side_length
        for i in range(11):
            angle = random.uniform(0, 2 * np.pi)
            dx = perturbation_mag * np.cos(angle)
            dy = perturbation_mag * np.sin(angle)
            new_point = points[i] + np.array([dx, dy])
            if is_inside_triangle(new_point, A, B, C):
                points[i] = new_point

        # Force-directed repulsion for better spacing
        max_repulsion_iter = 100
        for repel_iter in range(max_repulsion_iter):
            forces = np.zeros((11, 2))
            # Compute repulsive forces between all point pairs
            for i in range(11):
                for j in range(i+1, 11):
                    diff = points[i] - points[j]
                    dist_sq = np.dot(diff, diff)
                    if dist_sq < 1e-10:
                        direction = np.random.uniform(-1, 1, 2)
                        direction /= np.linalg.norm(direction) + 1e-8
                        forces[i] += direction
                        forces[j] -= direction
                    else:
                        force_vec = diff / (dist_sq + 1e-8)
                        forces[i] += force_vec
                        forces[j] -= force_vec

            # Apply forces with decaying step size
            step_size_repel = 0.001 * side_length / (repel_iter + 1)
            for i in range(11):
                force = forces[i]
                force_norm = np.linalg.norm(force)
                if force_norm > 1e-5:
                    direction = force / force_norm
                    new_point = points[i] + direction * step_size_repel
                    if is_inside_triangle(new_point, A, B, C):
                        points[i] = new_point

        current_min_area = get_smallest_triangle_area(points)
        step_size = 0.05
        no_improve_count = 0
        max_steps = 100000
        step = 0

        while step < max_steps:
            step += 1
            improved = False

            # Dynamic exploration ratio
            random_ratio = min(0.9, 0.3 + 0.005 * no_improve_count)
            if random.random() < (1 - random_ratio):  # Targeted move
                # Find top-5 smallest triangles
                triangles = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            area = triangle_area(points[i], points[j], points[k])
                            triangles.append((area, i, j, k))
                triangles.sort(key=lambda x: x[0])
                top_k = triangles[:5]

                # Compute composite gradient for each point
                grads = np.zeros((11, 2))
                for idx, (area, i, j, k) in enumerate(top_k):
                    P, Q, R = points[i], points[j], points[k]
                    signed_area = 0.5 * ((Q[0]-P[0])*(R[1]-P[1]) - (Q[1]-P[1])*(R[0]-P[0]))
                    sign = 1.0 if signed_area > 0 else -1.0

                    grad_P = np.array([Q[1] - R[1], R[0] - Q[0]]) * sign
                    grad_Q = np.array([R[1] - P[1], P[0] - R[0]]) * sign
                    grad_R = np.array([P[1] - Q[1], Q[0] - P[0]]) * sign

                    weight = 1.0 / (idx + 1)
                    grads[i] += weight * grad_P
                    grads[j] += weight * grad_Q
                    grads[k] += weight * grad_R

                # Apply step without normalization
                step_size_grad = step_size * 0.5
                total_step = grads * step_size_grad
                old_points = points.copy()
                points += total_step

                # Check validity
                valid_move = True
                for i in range(11):
                    if not is_inside_triangle(points[i], A, B, C):
                        valid_move = False
                        break

                if valid_move:
                    new_min_area = get_smallest_triangle_area(points)
                    if new_min_area > current_min_area:
                        if is_resistant(points):
                            current_min_area = new_min_area
                            improved = True
                            no_improve_count = 0
                            step_size = min(0.1, step_size * 1.1)  # Step size recovery
                        else:
                            points = old_points.copy()
                    else:
                        points = old_points.copy()
                else:
                    points = old_points.copy()

            else:  # Random perturbation
                k = random.randint(1, min(5, 11))
                indices_to_perturb = random.sample(range(11), k)

                old_points = []
                for i in indices_to_perturb:
                    old_points.append((i, points[i].copy()))

                step_size_per_point = step_size / np.sqrt(k)
                valid_move = True
                for (i, old_p) in old_points:
                    direction = np.random.uniform(-1, 1, 2)
                    if np.linalg.norm(direction) < 1e-10:
                        direction = np.array([1.0, 0.0])
                    direction = direction / np.linalg.norm(direction) * step_size_per_point
                    new_point = old_p + direction

                    if not is_inside_triangle(new_point, A, B, C):
                        valid_move = False
                        break

                    points[i] = new_point

                if not valid_move:
                    for (i, old_p) in old_points:
                        points[i] = old_p
                else:
                    new_min_area = get_smallest_triangle_area(points)
                    if new_min_area > current_min_area:
                        if is_resistant(points):
                            current_min_area = new_min_area
                            improved = True
                            no_improve_count = 0
                            step_size = min(0.1, step_size * 1.1)  # Step size recovery
                        else:
                            for (i, old_p) in old_points:
                                points[i] = old_p
                    else:
                        for (i, old_p) in old_points:
                            points[i] = old_p

            if not improved:
                no_improve_count += 1
                if no_improve_count % 50 == 0 and step_size > 1e-5:
                    step_size *= 0.95
            else:
                no_improve_count = 0

            # Adaptive termination
            if step_size < 1e-5 and no_improve_count >= 100:
                break

        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config