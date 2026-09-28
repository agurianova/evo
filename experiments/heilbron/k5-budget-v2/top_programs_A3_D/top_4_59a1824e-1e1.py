from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_triangle(point, A, B, C):
        """Project point to nearest point on triangle boundary if outside."""
        if is_inside_triangle(point, A, B, C):
            return point
        
        # Calculate distances to each edge and find closest projection
        def distance_to_edge(p, v1, v2):
            edge = v2 - v1
            edge_length_sq = np.dot(edge, edge)
            if edge_length_sq < 1e-10:  # Degenerate edge
                return np.linalg.norm(p - v1), v1
            
            t = max(0, min(1, np.dot(p - v1, edge) / edge_length_sq))
            projection = v1 + t * edge
            return np.linalg.norm(p - projection), projection
        
        d1, p1 = distance_to_edge(point, A, B)
        d2, p2 = distance_to_edge(point, B, C)
        d3, p3 = distance_to_edge(point, C, A)
        
        if d1 <= d2 and d1 <= d3:
            return p1
        elif d2 <= d1 and d2 <= d3:
            return p2
        else:
            return p3

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)

        # Enhanced simulated annealing parameters
        initial_temp = 0.05  # Reduced from 0.1 for better initial focus
        cooling_rate = 0.92  # Changed from 0.98 to balance exploration/exploitation
        temp = initial_temp
        step_size = 0.015  # Reduced from 0.05 for better precision
        max_iter = 500
        tol = 1e-5

        # Precompute all triangle indices for incremental updates
        n = 11
        triangle_indices = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    triangle_indices.append((i, j, k))
        
        # Cache areas for incremental computation
        areas = np.zeros(len(triangle_indices))
        for idx, (i, j, k) in enumerate(triangle_indices):
            A_pt, B_pt, C_pt = current[i], current[j], current[k]
            areas[idx] = 0.5 * abs((B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - 
                                 (B_pt[1]-A_pt[1])*(C_pt[0]-A_pt[0]))
        
        min_area_val = np.min(areas)
        best_configuration = current.copy()
        best_score = current_score
        no_improve_count = 0
        stagnation_threshold = 50

        # Main optimization loop
        for i in range(max_iter):
            # Identify critical triangles (adaptive threshold: 5-10% of total triangles)
            min_area_val = np.min(areas)
            adaptive_threshold = 1.1 * min_area_val
            critical_indices = np.where(areas <= adaptive_threshold)[0]
            # Ensure adaptive number of critical triangles (5-10% of total)
            min_critical = max(5, int(0.07 * len(triangle_indices)))
            if len(critical_indices) < min_critical:
                critical_indices = np.argsort(areas)[:min_critical]
            critical_triangles = [triangle_indices[idx] for idx in critical_indices]
            
            # Collect all points in critical triangles
            critical_points = set()
            for tri in critical_triangles:
                critical_points.update(tri)
            critical_points = list(critical_points)

            if not critical_points:
                break

            # Compute weighted gradient directions for each critical point
            move_directions = np.zeros((n, 2))
            for point_idx in critical_points:
                total_direction = np.zeros(2)
                total_weight = 0.0
                
                # Find all critical triangles containing this point
                for tri_idx in critical_indices:
                    if point_idx in triangle_indices[tri_idx]:
                        i1, i2, i3 = triangle_indices[tri_idx]
                        # Identify the other two points in the triangle
                        other_points = [idx for idx in (i1, i2, i3) if idx != point_idx]
                        A_pt = current[other_points[0]]
                        B_pt = current[other_points[1]]
                        C_pt = current[point_idx]
                        
                        s = 0.5 * ((B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - 
                                  (B_pt[1]-A_pt[1])*(C_pt[0]-A_pt[0]))
                        base_vec = B_pt - A_pt
                        direction = np.array([-base_vec[1], base_vec[0]])
                        if s < 0:
                            direction = -direction
                        
                        # Use square root weighting for stability (fixes numerical instability)
                        weight = 1.0 / np.sqrt(areas[tri_idx] + 1e-10)
                        total_direction += weight * direction
                        total_weight += weight

                if total_weight > 1e-10:
                    move_directions[point_idx] = total_direction / total_weight

            # Apply multi-point perturbation
            candidate = current.copy()
            moved_points = []
            
            for point_idx in critical_points:
                if np.linalg.norm(move_directions[point_idx]) > 1e-10:
                    candidate[point_idx] = current[point_idx] + step_size * move_directions[point_idx]
                    moved_points.append(point_idx)

            # Boundary handling with geometric projection
            if not is_inside_triangle(candidate, A, B, C):
                for point_idx in moved_points:
                    if not is_inside_triangle(candidate[point_idx], A, B, C):
                        candidate[point_idx] = project_to_triangle(candidate[point_idx], A, B, C)

            # Incremental area update for affected triangles
            new_areas = areas.copy()
            affected_indices = []
            for idx, (i, j, k) in enumerate(triangle_indices):
                if i in moved_points or j in moved_points or k in moved_points:
                    A_pt, B_pt, C_pt = candidate[i], candidate[j], candidate[k]
                    new_areas[idx] = 0.5 * abs((B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - 
                                         (B_pt[1]-A_pt[1])*(C_pt[0]-A_pt[0]))
                    affected_indices.append(idx)
            
            new_min_area = np.min(new_areas)

            # Simulated annealing acceptance
            if new_min_area > current_score:
                current, current_score, areas = candidate, new_min_area, new_areas
            else:
                delta = new_min_area - current_score
                if np.random.rand() < np.exp(delta / temp):
                    current, current_score, areas = candidate, new_min_area, new_areas

            # Update best configuration if improved
            if current_score > best_score:
                best_score = current_score
                best_configuration = current.copy()

            # Update optimization parameters
            temp *= cooling_rate
            if (i+1) % 50 == 0:
                step_size *= 0.995

            # Stagnation recovery with diversity injection
            if current_score > best_score - 1e-8:
                no_improve_count = 0
            else:
                no_improve_count += 1

            if no_improve_count >= stagnation_threshold:
                # Inject diversity while preserving best solution
                current = best_configuration.copy()
                current_score = best_score
                
                # Add controlled random perturbations to escape local optima
                for idx in range(n):
                    if np.random.rand() < 0.3:  # Perturb 30% of points
                        current[idx] += np.random.uniform(-0.005, 0.005, size=2)
                        if not is_inside_triangle(current[idx], A, B, C):
                            current[idx] = project_to_triangle(current[idx], A, B, C)
                
                # Recompute areas for current configuration
                for idx, (i, j, k) in enumerate(triangle_indices):
                    A_pt, B_pt, C_pt = current[i], current[j], current[k]
                    areas[idx] = 0.5 * abs((B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - 
                                         (B_pt[1]-A_pt[1])*(C_pt[0]-A_pt[0]))
                current_score = np.min(areas)
                
                # Reset optimization parameters for new exploration
                temp = initial_temp * 0.7
                step_size = 0.01
                no_improve_count = 0

        # Final strategic point swap phase to escape local optima
        final_candidate = best_configuration.copy()
        final_score = best_score
        
        # Identify critical points (in smallest triangles) and non-critical points
        critical_indices = np.argsort(areas)[:5]  # Top 5 smallest triangles
        critical_points = set()
        for idx in critical_indices:
            i, j, k = triangle_indices[idx]
            critical_points.update([i, j, k])
        critical_points = list(critical_points)
        non_critical_points = [i for i in range(n) if i not in critical_points]
        
        # Try strategic swaps between critical and non-critical regions
        if len(critical_points) > 0 and len(non_critical_points) > 0:
            for _ in range(10):  # Try up to 10 swaps
                # Select one point from critical region and one from non-critical
                c_idx = np.random.choice(critical_points)
                nc_idx = np.random.choice(non_critical_points)
                
                # Swap the points
                swapped = final_candidate.copy()
                swapped[c_idx], swapped[nc_idx] = final_candidate[nc_idx].copy(), final_candidate[c_idx].copy()
                
                # Ensure points remain inside triangle
                if is_inside_triangle(swapped, A, B, C):
                    swapped_score = get_smallest_triangle_area(swapped)
                    if swapped_score > final_score:
                        final_candidate, final_score = swapped, swapped_score

        return final_candidate

    return improve