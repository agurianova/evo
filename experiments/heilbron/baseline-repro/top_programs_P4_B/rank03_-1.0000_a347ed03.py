import numpy as np
import hashlib
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
from scipy.optimize import minimize
from scipy.spatial import KDTree


def entrypoint():
    A, B, C = get_unit_triangle()

    def triangle_area(a, b, c):
        return 0.5 * abs((a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1])))

    def nelder_mead_refinement(points, max_iter=100):
        """Apply Nelder-Mead to refine promising configurations"""
        n_points = len(points)
        
        def objective(flattened_points):
            reshaped = flattened_points.reshape(n_points, 2)
            if not is_inside_triangle(reshaped, A, B, C):
                return float('inf')
            return -get_smallest_triangle_area(reshaped)
        
        result = minimize(
            objective,
            points.flatten(),
            method='Nelder-Mead',
            options={'maxiter': max_iter, 'xatol': 1e-8, 'fatol': 1e-8}
        )
        
        if result.success and is_inside_triangle(result.x.reshape(n_points, 2), A, B, C):
            return result.x.reshape(n_points, 2)
        return points

    def get_small_triplets_spatial(points, k=3, tol=1e-5):
        """Efficient spatial-based method to find smallest triangles"""
        n = len(points)
        # Build KDTree for efficient nearest neighbor search
        tree = KDTree(points)
        
        # For each point, find its nearest neighbors to form candidate triplets
        candidate_triplets = set()
        for i in range(n):
            # Find 8 nearest neighbors (including self) for candidate triangles
            _, indices = tree.query(points[i], k=min(9, n))
            for j in range(len(indices)):
                for l in range(j+1, len(indices)):
                    if indices[j] != indices[l]:
                        candidate_triplets.add(tuple(sorted([i, indices[j], indices[l]])))
        
        # Calculate areas for candidate triplets
        areas = []
        triplets = []
        for triplet in candidate_triplets:
            i, j, l = triplet
            area = triangle_area(points[i], points[j], points[l])
            areas.append(area)
            triplets.append(triplet)
        
        # Return k smallest with tolerance
