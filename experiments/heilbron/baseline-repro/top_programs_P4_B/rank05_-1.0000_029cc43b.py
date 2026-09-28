import numpy as np
import hashlib
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle

def entrypoint():
    A, B, C = get_unit_triangle()

    def triangle_area(a, b, c):
        return 0.5 * abs((a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1])))

    def improve(points: np.ndarray) -> np.ndarray:
        seed = int.from_bytes(hashlib.sha256(points.tobytes()).digest()[:4], 'little') % (2**32)
        np.random.seed(seed)

        # Adaptive iteration count: prioritize harder configurations (lower initial_min_area)
        initial_min_area = get_smallest_triangle_area(points)
        deficit = max(0.0, 0.0365 - initial_min_area)
        total_iterations = int(1500 + 1500 * (deficit / 0.0365))

        # Compute side length for adaptive scaling
        side_length = np.linalg.norm(B - A)
        initial_step = 0.01 * side_length
        current_step = initial_step

        # Adaptive temperature initialization
        initial_temperature = 0.1 * max(0.001, 0.0365 - initial_min_area)
        current_temp = initial_temperature

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score

        best_score_streak = 0
        rejection_count = 0
        success_streak = 0
        reheating_count = 0  # Track reheating events

        def get_small_triplets(points, k=3, tol=1e-5):
            n = len(points)
            areas = []
            triplets = []
            for i in range(n):
                for j in range(i+1, n):
                    for l in range(j+1, n):
                        area = triangle_area(points[i], points[j], points[l])
                        areas.append(area)
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
            if best_score_streak >= 400:
                break

            min_area_val = get_smallest_triangle_area(current)
            # Adaptive tolerance with minimum floor to prevent numerical issues
            tol = max(1e-7, 1e-5 * max(min_area_val, 1e-10))
            
            # Adaptive triplet counting based on solution quality
            deficit = max(0.0, 0.0365 - min_area_val)
            k_val = min(10, 3 + int(deficit / 0.005))
            small_triplets = get_small_triplets(current, k=k_val, tol=tol)
            
            all_points_in_small_triplets = set()
            for triplet in small_triplets:
                all_points_in_small_triplets.update(triplet)

            r = np.random.rand()
            if r < 0.05:
                non_triplet_indices = list(set(range(11)) - all_points_in_small_triplets)
                if non_triplet_indices:
                    chosen_indices = [np.random.choice(non_triplet_indices)]
                else:
                    chosen_indices = [np.random.randint(0, 11)]
            elif r < 0.55:
                points_list = list(all_points_in_small_triplets)
                num_points = 2
                if len(points_list) < num_points):
                    num_points = len(points_list)
                chosen_indices = np.random.choice(points_list, num_points, replace=False)
            else:
                points_list = list(all_points_in_small_triplets)
                chosen_indices = [np.random.choice(points_list)]

            candidate = current.copy()
            valid_candidate = True
            for idx in chosen_indices:
                if idx in all_points_in_small_triplets:
                    total_grad = np.zeros(2)
                    count = 0
                    for triplet in small_triplets:
                        if idx in triplet:
                            pts = [candidate[i] for i in triplet]
                            a, b, c = pts
                            f_val = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                            abs_f = abs(f_val)
                            sign_f = 1 if f_val >= 0 else -1

                            if idx == triplet[0]:
                                grad = np.array([b[1]-c[1], c[0]-b[0]])
                            elif idx == triplet[1]:
                                grad = np.array([c[1]-a[1], a[0]-c[0]])
                            else:
                                grad = np.array([a[1]-b[1], b[0]-a[0]])

                            # Weight gradient by inverse area to prioritize critical triangles
                            weight = 1.0 / (abs_f + 1e-10)
                            total_grad += weight * (sign_f * grad)
                            count += 1

                    if count > 0:
                        norm_dir = np.linalg.norm(total_grad)
                        if norm_dir < 1e-10:
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
                            perturbation = current_step * avg_edge * direction
                        else:
                            direction = total_grad / norm_dir
                            perturbation = current_step * direction
                    else:
                        perturbation = current_step * np.random.normal(0, 1, size=2)
                else:
                    # Compute global average edge length for geometry-aware perturbation
                    total_length = 0.0
                    count_edges = 0
                    n_pts = candidate.shape[0]
                    for i in range(n_pts):
                        for j in range(i+1, n_pts):
                            total_length += np.linalg.norm(candidate[i] - candidate[j])
                            count_edges += 1
                    avg_edge_global = total_length / count_edges if count_edges > 0 else 1.0
                    perturbation = current_step * avg_edge_global * np.random.normal(0, 1, size=2)

                new_point = candidate[idx] + perturbation
                if not is_inside_triangle(new_point, A, B, C):
                    valid_candidate = False
                    break
                candidate[idx] = new_point

            if not valid_candidate:
                rejection_count += 1
                if rejection_count >= 10:
                    current_step = max(0.0001, current_step * 0.95)
                    rejection_count = 0
                best_score_streak += 1
                continue

            candidate_score = get_smallest_triangle_area(candidate)

            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                best_score_streak = 0
                success_streak += 1
                if success_streak >= 10:
                    current_step = max(0.0001, current_step * 0.95)
                    success_streak = 0
            else:
                best_score_streak += 1
                success_streak = 0

            # Adaptive reheating threshold based on solution quality
            deficit = max(0.0, 0.0365 - best_score)
            reheat_threshold = max(150, 300 - int(deficit * 5000))
            if best_score_streak >= reheat_threshold and reheating_count < 4:
                current_step = initial_step
                current_temp = initial_temperature
                best_score_streak = 0
                rejection_count = 0
                success_streak = 0
                reheating_count += 1

            # Adaptive step reduction threshold based on solution quality
            deficit = max(0.0, 0.0365 - best_score)
            step_reduce_threshold = 250 + int(deficit * 1000)
            if best_score_streak >= step_reduce_threshold:
                current_step = max(0.0001, current_step * 0.95)
                best_score_streak = 0

            delta = candidate_score - current_score
            if delta > 0:
                current = candidate
                current_score = candidate_score
            else:
                # Use current_temp for acceptance probability
                if current_temp > 0 and np.random.rand() < np.exp(delta / current_temp):
                    current = candidate
                    current_score = candidate_score

            # Slow cooling schedule (0.995 vs previous 0.95)
            current_temp = current_temp * 0.995

        return best

    return improve