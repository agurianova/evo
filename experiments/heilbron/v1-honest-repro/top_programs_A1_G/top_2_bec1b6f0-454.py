import numpy as np
import random
from helper import get_unit_triangle, get_smallest_triangle_area
from scipy import optimize

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    s = B[0]

    # Define triangle boundary constraints for SLSQP
    def constraint1(x):
        pts = x.reshape(11, 2)
        return pts[:, 1]  # y >= 0

    def constraint2(x):
        pts = x.reshape(11, 2)
        return np.sqrt(3) * pts[:, 0] - pts[:, 1]  # y <= sqrt(3)*x

    def constraint3(x):
        pts = x.reshape(11, 2)
        return np.sqrt(3) * (s - pts[:, 0]) - pts[:, 1]  # y <= sqrt(3)*(s - x)

    constraints = [
        {'type': 'ineq', 'fun': constraint1},
        {'type': 'ineq', 'fun': constraint2},
        {'type': 'ineq', 'fun': constraint3}
    ]

    # Objective: maximize minimum triangle area
    def objective(x):
        pts = x.reshape(11, 2)
        return -get_smallest_triangle_area(pts)

    # Generate chaotic initial configuration with logistic map perturbations
    def generate_initial():
        rows = [5, 3, 3]
        base_heights = [0.2, 0.5, 0.8]  # Base heights from triangle base
        r = 3.99  # Chaotic parameter
        
        # Perturb row heights chaotically
        x = random.random()
        perturbations = []
        for _ in range(len(rows)):
            x = r * x * (1 - x)
            perturbations.append(x * 0.04 - 0.02)  # [-0.02, 0.02]
        heights = [base_heights[i] + perturbations[i] for i in range(len(rows))]

        points = []
        for i, row_count in enumerate(rows):
            h = heights[i]
            for j in range(row_count):
                # Base horizontal position
                base_u = (j + 0.5) / row_count * (1 - h)
                
                # Chaotic horizontal offset
                x_offset = (i * 10 + j + 1) * 0.1
                for _ in range(5):
                    x_offset = r * x_offset * (1 - x_offset)
                offset = (x_offset - 0.5) * 0.1 * (1 - h)
                
                u = np.clip(base_u + offset, 0, 1 - h)
                P = (1 - u - h) * A + u * B + h * C
                points.append(P)
        return np.array(points)

    # Multiple restarts with SLSQP optimization
    best_points = None
    best_area = -1.0

    for _ in range(15):
        initial = generate_initial()
        perturbed = initial + np.random.uniform(-0.005, 0.005, size=initial.shape)
        
        res = optimize.minimize(
            objective,
            perturbed.flatten(),
            method='SLSQP',
            constraints=constraints,
            options={'maxiter': 2000, 'ftol': 1e-8}
        )

        if res.success:
            candidate = res.x.reshape(11, 2)
            area = get_smallest_triangle_area(candidate)
            if area > best_area:
                best_area = area
                best_points = candidate

    # Verify local optimality through hill-climbing
    if best_points is not None:
        current = best_points
        current_area = best_area
        for _ in range(5):
            pert = current + np.random.uniform(-0.001, 0.001, size=current.shape)
            res_verify = optimize.minimize(
                objective,
                pert.flatten(),
                method='SLSQP',
                constraints=constraints,
                options={'maxiter': 100}
            )
            if res_verify.success:
                improved = res_verify.x.reshape(11, 2)
                improved_area = get_smallest_triangle_area(improved)
                if improved_area > current_area:
                    current = improved
                    current_area = improved_area
                else:
                    break
        return current
    
    return generate_initial()