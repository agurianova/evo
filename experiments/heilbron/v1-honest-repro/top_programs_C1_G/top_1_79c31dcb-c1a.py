import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area
import scipy.optimize

def entrypoint() -> np.ndarray:
    # Get triangle vertices and compute key dimensions
    A, B, C = get_unit_triangle()
    s = B[0] - A[0]  # Base length
    H = C[1]         # Height (since base is on x-axis)

    # Generate initial configuration using known [4,3,2,2] hexagonal pattern
    rows = [4, 3, 2, 2]
    total_rows = len(rows)
    points = []
    for i in range(total_rows):
        y_i = H * (i + 0.5) / total_rows
        width_i = s * (1 - y_i / H)
        num_points = rows[i]
        
        # Horizontal spacing and hexagonal offset
        dx = width_i / (num_points - 1) if num_points > 1 else 0.0
        start_x = dx / 2.0 if i % 2 == 1 else 0.0
        
        # Left boundary at current height
        left_boundary = (s * y_i) / (2 * H)
        
        # Generate points for this row
        for j in range(num_points):
            x = left_boundary + start_x + j * dx
            points.append([x, y_i])

    initial_points = np.array(points)

    # Define constraints for COBYLA (points must stay inside triangle)
    def constraint_func(x_flat):
        pts = x_flat.reshape(11, 2)
        constraints = []
        for i in range(11):
            x, y = pts[i]
            constraints.append(y)  # y >= 0
            constraints.append(np.sqrt(3) * x - y)  # y <= sqrt(3)*x
            constraints.append(np.sqrt(3) * (s - x) - y)  # y <= sqrt(3)*(s-x)
        return np.array(constraints)

    # Define objective: maximize min_area = minimize -min_area
    def objective(x_flat):
        pts = x_flat.reshape(11, 2)
        return -get_smallest_triangle_area(pts)

    # Run constrained optimization
    x0 = initial_points.flatten()
    cons = {'type': 'ineq', 'fun': constraint_func}
    res = scipy.optimize.minimize(
        objective, 
        x0, 
        method='COBYLA',
        constraints=cons,
        options={'maxiter': 10000, 'disp': False}
    )

    # Return optimized points if successful, else initial configuration
    return res.x.reshape(11, 2) if res.success else initial_points