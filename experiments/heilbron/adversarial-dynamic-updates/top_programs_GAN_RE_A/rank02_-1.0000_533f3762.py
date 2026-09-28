import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
from scipy.spatial import Delaunay
import matplotlib.pyplot as plt

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Function to place points along an edge with geometric progression
    def place_along_edge(start, end, count, ratio=0.7):
        points = []
        total_length = 1.0
        segment_lengths = []
        current_length = total_length
        for _ in range(count):
            segment_length = current_length * ratio
            segment_lengths.append(segment_length)
            current_length -= segment_length
        
        # Normalize to ensure they sum to 1.0
        total = sum(segment_lengths)
        segment_lengths = [sl/total for sl in segment_lengths]
        
        # Create points
        cumulative = 0.0
        for sl in segment_lengths:
            t = cumulative + sl/2  # Center of segment
            point = (1-t) * start + t * end
            points.append(point)
            cumulative += sl
            
        return points

    # Barycentric coordinate helpers for safe perturbations
    def cartesian_to_barycentric(p):
        v0 = B - A
        v1 = C - A
        v2 = p - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01 + 1e-10
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w
        return np.array([u, v, w])

    def barycentric_to_cartesian(bary):
        u, v, w = bary
        return u * A + v * B + w * C

    def project_to_triangle(point):
        bary = cartesian_to_barycentric(point)
        # Clip to [0,1] and renormalize
        bary = np.clip(bary, 0.001, 0.999)
        bary = bary / np.sum(bary)
        return barycentric_to_cartesian(bary)

    # Function to get indices of triangles with area below threshold
    def get_adaptive_triangle_indices(pts, k_min=3, threshold_factor=1.3):
        n = pts.shape[0]
        areas = []
        indices = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = pts[i], pts[j], pts[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                    areas.append(area)
                    indices.append((i, j, k))
        
        if not areas:
            return [(0, 1, 2)]
            
        # Sort by area
        sorted_indices = [idx for _, idx in sorted(zip(areas, indices))]
        sorted_areas = [area for area, _ in sorted(zip(areas, indices))]
        
        # Determine threshold based on min area
        min_area = sorted_areas[0]
        threshold = min_area * threshold_factor
        
        # Get all triangles below threshold
        relevant_indices = [idx for area, idx in zip(areas, indices) if area <= threshold]
        
        # Ensure we have at least k_min triangles
        if len(relevant_indices) < k_min:
            return sorted_indices[:k_min]
            
        return relevant_indices

    # Function to find the largest empty triangle using Delaunay triangulation
    def find_largest_empty_triangle(points, boundary_points):
        # Combine all points
        all_points = np.vstack([points, boundary_points])
        
        # Create Delaunay triangulation
        tri = Delaunay(all_points)
        
        # Find the largest triangle that doesn't contain any points
        max_area = 0
        largest_triangle = None
        
        # Check each triangle in the triangulation
        for simplex in tri.simplices:
            # Get the three vertices of the triangle
            a, b, c = all_points[simplex]
            
            # Calculate area
            area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
            
            # Skip if area is too small
            if area < 1e-5:
                continue

            # Check if this triangle is empty (no points inside)
            empty = True
            for i in range(len(all_points)):
                if i not in simplex:
                    # Barycentric coordinates to check if point is inside triangle
                    v0 = b - a
                    v1 = c - a
                    v2 = all_points[i] - a
                    d00 = np.dot(v0, v0)
                    d01 = np.dot(v0, v1)
                    d11 = np.dot(v1, v1)
                    d20 = np.dot(v2, v0)
                    d21 = np.dot(v2, v1)
                    denom = d00 * d11 - d01 * d01
                    if abs(denom) < 1e-10:
                        continue
                    
                    v = (d11 * d20 - d01 * d21) / denom
                    w = (d00 * d21 - d01 * d20) / denom
                    u = 1.0 - v - w
                    
                    # Point is inside triangle if 0 <= u,v,w <= 1
                    if 0 <= u <= 1 and 0 <= v <= 1 and 0 <= w <= 1:
                        empty = False
                        break

            if empty and area > max_area:
                max_area = area
                largest_triangle = (a, b, c)

        # If no empty triangle found, use the largest triangle overall
        if largest_triangle is None:
            max_area = 0
            for i in range(len(all_points)):
                for j in range(i+1, len(all_points)):
                    for k in range(j+1, len(all_points)):
                        a, b, c = all_points[i], all_points[j], all_points[k]
                        area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                        if area > max_area:
                            max_area = area
                            largest_triangle = (a, b, c)

        return largest_triangle

    # Function to calculate the centroid of a triangle
    def triangle_centroid(a, b, c):
        return (a + b + c) / 3.0

    # Function to enforce rotational symmetry around triangle centroid
    def enforce_rotational_symmetry(points):
        # Calculate triangle centroid
        triangle_center = (A + B + C) / 3.0
        
        # Calculate rotation matrix for 120 degrees
        theta = 2 * np.pi / 3
        rot_matrix = np.array([
            [np.cos(theta), -np.sin(theta)],
            [np.sin(theta), np.cos(theta)]
        ])
        
        # For each point, find its symmetric counterparts
        symmetric_points = []
        for point in points:
            # Vector from triangle center to point
            vec = point - triangle_center
n            # Calculate symmetric points
            sym1 = triangle_center + np.dot(rot_matrix, vec)
            sym2 = triangle_center + np.dot(rot_matrix.T, vec)  # 240 degrees
            
            # Project back to triangle if needed
            if not is_inside_triangle(sym1, A, B, C):
                sym1 = project_to_triangle(sym1)
            if not is_inside_triangle(sym2, A, B, C):
                sym2 = project_to_triangle(sym2)
            
            symmetric_points.append((point, sym1, sym2))
        
        # Create a more symmetric configuration by averaging points with their counterparts
        new_points = []
        for i, (p, s1, s2) in enumerate(symmetric_points):
            # Find closest symmetric counterpart among existing points
            min_dist = float('inf')
            closest_point = p
            
            for j, (p2, _, _) in enumerate(symmetric_points):
                if i == j:
                    continue
                
                # Check distance to both symmetric counterparts
                dist1 = np.linalg.norm(p - p2)
                dist2 = np.linalg.norm(s1 - p2)
                dist3 = np.linalg.norm(s2 - p2)
                
                min_dist_here = min(dist1, dist2, dist3)
                if min_dist_here < min_dist:
                    min_dist = min_dist_here
                    if dist1 <= dist2 and dist1 <= dist3:
                        closest_point = p2
                    elif dist2 <= dist3:
                        closest_point = s1
                    else:
                        closest_point = s2

            # Blend with closest symmetric counterpart
            if min_dist < 0.1:  # Only blend if reasonably close
                new_point = (p + closest_point) / 2.0
                if is_inside_triangle(new_point, A, B, C):
                    new_points.append(new_point)
                else:
                    new_points.append(project_to_triangle(new_point))
            else:
                new_points.append(p)

        return np.array(new_points)

    # Initialize with points on edges using asymmetric distribution
    edge_points = []
    # AB edge: 4 points (was 3)
    edge_points.extend(place_along_edge(A, B, 4, ratio=0.7))
    # BC edge: 3 points
    edge_points.extend(place_along_edge(B, C, 3, ratio=0.7))
    # CA edge: 2 points (was 3)
    edge_points.extend(place_along_edge(C, A, 2, ratio=0.7))
    edge_points = np.array(edge_points)

    # Add 4 interior points (was 2) using Delaunay triangulation to find largest empty spaces
    interior_points = []
    current_points = edge_points.copy()
    
    for _ in range(4):
        # Find largest empty triangle
        largest_triangle = find_largest_empty_triangle(current_points, [A, B, C])
        if largest_triangle is not None:
            # Place new point at centroid of largest empty triangle
            new_point = triangle_centroid(*largest_triangle)
            
            # Project back to triangle if needed
            if not is_inside_triangle(new_point, A, B, C):
                new_point = project_to_triangle(new_point)
            
            interior_points.append(new_point)
            current_points = np.vstack([current_points, new_point])
        else:
            # Fallback: add random interior point
            bary = np.random.dirichlet([1, 1, 1])
            new_point = barycentric_to_cartesian(bary)
            interior_points.append(new_point)
            current_points = np.vstack([current_points, new_point])

    # Combine all points
    points = np.vstack([edge_points, interior_points])

    # Enforce rotational symmetry to create more robust configuration
    points = enforce_rotational_symmetry(points)

    # Function to get the smallest triangle area and indices
    def get_smallest_triangle_info(pts):
        n = pts.shape[0]
        min_area = float('inf')
        min_indices = (0, 1, 2)
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = pts[i], pts[j], pts[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        
        return min_area, min_indices

    # Adaptive simulated annealing for global optimization
    current = points.copy()
    current_score = get_smallest_triangle_area(current)
    best = current.copy()
    best_score = current_score

    # Adaptive parameters based on target min_area (0.0365)
    target_min_area = 0.0365
    T0 = target_min_area * 0.2  # Scale T0 to 20% of target
    base_step = 0.05
    max_rounds = 200
    convergence_threshold = 1e-5
    min_improvement_window = 20
    improvement_history = []

    # Track improvement for adaptive cooling
    for round_idx in range(max_rounds):
        # Calculate adaptive temperature and step size
        T = T0 * (0.99 ** round_idx)
        current_step = base_step * (0.98 ** round_idx)
        
        # Get adaptive triangle selection
        smallest_triangles = get_adaptive_triangle_indices(current, k_min=3, threshold_factor=1.3)
        
        # Choose a random triangle from the smallest ones
        chosen_triangle = smallest_triangles[np.random.randint(len(smallest_triangles))]
        
        # 70% chance to perturb one point, 30% to perturb all three
        candidate = current.copy()
        if np.random.rand() < 0.7:
            idx = chosen_triangle[np.random.randint(3)]
            bary = cartesian_to_barycentric(candidate[idx])
            # Add perturbation in barycentric space
            bary_perturb = bary + np.random.normal(0, current_step, size=3)
            bary_perturb = np.clip(bary_perturb, 0.001, 0.999)
            bary_perturb = bary_perturb / np.sum(bary_perturb)
            candidate[idx] = barycentric_to_cartesian(bary_perturb)
        else:
            for idx in chosen_triangle:
                bary = cartesian_to_barycentric(candidate[idx])
                # Add perturbation in barycentric space
                bary_perturb = bary + np.random.normal(0, current_step, size=3)
                bary_perturb = np.clip(bary_perturb, 0.001, 0.999)
                bary_perturb = bary_perturb / np.sum(bary_perturb)
                candidate[idx] = barycentric_to_cartesian(bary_perturb)

        candidate_score = get_smallest_triangle_area(candidate)
        delta = candidate_score - current_score
        
        # Track best overall solution
        if candidate_score > best_score:
            best = candidate.copy()
            best_score = candidate_score

        # Acceptance criterion
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            current = candidate
            current_score = candidate_score

        # Track improvements for convergence detection
        improvement_history.append(max(0, delta))
        if len(improvement_history) > min_improvement_window:
            improvement_history.pop(0)
            
        # Check for convergence
        if len(improvement_history) >= min_improvement_window:
            avg_improvement = np.mean(improvement_history)
            if avg_improvement < convergence_threshold:
                break

    return best