import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area
import scipy.optimize

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    def st_to_cart(s, t):
        u = s
        v = t * (1 - s)
        return (1 - u - v) * A + u * B + v * C

    def objective(x):
        points = []
        for i in range(11):
            s, t = x[2*i], x[2*i+1]
            points.append(st_to_cart(s, t))
        min_area = get_smallest_triangle_area(np.array(points))
        return -min_area

    # Global optimization with sufficient restarts
    bounds = [(0, 1)] * 22
    res_de = scipy.optimize.differential_evolution(
        objective, bounds,
        popsize=50,
        maxiter=1000,
        tol=1e-6,
        seed=42,
        disp=False
    )
    best_de = res_de.x

    # Local refinement with constraints
    constraints = []
    for i in range(22):
        constraints.append({'type': 'ineq', 'fun': lambda x, i=i: x[i]})
        constraints.append({'type': 'ineq', 'fun': lambda x, i=i: 1 - x[i]})
    
    res_cobyla = scipy.optimize.minimize(
        objective, best_de, method='COBYLA',
        constraints=constraints,
        options={'maxiter': 1000, 'tol': 1e-6}
    )
    best_cobyla = res_cobyla.x

    # Resistance-ensuring perturbation test
    current_config = best_cobyla.copy()
    step_size = 0.001
    max_perturb_iters = 100
    
    for _ in range(max_perturb_iters):
        # Compute current min_area
        points_current = [
            st_to_cart(current_config[2*i], current_config[2*i+1]) 
            for i in range(11)
        ]
        current_min_area = get_smallest_triangle_area(np.array(points_current))
        improved = False
        
        for i in range(11):
            if improved:
                break
            s0, t0 = current_config[2*i:2*i+2]
            for dx in [-step_size, 0, step_size]:
                for dy in [-step_size, 0, step_size]:
                    if dx == 0 and dy == 0:
                        continue
                    s_new = np.clip(s0 + dx, 0, 1)
                    t_new = np.clip(t0 + dy, 0, 1)
                    new_config = current_config.copy()
                    new_config[2*i:2*i+2] = [s_new, t_new]
                    
                    # Evaluate new configuration
                    points_new = [
                        st_to_cart(new_config[2*j], new_config[2*j+1]) 
                        for j in range(11)
                    ]
                    new_min_area = get_smallest_triangle_area(np.array(points_new))
                    
                    if new_min_area > current_min_area:
                        current_config = new_config
                        improved = True
                        break
                if improved:
                    break
        
        if not improved:
            break

    # Convert final configuration to Cartesian coordinates
    return np.array([
        st_to_cart(current_config[2*i], current_config[2*i+1]) 
        for i in range(11)
    ])