n        if len(areas) == 0:
            return []
        
        sorted_indices = np.argsort(areas)
        min_area = areas[sorted_indices[0]]
        result = []
        for idx in sorted_indices:
            if areas[idx] <= min_area + tol:
                result.append(triplets[idx])
                if len(result) >= k:
                    break
        return result

    def improve(points: np.ndarray) -> np.ndarray:
        seed_base = int.from_bytes(hashlib.sha256(points.tobytes()).digest()[:4], 'little') % (2**32)
        
        # MULTI-START: 5 independent restarts with seed variation
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)
        
        for restart_idx in range(5):
            np.random.seed(seed_base + restart_idx)

            initial_min_area = get_smallest_triangle_area(points)
            # FIXED: Inverted iteration allocation to prioritize harder problems
            total_iterations = int(500 + 4500 * (1.0 - min(1.0, initial_min_area / 0.0365)))

            side_length = np.linalg.norm(B - A)
            initial_step = 0.01 * side_length
            current_step = initial_step

            # IMPLEMENTED: Adaptive temperature initialization based on problem difficulty
            initial_temperature = max(0.001, 0.01 * (0.0365 - initial_min_area) + 0.005)
            current_temp = initial_temperature

            best = points.copy()
            best_score = get_smallest_triangle_area(best)
            current = best.copy()
            current_score = best_score

            best_score_streak = 0
            rejection_count = 0
            success_streak = 0
            reheating_count = 0

            # FIXED: Increased k_adaptive ceiling to handle denser configurations
            k_adaptive = max(5, min(25, int(25 - 15 * (initial_min_area / 0.0365))))

            velocity = np.zeros((11, 2))
            # FIXED: Momentum range adjusted for better refinement
            momentum_factor = max(0.3, min(0.7, 0.7 - 0.4 * (best_score / 0.0365)))

            # Track recent improvements for adaptive cooling
            improvement_history = []
            max_history = 50

            for iteration in range(total_iterations):
                if best_score_streak >= 800:
                    break

                min_area_val = get_smallest_triangle_area(current)
                tolerance_factor = max(0.05, 0.15 - 0.1 * (min_area_val / 0.0365))
                tol = tolerance_factor * min_area_val
                
                # IMPLEMENTED: Spatial-based efficient triplet search
                small_triplets = get_small_triplets_spatial(current, k=k_adaptive, tol=tol)
                
                all_points_in_small_triplets = set()
                for triplet in small_triplets:
                    all_points_in_small_triplets.update(triplet)

                # IMPLEMENTED: Floor value to maintain exploration of non-critical areas
                non_critical_prob = max(0.05, 0.2 * (1 - best_score / 0.0365))
                critical_pair_prob = 0.35 + 0.25 * (best_score / 0.0365) * (1 - best_score / 0.0365)
                
                r = np.random.rand()
                if r < non_critical_prob:
                    non_triplet_indices = list(set(range(11)) - all_points_in_small_triplets)
                    if non_triplet_indices:
                        chosen_indices = [np.random.choice(non_triplet_indices)]
                    else:
                        chosen_indices = [np.random.randint(0, 11)]
                elif r < non_critical_prob + critical_pair_prob:
                    points_list = list(all_points_in_small_triplets)
                    num_points = 2
                    if len(points_list) < num_points:
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
                                
                                # FIXED: Stabilized gradient weighting
                                weight = np.sign(f_val) / (np.abs(f_val) + 1e-8)
                                
                                if idx == triplet[0]:
                                    grad = np.array([b[1]-c[1], c[0]-b[0]])
                                elif idx == triplet[1]:
                                    grad = np.array([c[1]-a[1], a[0]-c[0]])
                                else:
                                    grad = np.array([a[1]-b[1], b[0]-a[0]])
                                
                                total_grad += weight * grad
                                count += 1

                        if count > 0:
                            momentum_factor = max(0.3, min(0.7, 0.7 - 0.4 * (best_score / 0.0365)))
                            velocity[idx] = momentum_factor * velocity[idx] + total_grad
                            norm_dir = np.linalg.norm(velocity[idx])
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

                # Track improvements for adaptive cooling
                if candidate_score > current_score:
                    improvement = candidate_score - current_score
                    improvement_history.append(improvement)
                    if len(improvement_history) > max_history:
                        improvement_history.pop(0)

                if candidate_score > best_score:
                    best = candidate.copy()
                    best_score = candidate_score
                    best_score_streak = 0
                    success_streak += 1
                    if success_streak >= 10:
                        current_step = max(0.0001, current_step * 0.99)
                        success_streak = 0
                else:
                    best_score_streak += 1
                    success_streak = 0

                # FIXED: Increased reheating threshold to allow deeper local search
                reheating_threshold = max(150, 300 - int(150 * (best_score / 0.0365)))
                if best_score_streak >= reheating_threshold and reheating_count < 8:
                    current_step = initial_step
                    current_temp = initial_temperature
                    best_score_streak = 0
                    rejection_count = 0
                    success_streak = 0
                    reheating_count += 1

                if best_score_streak >= 150:
                    current_step = max(0.0001, current_step * 0.99)
                    best_score_streak = 0

                # IMPLEMENTED: Adaptive temperature cooling based on improvement rate
                if len(improvement_history) > 0:
                    success_rate = sum(1 for imp in improvement_history if imp > 0) / len(improvement_history)
                    if success_rate > 0.3:
                        # Slow cooling when improvements are frequent
                        cooling_rate = 0.95 - 0.05 * success_rate
                    else:
                        # Faster cooling during stagnation
                        stagnation_rate = 1.0 - success_rate
                        cooling_rate = 0.90 - 0.10 * stagnation_rate
                    current_temp = max(1e-6, current_temp * cooling_rate)
                else:
                    current_temp = max(1e-6, current_temp * 0.99)

                # ADDED: Periodic Nelder-Mead refinement
                if iteration % 500 == 0 and iteration > 0:
                    refined = nelder_mead_refinement(best)
                    refined_score = get_smallest_triangle_area(refined)
                    if refined_score > best_score:
                        best = refined
                        best_score = refined_score

                delta = candidate_score - current_score
                if delta > 0:
                    current = candidate
                    current_score = candidate_score
                else:
                    if current_temp > 0 and np.random.rand() < np.exp(delta / current_temp):
                        current = candidate
                        current_score = candidate_score

            # Update overall best after each restart
            if best_score > best_score_overall:
                best_overall = best.copy()
                best_score_overall = best_score

        return best_overall

    return improve