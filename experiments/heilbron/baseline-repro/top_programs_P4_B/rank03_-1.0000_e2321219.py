import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        seed = int(hash(points.tobytes())) % (2**32)
        np.random.seed(seed)

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        
        def find_min_triangle(pts):
            min_area = float('inf')
            min_indices = None
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        x1, y1 = pts[i]
                        x2, y2 = pts[j]
                        x3, y3 = pts[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area < min_area:
                            min_area = area
                            min_indices = (i, j, k)
            return min_indices, min_area

        current_min_indices, current_min_area = find_min_triangle(current)
        best = current.copy()
        best_score = current_score

        base_step = 0.01
        current_step = base_step
        stagnation_counter = 0
        rejection_count = 0
        max_rejection = 5

        initial_temp = max(0.01, 0.5 * best_score)
        temp = initial_temp
        cooling_rate = 0.995

        total_candidate_moves = 0
        accepted_moves = 0
        acceptance_window = 100

        for _ in range(500):
            # Decide move type: 50% chance for two-point move
            if np.random.rand() < 0.5:
                # Two-point move on smallest triangle edge
                idxs = np.array(current_min_indices)
                np.random.shuffle(idxs)
                idx1, idx2 = idxs[:2]
                
                # Compute perpendicular displacement vector
                v = current[idx2] - current[idx1]
                n = np.array([-v[1], v[0]])
                n_norm = np.linalg.norm(n)
                if n_norm > 1e-10:
                    n = n / n_norm
                else:
                    n = np.array([0.0, 0.0])
                
                candidate = current.copy()
                candidate[idx1] -= current_step * n
                candidate[idx2] += current_step * n
            else:
                # Single-point move
                idx = np.random.choice(current_min_indices)
                angle = np.random.uniform(0, 2 * np.pi)
                dx = current_step * np.cos(angle)
                dy = current_step * np.sin(angle)
                candidate = current.copy()
                candidate[idx] += [dx, dy]

            # Boundary check
            if not is_inside_triangle(candidate, A, B, C):
                rejection_count += 1
                stagnation_counter += 1
                if rejection_count >= max_rejection:
                    current_step = max(current_step * 0.7, 1e-5)
                    rejection_count = 0
                continue
            else:
                rejection_count = 0

            score = get_smallest_triangle_area(candidate)

            # Acceptance criterion
            if score > current_score:
                accept = True
            else:
                delta = score - current_score
                if delta > 0:
                    accept = True
                else:
                    prob = np.exp(delta / temp)
                    accept = (np.random.rand() < prob)

            total_candidate_moves += 1
            if accept:
                accepted_moves += 1

            # Step size adaptation
            if total_candidate_moves >= acceptance_window:
                rate = accepted_moves / total_candidate_moves
n                if rate > 0.6:
                    current_step = min(current_step * 1.1, 0.5)
                elif rate < 0.2:
                    current_step = max(current_step * 0.9, 1e-5)
                total_candidate_moves = 0
                accepted_moves = 0

            if accept:
                current = candidate
                current_score = score
                # Update current bottleneck immediately
                current_min_indices, current_min_area = find_min_triangle(current)

                if score > best_score:
                    best = candidate.copy()
                    best_score = score
                stagnation_counter = 0
            else:
                stagnation_counter += 1

            # Cooling
            if stagnation_counter > 0 and stagnation_counter % 20 == 0:
                temp *= cooling_rate

            # Restart on stagnation
            if stagnation_counter >= 100:
                current = best.copy()
                current_score = best_score
                # Adaptive restart temperature
                initial_temp = max(0.01, 0.5 * best_score)
                temp = 2.0 * initial_temp
                current_step = min(current_step * 2.0, 0.5)
                stagnation_counter = 0
                # Update current bottleneck after restart
                current_min_indices, current_min_area = find_min_triangle(current)

        return best

    return improve