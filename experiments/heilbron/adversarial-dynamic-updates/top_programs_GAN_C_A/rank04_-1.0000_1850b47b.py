import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Calculate triangle height for boundary buffer
    height = np.linalg.norm(C - A)
    boundary_buffer = 0.015 * height  # 1.5% of height as buffer

    # Enhanced row distributions (asymmetric patterns for n=11)
    distributions = [
        [5, 3, 2, 1],
        [4, 3, 3, 1],
        [4, 4, 2, 1],
        [3, 3, 3, 2],
        [5, 4, 2],
        [6, 3, 2],
        [3, 2, 3, 2, 1]
    ]
    
    # Track performance of each distribution for adaptive selection
    distribution_scores = {str(dist): {'total_score': 0, 'count': 0} for dist in distributions}
    
    best_config = None
    best_score = -1
    
    # Adaptive bottleneck weights based on relative gaps
    def adaptive_bottleneck_weights(areas, k=3):
        if len(areas) < k:
            k = len(areas)
        
        top_areas = sorted(areas)[:k]
        
        # Handle degenerate case
        if top_areas[0] < 1e-10:
            weights = [1.0] + [0.0] * (k-1)
            return weights[:k]
        
        # Compute relative gaps
        gaps = []
        for i in range(1, k):
            gap = (top_areas[i] - top_areas[0]) / max(top_areas[0], 1e-10)
            gaps.append(gap)
        
        # Higher weight for smaller areas, adapt based on gaps
        base_weights = [1.0]
        for gap in gaps:
            weight = 1.0 / (1.0 + 5.0 * gap)  # Stronger focus when gaps are large
            base_weights.append(weight)
        
        # Normalize
        total = sum(base_weights)
        weights = [w/total for w in base_weights]
        
        return weights

    # Multi-bottleneck scoring function with adaptive weights
    def multi_bottleneck_score(points):
        areas = []
        n = points.shape[0]
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    areas.append(area)
        
        # Sort and take top k smallest
        areas.sort()
        k = min(3, len(areas))
        top_areas = areas[:k]
        
        # Get adaptive weights
        weights = adaptive_bottleneck_weights(areas, k)
        
        # Weighted combination
        return sum(w * a for w, a in zip(weights, top_areas))

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

    # Proper hexagonal lattice initialization
    def generate_hexagonal_points():
        points = []
        # Hexagonal pattern parameters
        rows = 4
        for i in range(rows):
            # Adjust row height
            v = i / (rows - 1)
            num_in_row = 4 - abs(i - 2)  # Proper hexagonal pattern: 2, 3, 3, 2
            
            for j in range(num_in_row):
                # Horizontal offset for hex pattern
                u = j / (num_in_row - 1) if num_in_row > 1 else 0.5
                # Center the row
                u = u * (1 - v)
                
                P = (1 - u - v) * A + u * B + v * C
                # Add controlled perturbation
                perturbation = np.random.uniform(-0.02 * (1 - v), 0.02 * (1 - v), size=2)
                points.append(P + perturbation)
        
        # Ensure we have exactly 11 points
        while len(points) < 11:
            if len(points) == 8:
                # Center point
                center = (A + B + C) / 3
                points.append(center + np.random.uniform(-0.01, 0.01, size=2))
            else:
                # Find largest empty area and add point there
                r = np.random.rand()
                theta = np.random.rand() * 2 * np.pi
                # Radial bias toward center
                radius = 0.3 * (1 - np.sqrt(r))
                dx = radius * np.cos(theta)
                dy = radius * np.sin(theta)
                
                center = (A + B + C) / 3
                candidate = center + np.array([dx, dy])
                points.append(candidate)
        
        return np.array(points)[:11]

    # Helper to find indices of smallest triangles
    def compute_min_triangle_indices(points, k=5):
        n = points.shape[0]
        triangle_data = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    triangle_data.append((area, i, j, k))
        
        # Sort by area and return top k
        triangle_data.sort(key=lambda x: x[0])
        return [(data[1], data[2], data[3]) for data in triangle_data[:k]]

    # UCB1 selection for distributions
    def select_distribution():
        c = 1.4  # Exploration parameter
        total_count = sum(info['count'] for info in distribution_scores.values())
        
        if total_count == 0:
            return random.choice(distributions)
        
        best_score = -1
        best_dist = None
        
        for dist_str, info in distribution_scores.items():
            dist = eval(dist_str)
            if info['count'] == 0:
                return dist  # Always try untried distributions first
            
            avg_score = info['total_score'] / info['count']
            ucb_score = avg_score + c * np.sqrt(np.log(total_count) / info['count'])
            
            if ucb_score > best_score:
                best_score = ucb_score
                best_dist = dist
        
        return best_dist

    # Track improvement history for adaptive cooling
    improvement_history = []
    max_history = 50

    # Try row-based distributions with adaptive selection
    for _ in range(len(distributions) * 2):  # More total iterations
        row_dist = select_distribution()
        points = []
        rows = len(row_dist)
        
        # Generate initial grid with row-width scaled perturbation
        for i, num_in_row in enumerate(row_dist):
            v = (i + 0.5) / rows
            for j in range(num_in_row):
                u = (j + 0.5) / num_in_row * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                # Scale perturbation by row width (1-v)
                perturbation = np.random.uniform(-0.025 * (1 - v), 0.025 * (1 - v), size=2)
                points.append(P + perturbation)

        current = np.array(points)
        current_score = multi_bottleneck_score(current)
        
        # Simulated annealing parameters
        initial_temp = 0.005
        temp_decay = 0.997
        initial_step = 0.02
        step_decay = 0.9992
        max_iter = 5000
        early_stop = 500
        
        temp = initial_temp
        step_size = initial_step
        no_improve = 0
        
        # Track best in this restart
        restart_best = current.copy()
        restart_best_score = current_score
        
        for it in range(max_iter):
            # Identify bottleneck triangles (top 3 smallest)
            bottleneck_triples = compute_min_triangle_indices(current, k=3)
            all_bottleneck_indices = set()
            for triple in bottleneck_triples:
                all_bottleneck_indices.update(triple)
            
            # 70% chance to perturb bottleneck points, 30% random
            if np.random.rand() < 0.7 and all_bottleneck_indices:
                idx = np.random.choice(list(all_bottleneck_indices))
            else:
                idx = np.random.randint(0, 11)

            # Generate candidate move
            step = np.random.normal(0, step_size, size=2)
            candidate = current.copy()
            candidate[idx] += step

            # Validate containment with boundary buffer
            if not is_inside_triangle(candidate[idx], A, B, C):
                continue
            if distance_to_boundary(candidate[idx]) < boundary_buffer:
                continue

            # Evaluate candidate
            new_score = multi_bottleneck_score(candidate)

            # Simulated annealing acceptance
            if new_score > current_score:
                # Record improvement for adaptive cooling
                improvement = new_score - current_score
                improvement_history.append(improvement)
                if len(improvement_history) > max_history:
                    improvement_history.pop(0)
                
                current = candidate
                current_score = new_score
                if new_score > restart_best_score:
                    restart_best = candidate.copy()
                    restart_best_score = new_score
                no_improve = 0
            else:
                delta = current_score - new_score
                if np.random.rand() < np.exp(-delta / temp):
                    current = candidate
                    current_score = new_score
                    no_improve = 0
                else:
                    no_improve += 1

            # Adaptive cooling based on recent progress
            if improvement_history:
                avg_improvement = sum(improvement_history) / len(improvement_history)
                # If making good progress, cool more slowly
                if avg_improvement > 1e-5:
                    adaptive_cooling = max(0.98, temp_decay * (1 - 0.1 * avg_improvement))
                else:
                    # If stuck, cool faster to escape local optima
                    adaptive_cooling = min(0.9995, temp_decay * 1.05)
            else:
                adaptive_cooling = temp_decay

            # Update temperature and step size
            temp *= adaptive_cooling
            step_size *= adaptive_cooling

            # Early stopping
            if no_improve >= early_stop:
                break

        # Update distribution scores for UCB1
        distribution_key = str(row_dist)
        distribution_scores[distribution_key]['total_score'] += restart_best_score
        distribution_scores[distribution_key]['count'] += 1

        # Update global best
        if restart_best_score > best_score:
            best_score = restart_best_score
            best_config = restart_best

    # Try hexagonal pattern
    hex_points = generate_hexagonal_points()
    hex_score = multi_bottleneck_score(hex_points)
    if hex_score > best_score:
        best_score = hex_score
        best_config = hex_points

    # Final validation and minor adjustments
    for i in range(11):
        dist = distance_to_boundary(best_config[i])
        if dist < boundary_buffer:
            # Move proportionally to boundary risk
            center = (A + B + C) / 3
            direction = center - best_config[i]
            if np.linalg.norm(direction) > 1e-10:
                direction = direction / np.linalg.norm(direction)
                # Move less if very close to optimal position
                move_amount = max(0, boundary_buffer - dist)
                best_config[i] += direction * move_amount

    return best_config