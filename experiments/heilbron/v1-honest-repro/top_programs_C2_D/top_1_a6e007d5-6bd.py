from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import itertools

np.random.seed(42)

def entrypoint():
    A_big, B_big, C_big = get_unit_triangle()

    def project_to_triangle(point):
        # Simple projection: if outside, move toward nearest edge
        # This is a basic implementation - could be improved with proper barycentric projection
        if not is_inside_triangle(point, A_big, B_big, C_big):
            # Try moving toward centroid
            centroid = (A_big + B_big + C_big) / 3
            direction = centroid - point
            for t in np.linspace(0.1, 1.0, 10):
                candidate = point + t * direction
                if is_inside_triangle(candidate, A_big, B_big, C_big):
                    return candidate
            # Fallback: return original point (shouldn't happen with centroid approach)
            return point
        return point

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        max_iter = 300  # Increased from 200 for harder opponents
        initial_step = 0.05
        initial_temp = 0.01
        cooling_rate = 0.99
        temp = initial_temp
        
        # Track acceptance rate for adaptive cooling
        accepted_count = 0
        
        # Consider k smallest triangles to avoid bottlenecks
        k_smallest = 3
        
        for iter in range(max_iter):
            # Find the k smallest triangle triplets
            triangle_areas = []
            for triplet in itertools.combinations(range(11), 3):
                i, j, k = triplet
                A_pt = current[i]
                B_pt = current[j]
                C_pt = current[k]
                signed_area = (B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (B_pt[1]-A_pt[1])*(C_pt[0]-A_pt[0])
                abs_area = 0.5 * abs(signed_area)
                triangle_areas.append((abs_area, triplet))
            
            # Sort and take k smallest
            triangle_areas.sort(key=lambda x: x[0])
            candidate_triplets = [ta[1] for ta in triangle_areas[:k_smallest]]
            
            # Randomly select from candidate triplets
            best_triplet = candidate_triplets[np.random.randint(len(candidate_triplets))]
            
            if best_triplet is None:
                continue
                
            i, j, k = best_triplet
            
            # Evaluate all 3 points to find which one gives best potential improvement
            best_idx = None
            best_improvement = -np.inf
            
            for idx in [i, j, k]:
                others = [x for x in [i, j, k] if x != idx]
                P = current[idx]
                Q = current[others[0]]
                R = current[others[1]]
                
                # Compute signed area for triangle (P, Q, R)
                s = (Q[0]-P[0])*(R[1]-P[1]) - (Q[1]-P[1])*(R[0]-P[0])
                # Compute direction vector
                dir_vec = np.sign(s) * np.array([Q[1]-R[1], R[0]-Q[0]])
                norm_dir = np.linalg.norm(dir_vec)
                if norm_dir < 1e-10:
                    continue
                dir_vec = dir_vec / norm_dir
                
                # Calculate potential improvement
                step_size = initial_step * temp / initial_temp  # Proportional to temperature
                candidate_point = P + step_size * dir_vec
                candidate = current.copy()
                candidate[idx] = candidate_point
                
                # Check if inside triangle
                if not is_inside_triangle(candidate, A_big, B_big, C_big):
                    candidate_point = project_to_triangle(candidate_point)
                    candidate[idx] = candidate_point
                    
                new_score = get_smallest_triangle_area(candidate)
                improvement = new_score - current_score
                
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_idx = idx
                    best_dir_vec = dir_vec

            if best_idx is None:
                continue
                
            # Now move the best point
            P = current[best_idx]
            step_size = initial_step * temp / initial_temp
            
            # Attempt move with boundary retries
            candidate = current.copy()
            valid = False
            for retry in range(10):  # Increased from 5
                candidate_point = P + step_size * best_dir_vec
                candidate[best_idx] = candidate_point
                
                if not is_inside_triangle(candidate, A_big, B_big, C_big):
                    # Use projection instead of just halving step
                    candidate_point = project_to_triangle(candidate_point)
                    candidate[best_idx] = candidate_point
                    
                if is_inside_triangle(candidate, A_big, B_big, C_big):
                    valid = True
                    break
                
                step_size *= 0.5
            
            if not valid:
                continue
                
            new_score = get_smallest_triangle_area(candidate)
            delta = new_score - current_score
            
            # Simulated annealing acceptance
            if delta > 0 or np.random.rand() < np.exp(delta / temp):
                current = candidate
                current_score = new_score
                accepted_count += 1
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
            
            # Adaptive cooling: cool based on acceptance rate
            if accepted_count >= 10:
                temp *= cooling_rate
                accepted_count = 0

        return best

    return improve