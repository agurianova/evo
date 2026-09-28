from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        def compute_min_area_and_triplet(coords):
            n = coords.shape[0]
            min_area = float('inf')
            best_triplet = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = coords[i], coords[j], coords[k]
                        area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        if area_val < min_area:
                            min_area = area_val
                            best_triplet = (i, j, k)
            return min_area, best_triplet
        
        # Function to compute gradient for a specific point in a triangle
        def compute_point_gradient(coords, point_idx, triangle_indices):
            i, j, k = triangle_indices
            a, b, c = coords[i], coords[j], coords[k]
            
            # Determine which point we're moving
            if point_idx == i:
                ref1, ref2 = b, c
            elif point_idx == j:
                ref1, ref2 = a, c
            else:  # point_idx == k
                ref1, ref2 = a, b
            
            # Compute gradient for the moving point
            S = (ref1[0]-a[0])*(ref2[1]-a[1]) - (ref1[1]-a[1])*(ref2[0]-a[0])
            sign_S = 1 if S >= 0 else -1
            grad_x = (ref1[1] - ref2[1]) * sign_S
            grad_y = (ref2[0] - ref1[0]) * sign_S
            grad = np.array([grad_x, grad_y])
            
            grad_norm = np.linalg.norm(grad)
            if grad_norm > 1e-8:
                grad = grad / grad_norm
            else:
                grad = np.random.normal(0, 1, size=2)
                grad = grad / np.linalg.norm(grad)
            
            return grad

        # Find smallest triangle involving a specific point
        def find_smallest_triangle_with_point(coords, point_idx):
            n = coords.shape[0]
            min_area = float('inf')
            best_triplet = None
            
            for i in range(n):
                if i == point_idx:
                    continue
                for j in range(i+1, n):
                    if j == point_idx:
                        continue
                    k = point_idx
                    a, b, c = coords[i], coords[j], coords[k]
                    area_val = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    if area_val < min_area:
                        min_area = area_val
                        best_triplet = (i, j, k)
            
            return min_area, best_triplet

        max_rounds = 500  # Increased from 200 to address insufficient iterations
        initial_step = 0.05
        T0 = 0.01  # Increased from 0.001 to enable better exploration
        alpha = 0.99  # Slowed cooling from 0.95 to 0.99

        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score

        for round_idx in range(max_rounds):
            current_score, triplet = compute_min_area_and_triplet(current)
            
            # Dynamic bias scheduling - starts at 0.5, increases to 0.95
            bias = 0.5 + 0.45 * (round_idx / max_rounds)
            
            # Point selection with dynamic bias
            if np.random.rand() < bias:
                idx = np.random.choice(triplet)
            else:
                idx = np.random.randint(0, 11)
            
            # Adaptive step size - slower decay and scaled by current min_area
            step = initial_step * (0.95 ** (round_idx / 10)) * (current_score / 0.0365)
            
            candidate = current.copy()
            
            # Directed move for ALL points (critical and non-critical)
            if idx in triplet:
                # For critical points, use the existing gradient approach
                other_indices = [x for x in triplet if x != idx]
                a, b, c = candidate[idx], candidate[other_indices[0]], candidate[other_indices[1]]
                S = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                sign_S = 1 if S >= 0 else -1
                grad_x = (b[1] - c[1]) * sign_S
                grad_y = (c[0] - b[0]) * sign_S
                grad = np.array([grad_x, grad_y])
                
                grad_norm = np.linalg.norm(grad)
                if grad_norm > 1e-8:
                    grad = grad / grad_norm
                else:
                    grad = np.random.normal(0, 1, size=2)
                    grad = grad / np.linalg.norm(grad)
                
                candidate[idx] += grad * step
            else:
                # For non-critical points, compute gradient for smallest triangle involving the point
                _, smallest_triplet = find_smallest_triangle_with_point(candidate, idx)
                if smallest_triplet:
                    grad = compute_point_gradient(candidate, idx, smallest_triplet)
                    candidate[idx] += grad * step
                else:
                    # Fallback to random if no valid triangle found (shouldn't happen with 11 points)
                    candidate[idx] += np.random.normal(0, step, size=2)

            # Containment check
            if not is_inside_triangle(candidate, A, B, C):
                continue

            new_score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            if new_score > current_score:
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
            else:
                delta = current_score - new_score
                T = T0 * (alpha ** round_idx)
                if np.random.rand() < np.exp(-delta / T):
                    current = candidate
                    current_score = new_score

        return best

    return improve