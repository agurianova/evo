import random
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import numpy as np
import cma
from scipy.stats import qmc
from scipy.spatial import Delaunay

np.random.seed(123)
random.seed(123)

# Precompute unit triangle once
global_tri = get_unit_triangle()
A, B, C = global_tri

# Helper function to generate non-decreasing partitions with more flexibility
def generate_partitions(k, total, min_val, max_val):
    if k == 1:
        if min_val <= total <= max_val:
            return [[total]]
        return []
    res = []
    start = min_val
    end = min(max_val, total - (k-1)*min_val)
    for first in range(start, end+1):
        for p in generate_partitions(k-1, total - first, first, max_val):
            res.append([first] + p)
    return res

def get_bottleneck_triangles(points, top_n=5):
    """Use Delaunay triangulation to identify critical bottleneck triangles"""
    try:
        tri = Delaunay(points)
        areas = []
        
        for simplex in tri.simplices:
            i, j, k = simplex
            a, b, c = points[i], points[j], points[k]
            area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
            areas.append((area_val, i, j, k))
        
        areas.sort(key=lambda x: x[0])
        return [tri for (_, i, j, k) in areas[:top_n] for tri in [(i, j, k)]]
    except:
        # Fallback to brute force if Delaunay fails
        n = points.shape[0]
        areas = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                    areas.append((area_val, i, j, k))
        
        areas.sort(key=lambda x: x[0])
        return [tri for (_, i, j, k) in areas[:top_n] for tri in [(i, j, k)]]

def resistance_score(points, num_tests=25, perturbation_scale=0.02):
    """Estimate resistance by applying random perturbations and checking if min_area improves"""
    original_min_area = get_smallest_triangle_area(points)
    robust_count = 0
    
    # Identify critical bottleneck triangles to focus perturbations
    bottleneck_indices = set()
    for tri in get_bottleneck_triangles(points, top_n=3):
        bottleneck_indices.update(tri)
    bottleneck_indices = list(bottleneck_indices)
    
    for _ in range(num_tests):
        perturbed = points.copy()
        
        # Apply perturbations focused on bottleneck points
        for idx in bottleneck_indices:
            perturbation = np.random.normal(0, perturbation_scale, size=2)
            perturbed[idx] = points[idx] + perturbation
            
            # Project back to triangle if needed
            if not is_inside_triangle(perturbed[idx], A, B, C):
                bary = np.linalg.solve(
                    np.array([[A[0], B[0], C[0]], 
                              [A[1], B[1], C[1]], 
                              [1, 1, 1]]), 
                    np.array([perturbed[idx,0], perturbed[idx,1], 1]))
                bary = np.maximum(bary, 0)
                bary = bary / np.sum(bary)
                perturbed[idx] = A * bary[0] + B * bary[1] + C * bary[2]
        
        # Check distinctness
        distinct = True
        for i in range(len(perturbed)):
            for j in range(i+1, len(perturbed)):
                if np.linalg.norm(perturbed[i] - perturbed[j]) < 1e-5:
                    distinct = False
                    break
            if not distinct:
                break
        
        if not distinct:
            continue
        
        new_min_area = get_smallest_triangle_area(perturbed)
        if new_min_area <= original_min_area:
            robust_count += 1
    
    return robust_count / num_tests

