import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math
import scipy.optimize
import itertools
from scipy.spatial import distance

np.random.seed(42)
random.seed(42)

base_seed = 42

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    def project_to_triangle(p, existing_points=None):
        """Project point to triangle boundary while maximizing min distance to existing points"""
        if is_inside_triangle(p, A, B, C):
            return p
            
        # Candidate projection points on each edge
        edges = [(A, B), (B, C), (C, A)]
        candidates = []
        
        for a, b in edges:
            ab = b - a
            ap = p - a
            t = np.dot(ap, ab) / np.dot(ab, ab)
            t = max(0.0, min(1.0, t))
            proj = a + t * ab
            candidates.append(proj)

        # If no existing points, just pick closest projection
        if existing_points is None or len(existing_points) == 0:
            dists = [np.linalg.norm(p - c) for c in candidates]
            return candidates[np.argmin(dists)]
        
        # Otherwise, select projection that maximizes min distance to existing points
        min_dists = []
        for c in candidates:
            dists = np.linalg.norm(existing_points - c, axis=1)
            min_dists.append(np.min(dists))
            
        return candidates[np.argmax(min_dists)]

    def track_critical_triangles(points):
        """Identify vertices involved in smallest triangles"""
        n = len(points)
        min_area = float('inf')
        critical_vertices = np.zeros(n)
        
        # Find minimum triangle area
        for i, j, k in itertools.combinations(range(n), 3):
            area = 0.5 * abs(
                points[i][0]*(points[j][1]-points[k][1]) + 
                points[j][0]*(points[k][1]-points[i][1]) + 
                points[k][0]*(points[i][1]-points[j][1])
            )
            if area < min_area:
                min_area = area
        
        # Count vertices in triangles within 5% of min area
        for i, j, k in itertools.combinations(range(n), 3):
            area = 0.5 * abs(
                points[i][0]*(points[j][1]-points[k][1]) + 
                points[j][0]*(points[k][1]-points[i][1]) + 
                points[k][0]*(points[i][1]-points[j][1])
            )
            if area <= min_area * 1.05:  # Within 5% of minimum
                critical_vertices[i] += 1
                critical_vertices[j] += 1
                critical_vertices[k] += 1

        # Normalize and boost critical vertices
        if np.sum(critical_vertices) > 0:
            critical_vertices = critical_vertices / np.sum(critical_vertices)
            # Boost probability for critical vertices
n            critical_vertices = critical_vertices * 4.0
            critical_vertices = critical_vertices / np.sum(critical_vertices)
        else:
            critical_vertices = np.ones(n) / n
            
        return critical_vertices

    # Initialize 11 points with bias toward boundaries
    def initialize_points():
        points = []
        for _ in range(11):
            # Beta distribution biased toward boundaries (alpha=beta=0.5)
            a = np.random.beta(0.5, 0.5)
            b = np.random.beta(0.5, 0.5) * (1 - a)
            c = 1 - a - b
            p = a * A + b * B + c * C
            points.append(p)
        return np.array(points)

    best_overall_points = None
    best_overall_min_area = -1

    for restart in range(10):
        np.random.seed(base_seed + restart)
        random.seed(base_seed + restart)
        
        # Directly initialize 11 points (no symmetry)
        points = initialize_points()
        
        # Project all points to ensure validity
        for i in range(11):
            points[i] = project_to_triangle(points[i])

        current_min_area = get_smallest_triangle_area(points)
        current_points = points.copy()

        # Simulated annealing with targeted perturbations
        T0 = 0.2
        cooling_rate = 0.995
        max_iter = 30000

        for iter in range(max_iter):
            T = T0 * (cooling_rate ** iter)
            step_size = 0.05 * T
            
            # Identify critical vertices for targeted perturbation
            critical_probs = track_critical_triangles(current_points)
            
            # Select point to perturb (biased toward critical vertices)
            idx = np.random.choice(11, p=critical_probs)
            
            # Generate perturbation
            dx = random.uniform(-step_size, step_size)
            dy = random.uniform(-step_size, step_size)
            new_point = current_points[idx] + np.array([dx, dy])
            
            # Project to triangle (with distance maximization)
            new_point = project_to_triangle(new_point, current_points)
            
            # Create candidate configuration
            new_points = current_points.copy()
            new_points[idx] = new_point
            new_min_area = get_smallest_triangle_area(new_points)

            # Acceptance criteria
            if new_min_area > current_min_area:
                current_points = new_points
                current_min_area = new_min_area
            else:
                delta = current_min_area - new_min_area
                if delta > 0 and random.random() < math.exp(-delta / T):
                    current_points = new_points
                    current_min_area = new_min_area

        # Multi-start Powell refinement (5 variants)
        best_refined_points = current_points.copy()
        best_refined_min_area = current_min_area
        
        for _ in range(5):
            # Create perturbed starting point (0.5% relative noise)
            perturbed_points = current_points.copy()
            noise = 0.005 * (np.max(current_points) - np.min(current_points))
            perturbed_points += np.random.normal(0, noise, perturbed_points.shape)
            
            # Project all points to ensure validity
            for i in range(11):
                perturbed_points[i] = project_to_triangle(perturbed_points[i])

            def objective(x):
                points = x.reshape(11, 2)
                if not is_inside_triangle(points, A, B, C):
                    return 1e10
                return -get_smallest_triangle_area(points)

            res = scipy.optimize.minimize(
                objective,
                perturbed_points.flatten(),
                method='Powell',
                options={'maxiter': 1000, 'xatol': 1e-10, 'fatol': 1e-10}
            )

            if res.success:
                refined_points = res.x.reshape(11, 2)
                refined_min_area = get_smallest_triangle_area(refined_points)
                if refined_min_area > best_refined_min_area:
                    best_refined_points = refined_points
                    best_refined_min_area = refined_min_area

        if best_refined_min_area > best_overall_min_area:
            best_overall_min_area = best_refined_min_area
            best_overall_points = best_refined_points.copy()

    return best_overall_points