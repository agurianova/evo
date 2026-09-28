import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Calculate triangle height for boundary buffer
    height = np.linalg.norm(C - A)
    # Set boundary buffer to minimal value to allow boundary placements while maintaining validity
    boundary_buffer = 1e-10 * height

    # Expanded row distributions with domain-specific Heilbronn patterns for n=11
    distributions = [
        [5, 3, 2, 1],
        [4, 3, 3, 1],
        [4, 4, 2, 1],
        [3, 3, 3, 2],
        [5, 4, 2],
        [6, 3, 2],
        [3, 2, 3, 2, 1],
        [4, 3, 2, 2],
        [5, 2, 2, 2],
        # Added known Heilbronn patterns for n=11
        [4, 3, 2, 1, 1],
        [5, 3, 2, 1],
        [4, 4, 1, 1, 1],
        [3, 3, 3, 1, 1],
        [5, 2, 2, 1, 1],
        [4, 3, 1, 1, 1, 1]
    ]
    
    # Track performance for UCB1 selection
    pattern_scores = {}
    base_score = 0.025  # Historical average min_area
    for i in range(len(distributions)):
        # Initialize with historical average plus some noise
        pattern_scores[i] = {'score': base_score + np.random.normal(0, 0.005), 'count': 1}
    
    # Initialize scale_scores using Gaussian prior centered at 0.02 with std 0.005
    base_scale = 0.02
    scale_std = 0.005
    scale_scores = {i: {'scale': max(0.005, base_scale + np.random.normal(0, scale_std)), 
                       'score': 0.0, 'count': 0} for i in range(6)}
    total_evals = 0
    
    best_config = None
    best_score = -1
    
    # Direct min_area scoring (removed stability term)
    def direct_min_area_score(points):
        return get_smallest_triangle_area(points)

    # Boundary distance check
    def distance_to_boundary(point):
        # Calculate distance to each edge using line-point distance formula
        def edge_distance(p, v1, v2):
            line_vec = v2 - v1
            point_vec = p - v1
            line_len = np.linalg.norm(line_vec)
            if line_len < 1e-10:
                return np.linalg.norm(point_vec)
            proj = np.dot(point_vec, line_vec) / line_len
            proj = max(0, min(line_len, proj))
            closest = v1 + (proj / line_len) * line_vec
            return np.linalg.norm(p - closest)
        
        d1 = edge_distance(point, A, B)
        d2 = edge_distance(point, B, C)
        d3 = edge_distance(point, C, A)
        return min(d1, d2, d3)

    # UCB1 selection for distribution patterns
    def select_distribution():
        nonlocal total_evals
        c = 1.414  # Exploration parameter
        
        # Calculate UCB1 scores
        ucb_scores = []
        for i, dist in enumerate(distributions):
            if pattern_scores[i]['count'] == 0:
                return i  # Always explore untried patterns first
            
            avg_score = pattern_scores[i]['score']
            ucb = avg_score + c * np.sqrt(np.log(total_evals) / pattern_scores[i]['count'])
            ucb_scores.append((ucb, i))
        
        # Select pattern with highest UCB score
        _, selected_idx = max(ucb_scores, key=lambda x: x[0])
        return selected_idx

    # UCB1 selection for perturbation scales using barycentric v-coordinate
    def select_scale(v_coord, current_min_area):
        c = 1.2
        ucb_scores = []
        
        # Adaptive base scale based on current progress and v-coordinate
        base_scale = 0.01 * (1 - current_min_area / 0.0365) * (1 - v_coord)
        
        for i in scale_scores:
            if scale_scores[i]['count'] == 0:
                # Return adaptive scale instead of fixed value
                return max(0.005, base_scale + i*0.005)
            
            avg_score = scale_scores[i]['score'] / scale_scores[i]['count']
            ucb = avg_score + c * np.sqrt(np.log(total_evals) / scale_scores[i]['count'])
            ucb_scores.append((ucb, i))
        
        _, selected_idx = max(ucb_scores, key=lambda x: x[0])
        return scale_scores[selected_idx]['scale']

    # Function to dynamically generate new distributions
    def generate_new_distributions(existing):
        new_dists = []
        
        # Splitting: split a row into two
        for dist in existing:
            for i in range(len(dist)):
                if dist[i] >= 2:  # Can only split rows with at least 2 points
                    # Try different split ratios
                    for split_size in range(1, dist[i]):
                        new_dist = dist[:i] + [split_size, dist[i]-split_size] + dist[i+1:]
                        if sum(new_dist) == 11 and new_dist not in existing and new_dist not in new_dists:
                            new_dists.append(new_dist)

        # Merging: merge adjacent rows
        for dist in existing:
            for i in range(len(dist)-1):
                new_dist = dist[:i] + [dist[i] + dist[i+1]] + dist[i+2:]
                if sum(new_dist) == 11 and new_dist not in existing and new_dist not in new_dists:
                    new_dists.append(new_dist)

        # Shifting: move a point between adjacent rows
        for dist in existing:
            for i in range(len(dist)-1):
                if dist[i] >= 1 and dist[i+1] <= 9:  # Can shift from row i to i+1
                    new_dist = dist[:]
                    new_dist[i] -= 1
                    new_dist[i+1] += 1
                    if sum(new_dist) == 11 and new_dist not in existing and new_dist not in new_dists:
                        new_dists.append(new_dist)
                
                if dist[i] <= 9 and dist[i+1] >= 1:  # Can shift from row i+1 to i
                    new_dist = dist[:]
                    new_dist[i] += 1
                    new_dist[i+1] -= 1
                    if sum(new_dist) == 11 and new_dist not in existing and new_dist not in new_dists:
                        new_dists.append(new_dist)

        return new_dists

    # Adaptive restart count based on observed progress
    base_restart_count = 10
    max_restart_count = 30  # Don't go overboard
    adaptive_restart_count = base_restart_count
    restarts_with_improvement = 0
    
    # Try distributions with UCB1 selection
    restart_idx = 0
    while restart_idx < adaptive_restart_count and restart_idx < max_restart_count:
        total_evals += 1
        dist_idx = select_distribution()
        pattern_scores[dist_idx]['count'] += 1
        
        row_dist = distributions[dist_idx]
        points = []
        rows = len(row_dist)
        
        # Generate initial grid with UCB1-selected perturbation scales
        for i, num_in_row in enumerate(row_dist):
            v = (i + 0.5) / rows
            # Get current min_area for adaptive scaling (using a conservative estimate)
            current_min_area = 0.02 if best_score == -1 else best_score
            scale = select_scale(v, current_min_area)
            for j in range(num_in_row):
                u = (j + 0.5) / num_in_row * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                
                # For similar spread to uniform[-a,a], use sigma = a/sqrt(3)
                a = scale * (1 - v)
                sigma = a / np.sqrt(3)
                # Generate normal samples and truncate to ±2*sigma
                perturbation = np.random.normal(0, sigma, size=2)
                perturbation = np.clip(perturbation, -2*sigma, 2*sigma)
                points.append(P + perturbation)

        current = np.array(points)
        current_score = direct_min_area_score(current)
        
        # Simulated annealing parameters
        initial_temp = 0.005
        temp_decay = 0.995  # Slower cooling for better exploration
        max_iter = 5000
        early_stop = 1000
        
        no_improve = 0
        last_improve_iter = 0
        
        # Track best in this restart
        restart_best = current.copy()
        restart_best_score = current_score
        
        # Adaptive bottleneck targeting probability
        # Now INCREASES from 50% to 80% as temperature drops
        initial_bottleneck_prob = 0.5
        final_bottleneck_prob = 0.8
        
        for it in range(max_iter):
            # Calculate current bottleneck targeting probability
            # As temperature decreases (it increases), temp_ratio goes from 1 to 0
            temp_ratio = max(0.0, min(1.0, 1 - (it * (1 - temp_decay**it)) / max_iter))
            bottleneck_prob = initial_bottleneck_prob + (final_bottleneck_prob - initial_bottleneck_prob) * temp_ratio

            # Identify bottleneck triangles (those within 15% of the minimum area)
            areas = []
            indices = []
            n = current.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = current[i], current[j], current[k]
                        area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                        areas.append(area)
                        indices.append((i, j, k))

            # Find all triangles within 15% of the minimum area
            min_area = min(areas) if areas else 0
            threshold = min_area * 1.15
            relevant_indices = [(area, idx) for area, idx in zip(areas, indices) if area <= threshold]
            # Sort by area and select top N (at least 2, up to 10)
            relevant_indices.sort(key=lambda x: x[0])
            selected_indices = [idx for _, idx in relevant_indices[:max(2, min(10, len(relevant_indices)))]
            all_bottleneck_indices = set()
            for triple in selected_indices:
                all_bottleneck_indices.update(triple)
            
            # Adaptive chance to perturb bottleneck points
            if np.random.rand() < bottleneck_prob and all_bottleneck_indices:
                idx = np.random.choice(list(all_bottleneck_indices))
            else:
                idx = np.random.randint(0, 11)

            # Generate candidate move
            step_size = 0.02 * (temp_decay ** it)
            step = np.random.normal(0, step_size, size=2)
            candidate = current.copy()
            candidate[idx] += step

            # Validate containment with fixed minimal buffer
            if not is_inside_triangle(candidate[idx], A, B, C):
                continue
            if distance_to_boundary(candidate[idx]) < boundary_buffer:
                continue

            # Evaluate candidate
            new_score = direct_min_area_score(candidate)

            # Simulated annealing acceptance
            if new_score > current_score:
                current = candidate
                current_score = new_score
                if new_score > restart_best_score:
                    restart_best = candidate.copy()
                    restart_best_score = new_score
                
                # Track improvement
                last_improve_iter = it
            else:
                delta = current_score - new_score
                if np.random.rand() < np.exp(-delta / (initial_temp * (temp_decay ** it))):
                    current = candidate
                    current_score = new_score
                
            # Track no improvement count
            if it - last_improve_iter > early_stop:
                break

        # Update global best
        if restart_best_score > best_score:
            best_score = restart_best_score
            best_config = restart_best
            restarts_with_improvement += 1
            
        # Update pattern score
        pattern_scores[dist_idx]['score'] = (
            pattern_scores[dist_idx]['score'] * (pattern_scores[dist_idx]['count'] - 1) + 
            restart_best_score
        ) / pattern_scores[dist_idx]['count']

        # Update scale scores
        for i in range(len(row_dist)):
            v = (i + 0.5) / rows
            scale_idx = min(len(scale_scores) - 1, int(v * len(scale_scores)))
            scale_scores[scale_idx]['count'] += 1
            scale_scores[scale_idx]['score'] += restart_best_score

        # Periodically generate new distributions if not improving
        if restart_idx % 5 == 0 and restarts_with_improvement < 2 and len(distributions) < 30:
            new_dists = generate_new_distributions(distributions)
            for new_dist in new_dists:
                if len(distributions) < 30:  # Limit total number
                    distributions.append(new_dist)
                    pattern_scores[len(distributions)-1] = {
                        'score': base_score + np.random.normal(0, 0.005),
                        'count': 1
                    }

        # If we're not seeing improvements, extend the search
        if restart_idx >= base_restart_count - 1 and restarts_with_improvement < 2:
            adaptive_restart_count += 1  # Keep searching if not improving
            
        restart_idx += 1

    # Only adjust points that violate containment
    for i in range(11):
        if not is_inside_triangle(best_config[i], A, B, C):
            # Move toward center proportionally
            center = (A + B + C) / 3
            direction = center - best_config[i]
            if np.linalg.norm(direction) > 1e-10:
                direction = direction / np.linalg.norm(direction)
                best_config[i] += direction * boundary_buffer

    return best_config