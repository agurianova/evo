import numpy as np
from scipy.optimize import basinhopping
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)

# Precompute all triangle index combinations for 11 points
def get_triangle_indices(n=11):
    indices = []
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                indices.append((i, j, k))
    return np.array(indices)

TRIANGLE_INDICES = get_triangle_indices()

# Compute all triangle areas efficiently
def compute_all_areas(points):
    areas = []
    for i, j, k in TRIANGLE_INDICES:
        a, b, c = points[i], points[j], points[k]
        area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
        areas.append(area)
    return np.array(areas)

# Smoothed minimum using log-sum-exp
def smoothed_min(areas, beta=50.0):
    return -np.log(np.sum(np.exp(-beta * areas))) / beta

# Custom step-taking routine that respects triangle constraints
class TriangleStep():
    def __init__(self, A, B, C, max_step=0.05):
        self.A = A
        self.B = B
        self.C = C
        self.max_step = max_step
        self.iter = 0
        
    def __call__(self, x):
        n_points = len(x) // 2
        # Adaptive step size: larger early, smaller later
        step_size = self.max_step * (0.95 ** self.iter)
        self.iter += 1
        
        # Convert to Cartesian for perturbation
        points = barycentric_to_cartesian(x, self.A, self.B, self.C)
        
        # Select points to perturb (focus on problematic areas)
        min_idx = np.argmin(compute_all_areas(points))
        i, j, k = TRIANGLE_INDICES[min_idx]
        
        # Perturb the points forming the smallest triangle more aggressively
        for idx in [i, j, k]:
            points[idx] += np.random.uniform(-step_size, step_size, size=2)
        # Perturb other points slightly
        for idx in range(n_points):
            if idx not in [i, j, k]:
                points[idx] += np.random.uniform(-step_size/2, step_size/2, size=2)
        
        # Convert back to barycentric
        x_new = cartesian_to_barycentric(points, self.A, self.B, self.C)
        return x_new

def barycentric_to_cartesian(x, A, B, C):
    points = []
    for i in range(len(x) // 2):
        u, v = x[2*i], x[2*i+1]
        w = 1 - u - v
        points.append(u * A + v * B + w * C)
    return np.array(points)

def cartesian_to_barycentric(points, A, B, C):
    x = []
    for P in points:
        # Solve for barycentric coordinates
        v0 = B - A
        v1 = C - A
        v2 = P - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1 - v - w
        x.extend([u, v])
    return np.array(x)

def is_valid_configuration(x, A, B, C):
    points = barycentric_to_cartesian(x, A, B, C)
    return is_inside_triangle(points, A, B, C)

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Generate hexagonal grid pattern with perturbations
    def generate_grid_points():
        points = []
        rows = 5
        count = 0
        for row in range(rows):
            num_points = rows - row
            v = (row + 0.5) / rows
            for i in range(num_points):
                if count >= 11:
                    break
                u = (i + 0.5) / num_points * (1 - v)
                # Add adaptive perturbation
                perturb = 0.05 * (1 - row/rows)  # Smaller perturbations in lower rows
                u += np.random.uniform(-perturb, perturb)
                v += np.random.uniform(-perturb, perturb)
                # Ensure valid barycentric coordinates
                u = max(0, min(u, 1))
                v = max(0, min(v, 1))
                if u + v > 1:
                    excess = u + v - 1
                    u -= excess * 0.5
                    v -= excess * 0.5
                P = (1 - u - v) * A + u * B + v * C
                points.append(P)
                count += 1
            if count >= 11:
                break
        return np.array(points)

    # Objective function with smoothed minimum
    def objective(x):
        points = barycentric_to_cartesian(x, A, B, C)
        if not is_inside_triangle(points, A, B, C):
            return 1e6  # Large penalty for invalid points
            
        areas = compute_all_areas(points)
        # Apply log-sum-exp smoothing
        smooth_min_val = smoothed_min(areas)
        # Penalize configurations with many small triangles
        penalty = 0.1 * np.sum(areas < 0.01)
        return -smooth_min_val + penalty

    # Adversarial self-test to ensure resistance
    def adversarial_self_test(points, max_iter=20):
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        for _ in range(max_iter):
            # Find smallest triangle
            min_area_val = float('inf')
            min_triangle_indices = None
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        p, q, r = points[i], points[j], points[k]
                        area = 0.5 * abs((q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0]))
                        if area < min_area_val:
                            min_area_val = area
                            min_triangle_indices = (i, j, k)

            if min_triangle_indices is None:
                break

            i, j, k = min_triangle_indices
            A_pt, B_pt, C_pt = points[i], points[j], points[k]

            # Compute gradients
            s = 0.5 * ((B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (B_pt[1]-A_pt[1])*(C_pt[0]-A_pt[0]))
            sign_s = 1 if s >= 0 else -1

            grad_A = np.array([B_pt[1]-C_pt[1], C_pt[0]-B_pt[0]]) * sign_s
            grad_B = np.array([C_pt[1]-A_pt[1], A_pt[0]-C_pt[0]]) * sign_s
            grad_C = np.array([A_pt[1]-B_pt[1], B_pt[0]-A_pt[0]]) * sign_s

            # Normalize
            if np.linalg.norm(grad_A) > 1e-8:
                grad_A = grad_A / np.linalg.norm(grad_A)
            if np.linalg.norm(grad_B) > 1e-8:
                grad_B = grad_B / np.linalg.norm(grad_B)
            if np.linalg.norm(grad_C) > 1e-8:
                grad_C = grad_C / np.linalg.norm(grad_C)

            candidate = points.copy()
            candidate[i] += 0.005 * grad_A
            candidate[j] += 0.005 * grad_B
            candidate[k] += 0.005 * grad_C

            if not is_inside_triangle(candidate, A, B, C):
                continue

            score = get_smallest_triangle_area(candidate)
            if score > best_score:
                best = candidate
                best_score = score

        return best, best_score

    best_min_area = -1
    best_points = None

    # Generate multiple grid patterns with different perturbations
    for seed in range(10):
        np.random.seed(seed)
        grid_points = generate_grid_points()
        # Convert to barycentric for optimization
        x0 = cartesian_to_barycentric(grid_points, A, B, C)
        
        # Set up step-taking routine
        step_taker = TriangleStep(A, B, C, max_step=0.05)
        
        # Run basin-hopping
        minimizer_kwargs = {"method": "L-BFGS-B"}
        res = basinhopping(
            objective, 
n            x0,
            niter=50,
            T=1.0,
            stepsize=0.05,
            minimizer_kwargs=minimizer_kwargs,
            take_step=step_taker,
            accept_test=lambda **kwargs: is_valid_configuration(kwargs['x_new'], A, B, C)
        )
        
        if res.fun < 0:  # Valid solution
            points = barycentric_to_cartesian(res.x, A, B, C)
            # Apply adversarial self-test
            resistant_points, resistant_score = adversarial_self_test(points)
            
            # Only accept if it meets quality threshold and resists self-test
            if resistant_score > 0.01 and resistant_score > best_min_area:
                best_min_area = resistant_score
                best_points = resistant_points

    # Final fallback if no good solution found
    if best_points is None or best_min_area < 0.01:
        np.random.seed(42)
        best_points = generate_grid_points()

    return best_points