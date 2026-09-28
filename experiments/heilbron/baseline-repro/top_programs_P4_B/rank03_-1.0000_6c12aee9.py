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
        return [triplet for _, triplet in triplets[:k]]

    def gradient_for_point_in_triplet(point_idx, triplet, points, area):
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
        return sign_f * grad / norm_dir * (1.0 / (area + 1e-10))  # Area-weighted gradient

    def project_point(p, A, B, C):
        if is_inside_triangle(p, A, B, C):
            return p
        
        def point_to_line_segment(p, a, b):
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
            t = max(0.0, min(1.0, t))
            return a + t * ab
        
        p1 = point_to_line_segment(p, A, B)
        p2 = point_to_line_segment(p, B, C)
        p3 = point_to_line_segment(p, C, A)
        d1 = np.linalg.norm(p1 - p)
        d2 = np.linalg.norm(p2 - p)
        d3 = np.linalg.norm(p3 - p)
        if d1 <= d2 and d1 <= d3:
            return p1
        elif d2 <= d1 and d2 <= d3:
            return p2
        else:
            return p3

    def boundary_repulsion(p, A, B, C):
        # Calculate distance to each boundary
        def distance_to_line(p, a, b):
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
            t = max(0.0, min(1.0, t))
            projection = a + t * ab
            return np.linalg.norm(p - projection)
        
        d1 = distance_to_line(p, A, B)
        d2 = distance_to_line(p, B, C)
        d3 = distance_to_line(p, C, A)
        
        # Return repulsion vector (push away from nearest boundary)
        min_d = min(d1, d2, d3)
        if min_d < 1e-5:  # Very close to boundary
            return np.zeros(2)  # Already on boundary, no repulsion
        
        # Calculate direction away from nearest boundary
        if d1 <= d2 and d1 <= d3:
            # Closest to AB
            normal = np.array([0, 1])  # Assuming AB is bottom edge
            return normal / (min_d * min_d)
        elif d2 <= d1 and d2 <= d3:
            # Closest to BC
            bc = C - B
            normal = np.array([-bc[1], bc[0]])
            normal = normal / np.linalg.norm(normal)
            return normal / (min_d * min_d)
        else:
            # Closest to CA
            ca = A - C
            normal = np.array([-ca[1], ca[0]])
            normal = normal / np.linalg.norm(normal)
            return normal / (min_d * min_d)

    def improve(points: np.ndarray) -> np.ndarray:
        seed = int.from_bytes(hashlib.sha256(points.tobytes()).digest()[:4], 'little') % (2**32)
        np.random.seed(seed)

        total_iterations = 500
        initial_temperature = 0.1  # Increased from 0.01

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score

        best_score_streak = 0

        # Adaptive step multiplier setup - WIDENED RANGE
        base_step_multiplier = 0.05  # Increased from 0.02
        step_multiplier = base_step_multiplier
        success_window = 50
        success_count = 0
        move_count = 0

        for iteration in range(total_iterations):
            if best_score_streak >= 400:
                break

            # Slow decay of k_val: remains 5 for first 150 iterations, then decreases every 150
            k_val = max(1, 5 - int(iteration / 150))
            top_triplets = get_top_k_triplets(current, k=k_val)
            small_points = set()
            triplet_counts = {}  # Track how many triplets each point appears in
            for triplet in top_triplets:
                small_points.update(triplet)
                for idx in triplet:
                    triplet_counts[idx] = triplet_counts.get(idx, 0) + 1

            # 30% chance for global exploration (increased from 10%)
            if np.random.rand() < 0.3:
                all_indices = set(range(11))
                non_triplet_indices = list(all_indices - small_points)
                if non_triplet_indices:
                    # Prefer points that appear in fewer triplets (more 'free')
                    candidate_indices = [(triplet_counts.get(i, 0), i) for i in non_triplet_indices]
                    candidate_indices.sort()  # Sort by triplet count (ascending)
                    chosen_indices = [candidate_indices[0][1]]
                else:
                    # Fallback: choose point with highest triplet count (most constrained)
                    candidate_indices = [(triplet_counts.get(i, 0), i) for i in small_points]
                    candidate_indices.sort(reverse=True)  # Sort by triplet count (descending)
                    chosen_indices = [candidate_indices[0][1]]
            else:
                # 30% chance for 2 points, 70% for 1 point (increased from 10%)
                num_points = 2 if np.random.rand() < 0.3 else 1
                
                if num_points == 2:
                    # Prefer points that co-occur in multiple triplets
                    co_occurrence = {}
                    for triplet in top_triplets:
                        for i in range(len(triplet)):
                            for j in range(i+1, len(triplet)):
                                pair = tuple(sorted([triplet[i], triplet[j]]))
                                co_occurrence[pair] = co_occurrence.get(pair, 0) + 1
                    
                    if co_occurrence:
                        best_pair = max(co_occurrence.items(), key=lambda x: x[1])[0]
                        chosen_indices = list(best_pair)
                    else:
                        # Fallback to random selection
                        chosen_indices = np.random.choice(list(small_points), num_points, replace=False)
                else:
                    chosen_indices = [np.random.choice(list(small_points))]

            candidate = current.copy()

            # Room-based step size
            room = max(0.0, 0.0365 - current_score)

            # Line search for single-point moves
            if len(chosen_indices) == 1:
                idx = chosen_indices[0]
                base_point = candidate[idx].copy()

                # Compute direction for this point (aggregating all top triplets containing the point)
                if idx in small_points:
                    total_grad = np.zeros(2)
                    count = 0
                    for triplet in top_triplets:
                        if idx in triplet:
                            # Get actual area for weighting
                            area = triangle_area(current[triplet[0]], current[triplet[1]], current[triplet[2]])
                            grad = gradient_for_point_in_triplet(idx, triplet, current, area)
                            total_grad += grad
                            count += 1
                    if count > 0:
                        norm_total = np.linalg.norm(total_grad)
                        if norm_total > 1e-10:
                            direction = total_grad / norm_total
                        else:
                            direction = np.random.normal(0, 1, size=2)
                            norm_dir = np.linalg.norm(direction)
                            direction = direction / norm_dir if norm_dir > 1e-10 else np.array([1.0, 0.0])
                    else:
                        direction = np.random.normal(0, 1, size=2)
                        norm_dir = np.linalg.norm(direction)
                        direction = direction / norm_dir if norm_dir > 1e-10 else np.array([1.0, 0.0])
                else:
                    direction = np.random.normal(0, 1, size=2)
                    norm_dir = np.linalg.norm(direction)
                    direction = direction / norm_dir if norm_dir > 1e-10 else np.array([1.0, 0.0])

                # Add boundary repulsion
                repulsion = boundary_repulsion(base_point, A, B, C)
                if np.linalg.norm(repulsion) > 0:
                    direction = direction * 0.7 + repulsion * 0.3
                    norm_dir = np.linalg.norm(direction)
                    if norm_dir > 1e-10:
                        direction = direction / norm_dir

                # Adaptive step size
                step_size = step_multiplier * room / 0.0365
                v = step_size * direction

                # Try multiple scales for line search
                scales = [1.0, 0.5, 0.25, 0.125, 0.0625]
                best_min_area = current_score
                best_point = base_point

                for scale in scales:
                    candidate_point = base_point + scale * v
                    projected_point = project_point(candidate_point, A, B, C)
                    temp_candidate = candidate.copy()
                    temp_candidate[idx] = projected_point
                    area_val = get_smallest_triangle_area(temp_candidate)
                    if area_val > best_min_area:
                        best_min_area = area_val
                        best_point = projected_point

                candidate[idx] = best_point

            else:
                # Adaptive step size for multi-point moves - WIDENED RANGE
                step_size = step_multiplier * room / 0.0365

                for idx in chosen_indices:
                    # Compute direction for this point (aggregating all top triplets containing the point)
                    if idx in small_points:
                        total_grad = np.zeros(2)
                        count = 0
                        for triplet in top_triplets:
                            if idx in triplet:
                                # Get actual area for weighting
                                area = triangle_area(current[triplet[0]], current[triplet[1]], current[triplet[2]])
                                grad = gradient_for_point_in_triplet(idx, triplet, current, area)
                                total_grad += grad
                                count += 1
                        if count > 0:
                            norm_total = np.linalg.norm(total_grad)
                            if norm_total > 1e-10:
                                direction = total_grad / norm_total
                            else:
                                direction = np.random.normal(0, 1, size=2)
                                norm_dir = np.linalg.norm(direction)
                                direction = direction / norm_dir if norm_dir > 1e-10 else np.array([1.0, 0.0])
                        else:
                            direction = np.random.normal(0, 1, size=2)
                            norm_dir = np.linalg.norm(direction)
                            direction = direction / norm_dir if norm_dir > 1e-10 else np.array([1.0, 0.0])
                    else:
                        direction = np.random.normal(0, 1, size=2)
                        norm_dir = np.linalg.norm(direction)
                        direction = direction / norm_dir if norm_dir > 1e-10 else np.array([1.0, 0.0])

                    # Add boundary repulsion
                    repulsion = boundary_repulsion(candidate[idx], A, B, C)
                    if np.linalg.norm(repulsion) > 0:
                        direction = direction * 0.7 + repulsion * 0.3
                        norm_dir = np.linalg.norm(direction)
                        if norm_dir > 1e-10:
                            direction = direction / norm_dir

                    v = step_size * direction

                    # Boundary projection with 20 backtracking steps and fallback
                    beta = 1.0
                    found = False
                    for _ in range(20):
                        new_point = candidate[idx] + beta * v
