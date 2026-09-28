import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
from scipy.spatial import Delaunay

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Function to place points along an edge with geometric progression
    def place_along_edge(start, end, count, ratio=0.6):
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
    
    # Place 3 points on each edge (total 9 points)
    edge_points = []
    edge_points.extend(place_along_edge(A, B, 3, ratio=0.6))
    edge_points.extend(place_along_edge(B, C, 3, ratio=0.6))
    edge_points.extend(place_along_edge(C, A, 3, ratio=0.6))
    
    # Convert to numpy array for Delaunay triangulation
    boundary_points = np.array(edge_points)
    
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
        bary = np.clip(bary, 0.0001, 0.9999)
        bary = bary / np.sum(bary)
        return barycentric_to_cartesian(bary)

    # Find interior points using Delaunay triangulation
    def find_interior_points(boundary_points, n_interior=2):
        # Create a grid of candidate points inside the triangle
        grid_size = 50
        u = np.linspace(0, 1, grid_size)
        v = np.linspace(0, 1, grid_size)
        candidates = []
        
        for ui in u:
            for vi in v:
                if ui + vi <= 1.0:
                    wi = 1.0 - ui - vi
                    point = ui * A + vi * B + wi * C
                    candidates.append(point)
        
        candidates = np.array(candidates)
        
        # Compute Delaunay triangulation of boundary points
        all_points = np.vstack([boundary_points, candidates])
        tri = Delaunay(all_points)
        
        # Find candidate points that are in the largest empty triangles
        void_scores = np.zeros(len(candidates))
        for simplex in tri.simplices:
            # Check if the simplex contains only boundary points
            if np.all(simplex < len(boundary_points)):
                # Calculate area of this triangle
                pts = all_points[simplex]
                area = 0.5 * abs((pts[1,0]-pts[0,0])*(pts[2,1]-pts[0,1]) - 
                                (pts[2,0]-pts[0,0])*(pts[1,1]-pts[0,1]))
                # Add area to candidate points that are inside this triangle
                for i in range(len(candidates)):
                    if tri.find_simplex(candidates[i]) == -1:  # Outside triangulation
                        # Check if candidate is inside this triangle
                        p = candidates[i]
                        a, b, c = pts[0], pts[1], pts[2]
                        area1 = 0.5 * abs((b[0]-p[0])*(c[1]-p[1]) - (c[0]-p[0])*(b[1]-p[1]))
                        area2 = 0.5 * abs((c[0]-p[0])*(a[1]-p[1]) - (a[0]-p[0])*(c[1]-p[1]))
                        area3 = 0.5 * abs((a[0]-p[0])*(b[1]-p[1]) - (b[0]-p[0])*(a[1]-p[1]))
                        if abs(area1 + area2 + area3 - area) < 1e-5:
                            void_scores[i] += area

        # Select top n_interior candidates with highest void scores
        top_indices = np.argsort(void_scores)[-n_interior:]
        return [candidates[i] for i in top_indices]

    # Add 2 interior points in largest voids
    interior_points = find_interior_points(boundary_points, n_interior=2)
    points = np.vstack([boundary_points, interior_points])
    
    # Function to get adaptive triangle selection threshold
    def get_adaptive_triangle_indices(pts, min_area):
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
        
        # Adaptive threshold: include triangles within 15% of min_area
        threshold = min_area * 1.15
        relevant_indices = [idx for idx, area in zip(indices, areas) if area <= threshold]
        
        # Ensure we have at least 3 triangles
