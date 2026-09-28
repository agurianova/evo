from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def get_smallest_triangle_indices(points, k=1):
    """Return indices of the k smallest triangles."""
    n = len(points)
    areas = []
    
    for i in range(n):
        for j in range(i+1, n):
            for k_idx in range(j+1, n):
                # Create triangle with these three points
                triangle = np.array([points[i], points[j], points[k_idx]])
                # Calculate area using cross product
                area = 0.5 * abs(
                    (triangle[1,0] - triangle[0,0]) * (triangle[2,1] - triangle[0,1]) -
                    (triangle[2,0] - triangle[0,0]) * (triangle[1,1] - triangle[0,1])
                )
                areas.append((area, (i, j, k_idx)))
    
    # Sort by area and return top k
    areas.sort(key=lambda x: x[0])
    return [indices for _, indices in areas[:k]]

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        seed = abs(hash(points.tobytes())) % (2**32)
        rng = np.random.default_rng(seed)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        
        total_iterations = 500
        early_stop_patience = 30
        T0 = 0.01
        base_ratio = 0.5
        no_improve_count = 0
        base_bottleneck_rate = 0.5  # Base rate for bottleneck targeting

        for i in range(total_iterations):
            # Faster step size decay
            exponent = i / (total_iterations * 1.5)
            sigma = 0.03 * (base_ratio) ** exponent
            
            # Exponential temperature decay for longer exploration
            T = T0 * (0.99 ** i)
            
            # Adaptive bottleneck targeting rate based on stagnation
            bottleneck_rate = base_bottleneck_rate
            if no_improve_count > early_stop_patience * 0.5:
                bottleneck_rate = min(0.8, base_bottleneck_rate + 0.3 * (no_improve_count / early_stop_patience))

            # Multi-triangle targeting: top-3 smallest triangles
            if rng.random() < bottleneck_rate:
                smallest_triangles = get_smallest_triangle_indices(current, k=3)
                # Collect all unique points from the smallest triangles
                indices = list(set(idx for triangle in smallest_triangles for idx in triangle))
                # Limit to 3-5 points for perturbation to avoid excessive changes
                num_points = min(max(3, len(indices)), 5)
                indices = rng.choice(indices, size=num_points, replace=False).tolist()
            else:
                # Perturbation scope: 70% single point, 30% multi-point
                if rng.random() < 0.3:
                    num_points = rng.choice([2, 3, 4])
                    indices = rng.choice(11, size=num_points, replace=False).tolist()
                else:
                    indices = [rng.choice(11)]

            candidate = current.copy()
            for idx in indices:
                candidate[idx] += rng.normal(0, sigma, size=2)

            if not is_inside_triangle(candidate, A, B, C):
                continue

            score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
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

            # Multi-triangle escape from stagnation (replaces gradient escape)
            if no_improve_count >= early_stop_patience:
                # Increase focus on bottleneck triangles
                smallest_triangles = get_smallest_triangle_indices(current, k=3)
                indices = list(set(idx for triangle in smallest_triangles for idx in triangle))
                
                # Perturb points from smallest triangles with larger step
                candidate_try = current.copy()
                for idx in indices:
                    # Use larger step for escape: 1.5 * current sigma
                    candidate_try[idx] += rng.normal(0, 1.5 * sigma, size=2)
                
                if is_inside_triangle(candidate_try, A, B, C):
                    score_try = get_smallest_triangle_area(candidate_try)
                    delta_try = score_try - current_score
n                    # Accept with higher probability for escape moves
                    if score_try > current_score or (delta_try > -0.0005 and rng.random() < np.exp(delta_try / (T * 2))):
                        current = candidate_try
                        current_score = score_try
                        no_improve_count = 0
                        if score_try > best_score:
                            best = candidate_try
                            best_score = score_try
                        continue

                # Fall back to amplified random restart with adaptive step size
                current = best.copy()
                current_score = best_score
                no_improve_count = 0
                restart_indices = rng.choice(11, size=rng.choice([2, 3]), replace=False)
                for idx in restart_indices:
                    # Adaptive step size based on current exploration radius
                    current[idx] += rng.normal(0, 1.5 * sigma, size=2)
                
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