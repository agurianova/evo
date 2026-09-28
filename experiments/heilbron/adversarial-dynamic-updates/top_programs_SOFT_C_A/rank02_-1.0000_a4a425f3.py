import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from collections import deque
import random

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    # Get the unit triangle vertices
    A, B, C = get_unit_triangle()
    
    # Precompute side length for barycentric scaling
    side_length = np.linalg.norm(B - A)
    
    # Helper functions for barycentric conversion
    denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
    
    def to_bary(p):
        u = ((B[1] - C[1]) * (p[0] - C[0]) + (C[0] - B[0]) * (p[1] - C[1])) / denom
        v = ((C[1] - A[1]) * (p[0] - C[0]) + (A[0] - C[0]) * (p[1] - C[1])) / denom
        return u, v
    
    def to_cart(u, v):
        w = 1 - u - v
        return u * A + v * B + w * C
    
    def clamp_bary(u, v):
        """Clamp barycentric coordinates to be inside the triangle."""
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))
        if u + v > 1.0:
            scale = 1.0 / (u + v)
            u *= scale
            v *= scale
        return u, v
    
    def get_boundary_penalty(p):
        """Returns scaling factor based on proximity to boundary (1.0 at center, approaches 0 near boundaries)"""
        u, v = to_bary(p)
        w = 1 - u - v
        
        # Distance to each boundary
        dist_to_AB = w
        dist_to_AC = v
        dist_to_BC = u
        
        # Get nearest boundary distance
        min_dist = min(dist_to_AB, dist_to_AC, dist_to_BC)
        
        # Smooth scaling factor (cubic function for smooth transition)
        scale_factor = 1.0 - (1.0 - min_dist)**3
        
        return scale_factor
    
    def calculate_triangle_areas(points, triangles):
        """Calculate areas for specified triangles only."""
        areas = {}
        for i, j, k in triangles:
            x1, y1 = points[i]
            x2, y2 = points[j]
            x3, y3 = points[k]
            area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
            areas[(i, j, k)] = area
        return areas

    def get_affected_triangles(perturbed_indices, n):
        """Return indices of all triangles containing any of the perturbed points."""
        affected = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    if i in perturbed_indices or j in perturbed_indices or k in perturbed_indices:
                        affected.append((i, j, k))
        return affected

    def get_minimal_triangles(area_cache, tol=1e-9):
        """Find minimal area triangles from cache."""
        if not area_cache:
            return [], float('inf')
        
        min_area = min(area_cache.values())
        min_triplets = [triplet for triplet, area in area_cache.items() 
                       if abs(area - min_area) < tol]
        return min_triplets, min_area

    def run_optimization(initial_points):
        best_points = initial_points.copy()
        n = len(best_points)
        
        # Initialize triangle area cache for all combinations
        all_triangles = [(i, j, k) for i in range(n) for j in range(i+1, n) for k in range(j+1, n)]
        area_cache = calculate_triangle_areas(best_points, all_triangles)
        min_triplets, min_area = get_minimal_triangles(area_cache)
        
        # Parameters for local search
        initial_step = 0.05
        step_size = initial_step
        stagnation_count = 0
        max_iterations = 500
        tol = 1e-10
        min_distance = 0.01  # Minimum distance between points
        
        # Track improvement rate for adaptive step decay
        improvement_history = deque(maxlen=20)
        improvement_history.append(0)  # Start with no improvement

        for _ in range(max_iterations):
            if not min_triplets:
                # Recalculate all if cache is empty
                area_cache = calculate_triangle_areas(best_points, all_triangles)
                min_triplets, min_area = get_minimal_triangles(area_cache)
                if not min_triplets:
                    break

            # Count vertex frequencies in minimal triangles
            freq = [0] * n
            for triplet in min_triplets:
                for idx in triplet:
                    freq[idx] += 1
            
            # Get points involved in minimal triangles, sorted by frequency
            candidate_indices = sorted(range(n), key=lambda i: -freq[i])
            
            # Try gradient-based improvements
            improvement_found = False
            best_candidate = None
            best_candidate_score = min_area

            # Calculate combined gradients for all minimal triangles
            gradients = np.zeros((n, 2))
            for triplet in min_triplets:
                i, j, k = triplet
                p_i, p_j, p_k = best_points[i], best_points[j], best_points[k]
                
                # Calculate gradient for area increase
                grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]])
                grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]])
                grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]])

                # Normalize gradients
                norm_i = np.linalg.norm(grad_i)
                norm_j = np.linalg.norm(grad_j)
                norm_k = np.linalg.norm(grad_k)
                
                if norm_i > 0: grad_i = grad_i / norm_i
                if norm_j > 0: grad_j = grad_j / norm_j
                if norm_k > 0: grad_k = grad_k / norm_k

                # Add to combined gradients
                gradients[i] += grad_i
                gradients[j] += grad_j
                gradients[k] += grad_k

            # Normalize combined gradients
            for i in range(n):
                norm = np.linalg.norm(gradients[i])
                if norm > 0:
                    gradients[i] = gradients[i] / norm

            # Apply gradient moves to high-frequency points
            for idx in candidate_indices:
                if freq[idx] == 0:
                    break
                
                # Skip if gradient is zero
                if np.linalg.norm(gradients[idx]) < 1e-10:
                    continue
                
                # Create candidate by moving point along combined gradient
                candidate = best_points.copy()
                candidate[idx] += gradients[idx] * step_size

                # Check minimum distance to other points
                too_close = False
                for i in range(n):
                    if i == idx:
                        continue
                    dist = np.linalg.norm(candidate[i] - candidate[idx])
                    if dist < min_distance:
                        too_close = True
                        break
                
                # Check and evaluate candidate
                if not too_close and is_inside_triangle(candidate, A, B, C):
                    # Only recalculate affected triangles
                    affected = get_affected_triangles([idx], n)
                    new_areas = calculate_triangle_areas(candidate, affected)
                    
                    # Update cache temporarily
                    old_cache = area_cache.copy()
                    area_cache.update(new_areas)
                    _, new_min_area = get_minimal_triangles(area_cache)
                    
                    # Restore cache
                    area_cache = old_cache
                    
                    if new_min_area > best_candidate_score:
                        best_candidate = candidate
                        best_candidate_score = new_min_area
                        improvement_found = True
                        break

            if improvement_found:
                best_points = best_candidate
                # Update cache with new areas
                affected = get_affected_triangles([idx], n)
                new_areas = calculate_triangle_areas(best_points, affected)
                area_cache.update(new_areas)
                min_triplets, min_area = get_minimal_triangles(area_cache)
                
                # Increase step size when improving (but cap it)
                step_size = min(step_size * 1.05, initial_step)
                improvement_history.append(1)
                stagnation_count = 0
                continue

            # If gradient moves didn't work, try perturbations on problematic points
            for idx in candidate_indices:
                if freq[idx] == 0:
                    break  # No more relevant points
                
                # Convert point to barycentric and perturb
                u, v = to_bary(best_points[idx])
                step_size_bary = step_size / side_length
                
                # Try multiple perturbations
                for _ in range(10):
                    du = np.random.normal(0, step_size_bary)
                    dv = np.random.normal(0, step_size_bary)
                    u_new, v_new = u + du, v + dv
                    u_new, v_new = clamp_bary(u_new, v_new)
                    
                    # Convert back to Cartesian
                    new_point = to_cart(u_new, v_new)
                    candidate = best_points.copy()
                    candidate[idx] = new_point
                    
                    # Check minimum distance to other points
                    too_close = False
                    for i in range(n):
                        if i == idx:
                            continue
                        dist = np.linalg.norm(candidate[i] - new_point)
                        if dist < min_distance:
                            too_close = True
                            break
                    
                    # Check and evaluate candidate
                    if too_close or not is_inside_triangle(candidate, A, B, C):
                        continue
                    
                    # Only recalculate affected triangles
                    affected = get_affected_triangles([idx], n)
                    new_areas = calculate_triangle_areas(candidate, affected)
                    
                    # Update cache temporarily
                    old_cache = area_cache.copy()
                    area_cache.update(new_areas)
                    _, new_min_area = get_minimal_triangles(area_cache)
                    
                    # Restore cache
                    area_cache = old_cache
                    
                    if new_min_area > best_candidate_score:
                        best_candidate = candidate
                        best_candidate_score = new_min_area
                        improvement_found = True

            if improvement_found:
                best_points = best_candidate
                # Update cache with new areas
                affected = get_affected_triangles([idx], n)
                new_areas = calculate_triangle_areas(best_points, affected)
                area_cache.update(new_areas)
                min_triplets, min_area = get_minimal_triangles(area_cache)
                
                # Increase step size when improving (but cap it)
                step_size = min(step_size * 1.05, initial_step)
                improvement_history.append(1)
                stagnation_count = 0
            else:
                improvement_history.append(0)
                stagnation_count += 1

            # Adaptive step decay based on improvement rate
            avg_improvement = sum(improvement_history) / len(improvement_history)
            # Decay more aggressively when stuck
            step_decay = 0.97 - 0.02 * avg_improvement  # Ranges from 0.95 to 0.97
            step_size *= step_decay

            # Step size reset on prolonged stagnation
            if stagnation_count >= 20:
                step_size = 0.25 * initial_step
                stagnation_count = 0

            # Termination condition: small step size with no improvement
            if step_size < 1e-6 and stagnation_count > 15:
                break

        return best_points

    def generate_randomized_initial_config():
        points = []
        n = 11
        
        # Randomly assign points to vertices (1-3 points per vertex)
        vertex_counts = [random.randint(1, 3) for _ in range(3)]
        # Ensure we have exactly 11 points
        while sum(vertex_counts) + 3 > n:  # +3 for edge points
            # Reduce a random count
            idx = random.randint(0, 2)
            if vertex_counts[idx] > 1:
                vertex_counts[idx] -= 1
        
        # Make sure we have enough points for interior
        while sum(vertex_counts) + 3 + 2 > n:  # +3 for edges, +2 for interior
            idx = random.randint(0, 2)
            if vertex_counts[idx] > 1:
                vertex_counts[idx] -= 1

        # Points near vertices
        for i, count in enumerate(vertex_counts):
            for _ in range(count):
                offset = 0.01 + 0.04 * np.random.random()
                if i == 0:  # Near A
                    points.append(to_cart(offset, offset))
                elif i == 1:  # Near B
                    points.append(to_cart(1 - offset, offset))
                else:  # Near C
                    points.append(to_cart(offset, 1 - offset))

        # Points along edges (1 on each edge)
        for i in range(3):
            edge_offset = 0.3 + 0.4 * np.random.random()
            if i == 0:  # AB edge
                points.append(to_cart(edge_offset, 0))
            elif i == 1:  # AC edge
                points.append(to_cart(0, edge_offset))
            else:  # BC edge
                points.append(to_cart(edge_offset, 1 - edge_offset))

        # Interior points (at least 2)
        interior_count = n - len(points)
        for _ in range(interior_count):
            u = 0.2 + 0.5 * np.random.random()
            v = 0.1 + 0.5 * np.random.random()
            # Ensure we're inside the triangle
n            if u + v > 1.0:
                u, v = u / (u + v), v / (u + v)
            points.append(to_cart(u, v))

        return np.array(points)

    # Run multiple restarts with randomized initial configurations
    best_overall = None
    best_score_overall = -1
    
    for restart in range(10):  # Increased restarts to 10
        initial_points = generate_randomized_initial_config()
        points = run_optimization(initial_points)
        score = get_smallest_triangle_area(points)
        
        if score > best_score_overall:
            best_overall = points
            best_score_overall = score

    return best_overall