import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

# Boundary buffer percentage (1.5%)
BOUNDARY_BUFFER = 0.015
MAX_THEORETICAL_AREA = 0.0365

# Multi-bottleneck weights for top 3 smallest triangles
BOTTLENECK_WEIGHTS = [0.7, 0.2, 0.1]


def hexagonal_lattice_points(n, buffer=BOUNDARY_BUFFER):
    """Generate n points in a hexagonal lattice pattern within the triangle with boundary buffer."""
    A, B, C = get_unit_triangle()
    
    # Calculate triangle height and base
    base = np.linalg.norm(B - A)
    height = np.linalg.norm(C - (A + B) / 2)
    
    # Adjust for boundary buffer
    buffer_base = base * (1 - buffer)
    buffer_height = height * (1 - buffer)
    
    # Hexagonal grid parameters
    points = []
    row_count = 1
    total_points = 0
    
    # Determine number of rows needed
    while total_points < n:
        points_in_row = min(row_count, n - total_points)
        total_points += points_in_row
n        row_count += 1
    
    # Generate points
    y_step = buffer_height / (row_count - 1)
    for row in range(row_count - 1):
        y_pos = buffer * height / 2 + row * y_step
        points_in_row = min(row + 1, n - len(points))
        
        # X positions with hexagonal staggering
        x_step = buffer_base / points_in_row
        for col in range(points_in_row):
            # Stagger even rows
            x_offset = 0 if row % 2 == 0 else x_step / 2
            x_pos = buffer * base / 2 + col * x_step + x_offset
            
            # Convert to barycentric coordinates
            v = y_pos / height
            u = x_pos / base * (1 - v)
            
            # Convert to Cartesian
            P = (1 - u - v) * A + u * B + v * C
            points.append(P)
    
    return np.array(points)

