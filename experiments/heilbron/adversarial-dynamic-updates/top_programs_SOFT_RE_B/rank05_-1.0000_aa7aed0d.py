from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def project_to_triangle(point, A, B, C):
    """Project a point to the nearest point inside the triangle."""
    # Convert to barycentric coordinates
    v0 = B - A
    v1 = C - A
    v2 = point - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    
    if abs(denom) < 1e-10:
        return point
        
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w

    # Clamp barycentric coordinates to ensure point is inside triangle
    if u < 0:
        # Project to edge BC
        total = v + w
        if total > 0:
            v, w = v / total, w / total
        u = 0
    if v < 0:
        # Project to edge AC
        total = u + w
        if total > 0:
            u, w = u / total, w / total
        v = 0
    if w < 0:
        # Project to edge AB
        total = u + v
        if total > 0:
            u, v = u / total, v / total
        w = 0

    # Ensure coordinates sum to 1
    total = u + v + w
    if total > 0:
        u, v, w = u/total, v/total, w/total
    
    return u * A + v * B + w * C

def get_bottleneck_triangles(config):
    """Identify triangles that form the smallest areas and return their indices."""
    n = len(config)
    min_area = float('inf')
    bottleneck_triangles = []
    
    # Find the minimum area triangle(s)
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Calculate area of triangle i,j,k
                area = 0.5 * abs(
                    (config[j,0]-config[i,0])*(config[k,1]-config[i,1]) - 
                    (config[k,0]-config[i,0])*(config[j,1]-config[i,1])
                )
                
                # If this is the smallest area seen so far, reset bottleneck triangles
                if area < min_area - 1e-10:
                    min_area = area
                    bottleneck_triangles = [(i, j, k)]
                # If this matches the current minimum area, add this triangle
                elif abs(area - min_area) < 1e-10:
                    bottleneck_triangles.append((i, j, k))
    
    return bottleneck_triangles, min_area

def get_bottleneck_points(config):
    """Identify points that form the smallest triangles."""
    bottleneck_triangles, min_area = get_bottleneck_triangles(config)
    bottleneck_indices = set()
    for tri in bottleneck_triangles:
        bottleneck_indices.update(tri)
    return list(bottleneck_indices), min_area

def calculate_gradient(point_idx, config, A, B, C, current_min_area):
    """Calculate finite-difference gradient for a single point's contribution to min_area with adaptive epsilon."""
    # Use relative epsilon based on current min_area for numerical stability
    epsilon = max(1e-7, 0.01 * current_min_area)
    
    original_score = get_smallest_triangle_area(config)
    
    # Try small perturbations in x and y directions
    dx = np.zeros(2)
    dy = np.zeros(2)
    dx[0] = epsilon
    dy[1] = epsilon
    
    config_x = config.copy()
    config_x[point_idx] += dx
    if not is_inside_triangle(config_x[point_idx].reshape(1, 2), A, B, C):
        config_x[point_idx] = project_to_triangle(config_x[point_idx], A, B, C)
    score_x = get_smallest_triangle_area(config_x)
    
    config_y = config.copy()
    config_y[point_idx] += dy
    if not is_inside_triangle(config_y[point_idx].reshape(1, 2), A, B, C):
        config_y[point_idx] = project_to_triangle(config_y[point_idx], A, B, C)
    score_y = get_smallest_triangle_area(config_y)
    
    # Calculate gradients
    grad_x = (score_x - original_score) / epsilon
    grad_y = (score_y - original_score) / epsilon
    
    return np.array([grad_x, grad_y])

def calculate_joint_gradient(triangle_indices, config, A, B, C, current_min_area):
    """Calculate joint gradient for multiple points forming a bottleneck triangle."""
    # Get individual gradients for each point in the triangle
    grads = []
    for idx in triangle_indices:
        grad = calculate_gradient(idx, config, A, B, C, current_min_area)
        grads.append(grad)
    
    # Create a unified direction that improves all affected triangles
    # We'll use the average gradient direction but scale by improvement potential
    avg_grad = np.mean(grads, axis=0)
    
    # Normalize to unit vector
    if np.linalg.norm(avg_grad) > 1e-5:
        avg_grad = avg_grad / np.linalg.norm(avg_grad)
    else:
        # If gradients are near zero, use a small random direction
        avg_grad = np.random.normal(0, 1, size=2)
        avg_grad = avg_grad / np.linalg.norm(avg_grad)
    
    return avg_grad

