import numpy as np
from helper import get_unit_triangle, is_inside_triangle

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Define initial grid parameters
    t_values = [0.05, 0.25, 0.45, 0.65, 0.85]  # Height fractions from base
    num_points_per_row = [4, 3, 2, 1, 1]      # Points per row
    total_height = C[1]  # Height of triangle

    # Generate initial symmetric grid
    points = []
    for i, t in enumerate(t_values):
        num = num_points_per_row[i]
        y = t * total_height
        # Calculate left and right x-boundaries at current height
        left_x = (C[0] / total_height) * y
        right_x = B[0] - (C[0] / total_height) * y
        
        for j in range(num):
            x = left_x + (j + 0.5) / num * (right_x - left_x)
            points.append(np.array([x, y]))
    
    points = np.array(points)
    
    # Break symmetry with controlled random perturbation
    np.random.seed(42)
    points += np.random.uniform(-0.001, 0.001, size=points.shape)
    
    # Helper: Project point to triangle using barycentric coordinates
    def project_to_triangle(P):
        v0 = B - A
        v1 = C - A
        v2 = P - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        if abs(denom) < 1e-10:
            return (A + B + C) / 3
            
        b_coord = (d11 * d20 - d01 * d21) / denom
        c_coord = (d00 * d21 - d01 * d20) / denom
        a_coord = 1.0 - b_coord - c_coord
        
        # Clamp negative coordinates and renormalize
        if a_coord < 0:
            a_coord = 0
            total = b_coord + c_coord
            if total > 0:
                b_coord /= total
                c_coord /= total
            else:
                b_coord = c_coord = 0.5
        if b_coord < 0:
            b_coord = 0
            total = a_coord + c_coord
            if total > 0:
                a_coord /= total
                c_coord /= total
            else:
                a_coord = c_coord = 0.5
        if c_coord < 0:
            c_coord = 0
            total = a_coord + b_coord
            if total > 0:
                a_coord /= total
                b_coord /= total
            else:
                a_coord = b_coord = 0.5

        return a_coord * A + b_coord * B + c_coord * C

    # Project perturbed points back to triangle
    for idx in range(len(points)):
        if not is_inside_triangle(points[idx], A, B, C):
            points[idx] = project_to_triangle(points[idx])

    # Local optimization: 1000 iterations with batch triangle updates
    n = len(points)
    for iteration in range(1000):
        # Compute all triangles and find top 3 smallest
        triangles = []  # (area, i, j, k)
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a = points[i]
                    b = points[j]
                    c = points[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    triangles.append((area, i, j, k))
        
        # Sort by area and take top 3 smallest
        triangles.sort(key=lambda x: x[0])
        top_k = triangles[:3]

        # Initialize gradient accumulators
        grad_accum = np.zeros((n, 2))
        count = np.zeros(n, dtype=int)

        # Process each critical triangle
        for (area_val, i, j, k) in top_k:
            a, b, c = points[i], points[j], points[k]
            # Compute signed area for direction
            s = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
            direction = 1.0 if s >= 0 else -1.0

            # Compute gradients for the three points
            grad_a = direction * np.array([0.5*(b[1]-c[1]), 0.5*(c[0]-b[0])])
            grad_b = direction * np.array([0.5*(c[1]-a[1]), 0.5*(a[0]-c[0])])
            grad_c = direction * np.array([0.5*(a[1]-b[1]), 0.5*(b[0]-a[0])])

            # Accumulate gradients
            grad_accum[i] += grad_a
            grad_accum[j] += grad_b
            grad_accum[k] += grad_c
            count[i] += 1
            count[j] += 1
            count[k] += 1

        # Update points with averaged gradients and adaptive step size
        for idx in range(n):
            if count[idx] > 0:
                avg_grad = grad_accum[idx] / count[idx]
                step_size = 0.01 * (0.99 ** iteration)
                points[idx] += step_size * avg_grad

        # Project updated points back to triangle if outside
        for idx in range(n):
            if not is_inside_triangle(points[idx], A, B, C):
                points[idx] = project_to_triangle(points[idx])

    return points