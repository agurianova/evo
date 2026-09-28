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
    
    def get_area_gradient(point_idx, triangle, points, all_bottlenecks=None):
        """Get the gradient direction to increase the area of the triangle, with compound effect consideration"""
        i, j, k = triangle
        p_i, p_j, p_k = points[i], points[j], points[k]
        
        # Calculate the cross product (signed area * 2)
        cross = (p_j[0] - p_i[0]) * (p_k[1] - p_i[1]) - (p_j[1] - p_i[1]) * (p_k[0] - p_i[0])
        sign = 1 if cross >= 0 else -1
        
        # Base gradient calculation
        if point_idx == i:
            # For point i, gradient direction before sign adjustment
            vec = p_k - p_j
            grad = np.array([-vec[1], vec[0]])
            base_grad = sign * grad
        elif point_idx == j:
            # For point j, gradient direction before sign adjustment
            vec = p_i - p_k
            grad = np.array([-vec[1], vec[0]])
            base_grad = sign * grad
        elif point_idx == k:
            # For point k, gradient direction before sign adjustment
            vec = p_j - p_i
            grad = np.array([-vec[1], vec[0]])
            base_grad = sign * grad
        else:
            return np.zeros(2)  # Point not in this triangle
        
        # Compound effect consideration - if this point is in multiple bottleneck triangles
        if all_bottlenecks and len(all_bottlenecks) > 1:
            # Find all triangles containing this point
            connected_tris = [tri for tri in all_bottlenecks if point_idx in tri and tri != triangle]
            
            if connected_tris:
                # Calculate how moving this point affects other connected triangles
                compound_effect = np.zeros(2)
                for other_tri in connected_tris:
                    # Calculate gradient for this other triangle
                    other_grad = get_area_gradient(point_idx, other_tri, points)
                    
                    # Get the area of this other triangle
                    oi, oj, ok = other_tri
                    oa, ob, oc = points[oi], points[oj], points[ok]
                    other_area = 0.5 * abs(oa[0]*(ob[1]-oc[1]) + ob[0]*(oc[1]-oa[1]) + oc[0]*(oa[1]-ob[1]))
                    
                    # Weight by relative importance (inverse of area)
                    weight = 1.0 / (other_area + 1e-8)
                    compound_effect += weight * other_grad
                
                # Normalize compound effect
                compound_norm = np.linalg.norm(compound_effect)
                if compound_norm > 1e-8:
                    compound_effect /= compound_norm
                
                # Blend compound effect with base gradient
                # The more triangles affected, the more we need to balance
                balance_factor = 0.3 + 0.7 * (1.0 / (1.0 + len(connected_tris)))
                return balance_factor * base_grad + (1.0 - balance_factor) * compound_effect
        
        return base_grad

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
        max_iter = 1000
        
        # Adaptive stagnation handling
        gap_ratio = max(0.0, min(1.0, (0.0365 - current_score) / 0.0365))
        stagnation_limit = max(100, 200 * (1 - gap_ratio) + 50)
        stagnation_count = 0
        last_improvement = current_score
        improvement_rate = 0.0
        
        # Start with focused bottleneck search
        bottleneck_top_n = 3
        use_delaunay = True
        
        # Track historical improvement rates for adaptive parameter tuning
        improvement_history = []
        
        for iter in range(max_iter):
            # Update improvement rate history
            if iter > 0 and iter % 10 == 0:
                recent_improvement = current_score - last_improvement
                improvement_history.append(recent_improvement)
                if len(improvement_history) > 5:
                    improvement_history.pop(0)
                
                # Calculate moving average improvement rate
                if len(improvement_history) > 0:
                    improvement_rate = sum(improvement_history) / len(improvement_history)
                
            # Dynamically adjust bottleneck count based on improvement rate
            if iter > 10:
                # Smoother adaptation using sigmoid function to avoid sensitivity to small changes
                # This addresses the bottleneck_adaptation [fragile] insight
                improvement_magnitude = max(1e-8, abs(improvement_rate))
                # Sigmoid-based adaptation: gradually increases bottleneck count as improvement slows
                bottleneck_top_n = 3 + 12 / (1 + np.exp(-10 * (0.001 - improvement_magnitude)))
                bottleneck_top_n = min(15, max(3, bottleneck_top_n))
                
            # Enhanced bottleneck selection with current minimum area
            bottleneck = get_bottleneck_tris(current, top_n=int(bottleneck_top_n), use_delaunay=use_delaunay, current_min_area=current_score)
            if not bottleneck:
                # If Delaunay failed, fall back to brute-force
                if use_delaunay:
                    use_delaunay = False
                    bottleneck = get_bottleneck_tris(current, top_n=int(bottleneck_top_n), use_delaunay=False, current_min_area=current_score)
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
                # Now passing all_bottlenecks to consider compound effects - addresses gradient_calculation [beneficial] insight
                gradient_direction = np.zeros(2)
                total_weight = 0
                for tri in bottleneck:
                    if idx in tri:
                        # Get the area of this triangle
                        i, j, k = tri
                        a, b, c = current[i], current[j], current[k]
                        area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        # Use softer weighting to balance triangle influences
                        weight = 1.0 / (area_val + 1e-8)**0.5
                        gradient_direction += weight * get_area_gradient(idx, tri, current, bottleneck)
                        total_weight += weight
                
                # Normalize by total weight if we have valid weights
                if total_weight > 1e-8:
                    gradient_direction /= total_weight
                
                # Add boundary proximity awareness to gradient - INVERTED to strengthen boundary adjustments
                boundary_proximity = get_boundary_proximity(current[idx], A, B, C)
                # Normalize boundary proximity (assuming max distance is triangle height)
                max_distance = np.linalg.norm(C - A)  # Triangle height
                boundary_factor = 1.0 - min(1.0, boundary_proximity / (max_distance * 0.5))
                # Blend to avoid complete dominance
                gradient_direction *= (0.2 + 0.8 * boundary_factor)

                # Normalize and blend with random direction using adaptive ratio
                grad_norm = np.linalg.norm(gradient_direction)
                if grad_norm > 1e-8:
                    gradient_direction /= grad_norm
                    
                    # Calculate gap to theoretical maximum
                    gap_to_max = 0.0365 - current_score
                    gap_ratio = max(0.0, min(1.0, gap_to_max / 0.0365))
                    
                    # Parameterized exploration ratio - addresses exploration_exploitation [beneficial] insight
                    # Base exploration parameters that adapt based on improvement rate
                    base_explore = 0.25
                    max_explore = 0.85
                    explore_decay = 0.5
                    
                    # If improvement rate is low, increase exploration
                    exploration_adjustment = 0.0
                    if len(improvement_history) > 0:
                        avg_improvement = sum(improvement_history) / len(improvement_history)
                        # If we're barely improving, explore more
                        if avg_improvement < 1e-5:
                            exploration_adjustment = 0.3
                        # If we're improving well, exploit more
                        elif avg_improvement > 1e-4:
                            exploration_adjustment = -0.2
                    
                    # Calculate exploration ratio with adaptive parameters
                    exploration_ratio = max(base_explore, 
                                         min(max_explore, 
                                             (max_explore - base_explore) * (T / initial_T)**explore_decay * (0.7 + 0.3 * gap_ratio) 
                                             + exploration_adjustment))
                    exploitation_ratio = 1.0 - exploration_ratio
                    
                    random_direction = np.random.randn(2)
                    random_direction /= np.linalg.norm(random_direction)
                    direction = exploitation_ratio * gradient_direction + exploration_ratio * random_direction
                    direction /= np.linalg.norm(direction)
                else:
                    # Fallback to random direction if gradient is zero
                    angle = np.random.uniform(0, 2 * np.pi)
                    direction = np.array([np.cos(angle), np.sin(angle)])
                
                # Adaptive step size based on gap to theoretical maximum
                gap_to_max = 0.0365 - current_score
                step_size = np.random.uniform(0.2 * T * (0.1 + gap_to_max), 0.8 * T * (0.1 + gap_to_max))
                step = step_size * direction
                
                # Apply perturbation
                candidate[idx] = current[idx] + step
                
                # Project back to triangle if needed
                candidate[idx] = project_to_triangle(candidate[idx])

            # Check distinctness with adaptive threshold
            distinct = True
            # Make distinct_threshold dynamic based on current min_area
            distinct_threshold = 0.0003 + 0.0005 * (0.0365 - current_score) / 0.0365
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
            
            # Update stagnation limit based on current progress
            gap_ratio = max(0.0, min(1.0, (0.0365 - best_score) / 0.0365))
            stagnation_limit = max(100, 200 * (1 - gap_ratio) + 50)
            
            if stagnation_count >= stagnation_limit:
                current = best.copy()
                current_score = best_score
                # Adaptive temperature reset based on progress and gap to theoretical maximum
                gap_ratio = max(0.0, min(1.0, (0.0365 - best_score) / 0.0365))
                reset_ratio = 0.85 * gap_ratio + 0.15
                T = reset_ratio * initial_T
                stagnation_count = 0
                
            T *= alpha
            if T < 1e-8:
                T = 1e-8
        
        return best
    
    return improve