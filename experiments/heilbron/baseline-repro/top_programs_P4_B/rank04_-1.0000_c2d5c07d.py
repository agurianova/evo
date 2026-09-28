import numpy as np
import hashlib
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle

def entrypoint():
    A, B, C = get_unit_triangle()

    def triangle_area(a, b, c):
        return 0.5 * abs((a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1])))

    def get_top_k_triplets(points, k=3):
        n = len(points)
        triplets = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = triangle_area(points[i], points[j], points[k])
                    triplets.append((area, (i, j, k)))
        triplets.sort(key=lambda x: x[0])
        return triplets[:k]

    def gradient_for_point_in_triplet(point_idx, triplet, points):
        idx0, idx1, idx2 = triplet
        a, b, c = points[idx0], points[idx1], points[idx2]
        f_val = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        sign_f = 1 if f_val >= 0 else -1

        if point_idx == idx0:
            grad = np.array([b[1]-c[1], c[0]-b[0]])
        elif point_idx == idx1:
            grad = np.array([c[1]-a[1], a[0]-c[0]])
        else:
            grad = np.array([a[1]-b[1], b[0]-a[0]])

        norm_dir = np.linalg.norm(grad)
        if norm_dir < 1e-10:
            return np.array([1.0, 0.0])
        return sign_f * grad / norm_dir

    def improve(points: np.ndarray) -> np.ndarray:
        seed = int.from_bytes(hashlib.sha256(points.tobytes()).digest()[:4], 'little') % (2**32)
        np.random.seed(seed)

        total_iterations = 500
        initial_temperature = 0.05

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score

        deficit = max(0, 0.0365 - best_score)
        # CHANGED: Logarithmic scaling instead of fourth root to maintain meaningful steps near optimum
        current_step = max(0.001, 0.015 * (1.0 + np.log(1.0 + deficit / 0.0365)))

        best_score_streak = 0
        success_window = []
        stagnation_counter = 0
        min_success_rate = 0.1
        stagnation_threshold = 50

        for iteration in range(total_iterations):
            if best_score_streak >= 400:
                break

            # CHANGED: Adaptive k-value based on current_score
            k_val = max(3, min(8, int(5 + 3 * (0.0365 - current_score) / 0.0365)))
            top_triplets = get_top_k_triplets(current, k=k_val)
            small_points = set()
            for _, triplet in top_triplets:
                small_points.update(triplet)

            # Time decay for gradient weights
            time_decay = 1.0 - 0.5 * (iteration / total_iterations)

            # CHANGED: Adaptive jump mechanism based on success rate instead of fixed iteration count
            if len(success_window) >= stagnation_threshold:
                recent_success_rate = sum(success_window[-stagnation_threshold:]) / stagnation_threshold
n                if recent_success_rate < min_success_rate:
                    stagnation_counter += 1
                else:
                    stagnation_counter = 0
            
            if stagnation_counter >= stagnation_threshold:
                top_triplets_jump = get_top_k_triplets(current, k=5)
                small_points_jump = set()
                for _, triplet in top_triplets_jump:
                    small_points_jump.update(triplet)
                if small_points_jump:
                    idx = np.random.choice(list(small_points_jump))
                else:
                    idx = np.random.randint(0, 11)
                direction = np.random.normal(0, 1, size=2)
                norm_dir = np.linalg.norm(direction)
                if norm_dir < 1e-10:
                    direction = np.array([1.0, 0.0])
                else:
                    direction = direction / norm_dir
                perturbation = 0.15 * direction
                new_point = current[idx] + perturbation
                max_attempts = 5
                attempt = 0
                while attempt < max_attempts and not is_inside_triangle(new_point, A, B, C):
                    step_fraction = 0.5 ** (attempt + 1)
                    new_point = current[idx] + step_fraction * perturbation
                    attempt += 1
                if not is_inside_triangle(new_point, A, B, C):
                    new_point = current[idx]
                candidate = current.copy()
                candidate[idx] = new_point
            else:
                # CHANGED: Minimum exploration probability of 0.05 to prevent zero exploration near optimum
                exploration_prob = 0.05 + 0.45 * min(1.0, best_score_streak / 300.0)
                exploration_prob = min(0.5, max(0.05, exploration_prob))

                if np.random.rand() < exploration_prob:
                    all_indices = set(range(11))
                    non_triplet_indices = list(all_indices - small_points)
                    if non_triplet_indices:
                        chosen_indices = [np.random.choice(non_triplet_indices)]
                    else:
                        chosen_indices = [np.random.randint(0, 11)]
                else:
                    r = np.random.rand()
                    if r < 0.15:
                        num_points = 3
                    elif r < 0.65:
                        num_points = 2
                    else:
                        num_points = 1
                    chosen_indices = np.random.choice(list(small_points), num_points, replace=False)

                candidate = current.copy()
                for idx in chosen_indices:
                    if idx in small_points:
                        total_grad = np.zeros(2)
                        total_weight = 0.0
                        for area, triplet in top_triplets:
                            if idx in triplet:
                                grad = gradient_for_point_in_triplet(idx, triplet, current)
                                weight = min(1000.0, 1.0 / (area + 1e-10)**2) * time_decay + 1e-5
                                total_grad += weight * grad
                                total_weight += weight
                        if total_weight > 0:
                            direction = total_grad / total_weight
                        else:
                            direction = np.random.normal(0, 1, size=2)
                            norm_dir = np.linalg.norm(direction)
                            direction = direction / norm_dir if norm_dir > 1e-10 else np.array([1.0, 0.0])
                        perturbation = current_step * direction
                    else:
                        perturbation = current_step * np.random.normal(0, 1, size=2)

                    new_point = candidate[idx] + perturbation
                    max_attempts = 5
                    attempt = 0
                    while attempt < max_attempts and not is_inside_triangle(new_point, A, B, C):
                        step_fraction = 0.5 ** (attempt + 1)
                        new_point = candidate[idx] + step_fraction * perturbation
                        attempt += 1
                    
                    if not is_inside_triangle(new_point, A, B, C):
                        new_point = candidate[idx]
                    
                    candidate[idx] = new_point

            candidate_score = get_smallest_triangle_area(candidate)

            success = 1 if candidate_score > current_score else 0
            success_window.append(success)
            if len(success_window) > 50:
                success_window.pop(0)
            success_rate = sum(success_window) / len(success_window) if success_window else 0

            # Enhanced step size adaptation
            if success_rate > 0.4:
                current_step = min(0.05, current_step * 1.2)
            elif success_rate < 0.1:
                current_step = max(0.001, current_step * 0.8)

            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                best_score_streak = 0
            else:
                best_score_streak += 1

            delta = candidate_score - current_score
            if delta > 0:
                current = candidate
                current_score = candidate_score
            else:
                # CHANGED: Slower temperature decay with minimum temperature floor
                T = max(0.01, initial_temperature * (1 - 0.5 * success_rate) * (1 - iteration / total_iterations) ** 0.5)
                if T > 0 and np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = candidate_score

        return best

    return improve