def identify_triangle_groups(bottleneck_triangles):
    """Identify groups of points that form connected bottleneck triangles."""
    # Create a graph where points are nodes and triangles are cliques
    from collections import defaultdict
    graph = defaultdict(list)
    
    for tri in bottleneck_triangles:
        i, j, k = tri
        graph[i].extend([j, k])
        graph[j].extend([i, k])
        graph[k].extend([i, j])
    
    # Find connected components
    visited = set()
    components = []
    
    for node in graph:
        if node not in visited:
            component = []
            stack = [node]
            visited.add(node)
            
            while stack:
                current = stack.pop()
                component.append(current)
                
                for neighbor in graph[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)
            
            components.append(component)
    
    return components

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Create input-dependent RNG for adversarial robustness
        seed = abs(hash(points.tobytes())) % (2**32)
        rng = np.random.default_rng(seed)
        
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        current = best.copy()
        current_score = best_score
        
        total_iterations = 500
        early_stop_patience = 30
        T0 = 0.01
        no_improve_count = 0
        stagnation_depth = 0

        for i in range(total_iterations):
            # Square root temperature decay to prolong exploration
            T = T0 * np.sqrt(1 - i / total_iterations)
            
            # Adaptive step size: slower decay to maintain exploration capability
            sigma = 0.05 * (0.01 / 0.05) ** (i / total_iterations)
            
            # IDENTIFY BOTTLENECK TRIANGLES AND POINTS FOR TARGETED IMPROVEMENT
            bottleneck_triangles, current_min_area = get_bottleneck_triangles(current)
            bottleneck_indices, _ = get_bottleneck_points(current)
            
            # IDENTIFY CONNECTED BOTTLENECK GROUPS FOR COORDINATED MOVEMENT
            triangle_groups = identify_triangle_groups(bottleneck_triangles)
            
            # ADAPTIVE BOTTLENECK WEIGHTING BASED ON NUMBER OF CRITICAL POINTS
            bottleneck_weight = 0.5 + 0.3 * (1 - len(bottleneck_indices)/11)
            
            # BOTTLENECK-FOCUSED POINT SELECTION WITH ADAPTIVE WEIGHTING
            if rng.random() < 0.4:
                num_points = rng.choice([2, 3])
                
                # Create weighted selection: bottleneck points have higher probability
                weights = np.zeros(11)
                weights[bottleneck_indices] = bottleneck_weight / len(bottleneck_indices)
                weights[np.setdiff1d(np.arange(11), bottleneck_indices)] = (1 - bottleneck_weight) / (11 - len(bottleneck_indices))
                
                indices = rng.choice(11, size=num_points, replace=False, p=weights)
            else:
                # Single point selection also prioritizes bottlenecks
                weights = np.zeros(11)
                weights[bottleneck_indices] = bottleneck_weight / len(bottleneck_indices)
                weights[np.setdiff1d(np.arange(11), bottleneck_indices)] = (1 - bottleneck_weight) / (11 - len(bottleneck_indices))
                indices = [rng.choice(11, p=weights)]

            # Try gradient-informed perturbation first
            use_gradient = rng.random() < (0.9 - 0.6 * i / total_iterations)  # Decay from 90% to 30%
            candidate = current.copy()
            gradient_success = False
            
            if use_gradient and i < total_iterations * 0.8:
                # COORDINATED MOVEMENT FOR CONNECTED BOTTLENECK GROUPS
                applied_gradients = set()
                
                # First handle connected bottleneck groups
                for group in triangle_groups:
                    # Check if any point in this group is in our indices
                    group_indices = [idx for idx in indices if idx in group]
                    if len(group_indices) > 0:
                        # Apply joint gradient to the entire group
                        joint_grad = calculate_joint_gradient(group, candidate, A, B, C, current_min_area)
                        
                        # Scale by adaptive step size
                        step = joint_grad * sigma * 1.5