def entrypoint() -> np.ndarray:
    # Generate candidate row patterns for 2-7 rows (expanded from 3-6)
    candidates = []
    for k in range(2, 8):  # Expanded from range(3, 7) to range(2, 8)
        parts = generate_partitions(k, 11, 1, 5)
        candidates.extend(parts)

    best_quality = -1
    best_resistance = -1
    best_points = None
    
    # Use Sobol sequence for more systematic phase exploration
    sobol = qmc.Sobol(d=1, scramble=False)
    phase_samples = sobol.random_base2(m=4)[:15]  # 15 deterministic samples

    for row_counts in candidates:
        num_rows = len(row_counts)
        # Generate vertical levels from top (v=1) to bottom (v=0)
        v_levels = [1 - i/(num_rows-1) if num_rows>1 else 1.0 for i in range(num_rows)]
        
        for phase in phase_samples:  # Using systematic Sobol samples instead of random
            phase_val = phase[0]
            points = []
            for i in range(num_rows):
                num_points = row_counts[i]
                v = v_levels[i]
                for j in range(num_points):
                    u_val = 0.5 * (1 - np.cos(np.pi * (j + phase_val) / num_points)) * (1 - v)
                    P = (1 - u_val - v) * A + u_val * B + v * C
                    
                    # Apply symmetry-breaking perturbation with adaptive size
                    max_attempts = 5
                    base_perturb = 0.03 * (1.0 / (1 + row_counts[i]))
                    for _ in range(max_attempts):
                        perturbation = np.random.uniform(-base_perturb, base_perturb, size=2)
                        P_pert = P + perturbation
                        if is_inside_triangle(P_pert, A, B, C):
                            points.append(P_pert)
                            break
                    else:
                        points.append(P)
            
            points = np.array(points)
            min_area = get_smallest_triangle_area(points)
            # Skip degenerate configurations
            if min_area < 1e-9:
                continue
            
            # Estimate resistance
            res_score = resistance_score(points, num_tests=15)
            
            # Balance quality and resistance in selection
            quality = min(min_area / 0.0365, 1.0)
            total_score = 0.5 * quality + 0.5 * res_score
            
            if total_score > 0.5 * best_quality + 0.5 * best_resistance:
                best_quality = quality
                best_resistance = res_score
                best_points = points

    # If we didn't find any valid configuration, use a fallback
    if best_points is None:
        # Fallback to a known good configuration
        angles = np.linspace(0, 2*np.pi, 11, endpoint=False)
        radii = np.sqrt(np.linspace(0.1, 0.9, 11))
        points = np.column_stack([
            0.7598 + radii * np.cos(angles) * 0.3,
            0.6580 + radii * np.sin(angles) * 0.3
        ])
        # Project all points to be inside triangle
        for i in range(11):
            if not is_inside_triangle(points[i], A, B, C):
                bary = np.linalg.solve(
                    np.array([[A[0], B[0], C[0]], 
                              [A[1], B[1], C[1]], 
                              [1, 1, 1]]), 
                    np.array([points[i,0], points[i,1], 1]))
                bary = np.maximum(bary, 0)
                bary = bary / np.sum(bary)
                points[i] = A * bary[0] + B * bary[1] + C * bary[2]
        best_points = points
        best_quality = min(get_smallest_triangle_area(points) / 0.0365, 1.0)
        best_resistance = 0.5  # Conservative estimate

    # Multi-start optimization with different seeds
    best_overall = None
    best_fitness = -1
    
    for seed in [123, 456, 789]:
        np.random.seed(seed)
        random.seed(seed)
        
        # Precompute conversion matrix from Cartesian to barycentric
        T = np.array([
            [A[0], B[0], C[0]],
            [A[1], B[1], C[1]],
            [1, 1, 1]
        ])
        T_inv = np.linalg.inv(T)
        
        def cartesian_to_barycentric(pts):
            if pts.ndim == 1:
                homogeneous = np.array([pts[0], pts[1], 1.0])
                return T_inv @ homogeneous
            else:
                result = np.empty((pts.shape[0], 3))
                for i in range(pts.shape[0]):
                    homogeneous = np.array([pts[i,0], pts[i,1], 1.0])
                    result[i] = T_inv @ homogeneous
                return result
        
        def barycentric_to_cartesian(bary):
            if bary.ndim == 1:
                return A * bary[0] + B * bary[1] + C * bary[2]
            else:
                return np.array([A * b[0] + B * b[1] + C * b[2] for b in bary])
        
        def fitness_function(flat_points):
            # Reshape to (11, 2)
            points = flat_points.reshape(11, 2)
            
            # Compute constraint violation penalty
            penalty = 0.0
            for i in range(11):
                bary = cartesian_to_barycentric(points[i])
                neg_parts = np.minimum(bary, 0)
                penalty += np.sum(np.abs(neg_parts))
            
            # Calculate minimum triangle area
            min_area = get_smallest_triangle_area(points)
            
            # Estimate resistance (lightweight version for optimization)
            res_score = 0.0
            if min_area > 1e-5:
                # Only do limited resistance check during optimization
                res_score = resistance_score(points, num_tests=5, perturbation_scale=0.01)
            
            # Apply soft penalty for constraint violations
            if penalty > 0:
                return -(0.5 * min_area + 0.5 * res_score) + 1000 * penalty
            
            # Balance quality and resistance in the fitness
            return -(0.5 * min_area + 0.5 * res_score)

        # Adaptive CMA-ES parameters
        initial_points = best_points.flatten()
        options = {
            'seed': seed,
            'maxiter': 400,  # Slightly increased base iterations
            'popsize': 100,
            'AdaptSigma': True,
            'verb_disp': 0,
            'verb_log': 0,
            'tolfun': 1e-8,
            'tolx': 1e-8
        }

        # Run CMA-ES optimization
        res = cma.fmin(
            fitness_function,
            initial_points,
            0.03,
            options=options
        )

        # Get the best solution and reshape
        candidate_points = res[0].reshape(11, 2)
        
        # Final constraint safeguard
        for i in range(11):
            if not is_inside_triangle(candidate_points[i], A, B, C):
                bary = cartesian_to_barycentric(candidate_points[i])
                bary = np.maximum(bary, 0)
                bary = bary / np.sum(bary)
                candidate_points[i] = barycentric_to_cartesian(bary)

        # Evaluate final quality and resistance
        min_area = get_smallest_triangle_area(candidate_points)
        quality = min(min_area / 0.0365, 1.0)
        res_score = resistance_score(candidate_points, num_tests=25)
        fitness = 0.5 * quality + 0.5 * res_score
        
        if fitness > best_fitness:
            best_fitness = fitness
            best_overall = candidate_points

    return best_overall