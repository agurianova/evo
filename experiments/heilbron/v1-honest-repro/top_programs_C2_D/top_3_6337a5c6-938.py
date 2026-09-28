from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib
from scipy.spatial import Delaunay


def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Triangle edge vectors for projection
    AB = B - A
    AC = C - A
    BC = C - B
    
    def project_to_triangle(point):
        """Project a point back into the triangle if it's outside"""
        # Check if point is already inside
        if is_inside_triangle(point, A, B, C):
            return point.copy()
        
        # Find closest point on each edge
        def point_to_line_segment(p, a, b):
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / np.dot(ab, ab)
            t = max(0, min(1, t))
            return a + t * ab
        
        p1 = point_to_line_segment(point, A, B)
        p2 = point_to_line_segment(point, B, C)
        p3 = point_to_line_segment(point, C, A)
        
        # Return the closest point among the three projections
        d1 = np.linalg.norm(point - p1)
        d2 = np.linalg.norm(point - p2)
        d3 = np.linalg.norm(point - p3)
        
        if d1 <= d2 and d1 <= d3:
            return p1
        elif d2 <= d1 and d2 <= d3:
            return p2
        else:
            return p3

    def get_boundary_proximity(point, triangle_vertices, epsilon=1e-5):
        """Calculate proximity to triangle boundaries (0 = on boundary, 1 = center)"""
        A, B, C = triangle_vertices
        # Using barycentric coordinates to determine proximity to boundaries
        v0 = C - A
        v1 = B - A
        v2 = point - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        if abs(denom) < 1e-10:
            return 0.5  # Degenerate case, assume middle
            
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1 - v - w
        
        # Sort barycentric coordinates to find smallest two
        coords = sorted([u, v, w])
        # Proximity to boundary = sum of smallest two coordinates
        boundary_proximity = coords[0] + coords[1]
        return max(0.0, 1.0 - boundary_proximity - epsilon)

    def detect_rows(points, threshold=0.05):
        """Detect horizontal rows of points based on y-coordinate clustering"""
        y_coords = points[:, 1]
        y_sorted = np.sort(y_coords)
        
        # Find gaps between consecutive y values
        gaps = np.diff(y_sorted)
        
        # Identify significant gaps that separate rows
        row_boundaries = [0]
        for i in range(len(gaps)):
            if gaps[i] > threshold:
                row_boundaries.append(i+1)
        row_boundaries.append(len(y_coords))
        
        # Group points into rows
        rows = []
        for i in range(len(row_boundaries)-1):
            start, end = row_boundaries[i], row_boundaries[i+1]
            row_indices = np.argsort(y_coords)[start:end]
            rows.append(row_indices)
        
        return rows

    def get_delaunay_bottleneck_tris(pts, top_n=5):
        """Use Delaunay triangulation to get geometrically meaningful small triangles"""
        try:
            # Perform Delaunay triangulation
            tri = Delaunay(pts)
            
            # Calculate area for each triangle in the triangulation
            areas = []
            for simplex in tri.simplices:
                i, j, k = simplex
                a, b, c = pts[i], pts[j], pts[k]
                area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                areas.append((area_val, i, j, k))
            
            # Sort by area and return top_n smallest
            areas.sort(key=lambda x: x[0])
            return [(i, j, k) for (_, i, j, k) in areas[:top_n]]
        except:
            # Fallback to brute-force if Delaunay fails
            return get_brute_force_bottleneck_tris(pts, top_n)

    def get_brute_force_bottleneck_tris(pts, top_n=5):
        """Brute-force calculation of smallest triangles"""
        n = pts.shape[0]
        areas = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = pts[i], pts[j], pts[k]
                    area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                    areas.append((area_val, i, j, k))
        
        areas.sort(key=lambda x: x[0])
        return [(i, j, k) for (_, i, j, k) in areas[:top_n]]
    
    def get_bottleneck_tris(pts, top_n=5, use_delaunay=True, current_min_area=None):
        """Get bottleneck triangles using Delaunay if possible, else brute-force, with enhanced selection"""
        if use_delaunay:
            del_tris = get_delaunay_bottleneck_tris(pts, top_n)
        else:
            del_tris = get_brute_force_bottleneck_tris(pts, top_n)
        
        # Enhanced bottleneck selection: include triangles near the current minimum area
        if current_min_area is not None:
            # Get all triangles with area close to minimum (adaptive threshold based on gap to theoretical max)
            near_min_tris = []
            n = pts.shape[0]
            
            # Adaptive threshold: tighter when close to theoretical maximum
            gap_ratio = (0.0365 - current_min_area) / 0.0365
            threshold_factor = 1.05 + 0.15 * gap_ratio  # 1.05 when close to max, 1.2 when far
            
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = pts[i], pts[j], pts[k]
                        area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        # Only consider triangles that are reasonably small
                        if area_val < current_min_area * threshold_factor:
                            near_min_tris.append((area_val, i, j, k))
            
            # Sort and take top ones
            near_min_tris.sort(key=lambda x: x[0])
            near_min_tris = [(i, j, k) for (_, i, j, k) in near_min_tris[:top_n*2]]
            
            # Combine with Delaunay results and remove duplicates
            combined = list(set(del_tris + near_min_tris))
            # Sort by area to get the smallest ones
            areas = []
            for (i, j, k) in combined:
                a, b, c = pts[i], pts[j], pts[k]
                area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                areas.append((area_val, i, j, k))
            areas.sort(key=lambda x: x[0])
            return [(i, j, k) for (_, i, j, k) in areas[:top_n]]
        
        return del_tris
    
    def get_area_gradient(point_idx, triangle, points):
        """Get the gradient direction to increase the area of the triangle"""
        i, j, k = triangle
        p_i, p_j, p_k = points[i], points[j], points[k]
        
        # Calculate the cross product (signed area * 2)
        cross = (p_j[0] - p_i[0]) * (p_k[1] - p_i[1]) - (p_j[1] - p_i[1]) * (p_k[0] - p_i[0])
        sign = 1 if cross >= 0 else -1
        
        if point_idx == i:
            # For point i, gradient direction before sign adjustment
            vec = p_k - p_j
            grad = np.array([-vec[1], vec[0]])
            return sign * grad
        elif point_idx == j:
            # For point j, gradient direction before sign adjustment
            vec = p_i - p_k
            grad = np.array([-vec[1], vec[0]])
            return sign * grad
        elif point_idx == k:
            # For point k, gradient direction before sign adjustment
            vec = p_j - p_i
            grad = np.array([-vec[1], vec[0]])
            return sign * grad
        else:
            return np.zeros(2)  # Point not in this triangle

    def improve(points: np.ndarray) -> np.ndarray:
        point_hash = hashlib.md5(points.tobytes()).hexdigest()
        np.random.seed(int(point_hash[:8], 16))
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        # Store initial temperature for reset strategy
        initial_T = 1.0 * current_score
        T = initial_T
        alpha = 0.999
        max_iter = 1000
        
        # Adaptive stagnation handling
        gap_ratio = (0.0365 - current_score) / 0.0365
        base_stagnation = 100 if gap_ratio > 0.1 else 150
        stagnation_limit = max(50, int(base_stagnation * gap_ratio))
        stagnation_count = 0
        last_improvement = current_score
        improvement_rate = 0.0
        
        # Start with focused bottleneck search
        bottleneck_top_n = 3
        use_delaunay = True
        
        for iter in range(max_iter):
            # Dynamically adjust bottleneck count based on improvement rate
            if iter > 10:
                improvement_rate = (current_score - last_improvement) / max(1, iter / 10.0)
                # Expand bottleneck search when improvement rate is low
                bottleneck_top_n = min(15, max(3, 3 + int(12 * (1 - improvement_rate / 0.0001)) if improvement_rate < 0.0001 else 3))
                
            # Enhanced bottleneck selection with current minimum area
            bottleneck = get_bottleneck_tris(current, top_n=bottleneck_top_n, use_delaunay=use_delaunay, current_min_area=current_score)
            if not bottleneck:
                # If Delaunay failed, fall back to brute-force
                if use_delaunay:
                    use_delaunay = False
                    bottleneck = get_bottleneck_tris(current, top_n=bottleneck_top_n, use_delaunay=False, current_min_area=current_score)
                if not bottleneck:
                    continue
            
            affected_indices = set()
            for tri in bottleneck:
                affected_indices.update(tri)
            affected_indices = list(affected_indices)
            
            if not affected_indices:
                continue
                
            candidate = current.copy()
            row_aware_perturbation = False
            
            # Check if configuration likely came from row-based Constructor
            rows = detect_rows(current)
            if 4 <= len(rows) <= 6:  # Matches Constructor's pattern
                row_aware_perturbation = True
                for row_idx, row in enumerate(rows):
                    if len(row) > 1:
                        # Optimize spacing within row
                        row_points = current[row]
                        x_sorted = np.sort(row_points[:, 0])
                        ideal_positions = np.linspace(x_sorted[0], x_sorted[-1], len(row))
                        
                        for i, point_idx in enumerate(row):
                            current_pos = np.where(np.sort(row_points[:, 0]) == current[point_idx, 0])[0][0]
                            target_x = ideal_positions[current_pos]
                            
                            # Move toward ideal position with adaptive step
                            direction = np.array([target_x - current[point_idx, 0], 0])
                            direction_norm = np.linalg.norm(direction)
                            if direction_norm > 1e-8:
                                direction /= direction_norm
                                step_size = min(0.1 * T * current_score, direction_norm)
                                candidate[point_idx] = current[point_idx] + step_size * direction
                                candidate[point_idx] = project_to_triangle(candidate[point_idx])

            if not row_aware_perturbation:
                for idx in affected_indices:
                    # Calculate gradient direction from all bottleneck triangles
                    gradient_direction = np.zeros(2)
                    total_weight = 0
                    for tri in bottleneck:
                        if idx in tri:
                            # Get the area of this triangle
                            i, j, k = tri
                            a, b, c = current[i], current[j], current[k]
                            area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                            # Weight inversely proportional to area (add small epsilon to avoid division by zero)
                            weight = 1.0 / (area_val + 1e-8)
                            gradient_direction += weight * get_area_gradient(idx, tri, current)
                            total_weight += weight
                    
                    # Normalize by total weight if we have valid weights
                    if total_weight > 1e-8:
                        gradient_direction /= total_weight
                    
                    # Apply boundary proximity factor to gradient
                    boundary_factor = get_boundary_proximity(current[idx], (A, B, C))
                    gradient_direction *= boundary_factor
                    
                    # Normalize and blend with random direction using adaptive ratio
                    grad_norm = np.linalg.norm(gradient_direction)
                    if grad_norm > 1e-8:
                        gradient_direction /= grad_norm
                        
                        # Dynamic exploration schedule based on gap to theoretical max
                        gap_ratio = (0.0365 - current_score) / 0.0365
                        base_exploration = 0.7 if gap_ratio > 0.2 else 0.5
                        exploration_ratio = max(0.05, base_exploration * (T / initial_T))
                        if improvement_rate < 0.00005 and gap_ratio > 0.1:
                            exploration_ratio = min(0.3, exploration_ratio * 1.5)
                        
                        exploitation_ratio = 1.0 - exploration_ratio
                        
                        random_direction = np.random.randn(2)
                        random_direction /= np.linalg.norm(random_direction)
                        direction = exploitation_ratio * gradient_direction + exploration_ratio * random_direction
                        direction /= np.linalg.norm(direction)
                    else:
                        # Fallback to random direction if gradient is zero
                        angle = np.random.uniform(0, 2 * np.pi)
                        direction = np.array([np.cos(angle), np.sin(angle)])
                    
                    # Adaptive step size based on current solution quality
                    step_size = np.random.uniform(0.2 * T * current_score, 0.8 * T * current_score)
                    step = step_size * direction
                    
                    # Apply perturbation
                    candidate[idx] = current[idx] + step
                    
                    # Project back to triangle if needed
                    candidate[idx] = project_to_triangle(candidate[idx])

            # Check distinctness with adaptive threshold
            distinct = True
            distinct_threshold = max(1e-5, 0.001 * current_score)
            for i in range(len(candidate)):
                for j in range(i+1, len(candidate)):
                    if np.linalg.norm(candidate[i] - candidate[j]) < distinct_threshold:
                        distinct = False
                        break
                if not distinct:
                    break
            
            if not distinct:
                candidate = current.copy()
            else:
                new_score = get_smallest_triangle_area(candidate)
                
                if new_score > best_score:
                    best = candidate.copy()
                    best_score = new_score
                    last_improvement = current_score
                    stagnation_count = 0
                    # Reset bottleneck count when we find improvement
                    bottleneck_top_n = 3
                else:
                    # Only increment stagnation when best_score doesn't improve
                    stagnation_count += 1
                    
                delta = new_score - current_score
                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    current = candidate.copy()
                    current_score = new_score
            
            if stagnation_count >= stagnation_limit:
                current = best.copy()
                current_score = best_score
                # Adaptive temperature reset based on progress and gap to maximum
                gap_ratio = (0.0365 - current_score) / 0.0365
                reset_ratio = 0.85 if gap_ratio < 0.1 else 0.7 if improvement_rate > 0.00005 else 0.5
                T = reset_ratio * initial_T
                stagnation_count = 0
                
            T *= alpha
            if T < 1e-8:
                T = 1e-8
        
        return best
    
    return improve