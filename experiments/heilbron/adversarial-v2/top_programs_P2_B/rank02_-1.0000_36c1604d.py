from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.optimize import minimize

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()

    def tri_area(a, b, c):
        return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    def project_to_triangle(point):
        """Project point back into triangle using closest boundary point"""
        if is_inside_triangle(point, A, B, C):
            return point.copy()
        
        # Try all three edges
        projections = []
        edges = [(A, B), (B, C), (C, A)]
        
        for (p1, p2) in edges:
            v = p2 - p1
            w = point - p1
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 == 0:
                b = p1
            else:
                b = max(0, min(1, c1/c2))
                b = p1 + b * v
            
            dist = np.linalg.norm(point - b)
            projections.append((dist, b))
        
        # Return closest projection
        _, closest = min(projections, key=lambda x: x[0])
        return closest

    def compute_soft_min_gradient(points, critical_triplets, min_area):
        """Compute gradient using soft-minimum approach with exponentially decaying weights"""
        n_points = len(points)
        gradient = np.zeros((n_points, 2))
        
        # Sort critical triplets by area (smallest first)
        critical_triplets.sort(key=lambda x: x[0])
        
        # Compute weights using exponential decay based on relative criticality
        total_weight = 0
        for i, (area, triplet) in enumerate(critical_triplets):
            # Weight = (min_area/area)^2 - gives exponentially higher weight to smaller triangles
            weight = (min_area / (area + 1e-10)) ** 2
            total_weight += weight
n            i, j, k = triplet
            
            # Compute gradient for each point in the triplet
            a, b, c = points[i], points[j], points[k]
            
            # Gradient for point i
            grad_i = np.array([b[1]-c[1], c[0]-b[0]])
            # Gradient for point j
            grad_j = np.array([c[1]-a[1], a[0]-c[0]])
            # Gradient for point k
            grad_k = np.array([a[1]-b[1], b[0]-a[0]])
            
            # Normalize gradients
            norm_i = np.linalg.norm(grad_i)
            norm_j = np.linalg.norm(grad_j)
            norm_k = np.linalg.norm(grad_k)
            
            if norm_i > 1e-8:
                grad_i = grad_i / norm_i
            if norm_j > 1e-8:
                grad_j = grad_j / norm_j
            if norm_k > 1e-8:
                grad_k = grad_k / norm_k
            
            # Add weighted gradients
            gradient[i] += weight * grad_i
            gradient[j] += weight * grad_j
            gradient[k] += weight * grad_k
        
        # Normalize by total weight if needed
        if total_weight > 1e-8:
            gradient /= total_weight
            
        return gradient

    def optimize_configuration(points, max_iter_inner=100):
        """Perform local optimization on a single configuration"""
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        
        step_size = 0.02
        initial_temp = 0.1
        no_improve_count = 0
        max_no_improve = 200
        
        # Adaptive threshold parameters
        base_threshold = 1.5  # Start more inclusive
        min_threshold = 1.1  # Narrow when progress stalls
        threshold = base_threshold
        
        for iter in range(max_iter_inner):
            # Find ALL critical triangles with adaptive threshold
            min_area = current_score
            areas_triplets = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = tri_area(current[i], current[j], current[k])
                        areas_triplets.append((area, (i, j, k)))
            
            # Sort by area
            areas_triplets.sort(key=lambda x: x[0])
            
            # Use adaptive threshold
            if no_improve_count > 50:
                # Narrow threshold when progress stalls
                threshold = max(min_threshold, base_threshold - 0.005 * no_improve_count)
            else:
                # Wider threshold when making progress
                threshold = min(base_threshold, min_threshold + 0.01 * (50 - no_improve_count))

            critical_triplets = [(area, triplet) for area, triplet in areas_triplets 
                                if area < threshold * min_area and area > 1e-10]
            
            if not critical_triplets:
                break

            # Compute gradient using soft-minimum approach
            gradient = compute_soft_min_gradient(current, critical_triplets, min_area)

            # Apply displacement with step size and noise
            candidate = current.copy()
            for idx in range(11):
                # Add some randomness to escape local minima
                noise = np.random.normal(0, step_size/4, 2)
                displacement = step_size * gradient[idx] + noise
                candidate[idx] += displacement

            # Project all points back into triangle
            for idx in range(11):
                candidate[idx] = project_to_triangle(candidate[idx])

            # Check validity
            candidate_score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            temp = initial_temp * (0.99 ** iter)
            if candidate_score > current_score:
                accept = True
            else:
                delta = current_score - candidate_score
                if np.random.rand() < np.exp(-delta / temp):
                    accept = True
                else:
                    accept = False

            if accept:
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score
                    no_improve_count = 0
                else:
                    no_improve_count += 1
            else:
                no_improve_count += 1

            # Adaptive step size control
            if no_improve_count > 50:
                step_size *= 1.08  # More aggressive exploration after stagnation
            elif no_improve_count < 5:
                step_size *= 0.92  # Reduce step after improvements

            # Clamp step size
            step_size = max(1e-5, min(step_size, 0.15))

            # Stopping condition
            if no_improve_count >= max_no_improve:
                break

        return best, best_score

    def improve(points: np.ndarray) -> np.ndarray:
        # Multi-start strategy: try 3 different starting points
        best_overall = points.copy()
        best_score_overall = get_smallest_triangle_area(best_overall)
        
        # First try with the original configuration
        best, best_score = optimize_configuration(points)
        if best_score > best_score_overall:
            best_overall, best_score_overall = best, best_score
        
        # Try with two perturbed versions
        for _ in range(2):
            perturbed = points.copy()
            # Apply larger perturbation to escape local optima
            for i in range(11):
                perturbation = np.random.normal(0, 0.05, 2)
                perturbed[i] += perturbation
                perturbed[i] = project_to_triangle(perturbed[i])
            
            # Optimize the perturbed configuration
            best, best_score = optimize_configuration(perturbed)
            if best_score > best_score_overall:
                best_overall, best_score_overall = best, best_score

        return best_overall

    return improve