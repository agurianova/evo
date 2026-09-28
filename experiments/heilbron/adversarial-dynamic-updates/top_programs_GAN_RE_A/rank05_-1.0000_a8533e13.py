import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
from scipy.spatial import Delaunay, Voronoi
import math

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Adaptive ratio calculation based on problem size (n=11)
    n_points = 11
    ratio = 0.55 + 0.15 * (11/n_points)  # Optimized for n=11
    
    # Function to place points along an edge with geometric progression
    def place_along_edge(start, end, count):
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

    # Phase 1: Create initial configuration with balanced boundary distribution
    # Boundary distribution: 4-3-2 (total 9 points)
    boundary_points = []
    # AB edge: 4 points
    boundary_points.extend(place_along_edge(A, B, 4))
    # BC edge: 3 points
    boundary_points.extend(place_along_edge(B, C, 3))
    # CA edge: 2 points
    boundary_points.extend(place_along_edge(C, A, 2))
    
    # Convert to numpy array
    points = np.array(boundary_points)
    
    # Phase 2: Add interior points using Voronoi diagram for largest empty circles
    # This creates more strategic interior point distribution
    for _ in range(2):  # Add 2 interior points (total 11 points)
        # Compute Voronoi diagram
        vor = Voronoi(points)
        
        # Find the Voronoi vertex with largest min distance to existing points
        max_min_dist = -1
        new_point = None
        
        # Check Voronoi vertices
        for vertex in vor.vertices:
            # Only consider vertices inside the triangle
            if is_inside_triangle(vertex, A, B, C):
                # Calculate min distance to all existing points
