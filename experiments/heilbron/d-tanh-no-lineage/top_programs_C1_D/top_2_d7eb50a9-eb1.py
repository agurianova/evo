from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib


def entrypoint():
    A, B, C = get_unit_triangle()
    triangle_height = np.linalg.norm((B - A) / 2 + (C - A))
    boundary_buffer = 0.005 * triangle_height  # 0.5% buffer from edges

    def config_dependent_seed(points):
        # Create a deterministic but unique seed for each configuration
        points_bytes = points.tobytes()
        hash_obj = hashlib.sha256(points_bytes)
        seed = int(hash_obj.hexdigest()[:15], 16) % (2**32 - 1)
        return seed

    def poisson_disk_sample(existing_points, initial_min_area, max_attempts=100):
        """Generate a new point using adaptive Poisson disk sampling relative to existing points"""
        # Adaptive minimum distance based on current configuration density
        min_dist = 0.08 * np.sqrt(initial_min_area / 0.0365)
        
        for _ in range(max_attempts):
            # Random barycentric coordinates
            u = np.random.rand()
            v = np.random.rand()
            if u + v > 1:
                u = 1 - u
                v = 1 - v
            P = A + u * (B - A) + v * (C - A)
            
            if not is_inside_triangle(P.reshape(1, 2), A, B, C):
                continue
                
            # Check distance to existing points
            too_close = False
            for p in existing_points:
                if np.linalg.norm(P - p) < min_dist:
                    too_close = True
                    break
                    
            if not too_close:
                return P
                
        # Fallback: random point inside triangle with boundary buffer
        u = np.random.rand()
        v = np.random.rand()
        if u + v > 1:
            u = 1 - u
            v = 1 - v
        P = A + u * (B - A) + v * (C - A)
        return project_point_to_buffered_triangle(P, A, B, C, boundary_buffer)

    def improve(points: np.ndarray) -> np.ndarray:
        # Create configuration-dependent random seed
        seed = config_dependent_seed(points)
        rng = np.random.default_rng(seed)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        initial_min_area = best_score
        
        # Linear step size adaptation based on problem difficulty
        base_step = 0.05 * ((0.0365 - initial_min_area) / 0.0365 * 0.09 + 0.01)
        T0 = 0.1 * base_step
        cooling_rate = 0.99
        T = T0
        
        # Allocate more iterations to hard problems (near optimal)
        total_iterations = min(500, max(100, 100 + 400 * (initial_min_area / 0.0365)))
        no_improve_count = 0
        stagnation_count = 0
        
        # Critical points tolerance with absolute floor
        tolerance = max(0.001, 0.05 * initial_min_area)

        for iteration in range(int(total_iterations)):
            # Identify critical points (vertices of smallest triangles)
            critical_points = set()
            n = best.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        # Compute triangle area
                        area = 0.5 * abs((best[j,0]-best[i,0])*(best[k,1]-best[i,1]) - 
                                      (best[k,0]-best[i,0])*(best[j,1]-best[i,1]))
                        # Adaptive tolerance based on current min_area
                        if area <= best_score * (1 + tolerance):
                            critical_points.add(i)
                            critical_points.add(j)
                            critical_points.add(k)

            # Adaptive number of points to perturb based on configuration difficulty
            num_perturb = min(6, max(2, int(3 * (initial_min_area / 0.0365))))
            
            # Select points to perturb: focus on critical points
            if critical_points:
                indices = rng.choice(list(critical_points), size=min(num_perturb, len(critical_points)), replace=False)
            else:
                indices = rng.choice(11, size=min(num_perturb, 11), replace=False)

            candidate = best.copy()
            # Perturb selected points with adaptive step size (square root decay)
            step_size = base_step * np.sqrt(T / T0)
            for idx in indices:
                perturbation = rng.normal(0, step_size, size=2)
                candidate[idx] += perturbation

            # Project any outside points to buffered triangle boundary
            for i in range(11):
                if not is_inside_triangle(candidate[i:i+1], A, B, C):
                    candidate[i] = project_point_to_buffered_triangle(candidate[i], A, B, C, boundary_buffer)

            # Validate candidate has no collinear points (relaxed threshold)
            score = get_smallest_triangle_area(candidate)
            if score <= 1e-10:
                no_improve_count += 1
                stagnation_count += 1
                T *= cooling_rate
                continue

            # Simulated annealing acceptance
            delta = score - best_score
            if delta > 0 or rng.random() < np.exp(delta / T):
                best = candidate
                best_score = score
                no_improve_count = 0
                stagnation_count = 0
            else:
                no_improve_count += 1
                stagnation_count += 1

            # Cooling
            T *= cooling_rate
            
            # Reheating: restart exploration when stuck
            reheating_threshold = max(20, min(100, 30 + 70 * (1 - initial_min_area / 0.0365)))
            if no_improve_count >= reheating_threshold:
                T = T0
                no_improve_count = 0

            # Hybrid search: add occasional large jumps for global exploration
            if stagnation_count >= reheating_threshold * 1.5:
                # Replace adaptive percentage of points with new Poisson disk samples
                num_replace = max(1, min(5, int(11 * (1 - initial_min_area / 0.0365))))
                replace_indices = rng.choice(11, size=num_replace, replace=False)
                
                for idx in replace_indices:
                    # Create list of other points for Poisson disk sampling
                    other_points = np.delete(best, idx, axis=0)
                    new_point = poisson_disk_sample(other_points, initial_min_area)
                    best[idx] = new_point
                    
                # Recalculate score after replacement
                best_score = get_smallest_triangle_area(best)
                stagnation_count = 0

        return best

    def project_point_to_buffered_triangle(p, A, B, C, buffer):
        """Project point to triangle with inward buffer to avoid boundary degeneracies"""
        def distance_to_segment(p, a, b):
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / np.dot(ab, ab)
            t = np.clip(t, 0.0, 1.0)
            projection = a + t * ab
            return np.linalg.norm(p - projection), projection

        # Calculate distances to all edges
        d_ab, proj_ab = distance_to_segment(p, A, B)
        d_bc, proj_bc = distance_to_segment(p, B, C)
        d_ca, proj_ca = distance_to_segment(p, C, A)

        # If point is inside with sufficient buffer, return as-is
        min_dist = min(d_ab, d_bc, d_ca)
        if min_dist > buffer:
            return p

        # Find closest edge and move inward by buffer
        if d_ab <= d_bc and d_ab <= d_ca:
            direction = (C - A) / np.linalg.norm(C - A)  # Perpendicular to AB
            direction = np.array([-direction[1], direction[0]])
            return proj_ab + buffer * direction / np.linalg.norm(direction)
        elif d_bc <= d_ab and d_bc <= d_ca:
            direction = (A - B) / np.linalg.norm(A - B)  # Perpendicular to BC
            direction = np.array([-direction[1], direction[0]])
            return proj_bc + buffer * direction / np.linalg.norm(direction)
        else:
            direction = (B - C) / np.linalg.norm(B - C)  # Perpendicular to CA
            direction = np.array([-direction[1], direction[0]])
            return proj_ca + buffer * direction / np.linalg.norm(direction)

    return improve