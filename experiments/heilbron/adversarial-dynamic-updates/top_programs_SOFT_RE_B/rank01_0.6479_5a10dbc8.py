from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Create input-dependent RNG for adversarial robustness
        seed = abs(hash(points.tobytes())) % (2**32)
        rng = np.random.default_rng(seed)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        
        total_iterations = 200
        early_stop_patience = 20
        T0 = 0.01
        no_improve_count = 0

        for i in range(total_iterations):
            # Adaptive step size decay: 0.05 -> 0.005
            sigma = 0.05 * (0.005 / 0.05) ** (i / total_iterations)
            
            # Decide perturbation scope: 70% single point, 30% multi-point
            if rng.random() < 0.3:
                num_points = rng.choice([2, 3])
                indices = rng.choice(11, size=num_points, replace=False)
            else:
                indices = [rng.choice(11)]

            candidate = current.copy()
            for idx in indices:
                candidate[idx] += rng.normal(0, sigma, size=2)

            # Skip invalid configurations
            if not is_inside_triangle(candidate, A, B, C):
                continue

            score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            T = T0 * (1 - i / total_iterations)
            if score > current_score:
                current = candidate
                current_score = score
                no_improve_count = 0
                if score > best_score:
                    best = candidate
                    best_score = score
            else:
                delta = score - current_score
                if rng.random() < np.exp(delta / T):
                    current = candidate
                    current_score = score
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            # Restart mechanism for stagnation
            if no_improve_count >= early_stop_patience:
                current = best.copy()
                current_score = best_score
                no_improve_count = 0
                
                # Aggressive multi-point perturbation
                restart_indices = rng.choice(11, size=rng.choice([2, 3]), replace=False)
                for idx in restart_indices:
                    current[idx] += rng.normal(0, 3 * sigma, size=2)
                
                if is_inside_triangle(current, A, B, C):
                    current_score = get_smallest_triangle_area(current)
                    if current_score > best_score:
                        best = current.copy()
                        best_score = current_score
                else:
                    current = best.copy()
                    current_score = best_score

        return best

    return improve