from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Create input-dependent RNG for adversarial robustness
        seed = hash(points.tobytes()) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        
        total_iterations = 200
        max_stagnation = 30
        max_restarts = 3
        
        best_points = points.copy()
        best_score = get_smallest_triangle_area(best_points)
        current_points = best_points.copy()
        current_score = best_score
        
        # Initialize temperature based on initial solution quality
        T0 = 0.1 * best_score
        stagnation_count = 0
        restart_count = 0

        for iteration in range(total_iterations):
            # Adaptive temperature cooling
            T = T0 * (0.99 ** iteration)
            # Slower step decay with minimum bound
            step = max(0.001, 0.05 * (0.995 ** iteration))

            # Restart mechanism for deep local optima
            if stagnation_count >= max_stagnation and restart_count < max_restarts:
                candidate = best_points.copy()
                valid_restart = False
                
                # Attempt restart with larger perturbations
                for _ in range(5):
                    restart_points = best_points.copy()
                    for _ in range(3):
                        idx = rng.integers(0, 11)
                        perturbation = rng.normal(0, 0.1, size=2)
                        restart_points[idx] += perturbation
                    
                    if is_inside_triangle(restart_points, A, B, C):
                        candidate = restart_points
n                        valid_restart = True
                        break
                
                if valid_restart:
                    current_points = candidate
                    current_score = get_smallest_triangle_area(current_points)
                    stagnation_count = 0
                    restart_count += 1
                    continue

            # Determine number of points to perturb (70% single, 20% double, 10% triple)
            p = rng.random()
            n_perturb = 1 if p < 0.7 else 2 if p < 0.9 else 3
            
            candidate = current_points.copy()
            for _ in range(n_perturb):
                idx = rng.integers(0, 11)
                perturbation = rng.normal(0, step, size=2)
                candidate[idx] += perturbation

            # Skip if outside triangle
            if not is_inside_triangle(candidate, A, B, C):
                stagnation_count += 1
                continue

            score = get_smallest_triangle_area(candidate)
            delta = score - current_score

            # Simulated annealing acceptance
            if delta > 0:
                current_points, current_score = candidate, score
                if score > best_score:
                    best_points, best_score = candidate, score
                    stagnation_count = 0
                else:
                    stagnation_count += 1
            else:
                if rng.random() < np.exp(delta / T):
                    current_points, current_score = candidate, score
                stagnation_count += 1

        return best_points

    return improve