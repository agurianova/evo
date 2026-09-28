from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def triangle_area(a, b, c):
        """Calculate area of triangle given three points."""
        return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

    def triangle_aspect_ratio(a, b, c):
        """Calculate aspect ratio of triangle (1.0 for equilateral, lower for flatter triangles)."""
        # Calculate sides
        ab = np.linalg.norm(b - a)
        bc = np.linalg.norm(c - b)
        ca = np.linalg.norm(a - c)
        
        # Semi-perimeter
        s = (ab + bc + ca) / 2
        
        # Area (using Heron's formula)
        area = np.sqrt(max(0, s * (s - ab) * (s - bc) * (s - ca)))
        
        if area < 1e-10:
            return 0.0
        
        # Circumradius
        R = (ab * bc * ca) / (4 * area)
        
        # Aspect ratio: 4*area/(3*sqrt(3)*R^2) for equilateral = 1
        aspect_ratio = 4 * area / (3 * np.sqrt(3) * R * R)
        return aspect_ratio

    def project_to_boundary(point, A, B, C):
        """Project point to nearest location on triangle boundary."""
        # Check distance to each edge
        def point_to_line_distance(p, a, b):
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / np.dot(ab, ab)
            t = max(0, min(1, t))
            projection = a + t * ab
            return projection, np.linalg.norm(ap - (t * ab))
        
        # Get projections to all three edges
        proj_AB, dist_AB = point_to_line_distance(point, A, B)
        proj_BC, dist_BC = point_to_line_distance(point, B, C)
        proj_CA, dist_CA = point_to_line_distance(point, C, A)
        
        # Choose closest projection
        if dist_AB <= dist_BC and dist_AB <= dist_CA:
            return proj_AB
        elif dist_BC <= dist_AB and dist_BC <= dist_CA:
            return proj_BC
        else:
            return proj_CA

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        # Enhanced parameters matching Constructor sophistication
        T0 = 0.1  # Increased from 0.001 to enable meaningful exploration
        cooling_rate = 0.99  # Exponential cooling instead of linear
        max_iter = 600  # Increased iterations with more efficient search
        min_temperature = 1e-5
        symmetry_break_count = 0

        for iter in range(max_iter):
            temperature = T0 * (cooling_rate ** iter)
            if temperature < min_temperature:
                break

            # Collect all triangle areas for dynamic tolerance
            all_areas = []
            for i in range(11):
                for j in range(i + 1, 11):
                    for k in range(j + 1, 11):
                        area = triangle_area(current[i], current[j], current[k])
                        all_areas.append(area)

            all_areas.sort()
            min_area = all_areas[0]
            # Include triangles within top 5% of critical values
            critical_percentile = min(5, len(all_areas) - 1)
            tolerance = max(1e-6, 0.05 * (all_areas[critical_percentile] - min_area))

            # Find all critical triangles within tolerance
            critical_triangles = []  # (i, j, k, area)
            for i in range(11):
                for j in range(i + 1, 11):
                    for k in range(j + 1, 11):
                        area = triangle_area(current[i], current[j], current[k])
                        if abs(area - min_area) <= tolerance:
                            critical_triangles.append((i, j, k, area))
            
            if not critical_triangles:
                continue

            # Compute gradient directions for all points
            gradients = np.zeros((11, 2))
            for idx in range(11):
                total_weight = 0.0
                grad = np.zeros(2)
                
                # Check all critical triangles containing this point
                for (i, j, k, area) in critical_triangles:
                    if idx not in (i, j, k):
                        continue
                    
                    # Determine the base points for this triangle
                    if idx == i:
                        base_p1, base_p2 = current[j], current[k]
                    elif idx == j:
                        base_p1, base_p2 = current[i], current[k]
                    else:  # idx == k
                        base_p1, base_p2 = current[i], current[j]
                    
                    # Compute perpendicular direction to increase area
                    base_vec = base_p2 - base_p1
                    perp_vec = np.array([-base_vec[1], base_vec[0]])
                    norm = np.linalg.norm(perp_vec)
                    if norm < 1e-8:
                        continue
                    perp_vec = perp_vec / norm
                    
                    apex = current[idx]
                    to_apex = apex - base_p1
                    height = np.dot(to_apex, perp_vec)
                    direction = perp_vec * np.sign(height)
                    
                    # Geometry-aware weighting: prioritize flatter triangles
                    aspect_ratio = triangle_aspect_ratio(base_p1, base_p2, apex)
                    # Higher weight for flatter triangles (lower aspect ratio)
                    geometry_weight = 1.0 - min(1.0, aspect_ratio)
                    # Weight by criticality (more critical = higher weight)
                    critical_weight = 1.0 / (area - min_area + 1e-8)
                    weight = critical_weight * (1.0 + 2.0 * geometry_weight)
                    
                    grad += weight * direction
                    total_weight += weight

                if total_weight > 0:
                    gradients[idx] = grad / total_weight

            # Dynamic multi-point move probability based on critical triangles
            critical_count = len(critical_triangles)
            # Scale from 0.3 to 0.9 based on critical triangle count
            multi_point_prob = min(0.9, 0.3 + 0.6 * (critical_count / 15.0))

            if np.random.random() < multi_point_prob and critical_count > 0:
                # Multi-point move: select random critical triangle
                i, j, k, _ = critical_triangles[np.random.randint(0, len(critical_triangles))]
                points_to_move = [i, j, k]
                step_per_point = temperature * 0.5 / np.sqrt(3)  # Scale for 3 points
                
                candidate = current.copy()
                
                for pt in points_to_move:
                    # Compute move vector with gradient
                    move_vec = gradients[pt] * step_per_point
                    
                    new_pt = current[pt] + move_vec
                    if not is_inside_triangle(new_pt, A, B, C):
                        # Boundary projection with symmetry breaking
                        new_pt = project_to_boundary(new_pt, A, B, C)
                        if symmetry_break_count < 2:
                            asymmetry = np.random.uniform(-0.001, 0.001, size=2)
                            new_pt = new_pt + asymmetry
                            symmetry_break_count += 1

                    candidate[pt] = new_pt
                
            else:
                # Single-point move: select random point with non-zero gradient
                candidate_points = [p for p in range(11) 
                                  if np.linalg.norm(gradients[p]) > 1e-8]
                if not candidate_points:
                    continue
                
                point_idx = np.random.choice(candidate_points)
                direction = gradients[point_idx]
                norm_dir = np.linalg.norm(direction)
                if norm_dir < 1e-8:
                    continue
                direction = direction / norm_dir
                
                step = temperature * 0.5
                move = direction * step
                
                candidate = current.copy()
                candidate[point_idx] += move
                
                if not is_inside_triangle(candidate[point_idx], A, B, C):
                    # Boundary projection with symmetry breaking
                    candidate[point_idx] = project_to_boundary(candidate[point_idx], A, B, C)
                    if symmetry_break_count < 2:
                        asymmetry = np.random.uniform(-0.001, 0.001, size=2)
                        candidate[point_idx] = candidate[point_idx] + asymmetry
                        symmetry_break_count += 1

            # Calculate new minimum area
            new_score = get_smallest_triangle_area(candidate)
            
            # Acceptance probability
            if new_score > current_score:
                accept = True
            else:
                delta = new_score - current_score
                accept_prob = math.exp(delta / temperature)
                accept = np.random.rand() < accept_prob
            
            if accept:
                current = candidate
                current_score = new_score
                
                if new_score > best_score:
                    best = candidate.copy()
                    best_score = new_score

        return best

    return improve