from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

np.random.seed(42)

def project_inside(point, A, B, C):
    """Project a point back inside the triangle if it's outside."""
    # If already inside, return as is
    if is_inside_triangle(np.array([point]), A, B, C):
        return point
    
    # Helper function to find closest point on a line segment
    def closest_point_on_segment(P, A, B):
        AB = B - A
        AP = P - A
        t = np.dot(AP, AB) / (np.dot(AB, AB) + 1e-10)  # Avoid division by zero
        t = max(0.0, min(1.0, t))
        return A + t * AB
    
    # Check each edge
    edges = [(A, B), (B, C), (C, A)]
    closest_points = [closest_point_on_segment(point, edge[0], edge[1]) for edge in edges]
    
    # Return the closest point on any edge
    distances = [np.linalg.norm(point - cp) for cp in closest_points]
    min_idx = np.argmin(distances)
    
    projected = closest_points[min_idx]
    
    # Check for collinearity after projection
    # If collinear with any two other points, perturb inward slightly
    epsilon = 1e-5
    collinear = False
    for i in range(len(edges)):
        edge = edges[i]
        # Vector along the edge
        edge_vec = edge[1] - edge[0]
        # Vector from edge start to projected point
        point_vec = projected - edge[0]
        # Cross product to check collinearity
        cross = np.abs(edge_vec[0] * point_vec[1] - edge_vec[1] * point_vec[0])
        if cross < 1e-10:  # Nearly collinear
            # Perturb inward perpendicular to the edge
            perp = np.array([-edge_vec[1], edge_vec[0]])
            if np.dot(perp, C - A) < 0:  # Ensure inward direction
                perp = -perp
            perp = perp / (np.linalg.norm(perp) + 1e-10)
            projected = projected + perp * epsilon
            collinear = True
            break
    
    return projected

def find_k_smallest_triangles(points, k=3):
    """Find indices of the k smallest triangles."""
    n = points.shape[0]
    triangle_areas = []
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                a, b, c = points[i], points[j], points[k]
                area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                triangle_areas.append((area, (i, j, k)))
    
    # Sort by area and take top k
    triangle_areas.sort(key=lambda x: x[0])
    return [indices for _, indices in triangle_areas[:k]]

def compute_triangle_gradients(points, i, j, k):
    """Compute gradients for the three points of a triangle to increase its area.
    Preserves natural gradient magnitude proportional to opposite side length."""
    A, B, C = points[i], points[j], points[k]
    
    # Compute partial derivatives - these magnitudes are naturally proportional to opposite side lengths
n    grad_i = np.array([0.5 * (B[1] - C[1]), 0.5 * (C[0] - B[0])])
    grad_j = np.array([0.5 * (C[1] - A[1]), 0.5 * (A[0] - C[0])])
    grad_k = np.array([0.5 * (A[1] - B[1]), 0.5 * (B[0] - A[0])])
    
    return {i: grad_i, j: grad_j, k: grad_k}

def compute_composite_gradient(points, triangle_indices_list):
    """Compute composite gradient from multiple bottleneck triangles."""
    n = points.shape[0]
    composite_grad = np.zeros((n, 2))
    
    # Weight each triangle by 1/(area + epsilon) so smaller triangles have higher weight
    epsilon = 1e-10
    total_weight = 0
    
    for indices in triangle_indices_list:
        i, j, k = indices
        area = 0.5 * abs((points[j,0]-points[i,0])*(points[k,1]-points[i,1]) - 
                        (points[j,1]-points[i,1])*(points[k,0]-points[i,0]))
        weight = 1.0 / (area + epsilon)
        total_weight += weight
        
        grads = compute_triangle_gradients(points, i, j, k)
        composite_grad[i] += weight * grads[i]
        composite_grad[j] += weight * grads[j]
        composite_grad[k] += weight * grads[k]
    
    if total_weight > 0:
        composite_grad /= total_weight
    
    return composite_grad

def entrypoint():
    """Return an improve(points) -> improved_points callable."""
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Initial setup
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        # Simulated annealing parameters
        initial_temp = 0.001
        temp_decay = 0.995
        initial_step = 0.05
        step_decay = 0.998
        max_iter = 200
        early_stop = 20
        
        # CMA-ES parameters
        mean = np.zeros(2)
        cov = np.eye(2) * (initial_step ** 2)
        learning_rate = 0.1
        min_eigenvalue = 1e-6  # Prevent covariance from becoming singular
        
        temp = initial_temp
        step_size = initial_step
        no_improve = 0
        
        for it in range(max_iter):
            # Find top 3 smallest triangles (k=3)
            top_triangles = find_k_smallest_triangles(current, k=3)
            
            # Compute composite gradient from all bottleneck triangles
            composite_grad = compute_composite_gradient(current, top_triangles)
            
            # Adaptive probabilities based on current temperature
            # As temperature decreases, focus more on bottleneck points and gradient guidance
            bottleneck_prob = 0.5 + 0.4 * (1 - temp / initial_temp)
            gradient_prob = 0.5 + 0.4 * (1 - temp / initial_temp)
            
            # Choose point to perturb
            if np.random.rand() < bottleneck_prob:
                # Flatten all indices from top triangles and choose one
                all_indices = [idx for tri in top_triangles for idx in tri]
                idx = np.random.choice(all_indices)
            else:
                idx = np.random.randint(0, 11)
            
            # Compute gradient for this point (if it's part of bottleneck triangles)
            gradient = np.zeros(2)
            use_gradient = (idx in [i for tri in top_triangles for i in tri]) and (np.random.rand() < gradient_prob)
            if use_gradient:
                gradient = composite_grad[idx]
            
            # Generate candidate move
            # 80% chance to use adapted distribution, 20% chance to use gradient + noise
            if np.random.rand() < 0.8:
                try:
                    # Ensure covariance is positive definite
                    eigenvals, eigenvecs = np.linalg.eigh(cov)
                    eigenvals = np.maximum(eigenvals, min_eigenvalue)
                    cov_adjusted = eigenvecs @ np.diag(eigenvals) @ eigenvecs.T
                    step = np.random.multivariate_normal(mean, cov_adjusted)
                except:
                    # Fallback if something goes wrong
                    step = np.random.normal(0, step_size, size=2)
            else:
                # Gradient direction + random noise
                direction = gradient + np.random.normal(0, 0.2, size=2)
                if np.linalg.norm(direction) > 1e-10:
                    direction = direction / np.linalg.norm(direction)
                step = direction * np.random.normal(step_size, step_size * 0.1)
            
            candidate = current.copy()
            candidate[idx] += step
            
            # Project back inside triangle if needed
            candidate[idx] = project_inside(candidate[idx], A, B, C)
            
            # Evaluate candidate
            new_score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            if new_score > current_score:
                accepted = True
            else:
                delta = current_score - new_score
                accepted = np.random.rand() < np.exp(-delta / temp)
            
            if accepted:
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate.copy()
                    best_score = new_score
                no_improve = 0
                
                # Update search distribution using ALL accepted moves (not just improvements)
                step_vector = candidate[idx] - points[idx]
                mean = (1 - learning_rate) * mean + learning_rate * step_vector
                cov = (1 - learning_rate) * cov + learning_rate * np.outer(step_vector, step_vector)
            else:
                no_improve += 1
            
            # Adaptive cooling
            temp *= temp_decay
            step_size *= step_decay
            
            # Early stopping (more tolerant when temperature is still high)
            if no_improve >= early_stop and temp < initial_temp * 0.1:
                break
        
        return best

    return improve