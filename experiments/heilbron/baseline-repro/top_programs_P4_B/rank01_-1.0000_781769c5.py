from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_triangle(p, A, B, C):
        if is_inside_triangle(p, A, B, C):
            return p
        edges = [(A, B), (B, C), (C, A)]
        best_point = None
        best_dist = float('inf')
        for (v1, v2) in edges:
            v = v2 - v1
            w = p - v1
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 < 1e-10:
                candidate = v1
            else:
                b = c1 / c2
                if b < 0:
                    candidate = v1
                elif b > 1:
                    candidate = v2
                else:
                    candidate = v1 + b * v
            dist = np.linalg.norm(p - candidate)
            if dist < best_dist:
                best_dist = dist
                best_point = candidate

        return best_point

    def get_bottleneck_triangles(pts, min_area_threshold_factor=1.2):
        n = pts.shape[0]
        triangles = []
        min_area = float('inf')
        
        # First pass to find the minimum area
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        (pts[j,0] - pts[i,0]) * (pts[k,1] - pts[i,1]) -
                        (pts[k,0] - pts[i,0]) * (pts[j,1] - pts[i,1])
                    )
                    if area < min_area:
                        min_area = area
        
        # Second pass to collect all triangles within threshold
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        (pts[j,0] - pts[i,0]) * (pts[k,1] - pts[i,1]) -
                        (pts[k,0] - pts[i,0]) * (pts[j,1] - pts[i,1])
                    )
                    if area <= min_area * min_area_threshold_factor:
                        triangles.append((area, i, j, k))
        
        # Sort by area (ascending)
        triangles.sort(key=lambda x: x[0])
        return triangles

    def get_gradient_direction(pts, i, j, k):
        x = pts[:, 0]
        y = pts[:, 1]
        S = 0.5 * ((x[j]-x[i])*(y[k]-y[i]) - (x[k]-x[i])*(y[j]-y[i]))
        sign_S = 1.0 if S >= 0 else -1.0
        
        grad_i = np.array([0.5*(y[j]-y[k]), 0.5*(x[k]-x[j])]) * sign_S
        grad_j = np.array([0.5*(y[k]-y[i]), 0.5*(x[i]-x[k])]) * sign_S
        grad_k = np.array([0.5*(y[i]-y[j]), 0.5*(x[j]-x[i])]) * sign_S

        # If gradient is near zero, use geometric fallback
        if np.linalg.norm(grad_i) < 1e-10:
            # Use perpendicular to longest edge
            edges = [(i,j), (j,k), (k,i)]
            lengths = []
            for (a,b) in edges:
                lengths.append(np.linalg.norm(pts[a] - pts[b]))
            longest_idx = np.argmax(lengths)
            a, b = edges[longest_idx]
            edge_vec = pts[b] - pts[a]
            perp_vec = np.array([-edge_vec[1], edge_vec[0]])
            grad_i = perp_vec
            
        if np.linalg.norm(grad_j) < 1e-10:
            edges = [(i,j), (j,k), (k,i)]
            lengths = []
            for (a,b) in edges:
                lengths.append(np.linalg.norm(pts[a] - pts[b]))
            longest_idx = np.argmax(lengths)
            a, b = edges[longest_idx]
            edge_vec = pts[b] - pts[a]
            perp_vec = np.array([-edge_vec[1], edge_vec[0]])
            grad_j = perp_vec

        if np.linalg.norm(grad_k) < 1e-10:
            edges = [(i,j), (j,k), (k,i)]
            lengths = []
            for (a,b) in edges:
                lengths.append(np.linalg.norm(pts[a] - pts[b]))
            longest_idx = np.argmax(lengths)
            a, b = edges[longest_idx]
            edge_vec = pts[b] - pts[a]
            perp_vec = np.array([-edge_vec[1], edge_vec[0]])
            grad_k = perp_vec

        # Normalize gradients
        grad_i = grad_i / np.linalg.norm(grad_i)
        grad_j = grad_j / np.linalg.norm(grad_j)
        grad_k = grad_k / np.linalg.norm(grad_k)

        return grad_i, grad_j, grad_k

    def improve(points: np.ndarray) -> np.ndarray:
        base_seed = hash(tuple(map(tuple, points))) % (2**32-1)
        initial_score = get_smallest_triangle_area(points)
        scale_factor = np.sqrt(0.0365 / max(initial_score, 1e-5))
        best_overall = points.copy()
        best_overall_score = initial_score
        num_chains = 5
        max_iter = 1000

        # Track global best across chains
        global_best = points.copy()
        global_best_score = initial_score
n        for chain in range(num_chains):
            chain_seed = (base_seed + chain) % (2**32-1)
            np.random.seed(chain_seed)

            current = points.copy()
            best_chain = points.copy()
            current_score = initial_score
            best_chain_score = initial_score
            
            # Initialize adaptive temperature
            T = max(0.02, 2.0 * initial_score)
            T_initial = T
            
            # Track move success rates for adaptive probabilities
            move_success = [0, 0, 0, 0]  # [two_point, one_point, non_bottleneck, global]
            move_attempts = [1, 1, 1, 1]  # Start with 1 to avoid division by zero
            
            # Track progress for adaptive cooling
            stall_counter = 0
            progress_threshold = 1e-5
            
            # For periodic reset of move success tracking
            reset_interval = 200

            for iter_idx in range(max_iter):
                # Periodically reset move success tracking to maintain exploration
                if iter_idx % reset_interval == 0 and iter_idx > 0:
                    move_success = [0, 0, 0, 0]
                    move_attempts = [1, 1, 1, 1]

                # Check for global best sharing
                if iter_idx % 200 == 0 and iter_idx > 0 and global_best_score > best_chain_score:
                    current = global_best.copy()
                    current_score = global_best_score
                    # Reset temperature when jumping to global best
                    T = max(0.02, 2.0 * global_best_score)

                candidate = current.copy()
                r = np.random.rand()
                base_step = scale_factor * np.sqrt(T)

                # Compute adaptive move probabilities based on success rates
                success_rates = [move_success[i] / move_attempts[i] for i in range(4)]
                total_success = sum(success_rates)
                
                if total_success > 0:
                    p1 = 0.7 * success_rates[0] / total_success
                    p2 = 0.7 * success_rates[1] / total_success
                    p3 = 0.7 * success_rates[2] / total_success
                    p4 = 0.7 * success_rates[3] / total_success
                else:
                    # Default to equal probabilities if no successes yet
