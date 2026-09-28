from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Precompute triangle edges for boundary distance calculations
    def point_to_line_distance(point, p1, p2):
        # Vector from p1 to p2
        line_vec = p2 - p1
        # Vector from p1 to point
        point_vec = point - p1
        # Length of the line
        line_len = np.linalg.norm(line_vec)
        # Normalize line vector
        line_unitvec = line_vec / line_len
        # Project point_vec onto line_unitvec
        proj = np.dot(point_vec, line_unitvec)
        # Ensure projection is within line segment
        if proj < 0:
            return np.linalg.norm(point - p1)
        elif proj > line_len:
            return np.linalg.norm(point - p2)
        else:
            # Calculate perpendicular distance
            proj_vec = line_unitvec * proj
            closest_point = p1 + proj_vec
n            return np.linalg.norm(point - closest_point)

    def boundary_proximity(point):
        # Calculate distance to each edge
        d1 = point_to_line_distance(point, A, B)
        d2 = point_to_line_distance(point, B, C)
        d3 = point_to_line_distance(point, C, A)
        return min(d1, d2, d3)

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        step_size = 0.05
        no_improve_count = 0
        max_iter = 500
        restart_threshold = 50  # Increased from previous threshold
        
        for iteration in range(max_iter):
            if no_improve_count >= restart_threshold:
                # Strategic restart: perturb best solution instead of just reducing step size
                perturbation = 0.1 * step_size
                perturbed = best.copy()
                for i in range(len(perturbed)):
                    angle = np.random.uniform(0, 2 * np.pi)
                    dx = perturbation * np.cos(angle)
                    dy = perturbation * np.sin(angle)
                    test_point = perturbed[i] + np.array([dx, dy])
                    if is_inside_triangle(test_point, A, B, C):
                        perturbed[i] = test_point
                
                # Evaluate perturbed solution
                perturbed_score = get_smallest_triangle_area(perturbed)
                if perturbed_score > best_score:
                    best, best_score = perturbed, perturbed_score
                
                # Reset search state
                no_improve_count = 0
                step_size = 0.05  # Reset to initial step size

            # Find ALL critical triplets (within epsilon of min area)
            min_area_val = float('inf')
            all_triplets = []
            critical_triplets = []
            epsilon = 1e-5
            n = len(best)
            
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = 0.5 * abs(
                            (best[j,0] - best[i,0]) * (best[k,1] - best[i,1]) - 
                            (best[j,1] - best[i,1]) * (best[k,0] - best[i,0])
                        )
                        all_triplets.append((area, i, j, k))
                        if area < min_area_val:
                            min_area_val = area

            # Collect all triplets within epsilon of minimum
            for area, i, j, k in all_triplets:
                if abs(area - min_area_val) < epsilon:
                    critical_triplets.append((i, j, k))

            if not critical_triplets:
                break

            # Determine move type: 70% one-point, 30% two-point
            use_two_point = np.random.rand() < 0.3

            if use_two_point and len(critical_triplets) > 1:
                # Try to find two points that appear in multiple critical triplets
                point_counts = np.zeros(n, dtype=int)
                for triplet in critical_triplets:
                    for idx in triplet:
                        point_counts[idx] += 1
                
                # Get top 2 points that appear most frequently in critical triplets
                top_points = np.argsort(-point_counts)[:2]
                if point_counts[top_points[0]] > 0 and point_counts[top_points[1]] > 0:
                    idx1, idx2 = top_points
                    
                    # Calculate optimal move directions for both points
                    directions = []
                    for idx in [idx1, idx2]:
                        # Find a critical triplet containing this point
                        for triplet in critical_triplets:
                            if idx in triplet:
                                others = [x for x in triplet if x != idx]
                                a, b = best[others[0]], best[others[1]]
                                
                                # Compute gradient direction for area increase
                                v = b - a
                                cross = v[0]*(best[idx,1]-a[1]) - v[1]*(best[idx,0]-a[0])
                                n_vec = np.array([-v[1], v[0]])
                                if cross < 0:
                                    n_vec = -n_vec
                                
                                norm = np.linalg.norm(n_vec)
                                if norm > 1e-5:
                                    n_vec = n_vec / norm
                                    directions.append(n_vec)
                                break

                    if len(directions) == 2:
                        # Create candidate with both points moved
                        candidate = best.copy()
                        
                        # Adaptive step size based on boundary proximity
                        prox1 = boundary_proximity(best[idx1])
                        prox2 = boundary_proximity(best[idx2])
                        adaptive_step1 = step_size * min(1.0, 5.0 * prox1)
                        adaptive_step2 = step_size * min(1.0, 5.0 * prox2)
                        
                        candidate[idx1] = best[idx1] + adaptive_step1 * directions[0]
                        candidate[idx2] = best[idx2] + adaptive_step2 * directions[1]

                        # Check containment
                        if (is_inside_triangle(candidate[idx1], A, B, C) and 
                            is_inside_triangle(candidate[idx2], A, B, C)):
                            
                            # Evaluate candidate
                            new_score = get_smallest_triangle_area(candidate)

                            # Temperature schedule - slower cooling
                            T = 0.5 * (1 - iteration / max_iter) ** 0.5
                            if T < 1e-6:
                                T = 0

                            if new_score > best_score:
                                best = candidate
                                best_score = new_score
                                no_improve_count = 0
                            else:
                                if T > 0:
                                    delta = new_score - best_score
                                    if np.random.rand() < np.exp(delta / T):
                                        best = candidate
                                        best_score = new_score
                                        no_improve_count = 0
                                    else:
                                        no_improve_count += 1
                                else:
                                    no_improve_count += 1
                        else:
                            no_improve_count += 1
                    else:
                        use_two_point = False

            if not use_two_point:
                # One-point move - evaluate all options and pick best
                best_candidate = None
                best_new_score = best_score
                
                for triplet in critical_triplets:
                    for idx in triplet:
                        others = [x for x in triplet if x != idx]
                        a, b = best[others[0]], best[others[1]]

                        # Compute gradient direction for area increase
                        v = b - a
                        cross = v[0]*(best[idx,1]-a[1]) - v[1]*(best[idx,0]-a[0])
                        n_vec = np.array([-v[1], v[0]])
                        if cross < 0:
                            n_vec = -n_vec
                        
                        norm = np.linalg.norm(n_vec)
                        if norm < 1e-5:
                            continue
                        n_vec = n_vec / norm

                        # Adaptive step size based on boundary proximity
                        prox = boundary_proximity(best[idx])
                        adaptive_step = step_size * min(1.0, 5.0 * prox)
                        
                        candidate = best.copy()
                        candidate[idx] = best[idx] + adaptive_step * n_vec

                        # Check containment
                        if not is_inside_triangle(candidate[idx], A, B, C):
                            continue

                        # Evaluate candidate
                        new_score = get_smallest_triangle_area(candidate)
                        
                        if new_score > best_new_score:
                            best_new_score = new_score
                            best_candidate = candidate

                if best_candidate is not None:
                    # Temperature schedule - slower cooling
                    T = 0.5 * (1 - iteration / max_iter) ** 0.5
                    if T < 1e-6:
                        T = 0

                    if best_new_score > best_score:
                        best = best_candidate
                        best_score = best_new_score
                        no_improve_count = 0
                    else:
                        if T > 0:
                            delta = best_new_score - best_score
                            if np.random.rand() < np.exp(delta / T):
                                best = best_candidate
                                best_score = best_new_score
                                no_improve_count = 0
                            else:
                                no_improve_count += 1
                        else:
                            no_improve_count += 1
                else:
                    no_improve_count += 1

        return best

    return improve