n        return relevant_indices[:max(3, len(relevant_indices))]

    # Two-phase optimization: exploration then refinement
    def two_phase_optimization(points):
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        # Phase 1: Exploration (larger steps, more aggressive)
        n_rounds_explore = 200
        T0_explore = 0.00365  # 10% of target min_area (0.0365)
        T_decay_explore = 0.99
        base_step_explore = 0.03
        step_decay_explore = 0.995

        # Phase 2: Refinement (smaller steps, precision)
        n_rounds_refine = 300
        T0_refine = T0_explore * 0.3
        T_decay_refine = 0.995
        base_step_refine = base_step_explore * 0.4
        step_decay_refine = 0.998

        # Track improvement history for adaptive cooling
        improvement_history = []
        stagnation_counter = 0
        stagnation_threshold = 40

        # Phase 1: Exploration
        for round_idx in range(n_rounds_explore):
            T = T0_explore * (T_decay_explore ** round_idx)
            current_step = base_step_explore * (step_decay_explore ** round_idx)
            
            # Get relevant triangles with adaptive threshold
            current_min_area = get_smallest_triangle_area(current)
            triangle_indices = get_adaptive_triangle_indices(current, current_min_area)
            
            if not triangle_indices:
                continue
                
            chosen_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
            
            # 60% chance to perturb one point, 40% to perturb all three
            candidate = current.copy()
            if np.random.rand() < 0.6:
                idx = chosen_triangle[np.random.randint(3)]
                bary = cartesian_to_barycentric(candidate[idx])
                bary_perturb = bary + np.random.normal(0, current_step, size=3)
                bary_perturb = np.clip(bary_perturb, 0.0001, 0.9999)
                bary_perturb = bary_perturb / np.sum(bary_perturb)
                candidate[idx] = barycentric_to_cartesian(bary_perturb)
            else:
                for idx in chosen_triangle:
                    bary = cartesian_to_barycentric(candidate[idx])
                    bary_perturb = bary + np.random.normal(0, current_step, size=3)
                    bary_perturb = np.clip(bary_perturb, 0.0001, 0.9999)
                    bary_perturb = bary_perturb / np.sum(bary_perturb)
                    candidate[idx] = barycentric_to_cartesian(bary_perturb)

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - current_score
            
            # Track best overall solution
            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                stagnation_counter = 0
            else:
                stagnation_counter += 1

            # Stagnation handling
            if stagnation_counter > stagnation_threshold:
                current = best.copy()
                current_score = best_score
                stagnation_counter = 0
            else:
                # Acceptance criterion
                if delta > 0 or np.random.rand() < np.exp(delta / (T + 1e-10)):
                    current = candidate
                    current_score = candidate_score

        # Phase 2: Refinement
        current = best.copy()
        current_score = best_score
        stagnation_counter = 0
        
        for round_idx in range(n_rounds_refine):
            T = T0_refine * (T_decay_refine ** round_idx)
            current_step = base_step_refine * (step_decay_refine ** round_idx)
            
            # Get relevant triangles with tighter threshold
            current_min_area = get_smallest_triangle_area(current)
            triangle_indices = get_adaptive_triangle_indices(current, current_min_area)
            
            if not triangle_indices:
                continue
                
            chosen_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
            
            # 70% chance to perturb one point, 30% to perturb all three (more precise)
            candidate = current.copy()
            if np.random.rand() < 0.7:
                idx = chosen_triangle[np.random.randint(3)]
                bary = cartesian_to_barycentric(candidate[idx])
                bary_perturb = bary + np.random.normal(0, current_step, size=3)
                bary_perturb = np.clip(bary_perturb, 0.0001, 0.9999)
                bary_perturb = bary_perturb / np.sum(bary_perturb)
                candidate[idx] = barycentric_to_cartesian(bary_perturb)
            else:
                for idx in chosen_triangle:
                    bary = cartesian_to_barycentric(candidate[idx])
                    bary_perturb = bary + np.random.normal(0, current_step, size=3)
                    bary_perturb = np.clip(bary_perturb, 0.0001, 0.9999)
                    bary_perturb = bary_perturb / np.sum(bary_perturb)
                    candidate[idx] = barycentric_to_cartesian(bary_perturb)

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - current_score
            
            # Track best overall solution
            if candidate_score > best_score:
                best = candidate.copy()
                best_score = candidate_score
                stagnation_counter = 0
            else:
                stagnation_counter += 1

            # Stagnation handling
            if stagnation_counter > stagnation_threshold:
                current = best.copy()
                current_score = best_score
                stagnation_counter = 0
            else:
                # Acceptance criterion
                if delta > 0 or np.random.rand() < np.exp(delta / (T + 1e-10)):
                    current = candidate
                    current_score = candidate_score

        return best

    # Apply two-phase optimization
    optimized_points = two_phase_optimization(points)
    
    # Final validation check
    if not is_inside_triangle(optimized_points, A, B, C):
        # Project any points outside back to the triangle
        for i in range(len(optimized_points)):
            if not is_inside_triangle(optimized_points[i], A, B, C):
                optimized_points[i] = project_to_triangle(optimized_points[i])

    return optimized_points