n                        if is_inside_triangle(new_point, A, B, C):
                            candidate[idx] = new_point
                            found = True
                            break
                        beta *= 0.5
                    if not found:
                        candidate[idx] = project_point(candidate[idx] + v, A, B, C)

            candidate_score = get_smallest_triangle_area(candidate)

            # Track move success for adaptive step multiplier
            move_count += 1
            if candidate_score > current_score:
                success_count += 1

            # Update step multiplier based on success rate
            if move_count >= success_window:
                success_rate = success_count / move_count
                if success_rate > 0.5:
                    step_multiplier = min(0.2, step_multiplier * 1.1)  # Upper bound increased to 0.2
                elif success_rate < 0.2:
                    step_multiplier = max(0.01, step_multiplier * 0.9)  # Lower bound increased to 0.01
                success_count = 0
                move_count = 0

            # Stagnation handling: reset step multiplier to encourage exploration
            if best_score_streak >= 50:  # Reduced from 200
                step_multiplier = base_step_multiplier
                best_score_streak = 0
                success_count = 0
                move_count = 0
                
                # Multi-point restart when stuck
                if np.random.rand() < 0.3:
                    # Perturb 3 random points
                    restart_indices = np.random.choice(11, 3, replace=False)
                    for idx in restart_indices:
                        # Small random move with boundary awareness
                        direction = np.random.normal(0, 1, size=2)
                        direction = direction / (np.linalg.norm(direction) + 1e-10)
                        step = 0.05 * np.random.rand()  # 5% of room
                        candidate[idx] = project_point(candidate[idx] + step * direction, A, B, C)

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
                # Logarithmic cooling schedule
                T = initial_temperature / (1 + np.log(1 + iteration))
                if T > 0 and np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = candidate_score

        return best

    return improve