n                        # Apply to all points in the group that are in our selection
                        for idx in group:
                            if idx in indices:
                                candidate[idx] += step
                                applied_gradients.add(idx)

                # Apply individual gradients to remaining points
                for idx in indices:
                    if idx not in applied_gradients:
                        grad = calculate_gradient(idx, candidate, A, B, C, current_min_area)
                        if np.linalg.norm(grad) > 1e-3:
                            # Normalize and scale by adaptive step size
                            grad = grad / np.linalg.norm(grad) * sigma * 1.0
                            candidate[idx] += grad
                            gradient_success = True
                        else:
                            # Fall back to random perturbation for this point if gradient is unreliable
                            candidate[idx] += rng.normal(0, sigma, size=2)
            else:
                # Pure random perturbation
                for idx in indices:
                    candidate[idx] += rng.normal(0, sigma, size=2)

            # Project to triangle with fallback
            valid = True
            for idx in indices:
                if not is_inside_triangle(candidate[idx].reshape(1, 2), A, B, C):
                    projected = project_to_triangle(candidate[idx], A, B, C)
                    # Check if projection created a degenerate configuration
                    test_config = candidate.copy()
                    test_config[idx] = projected
                    if get_smallest_triangle_area(test_config) < 1e-5:
                        valid = False
                        break
                    candidate[idx] = projected

            if not valid:
                # Amplified random restart as fallback with CAPPED AMPLIFICATION
                candidate = current.copy()
                # CAP RESTART AMPLIFICATION TO PREVENT DEGENERATE CONFIGURATIONS
                restart_amplification = min(10.0, 5 + stagnation_depth)  # Capped at 10x
                restart_sigma = sigma * restart_amplification
                for idx in indices:
                    candidate[idx] += rng.normal(0, restart_sigma, size=2)
                    if not is_inside_triangle(candidate[idx].reshape(1, 2), A, B, C):
                        candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

            score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            if score > current_score:
                current = candidate
                current_score = score
                no_improve_count = 0
                stagnation_depth = 0
                if score > best_score:
                    best = candidate
                    best_score = score
            else:
                delta = score - current_score
                if T > 1e-5 and rng.random() < np.exp(delta / T):
                    current = candidate
                    current_score = score
                    no_improve_count = 0
                    stagnation_depth = max(0, stagnation_depth - 1)
                else:
                    no_improve_count += 1
                    stagnation_depth += 1

            # Restart mechanism for stagnation
            if no_improve_count >= early_stop_patience:
                # Use amplified restart with gradient awareness
                current = best.copy()
                current_score = best_score
                no_improve_count = 0
                stagnation_depth += 1
                
                # Adaptive restart perturbation magnitude with CAPPED AMPLIFICATION
                restart_amplification = min(10.0, 5 + stagnation_depth)  # Capped at 10x
                restart_sigma = sigma * restart_amplification
                restart_indices = rng.choice(11, size=rng.choice([2, 3]), replace=False)
                
                # Try gradient-informed restart
                if rng.random() < 0.6 and stagnation_depth > 5:
                    for idx in restart_indices:
                        grad = calculate_gradient(idx, current, A, B, C, current_min_area)
                        if np.linalg.norm(grad) > 1e-3:
                            grad = grad / np.linalg.norm(grad) * restart_sigma * 1.5
                            current[idx] += grad
                else:
                    # Amplified random perturbation with CAPPED AMPLIFICATION
                    for idx in restart_indices:
                        current[idx] += rng.normal(0, restart_sigma, size=2)

                # Ensure validity after restart
                for idx in restart_indices:
                    if not is_inside_triangle(current[idx].reshape(1, 2), A, B, C):
                        current[idx] = project_to_triangle(current[idx], A, B, C)
                
                if is_inside_triangle(current, A, B, C):
                    current_score = get_smallest_triangle_area(current)
                    if current_score > best_score:
                        best = current.copy()
                        best_score = current_score
                else:
                    current = best.copy()
                    current_score = best_score

        return best

    return improve