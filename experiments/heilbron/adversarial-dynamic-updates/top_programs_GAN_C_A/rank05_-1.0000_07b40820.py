import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
from scipy.spatial import distance_matrix

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Add 1.5% boundary buffer to prevent edge vulnerabilities
    buffer = 0.015
    
    # Candidate row distributions (asymmetric patterns for n=11)
    distributions = [
        [5, 3, 2, 1],
        [4, 3, 3, 1],
        [4, 4, 2, 1],
        [3, 3, 3, 2],
        [5, 4, 2],
        [6, 3, 2],
        [5, 5, 1]
    ]
    
    best_config = None
    best_score = -1
    
    # Helper to find indices of smallest triangles with multi-bottleneck scoring
    def compute_min_triangle_indices(points, k=3):
        n = points.shape[0]
        triangles = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    triangles.append((area, i, j, k))
        
        # Sort by area and take top k
        triangles.sort(key=lambda x: x[0])
        return triangles[:k]

    # Force-directed layout initialization
    def generate_force_directed_layout(num_points):
        # Start with random points
        points = np.random.rand(num_points, 2)
        
        # Convert to barycentric coordinates inside triangle
        for i in range(num_points):
            u, v = np.random.rand(), np.random.rand()
            if u + v > 1:
                u, v = 1 - u, 1 - v
            w = 1 - u - v
            points[i] = u * A + v * B + w * C
        
        # Apply force-directed layout
        iterations = 100
        spring_constant = 0.05
        repulsion_constant = 0.01
        
        for _ in range(iterations):
            forces = np.zeros_like(points)
            
            # Calculate repulsion forces between all points
            dists = distance_matrix(points, points)
            for i in range(num_points):
                for j in range(i+1, num_points):
                    if dists[i, j] < 1e-5:
                        continue
                    direction = points[i] - points[j]
                    force_magnitude = repulsion_constant / (dists[i, j] ** 2)
                    force = direction / dists[i, j] * force_magnitude
                    forces[i] += force
                    forces[j] -= force
            
            # Apply forces with boundary constraints