def compute_bottleneck_score(points, k=3):
    """Compute weighted score based on top k smallest triangles."""
    n = points.shape[0]
    areas = []
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                a, b, c = points[i], points[j], points[k]
                area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                areas.append(area)
    
    areas.sort()
    # Take top k smallest areas
    top_k = areas[:k] if len(areas) >= k else areas
    
    # Pad with largest area if fewer than k triangles
    while len(top_k) < k:
        top_k.append(areas[-1] if areas else 0)
    
    # Weighted sum (larger weights for smaller triangles)
    score = sum(w * area for w, area in zip(BOTTLENECK_WEIGHTS, top_k))
    return score

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Generate initial hexagonal lattice points with boundary buffer
    initial_points = hexagonal_lattice_points(11, buffer=BOUNDARY_BUFFER)
    
    best_config = None
    best_score = -1
    
    # Try different initial configurations
    initial_configs = [
        initial_points,
        initial_points + np.random.uniform(-0.01, 0.01, size=initial_points.shape),
        initial_points + np.random.uniform(-0.02, 0.02, size=initial_points.shape)
    ]

    for config_idx, current in enumerate(initial_configs):
        # Ensure all points are inside triangle (with buffer)
        for i in range(len(current)):
            if not is_inside_triangle(current[i], A, B, C):
                # Project back inside with buffer
                v = (current[i][1] - A[1]) / (C[1] - A[1])
                u = (current[i][0] - A[0]) / (B[0] - A[0]) * (1 - v)
                # Apply buffer
                v = max(BOUNDARY_BUFFER/2, min(1 - BOUNDARY_BUFFER/2, v))
                u = max(BOUNDARY_BUFFER/2, min(1 - BOUNDARY_BUFFER/2, u))
                current[i] = (1 - u - v) * A + u * B + v * C

        current_score = compute_bottleneck_score(current)
        
        # Simulated annealing parameters - enhanced exploration
        initial_temp = 0.005  # Increased from 0.001
        temp_decay = 0.999    # Slowed from 0.995
        initial_step = 0.025  # Increased from 0.02
        step_decay = 0.9995   # Slowed from 0.999
        max_iter = 5000
        early_stop = 500
        
        temp = initial_temp
        step_size = initial_step
        no_improve = 0
        
        # Track best in this restart
        restart_best = current.copy()
        restart_best_score = current_score
        
        for it in range(max_iter):
            # 70% chance to perturb bottleneck points, 30% random
            if np.random.rand() < 0.7:
                # Get indices of top 3 smallest triangles
                n = current.shape[0]
                triangles = []
                for i in range(n):
                    for j in range(i+1, n):
                        for k in range(j+1, n):
                            a, b, c = current[i], current[j], current[k]
                            area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                            triangles.append((area, i, j, k))
                
                triangles.sort(key=lambda x: x[0])
                bottleneck_indices = set()
                for _, i, j, k in triangles[:3]:
                    bottleneck_indices.add(i)
                    bottleneck_indices.add(j)
                    bottleneck_indices.add(k)
                
                idx = np.random.choice(list(bottleneck_indices))
            else:
                idx = np.random.randint(0, 11)

            # Generate candidate move
            step = np.random.normal(0, step_size, size=2)
            candidate = current.copy()
            candidate[idx] += step

            # Validate containment with boundary buffer
            if not is_inside_triangle(candidate[idx], A, B, C):
                # Project back inside with buffer
                v = (candidate[idx][1] - A[1]) / (C[1] - A[1])
                u = (candidate[idx][0] - A[0]) / (B[0] - A[0]) * (1 - v)
                # Apply buffer
                v = max(BOUNDARY_BUFFER, min(1 - BOUNDARY_BUFFER, v))
                u = max(BOUNDARY_BUFFER, min(1 - BOUNDARY_BUFFER, u))
                candidate[idx] = (1 - u - v) * A + u * B + v * C

            # Evaluate candidate
            new_score = compute_bottleneck_score(candidate)

            # Simulated annealing acceptance
            if new_score > current_score:
                current = candidate
                current_score = new_score
                if new_score > restart_best_score:
                    restart_best = candidate.copy()
                    restart_best_score = new_score
                no_improve = 0
            else:
                delta = current_score - new_score
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

        # Final refinement phase - precise tuning of smallest triangle
        refinement_steps = 300
        refinement_step_size = 0.005
        
        for _ in range(refinement_steps):
            # Focus on absolute smallest triangle
            n = restart_best.shape[0]
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = restart_best[i], restart_best[j], restart_best[k]
                        area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        triangles.append((area, i, j, k))
            
            if not triangles:
                break
                
            triangles.sort(key=lambda x: x[0])
            _, i, j, k = triangles[0]
            
            # Compute gradient to increase triangle area
            a, b, c = restart_best[i], restart_best[j], restart_best[k]
            grad_i = np.array([b[1] - c[1], c[0] - b[0]])
            grad_j = np.array([c[1] - a[1], a[0] - c[0]])
            grad_k = np.array([a[1] - b[1], b[0] - a[0]])
            
            # Normalize gradients
            for grad in [grad_i, grad_j, grad_k]:
                norm = np.linalg.norm(grad)
                if norm > 1e-10:
                    grad /= norm

            # Apply noiseless movement
            candidate = restart_best.copy()
            candidate[i] += refinement_step_size * grad_i
            candidate[j] += refinement_step_size * grad_j
            candidate[k] += refinement_step_size * grad_k

            # Project out-of-bound points
            for idx in [i, j, k]:
                if not is_inside_triangle(candidate[idx], A, B, C):
                    v = (candidate[idx][1] - A[1]) / (C[1] - A[1])
                    u = (candidate[idx][0] - A[0]) / (B[0] - A[0]) * (1 - v)
                    v = max(BOUNDARY_BUFFER, min(1 - BOUNDARY_BUFFER, v))
                    u = max(BOUNDARY_BUFFER, min(1 - BOUNDARY_BUFFER, u))
                    candidate[idx] = (1 - u - v) * A + u * B + v * C

            # Evaluate candidate
            new_score = compute_bottleneck_score(candidate)
            if new_score > restart_best_score:
                restart_best = candidate
                restart_best_score = new_score

        # Update global best
        if restart_best_score > best_score:
            best_score = restart_best_score
            best_config = restart_best

    return best_config