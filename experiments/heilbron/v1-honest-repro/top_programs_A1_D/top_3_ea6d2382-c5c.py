from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib

def entrypoint():
    A, B, C = get_unit_triangle()
    # Precompute constants for barycentric conversion
    denom = (B[1]-C[1])*(A[0]-C[0]) + (C[0]-B[0])*(A[1]-C[1])
    side_length = np.linalg.norm(B - A)
    target_max_area = 0.0365  # Known theoretical upper bound for 11 points

    # Helper functions for coordinate conversion
    def cartesian_to_barycentric(p):
        u = ((B[1]-C[1])*(p[0]-C[0]) + (C[0]-B[0])*(p[1]-C[1])) / denom
        v = ((C[1]-A[1])*(p[0]-C[0]) + (A[0]-C[0])*(p[1]-C[1])) / denom
        w = 1 - u - v
        return np.array([u, v, w])

    def barycentric_to_cartesian(bary):
        return bary[0]*A + bary[1]*B + bary[2]*C

    def get_k_smallest_triangle_indices(points, k=3):
        n = points.shape[0]
        areas = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        (points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                        (points[k,0]-points[i,0])*(points[j,1]-points[i,1])
                    )
                    areas.append((area, (i, j, k)))
        
        # Sort by area and return top k
        areas.sort(key=lambda x: x[0])
        return areas[:k]

    def get_adaptive_seed(points):
        # Create a hash of the input points for seed derivation
        points_bytes = points.tobytes()
        hash_obj = hashlib.sha256(points_bytes)
        hash_int = int(hash_obj.hexdigest(), 16)
        return hash_int % 100000  # Keep seed in reasonable range

    def improve(points: np.ndarray) -> np.ndarray:
        # Derive seed from input for adaptive yet reproducible exploration
        seed = get_adaptive_seed(points)
        rng = np.random.RandomState(seed)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)

        # Initialize adaptive temperature
        initial_temperature = max(0.001, best_score * 0.3)
        cooling_rate = 0.995
        max_iterations = 1000
        no_improve_limit = 200
        no_improve_count = 0

        T = initial_temperature
        for i in range(max_iterations):
            # Check for early stopping
            if no_improve_count >= no_improve_limit:
                break

            # Multi-bottleneck targeting: get top 3 smallest triangles
            smallest_triangles = get_k_smallest_triangle_indices(best, k=3)
            
            # Select a triangle with probability weighted by inverse area
            weights = [1.0 / (area + 1e-10) for area, _ in smallest_triangles]
            weights = np.array(weights) / sum(weights)
            selected_idx = rng.choice(len(smallest_triangles), p=weights)
            _, min_indices = smallest_triangles[selected_idx]

            # Multi-point perturbation with 10% probability
            num_points_to_perturb = 1
            if rng.rand() < 0.1:  # 10% chance for coordinated move
                num_points_to_perturb = rng.randint(2, min(3, len(min_indices) + 1))
            
            # Select points to perturb (random subset of the bottleneck triangle)
            idxs = rng.choice(min_indices, size=num_points_to_perturb, replace=False)

            # Adaptive step size scaled by current min_area
            step_size_base = 0.02
            step_size_factor = 0.1 + 0.9 * (best_score / target_max_area)
            step_size_cartesian = step_size_base * step_size_factor * (T / initial_temperature)
            step_size_bary = step_size_cartesian / side_length

            candidate = best.copy()
            improved = False
            
            for idx in idxs:
                # Barycentric perturbation with constraint handling
                bary = cartesian_to_barycentric(best[idx])
                noise = rng.normal(0, step_size_bary, 3)
                new_bary = np.maximum(bary + noise, 0)
                new_bary = new_bary / np.sum(new_bary)
                candidate_point = barycentric_to_cartesian(new_bary)
                
                # Only update if point stays inside triangle (should always be true with barycentric)
                if is_inside_triangle(candidate_point, A, B, C):
                    candidate[idx] = candidate_point
                    improved = True

            # Skip evaluation if candidate wasn't properly updated
            if not improved:
                continue

            # Evaluate candidate
            score = get_smallest_triangle_area(candidate)

            # Simulated annealing acceptance
            delta = score - best_score
            if delta > 0 or (delta > -1e-10 and rng.rand() < np.exp(delta / T)):
                best = candidate
                best_score = score
                no_improve_count = 0
            else:
                no_improve_count += 1

            # Cool temperature
            T *= cooling_rate

        return best

    return improve