n            for i in range(num_points):
                new_point = points[i] + forces[i]
                
                # Convert to barycentric coordinates
                v0 = B - A
                v1 = C - A
                v2 = new_point - A
                d00 = np.dot(v0, v0)
                d01 = np.dot(v0, v1)
                d11 = np.dot(v1, v1)
                d20 = np.dot(v2, v0)
                d21 = np.dot(v2, v1)
                denom = d00 * d11 - d01 * d01
                
                if abs(denom) > 1e-10:
                    v = (d11 * d20 - d01 * d21) / denom
                    w = (d00 * d21 - d01 * d20) / denom
                    u = 1 - v - w
                    
                    # Apply boundary buffer
                    u = max(buffer, min(1-buffer, u))
                    v = max(buffer, min(1-buffer, v))
                    w = max(buffer, min(1-buffer, w))
                    
                    # Re-normalize
                    total = u + v + w
                    if total > 1e-10:
                        u, v, w = u/total, v/total, w/total
                    
                    points[i] = u * A + v * B + w * C

        return points

    # Helper to apply boundary buffer via barycentric coordinates
    def apply_boundary_buffer(point):
        v0 = B - A
        v1 = C - A
        v2 = point - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        if abs(denom) <= 1e-10:
            return point
            
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1 - v - w
        
        # Apply boundary buffer
        u = max(buffer, min(1-buffer, u))
        v = max(buffer, min(1-buffer, v))
        w = max(buffer, min(1-buffer, w))
        
        # Re-normalize
        total = u + v + w
        if total > 1e-10:
            u, v, w = u/total, v/total, w/total
        
        return u * A + v * B + w * C

    # Generate configurations from multiple strategies
    for _ in range(3):  # Force-directed layouts
        current = generate_force_directed_layout(11)
        current_score = get_smallest_triangle_area(current)
        
        # Simulated annealing parameters - adjusted for better exploration
        initial_temp = 0.01  # Increased from 0.001
        temp_decay = 0.999   # Reduced from 0.995
        initial_step = 0.02  
        step_decay = 0.9995  # Reduced decay from 0.999
        max_iter = 5000
        early_stop = 500
        
        temp = initial_temp
        step_size = initial_step
        no_improve = 0
        
        # Track best in this restart
        restart_best = current.copy()
        restart_best_score = current_score
        
        for it in range(max_iter):
            # Identify top k bottleneck triangles with weighted importance
            min_triangles = compute_min_triangle_indices(current, k=3)
            
            # Weighted selection of points from bottleneck triangles
            weights = [0.7, 0.2, 0.1]  # Decreasing importance for larger triangles
            point_weights = np.zeros(11)
            for i, (area, i1, i2, i3) in enumerate(min_triangles):
                weight = weights[i]
                point_weights[i1] += weight
                point_weights[i2] += weight
                point_weights[i3] += weight
            
            # Normalize and select point
            if np.sum(point_weights) > 0:
                point_weights /= np.sum(point_weights)
                idx = np.random.choice(11, p=point_weights)
            else:
                idx = np.random.randint(0, 11)

            # Generate candidate move
            step = np.random.normal(0, step_size, size=2)
            candidate = current.copy()
            candidate[idx] += step

            # Apply boundary buffer
            candidate[idx] = apply_boundary_buffer(candidate[idx])

            # Evaluate candidate
            new_score = get_smallest_triangle_area(candidate)

            # Multi-bottleneck scoring - consider top 3 triangles
            new_triangles = compute_min_triangle_indices(candidate, k=3)
            current_triangles = compute_min_triangle_indices(current, k=3)
            
            # Calculate weighted score
            new_weighted_score = sum(weights[i] * new_triangles[i][0] for i in range(min(3, len(new_triangles))))
            current_weighted_score = sum(weights[i] * current_triangles[i][0] for i in range(min(3, len(current_triangles))))

            # Simulated annealing acceptance
            if new_weighted_score > current_weighted_score:
                current = candidate
                current_score = new_score
                if new_score > restart_best_score:
                    restart_best = candidate.copy()
                    restart_best_score = new_score
                no_improve = 0
            else:
                delta = current_weighted_score - new_weighted_score
                if np.random.rand() < np.exp(-delta / temp):
                    current = candidate
                    current_score = new_score
                    no_improve = 0
                else:
                    no_improve += 1

            # Adaptive cooling
            temp *= temp_decay
            step_size *= step_decay

            # Early stopping
            if no_improve >= early_stop:
                break

        # Update global best
        if restart_best_score > best_score:
            best_score = restart_best_score
            best_config = restart_best

    # Generate configurations from row distributions
    for row_dist in distributions:
        points = []
        rows = len(row_dist)
        
        # Generate initial grid with row-width scaled perturbation
        for i, num_in_row in enumerate(row_dist):
            v = (i + 0.5) / rows
            for j in range(num_in_row):
                u = (j + 0.5) / num_in_row * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                # Increase perturbation magnitude to break symmetry
                perturbation = np.random.uniform(-0.05 * (1 - v), 0.05 * (1 - v), size=2)
                points.append(P + perturbation)

        current = np.array(points)
        
        # Apply boundary buffer to all points
        for i in range(len(current)):
            current[i] = apply_boundary_buffer(current[i])
            
        current_score = get_smallest_triangle_area(current)
        
        # Simulated annealing parameters - adjusted for better exploration
        initial_temp = 0.01  # Increased from 0.001
        temp_decay = 0.999   # Reduced from 0.995
        initial_step = 0.02  
        step_decay = 0.9995  # Reduced decay from 0.999
        max_iter = 5000
        early_stop = 500
        
        temp = initial_temp
        step_size = initial_step
        no_improve = 0
        
        # Track best in this restart
        restart_best = current.copy()
        restart_best_score = current_score
        
        for it in range(max_iter):
            # Identify top k bottleneck triangles with weighted importance
            min_triangles = compute_min_triangle_indices(current, k=3)
            
            # Weighted selection of points from bottleneck triangles
            weights = [0.7, 0.2, 0.1]  # Decreasing importance for larger triangles
            point_weights = np.zeros(11)
            for i, (area, i1, i2, i3) in enumerate(min_triangles):
                weight = weights[i]
                point_weights[i1] += weight
                point_weights[i2] += weight
                point_weights[i3] += weight
            
            # Normalize and select point
            if np.sum(point_weights) > 0:
                point_weights /= np.sum(point_weights)
                idx = np.random.choice(11, p=point_weights)
            else:
                idx = np.random.randint(0, 11)

            # Generate candidate move
            step = np.random.normal(0, step_size, size=2)
            candidate = current.copy()
            candidate[idx] += step

            # Apply boundary buffer
            candidate[idx] = apply_boundary_buffer(candidate[idx])

            # Evaluate candidate
            new_score = get_smallest_triangle_area(candidate)

            # Multi-bottleneck scoring - consider top 3 triangles
            new_triangles = compute_min_triangle_indices(candidate, k=3)
            current_triangles = compute_min_triangle_indices(current, k=3)
            
            # Calculate weighted score
            new_weighted_score = sum(weights[i] * new_triangles[i][0] for i in range(min(3, len(new_triangles))))
            current_weighted_score = sum(weights[i] * current_triangles[i][0] for i in range(min(3, len(current_triangles))))

            # Simulated annealing acceptance
            if new_weighted_score > current_weighted_score:
                current = candidate
                current_score = new_score
                if new_score > restart_best_score:
                    restart_best = candidate.copy()
                    restart_best_score = new_score
                no_improve = 0
            else:
                delta = current_weighted_score - new_weighted_score
                if np.random.rand() < np.exp(-delta / temp):
                    current = candidate
                    current_score = new_score
                    no_improve = 0
                else:
                    no_improve += 1

            # Adaptive cooling
            temp *= temp_decay
            step_size *= step_decay

            # Early stopping
            if no_improve >= early_stop:
                break

        # Update global best
        if restart_best_score > best_score:
            best_score = restart_best_score
            best_config = restart_best

    return best_config