from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Initialize with local RNG for determinism
        rng = np.random.default_rng(42)
        
        # Helper to compute min area and critical triangle indices
        def compute_min_triangle(pts):
            n = pts.shape[0]
            min_area = float('inf')
            best_indices = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = 0.5 * abs(
                            (pts[j,0]-pts[i,0])*(pts[k,1]-pts[i,1]) - 
                            (pts[k,0]-pts[i,0])*(pts[j,1]-pts[i,1])
                        )
                        if area < min_area:
                            min_area = area
                            best_indices = (i, j, k)
            return min_area, best_indices

        best = points.copy()
        best_score, _ = compute_min_triangle(best)
        current = best.copy()
        current_score = best_score

        # Parameters
        total_rounds = 200
        initial_temp = 0.0005
        step_size = 0.05

        for current_round in range(total_rounds):
            # Update step size every 10 rounds
            if current_round % 10 == 0 and current_round > 0:
                step_size *= 0.9

            # Compute current state's critical triangle
            current_score, critical_indices = compute_min_triangle(current)

            # Biased point selection (80% on critical points)
            if rng.random() < 0.8:
                idx = rng.choice(critical_indices)
            else:
                idx = rng.integers(0, 11)

            # Determine move direction
            if idx in critical_indices:
                # Get other two points in critical triangle
                other_indices = [x for x in critical_indices if x != idx]
                p0 = current[idx]
                p1 = current[other_indices[0]]
                p2 = current[other_indices[1]]

                # Compute cross product (2*signed area)
                dx1 = p1[0] - p0[0]
                dy1 = p1[1] - p0[1]
                dx2 = p2[0] - p0[0]
                dy2 = p2[1] - p0[1]
                cross = dx1 * dy2 - dx2 * dy1

                # Gradient direction for area increase
                direction = np.array([p1[1] - p2[1], p2[0] - p1[0]])
                if cross < 0:
                    direction = -direction

                # Normalize direction
                norm_dir = np.linalg.norm(direction)
                if norm_dir > 1e-10:
                    direction = direction / norm_dir
                else:
                    direction = rng.normal(0, 1, size=2)
                    direction = direction / np.linalg.norm(direction)
            else:
                # Random direction for non-critical points
                direction = rng.normal(0, 1, size=2)
                direction = direction / np.linalg.norm(direction)

            # Apply perturbation
            candidate = current.copy()
            candidate[idx] += direction * step_size

            # Check containment
            if not is_inside_triangle(candidate, A, B, C):
                continue

            # Evaluate candidate
            candidate_score = get_smallest_triangle_area(candidate)

            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta >= 0:
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score
            else:
                temp = initial_temp * (1 - current_round / total_rounds)
                if rng.random() < np.exp(delta / temp):
                    current = candidate
                    current_score = candidate_score

        return best

    return improve