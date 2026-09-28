import numpy as np
import hashlib
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle

def entrypoint():
    A, B, C = get_unit_triangle()

    def signed_area(a, b, c):
        return 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    def improve(points: np.ndarray) -> np.ndarray:
        base_seed = int.from_bytes(hashlib.sha256(points.tobytes()).digest()[:4], 'little') % (2**32)
        
        # Multiple restarts to avoid local optima
        num_restarts = 5
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)

        # Track recent successful directions for fallback when gradients vanish
        recent_successful_directions = []
        
        for restart in range(num_restarts):
            restart_seed = (base_seed + restart) % (2**32)
            np.random.seed(restart_seed)

            initial_min_area = get_smallest_triangle_area(points)
            # FIXED: Corrected iteration allocation - harder configs get more iterations
            total_iterations = int(5000 - 2000 * (initial_min_area / 0.0365))
            total_iterations = max(1000, min(5000, total_iterations))

            side_length = np.linalg.norm(B - A)
            initial_step = 0.03 * side_length  # Increased for better global exploration
            current_step = initial_step

            initial_temperature = 2.0 * max(0.001, 0.0365 - initial_min_area)
            current_temp = initial_temperature

            best = points.copy()
            best_score = get_smallest_triangle_area(best)
            current = best.copy()
            current_score = best_score

            best_score_streak = 0
            rejection_count = 0
            success_streak = 0
            reheating_count = 0

            # FIXED: Corrected triplet selection - better configs need smaller k
            k_adaptive = max(3, min(20, 20 - int(17 * (initial_min_area / 0.0365))))

            velocity = np.zeros((11, 2))
            momentum_factor = 0.9 - 0.2 * (best_score / 0.0365)

            def get_small_triplets(points, k=3, tol=1e-5):
                n = len(points)
                areas = []
                triplets = []
                for i in range(n):
                    for j in range(i+1, n):
                        for l in range(j+1, n):
                            s_area = signed_area(points[i], points[j], points[l])
                            areas.append(abs(s_area))
                            triplets.append((i, j, l))
                sorted_indices = np.argsort(areas)
                min_area = areas[sorted_indices[0]]
                result = []
                for idx in sorted_indices:
                    if areas[idx] <= min_area + tol:
                        result.append(triplets[idx])
                        if len(result) >= k:
                            break
                return result

            for iteration in range(total_iterations):
                if best_score_streak >= 800:
                    break

                min_area_val = get_smallest_triangle_area(current)
                tol = max(0.02 * min_area_val, 1e-5)
                small_triplets = get_small_triplets(current, k=k_adaptive, tol=tol)
                all_points_in_small_triplets = set()
                for triplet in small_triplets:
                    all_points_in_small_triplets.update(triplet)

                # FIXED: Corrected exploration bias - better configs get less non-critical exploration
                non_critical_prob = max(0.05, min(0.30, 0.30 - 0.25 * (min_area_val / 0.0365)))
                r = np.random.rand()
                candidate = current.copy()
                valid_candidate = True
                skip_loop = False

                if r < non_critical_prob:
                    non_triplet_indices = list(set(range(11)) - all_points_in_small_triplets)
                    if non_triplet_indices:
                        chosen_indices = [np.random.choice(non_triplet_indices)]
                    else:
                        chosen_indices = [np.random.randint(0, 11)]
                elif r < non_critical_prob + 0.50:
                    points_list = list(all_points_in_small_triplets)
                    num_points = 2
                    if len(points_list) < num_points):
                        num_points = len(points_list)
                    chosen_indices = np.random.choice(points_list, num_points, replace=False)
                # INCREASED: Coordinated two-point perturbation mode (15% probability)
                elif r < non_critical_prob + 0.65:
                    if len(small_triplets) == 0:
                        valid_candidate = False
                    else:
                        triplet = small_triplets[np.random.randint(len(small_triplets))]
                        idx1, idx2 = np.random.choice(triplet, 2, replace=False)
                        pts = [candidate[i] for i in triplet]
                        a, b, c = pts
                        
                        if idx1 == triplet[0]:
                            grad1 = np.array([b[1]-c[1], c[0]-b[0]])
                        elif idx1 == triplet[1]:
                            grad1 = np.array([c[1]-a[1], a[0]-c[0]])
                        else:
                            grad1 = np.array([a[1]-b[1], b[0]-a[0]])

                        if idx2 == triplet[0]:
                            grad2 = np.array([b[1]-c[1], c[0]-b[0]])
                        elif idx2 == triplet[1]:
                            grad2 = np.array([c[1]-a[1], a[0]-c[0]])
                        else:
                            grad2 = np.array([a[1]-b[1], b[0]-a[0]])

                        norm1 = np.linalg.norm(grad1)
                        norm2 = np.linalg.norm(grad2)
                        if norm1 < 1e-10:
                            dir1 = np.random.normal(0, 1, 2)
                            dir1 = dir1 / (np.linalg.norm(dir1) + 1e-10)
                        else:
                            dir1 = grad1 / norm1

                        if norm2 < 1e-10:
                            dir2 = np.random.normal(0, 1, 2)
                            dir2 = dir2 / (np.linalg.norm(dir2) + 1e-10)
                        else:
                            dir2 = grad2 / norm2

                        new_point1 = candidate[idx1] + current_step * dir1
                        new_point2 = candidate[idx2] + current_step * dir2

                        if not (is_inside_triangle(new_point1, A, B, C) and is_inside_triangle(new_point2, A, B, C)):
                            valid_candidate = False
                        else:
                            candidate[idx1] = new_point1
                            candidate[idx2] = new_point2
                            # Track successful coordinated move direction
                            if new_point1[0] != candidate[idx1][0] or new_point1[1] != candidate[idx1][1]:
                                recent_successful_directions.append(dir1)
                                if len(recent_successful_directions) > 10:
                                    recent_successful_directions.pop(0)
                            if new_point2[0] != candidate[idx2][0] or new_point2[1] != candidate[idx2][1]:
                                recent_successful_directions.append(dir2)
                                if len(recent_successful_directions) > 10:
                                    recent_successful_directions.pop(0)
                            skip_loop = True
                else:
                    points_list = list(all_points_in_small_triplets)
                    chosen_indices = [np.random.choice(points_list)]

                if not skip_loop and valid_candidate:
                    for idx in chosen_indices:
                        if idx in all_points_in_small_triplets:
                            total_grad = np.zeros(2)
                            count = 0
                            for triplet in small_triplets:
                                if idx in triplet:
                                    pts = [candidate[i] for i in triplet]
                                    a, b, c = pts
                                    
                                    s_area = signed_area(a, b, c)
                                    abs_area = abs(s_area)
                                    sign_area = 1 if s_area >= 0 else -1

                                    if idx == triplet[0]:
                                        grad = np.array([b[1]-c[1], c[0]-b[0]])
                                    elif idx == triplet[1]:
                                        grad = np.array([c[1]-a[1], a[0]-c[0]])
                                    else:
                                        grad = np.array([a[1]-b[1], b[0]-a[0]])

                                    weight = 1.0 / (abs_area + 1e-6)
                                    total_grad += weight * (sign_area * grad)
                                    count += 1

                            if count > 0:
                                velocity[idx] = momentum_factor * velocity[idx] + total_grad
                                norm_dir = np.linalg.norm(velocity[idx])
                                if norm_dir < 1e-10:
                                    # ENHANCED: Use historical successful directions when gradient vanishes
                                    if recent_successful_directions:
                                        direction = np.mean(recent_successful_directions, axis=0)
                                        norm_dir = np.linalg.norm(direction)
                                        if norm_dir < 1e-10:
                                            direction = np.random.normal(0, 1, 2)
                                            norm_dir = np.linalg.norm(direction)
                                            if norm_dir < 1e-10:
                                                direction = np.array([1.0, 0.0])
                                            else:
                                                direction = direction / norm_dir
                                        else:
                                            direction = direction / norm_dir
                                    else:
                                        edges = []
                                        for triplet in small_triplets:
                                            if idx in triplet:
                                                pts = [candidate[i] for i in triplet]
                                                edges.append(np.linalg.norm(pts[0]-pts[1]))
                                                edges.append(np.linalg.norm(pts[1]-pts[2]))
                                                edges.append(np.linalg.norm(pts[2]-pts[0]))
                                                break
                                        avg_edge = np.mean(edges) if edges else 1.0
                                        direction = np.random.normal(0, 1, size=2)
                                        norm_dir = np.linalg.norm(direction)
                                        if norm_dir < 1e-10:
                                            direction = np.array([1.0, 0.0])
                                        else:
                                            direction = direction / norm_dir
                                    perturbation = current_step * direction
                                else:
                                    direction = velocity[idx] / norm_dir
                                    perturbation = current_step * direction
                            else:
                                velocity[idx] = np.zeros(2)
                                perturbation = current_step * np.random.normal(0, 1, size=2)
                        else:
                            velocity[idx] = np.zeros(2)
                            perturbation = current_step * np.random.normal(0, 1, size=2)

                        new_point = candidate[idx] + perturbation
                        if not is_inside_triangle(new_point, A, B, C):
                            valid_candidate = False
                            break
                        candidate[idx] = new_point

                if not valid_candidate:
                    rejection_count += 1
                    if rejection_count >= 10:
                        current_step = max(0.0001, current_step * 0.99)
                        rejection_count = 0
                    best_score_streak += 1
                    continue

                candidate_score = get_smallest_triangle_area(candidate)

                if candidate_score > best_score:
                    best = candidate.copy()
                    best_score = candidate_score
                    best_score_streak = 0
                    success_streak += 1
                    if success_streak >= 50:
                        current_step = max(0.0001, current_step * 0.99)
                        success_streak = 0
                else:
                    best_score_streak += 1
                    success_streak = 0

                # FIXED: More aggressive reheating for better configs
                reheating_threshold = max(15, 70 - int(55 * (best_score / 0.0365)))
                if best_score_streak >= reheating_threshold and reheating_count < 15:
                    current_step = initial_step
                    current_temp = 2.0 * max(0.001, 0.0365 - best_score)
                    best_score_streak = 0
                    rejection_count = 0
                    success_streak = 0
                    reheating_count += 1

                if best_score_streak >= 150:
                    current_step = max(0.0001, current_step * 0.99)
                    best_score_streak = 0

                delta = candidate_score - current_score
                if delta > 0:
                    current = candidate
                    current_score = candidate_score
                else:
                    if current_temp > 0 and np.random.rand() < np.exp(delta / current_temp):
                        current = candidate
                        current_score = candidate_score

                # ENHANCED: Adaptive cooling based on small triangle density
                small_triangle_density = len(small_triplets) / (11 * 10 * 9 / 6)
                if success_streak > 0:
                    cooling_factor = 0.995 + 0.004 * min(success_streak / 50, 1.0)
                    # Slow cooling when many small triangles indicate difficult region
                    cooling_factor = max(cooling_factor, 0.99 + 0.008 * small_triangle_density)
                else:
                    cooling_factor = 0.999
                current_temp = current_temp * cooling_factor

            if best_score > best_score_overall:
                best_overall = best.copy()
                best_score_overall = best_score

        return best_overall

    return improve