n                    p1 = p2 = p3 = p4 = 0.25

                # Select move type based on adaptive probabilities
                if r < p1:
                    move_type = 0
                    # Two-point gradient move
                    triangles = get_bottleneck_triangles(current)
                    
                    # Weight selection by proximity to minimum area
                    weights = [1.0/(t[0] + 1e-10) for t in triangles]
                    weights = np.array(weights) / sum(weights)
                    
                    i, j, k = triangles[np.random.choice(len(triangles), p=weights)][1:]
                    
                    grad_i, grad_j, grad_k = get_gradient_direction(current, i, j, k)

                    idx1, idx2 = np.random.choice([i, j, k], size=2, replace=False)
                    
                    g1 = grad_i if idx1 == i else (grad_j if idx1 == j else grad_k)
                    g2 = grad_i if idx2 == i else (grad_j if idx2 == j else grad_k)

                    r_step = 0.2 * base_step * np.sqrt(np.random.uniform(0, 1))
                    candidate[idx1] = current[idx1] + r_step * g1
                    candidate[idx2] = current[idx2] + r_step * g2

                elif r < p1 + p2:
                    move_type = 1
                    # One-point gradient move
                    triangles = get_bottleneck_triangles(current)
                    
                    # Weight selection by proximity to minimum area
                    weights = [1.0/(t[0] + 1e-10) for t in triangles]
                    weights = np.array(weights) / sum(weights)
                    
                    i, j, k = triangles[np.random.choice(len(triangles), p=weights)][1:]
                    
                    grad_i, grad_j, grad_k = get_gradient_direction(current, i, j, k)

                    idx = np.random.choice([i, j, k])
                    g = grad_i if idx == i else (grad_j if idx == j else grad_k)

                    r_step = 0.2 * base_step * np.sqrt(np.random.uniform(0, 1))
                    candidate[idx] = current[idx] + r_step * g

                elif r < p1 + p2 + p3:
                    move_type = 2
                    # Non-bottleneck move
                    triangles = get_bottleneck_triangles(current)
                    bottleneck_set = set()
                    for _, i, j, k in triangles:
                        bottleneck_set.update([i, j, k])
                    
                    non_bottleneck = [i for i in range(11) if i not in bottleneck_set]
                    if non_bottleneck:
                        idx = np.random.choice(non_bottleneck)
                    else:
                        idx = np.random.choice(11)
                    
                    angle = np.random.uniform(0, 2*np.pi)
                    r_step = 0.6 * base_step * np.sqrt(np.random.uniform(0, 1))
                    dx = r_step * np.cos(angle)
                    dy = r_step * np.sin(angle)
                    new_p = candidate[idx] + np.array([dx, dy])
                    new_p = project_to_triangle(new_p, A, B, C)
                    candidate[idx] = new_p

                else:
                    move_type = 3
                    # Global random move
                    for idx in range(11):
                        angle = np.random.uniform(0, 2*np.pi)
                        r_step_global = 0.8 * base_step * np.sqrt(np.random.uniform(0, 1))
                        dx = r_step_global * np.cos(angle)
                        dy = r_step_global * np.sin(angle)
                        new_p = candidate[idx] + np.array([dx, dy])
                        new_p = project_to_triangle(new_p, A, B, C)
                        candidate[idx] = new_p

                # Project any points that might be outside
                for idx in range(11):
                    candidate[idx] = project_to_triangle(candidate[idx], A, B, C)

                candidate_score = get_smallest_triangle_area(candidate)

                # Update move success tracking
                move_attempts[move_type] += 1
                if candidate_score > current_score:
                    move_success[move_type] += 1

                if candidate_score > best_chain_score:
                    best_chain = candidate.copy()
                    best_chain_score = candidate_score
                    
                    # Update global best if needed
                    if candidate_score > global_best_score:
                        global_best = candidate.copy()
                        global_best_score = candidate_score

                # Check for progress to adjust stall counter
                if candidate_score - current_score > progress_threshold:
                    stall_counter = 0
                else:
                    stall_counter += 1

                # Adaptive cooling based on progress
                if stall_counter < 50:
                    cooling_rate = 0.99  # Slow cooling when making progress
                else:
                    cooling_rate = 0.95  # Faster cooling when stalled

                # Early termination if stalled for too long
                if stall_counter > 100:
                    break

                # Acceptance probability
                delta = candidate_score - current_score
n                if delta > 0 or np.random.rand() < np.exp(delta / T):
                    current = candidate
                    current_score = candidate_score

                T *= cooling_rate

            if best_chain_score > best_overall_score:
                best_overall = best_chain.copy()
                best_overall_score = best_chain_score

        return best_overall

    return improve