n                min_dist = float('inf')
                for p in points:
                    dist = np.linalg.norm(vertex - p)
                    if dist < min_dist:
                        min_dist = dist
                
                if min_dist > max_min_dist:
                    max_min_dist = min_dist
                    new_point = vertex
        
        # If no valid Voronoi vertex found, use Delaunay circumcenters as fallback
        if new_point is None:
            tri = Delaunay(points)
            for i, simplex in enumerate(tri.simplices):
                a, b, c = points[simplex]
                # Calculate circumcenter (center of circle through three points)
                ax, ay = a
                bx, by = b
                cx, cy = c
                
                d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
                if abs(d) < 1e-10:
                    continue
                    
                ux = ((ax*ax + ay*ay) * (by - cy) + (bx*bx + by*by) * (cy - ay) + (cx*cx + cy*cy) * (ay - by)) / d
                uy = ((ax*ax + ay*ay) * (cx - bx) + (bx*bx + by*by) * (ax - cx) + (cx*cx + cy*cy) * (bx - ax)) / d
                circumcenter = np.array([ux, uy])
                
                # Check if inside triangle and calculate min distance
                if is_inside_triangle(circumcenter, A, B, C):
                    min_dist = min(np.linalg.norm(circumcenter - p) for p in [a, b, c])
                    if min_dist > max_min_dist:
                        max_min_dist = min_dist
                        new_point = circumcenter

        # If still no point found, use centroid of whole triangle
        if new_point is None:
            new_point = (A + B + C) / 3

        # Ensure point is inside triangle
        if not is_inside_triangle(new_point, A, B, C):
            new_point = project_to_triangle(new_point)
        
        # Add the new point
        points = np.vstack([points, new_point])

    # Phase 3: Dual-phase optimization with adaptive parameters
    current = points.copy()
    current_score = get_smallest_triangle_area(current)
    best = current.copy()
    best_score = current_score

    # Global search phase (coarse)
    n_rounds_global = 60  # Increased from 40 for better exploration
    T0_global = 0.02
    T_decay_global = 0.97
    base_step_global = 0.03

    # Local refinement phase (fine)
    n_rounds_local = 50  # Slightly reduced to balance with global search
    T0_local = 0.005
    T_decay_local = 0.99
    base_step_local = 0.008

    # Get initial min area percentile for adaptive step size
    def get_min_area_percentile(score):
        # Approximate theoretical maximum for n=11 is ~0.0365
        max_possible = 0.0365
        return min(1.0, max(0.0, score / max_possible))

    # Track improvement history for restarts
    improvement_history = []
    stagnation_threshold = 10  # Restart after 10 rounds of no improvement

    # Global search phase with restart capability
    for round_idx in range(n_rounds_global):
        T = T0_global * (T_decay_global ** round_idx)
        # CORRECTED: Adaptive step size decreases near optimum (1-0.5*percentile)
        min_area_percentile = get_min_area_percentile(current_score)
        step_size = base_step_global * (0.95 ** round_idx) * (1 - 0.5 * min_area_percentile)
        
        # DYNAMIC: Select more triangles based on total count (0.2*comb(n,3))
        n_triangles = min(8, max(3, int(0.2 * math.comb(len(current), 3))))
        smallest_triangles = []
        for i in range(len(current)):
            for j in range(i+1, len(current)):
                for k in range(j+1, len(current)):
                    a, b, c = current[i], current[j], current[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                    smallest_triangles.append((area, (i, j, k)))
        smallest_triangles.sort()
        smallest_triangles = smallest_triangles[:n_triangles]
        
        # Choose a random triangle from the smallest ones
        chosen_triangle = smallest_triangles[np.random.randint(len(smallest_triangles))][1]
        
        # 70% chance to perturb one point, 30% to perturb all three
        candidate = current.copy()
        if np.random.rand() < 0.7:
            idx = chosen_triangle[np.random.randint(3)]
            bary = cartesian_to_barycentric(candidate[idx])
            # Add perturbation in barycentric space
            bary_perturb = bary + np.random.normal(0, step_size, size=3)
            bary_perturb = np.clip(bary_perturb, 0.001, 0.999)
            bary_perturb = bary_perturb / np.sum(bary_perturb)
            candidate[idx] = barycentric_to_cartesian(bary_perturb)
        else:
            for idx in chosen_triangle:
                bary = cartesian_to_barycentric(candidate[idx])
                # Add perturbation in barycentric space
                bary_perturb = bary + np.random.normal(0, step_size, size=3)
                bary_perturb = np.clip(bary_perturb, 0.001, 0.999)
                bary_perturb = bary_perturb / np.sum(bary_perturb)
                candidate[idx] = barycentric_to_cartesian(bary_perturb)

        candidate_score = get_smallest_triangle_area(candidate)
        delta = candidate_score - current_score
        
        # Track best overall solution
        if candidate_score > best_score:
            best = candidate.copy()
            best_score = candidate_score
            improvement_history.append(delta)
        else:
            improvement_history.append(0)
            
        # RANDOM RESTART: If no improvement for stagnation_threshold rounds
        if len(improvement_history) > stagnation_threshold and \
           all(imp <= 0 for imp in improvement_history[-stagnation_threshold:]):
            # Restart from best solution with increased temperature
            current = best.copy()
            current_score = best_score
            T = T0_global * 0.5  # Higher temperature for restart
            improvement_history = []

        # Acceptance criterion
        if delta > 0 or np.random.rand() < np.exp(delta / T):
            current = candidate
            current_score = candidate_score

    # Local refinement phase
    for round_idx in range(n_rounds_local):
        T = T0_local * (T_decay_local ** round_idx)
        # CORRECTED: Adaptive step size decreases near optimum (1-0.5*percentile)
        min_area_percentile = get_min_area_percentile(current_score)
        step_size = base_step_local * (0.95 ** round_idx) * (1 - 0.5 * min_area_percentile)
        
        # DYNAMIC: Select more triangles based on total count (0.2*comb(n,3))
        n_triangles = min(5, max(3, int(0.2 * math.comb(len(current), 3))))
        smallest_triangles = []
        for i in range(len(current)):
            for j in range(i+1, len(current)):
                for k in range(j+1, len(current)):
                    a, b, c = current[i], current[j], current[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                    smallest_triangles.append((area, (i, j, k)))
        smallest_triangles.sort()
        smallest_triangles = smallest_triangles[:n_triangles]  # Focus on critical weaknesses
        
        # Choose a random triangle from the smallest ones
        chosen_triangle = smallest_triangles[np.random.randint(len(smallest_triangles))][1]
        
        # 60% chance to perturb one point, 40% to perturb all three
        candidate = current.copy()
        if np.random.rand() < 0.6:
            idx = chosen_triangle[np.random.randint(3)]
            bary = cartesian_to_barycentric(candidate[idx])
            # Add perturbation in barycentric space
            bary_perturb = bary + np.random.normal(0, step_size, size=3)
            bary_perturb = np.clip(bary_perturb, 0.001, 0.999)
            bary_perturb = bary_perturb / np.sum(bary_perturb)
            candidate[idx] = barycentric_to_cartesian(bary_perturb)
        else:
            for idx in chosen_triangle:
                bary = cartesian_to_barycentric(candidate[idx])
                # Add perturbation in barycentric space
                bary_perturb = bary + np.random.normal(0, step_size, size=3)
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

    return best