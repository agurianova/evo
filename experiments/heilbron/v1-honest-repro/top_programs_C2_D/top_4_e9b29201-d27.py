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

    def get_boundary_tangent(point, A, B, C):
        """Get the tangent direction along the nearest boundary edge"""
        def distance_to_line(p, a, b):
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / np.dot(ab, ab)
            t = max(0, min(1, t))
            projection = a + t * ab
            return np.linalg.norm(p - projection), projection, b - a
        
        d1, proj1, edge1 = distance_to_line(point, A, B)
        d2, proj2, edge2 = distance_to_line(point, B, C)
        d3, proj3, edge3 = distance_to_line(point, C, A)
        
        # Find the closest edge
        if d1 <= d2 and d1 <= d3:
            edge = edge1
        elif d2 <= d1 and d2 <= d3:
            edge = edge2
        else:
            edge = edge3
        
        # Normalize and get tangent direction
        edge_norm = edge / np.linalg.norm(edge)
        return np.array([-edge_norm[1], edge_norm[0]])

    def get_boundary_proximity(point, A, B, C):
        """Calculate minimum distance from point to any triangle boundary"""
        def distance_to_line(p, a, b):
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / np.dot(ab, ab)
            t = max(0, min(1, t))
            projection = a + t * ab
            return np.linalg.norm(p - projection)
        
        d1 = distance_to_line(point, A, B)
        d2 = distance_to_line(point, B, C)
        d3 = distance_to_line(point, C, A)
        return min(d1, d2, d3)

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
            # Calculate how close we are to the theoretical maximum
            gap_ratio = max(0.0, min(1.0, (0.0365 - current_min_area) / 0.0365))
            # Threshold gets tighter as we approach the maximum
            threshold_factor = 0.25 * gap_ratio + 0.05
            near_min_threshold = current_min_area * (1 + threshold_factor)
            
            # Get all triangles with area close to minimum
            near_min_tris = []
            n = pts.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = pts[i], pts[j], pts[k]
                        area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        # Only consider triangles that are reasonably small
                        if area_val < near_min_threshold:
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
        alpha = 0.995  # Increased decay rate for more aggressive exploration
        # Make iteration limit adaptive to problem difficulty
        gap_ratio = max(0.0, min(1.0, (0.0365 - current_score) / 0.0365))
        max_iter = max(1000, int(1500 * (1.0 + 3.0 * gap_ratio)))
        
        # Adaptive stagnation handling
        base_stagnation = 200 * (0.0365 - current_score) / 0.0365 + 50
        # INVERTED stagnation limit formula to increase as solution improves
        stagnation_limit = max(50, int(base_stagnation * (2.0 - (0.0365 - current_score) / 0.0365)))
        stagnation_count = 0
        last_improvement = current_score
        improvement_rate = 0.0
        
        # Start with focused bottleneck search
        bottleneck_top_n = 3
        use_delaunay = True
        
        for iter in range(max_iter):
            # Dynamically adjust bottleneck count based on improvement rate
            if iter > 10:
                improvement_rate = (current_score - last_improvement) / max(1.0, iter / 10.0)
                # FIXED: Decreasing bottleneck count as improvement slows (corrected inversion)
                bottleneck_top_n = max(3, min(15, 3 + int(12 * min(1.0, improvement_rate / 0.001))))
                
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
                        # Enhanced weighting with adaptive exponent
                        gap_ratio = max(0.0, min(1.0, (0.0365 - current_score) / 0.0365))
                        weight = np.exp(-(1.0 + 2.0 * gap_ratio) * area_val / (current_score + 1e-8))
                        gradient_direction += weight * get_area_gradient(idx, tri, current)
                        total_weight += weight
                
                # Normalize by total weight if we have valid weights
                if total_weight > 1e-8:
                    gradient_direction /= total_weight
                
                # Boundary handling with escape mechanism
                boundary_proximity = get_boundary_proximity(current[idx], A, B, C)
                max_distance = np.linalg.norm(C - A)  # Triangle height
                if boundary_proximity < max_distance * 0.1:  # Near boundary
                    tangent = get_boundary_tangent(current[idx], A, B, C)
                    # Project gradient onto tangent direction
                    proj = np.dot(gradient_direction, tangent)
                    gradient_direction = proj * tangent
                    
                    # Add escape mechanism when stagnated near boundary
                    if stagnation_count > stagnation_limit * 0.7:
                        boundary_factor = min(1.0, 2.0 * (1.0 - boundary_proximity/(max_distance*0.1)) * 
                                           (stagnation_count/stagnation_limit))
                        if np.random.rand() < 0.2 * boundary_factor:
                            # Get normal direction pointing inward
                            normal = np.array([tangent[1], -tangent[0]])
                            normal /= np.linalg.norm(normal)
                            # Blend with current direction
                            gradient_direction = (1.0 - boundary_factor) * gradient_direction + boundary_factor * normal
                            
                # Normalize and blend with random direction using adaptive ratio
                grad_norm = np.linalg.norm(gradient_direction)
                if grad_norm > 1e-8:
                    gradient_direction /= grad_norm
                    
                    # Adaptive exploration ratio that decreases near optimum
                    gap_ratio = max(0.0, min(1.0, (0.0365 - current_score) / 0.0365))
                    exploration_ratio = max(0.05 + 0.3 * (1.0 - gap_ratio), 
                                         0.85 * (T / initial_T)**0.3 * (0.5 + 0.5 * gap_ratio))
                    exploitation_ratio = 1.0 - exploration_ratio
                    
                    random_direction = np.random.randn(2)
                    random_direction /= np.linalg.norm(random_direction)
                    direction = exploitation_ratio * gradient_direction + exploration_ratio * random_direction
                    direction /= np.linalg.norm(direction)
                else:
                    # Fallback to random direction if gradient is zero
                    angle = np.random.uniform(0, 2 * np.pi)
                    direction = np.array([np.cos(angle), np.sin(angle)])
                
                # FIXED: Step size scaling using relative gap with minimum floor
                gap_ratio = max(0.0, min(1.0, (0.0365 - current_score) / 0.0365))
                adaptive_step = max(0.001, 0.01 * gap_ratio * (1.0 + improvement_rate * 1000))
                step_size = np.random.uniform(0.2 * T * adaptive_step, 0.8 * T * adaptive_step)
                step = step_size * direction
                
                # Apply perturbation
                candidate[idx] = current[idx] + step
                
                # Project back to triangle if needed
                candidate[idx] = project_to_triangle(candidate[idx])

            # Check distinctness with adaptive threshold
            distinct = True
            # Adaptive distinctness threshold based on current minimum area
            distinct_threshold = 0.0005 * max(0.5, min(2.0, current_score / 0.015))
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
                # FIXED: Temperature reset strategy - lower temperature near optimum
                gap_ratio = max(0.0, min(1.0, (0.0365 - best_score) / 0.0365))
                reset_ratio = max(0.15, 0.85 - 0.7 * gap_ratio)
                T = reset_ratio * initial_T
                stagnation_count = 0
                
            T *= alpha
            if T < 1e-8:
                T = 1e-8
        
        return best
    
    return improve