import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import itertools
from sklearn.cluster import DBSCAN

np.random.seed(42)

MAX_THEORETICAL_AREA = 0.0365

# Composition memory to store successful patterns
COMPOSITION_MEMORY = []

def calculate_resistance_metric(score):
    """Calculate resistance metric as proportion of theoretical maximum"""
    return min(1.0, score / MAX_THEORETICAL_AREA)

# Helper function to find smallest triangle and its points
def find_smallest_triangle(points):
    n = points.shape[0]
    min_area = float('inf')
    best_indices = None
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                dx1 = points[j,0] - points[i,0]
                dy1 = points[j,1] - points[i,1]
                dx2 = points[k,0] - points[i,0]
                dy2 = points[k,1] - points[i,1]
                area = 0.5 * abs(dx1 * dy2 - dy1 * dx2)
                if area < min_area:
                    min_area = area
                    best_indices = (i, j, k)
    return min_area, best_indices

def find_k_smallest_triangles(points, k=5):
    """Find k smallest triangles and their areas"""
    n = points.shape[0]
    triangles = []  # (area, i, j, k)
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                dx1 = points[j,0] - points[i,0]
                dy1 = points[j,1] - points[i,1]
                dx2 = points[k,0] - points[i,0]
                dy2 = points[k,1] - points[i,1]
                area = 0.5 * abs(dx1 * dy2 - dy1 * dx2)
                triangles.append((area, i, j, k))
    
    # Sort by area and return top k
    triangles.sort(key=lambda x: x[0])
    return triangles[:k]

def get_boundary_proximity(point, A, B, C):
    """Calculate proximity to triangle boundaries (0 = center, 1 = boundary)"""
    # Barycentric coordinates
    v0 = C - A
    v1 = B - A
    v2 = point - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1 - v - w
    
    # Distance to nearest boundary is min of barycentric coordinates
    return 1.0 - min(u, v, w)

def project_to_boundary(point, A, B, C):
    """Project a point to the nearest boundary of the triangle with edge-following"""
    # Check if point is already inside
    if is_inside_triangle(point, A, B, C):
        return point
    
    # Function to project point to line segment
    def project_to_segment(p, a, b):
        ap = p - a
        ab = b - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)  # Avoid division by zero
        t = max(0, min(1, t))
        return a + t * ab
    
    # Project to each edge
    p_ab = project_to_segment(point, A, B)
    p_bc = project_to_segment(point, B, C)
    p_ca = project_to_segment(point, C, A)
    
    # Find closest projection
    d_ab = np.linalg.norm(point - p_ab)
    d_bc = np.linalg.norm(point - p_bc)
    d_ca = np.linalg.norm(point - p_ca)
    
    if d_ab <= d_bc and d_ab <= d_ca:
        return p_ab
    elif d_bc <= d_ab and d_bc <= d_ca:
        return p_bc
    else:
        return p_ca

def generate_random_compositions(n, resistance_metric, k_min=2, k_max=6, num_samples=15):
    """Generate random integer compositions of n into k parts with adaptive known pattern inclusion"""
    compositions = []
    
    # Add known good compositions with adaptive probability based on resistance
    known_good = [
        [1, 2, 3, 5],  # Fibonacci pattern often seen in Heilbronn solutions
        [1, 2, 4, 4],
        [2, 2, 3, 4],
        [1, 3, 3, 4],
        [1, 1, 2, 3, 4],
        [1, 2, 2, 3, 3],
        [1, 1, 3, 3, 3],
        [2, 2, 2, 2, 3]  # Added symmetric pattern for better balance
    ]
    
    # Include compositions from memory if available
    if COMPOSITION_MEMORY:
        known_good.extend(COMPOSITION_MEMORY)
    
    # Include known good compositions with adaptive probability
    adaptive_prob = min(0.75, 0.3 + resistance_metric * 0.7)  # Increased cap to 0.75
    num_known = int(adaptive_prob * num_samples)
    for _ in range(min(num_known, len(known_good))):
        compositions.append(known_good[np.random.randint(len(known_good))])
    
    while len(compositions) < num_samples:
        # Randomly choose k between k_min and k_max
        k = np.random.randint(k_min, k_max + 1)
        if k > n:
            continue
        # Generate k-1 random split points between 1 and n-1
        splits = sorted(np.random.choice(range(1, n), k-1, replace=False))
        # Convert to parts
        parts = [splits[0]] + [splits[i] - splits[i-1] for i in range(1, k-1)] + [n - splits[-1]]
        # Ensure no zeros
        if all(p > 0 for p in parts) and len(parts) == k:
            compositions.append(parts)
    return compositions

def generate_diverse_configs(A, B, C, num_configs=50, resistance_metric=0.5):
    """Generate diverse point configurations inside the triangle with resistance-aware parameters"""
    configs = []
    
    # 1. Random configurations
    for _ in range(15):
        points = []
        for _ in range(11):
            # Generate random barycentric coordinates
            u = np.random.random()
            v = np.random.random() * (1 - u)
            w = 1 - u - v
            P = w * A + u * B + v * C
            points.append(P)
        configs.append(np.array(points))
    
    # 2. Grid-based configurations
    for rows in range(2, 6):
        cols = (11 + rows - 1) // rows  # Ceiling division
        for _ in range(10):
            points = []
            for i in range(rows):
                v = (i + 0.5) / rows
                for j in range(min(11 - len(points), cols)):
                    u = (j + 0.5) / cols * (1 - v)
                    P = (1 - u - v) * A + u * B + v * C
                    # Add perturbation
                    boundary_proximity = get_boundary_proximity(P, A, B, C)
                    # Updated perturbation scaling: (1 - resistance_metric**0.5) instead of (1 - resistance_metric**1.5)
                    perturbation_scale = 0.05 * (1 - resistance_metric**0.5) * (1.5 + 0.5 * np.tanh(5 * (0.8 - boundary_proximity))) * ((1 - v) ** (0.5 + 0.5 * (1 - resistance_metric**0.5)))
                    perturbation = np.random.uniform(-perturbation_scale, perturbation_scale, size=2)
                    P_perturbed = P + perturbation
                    points.append(P_perturbed)
            configs.append(np.array(points[:11]))
    
    # 3. Asymmetric row patterns
    compositions = generate_random_compositions(11, resistance_metric, num_samples=15)
    for row_points in compositions:
        rows = len(row_points)
        points = []
        
        # Generate row heights (to be optimized later)
        heights = np.ones(rows)
        
        for i in range(rows):
            # v position based on cumulative height
            v = sum(heights[:i]) / sum(heights) + 0.5 * heights[i] / sum(heights)
            num_in_row = row_points[i]
            for j in range(num_in_row):
                u = (j + 0.5) / num_in_row * (1 - v)
                P = (1 - u - v) * A + u * B + v * C
                # Larger perturbation to break symmetry
                boundary_proximity = get_boundary_proximity(P, A, B, C)
                # Updated perturbation scaling: (1 - resistance_metric**0.5) instead of (1 - resistance_metric**1.5)
                perturbation_scale = 0.05 * (1 - resistance_metric**0.5) * (1.5 + 0.5 * np.tanh(5 * (0.8 - boundary_proximity))) * ((1 - v) ** (0.5 + 0.5 * (1 - resistance_metric**0.5)))
                perturbation = np.random.uniform(-perturbation_scale, perturbation_scale, size=2)
                P_perturbed = P + perturbation
                points.append(P_perturbed)

        configs.append(np.array(points))
        
    return configs

def optimize_configuration(points, A, B, C, resistance_metric=0.5):
    """Run simulated annealing on a configuration with adaptive cooling"""
    current = points.copy()
    current_score = get_smallest_triangle_area(current)
    best_current = current.copy()
    best_current_score = current_score
    last_improvement = 0
    
    # Calculate resistance metric as proxy
    resistance_metric = calculate_resistance_metric(current_score)
    
    # Optimized SA parameters - initial_temp now proportional to initial score and resistance
    initial_temp = 0.25 * (2 - resistance_metric) * (current_score / MAX_THEORETICAL_AREA)  # Increased base scaling factor from 0.12 to 0.25
    max_iterations = 3000
    early_stop_patience = 500
    
    temp = initial_temp
    improvement_window = []
    # Adaptive window size based on resistance_metric
    window_size = max(5, min(20, int(10 * resistance_metric)))
    
    # ADDED: Minimum cooling rate to prevent premature convergence
    min_cooling_rate = 0.92 + 0.03 * resistance_metric
    
    for iteration in range(max_iterations):
        # Calculate recent improvement rate
        if iteration > 0 and iteration % 20 == 0:
            improvement_window.append(best_current_score)
            if len(improvement_window) > window_size // 20:
                improvement_window = improvement_window[-window_size // 20:]
        
        # Adaptive cooling rate
        if len(improvement_window) >= 2:
            improvement_rate = (improvement_window[-1] - improvement_window[0]) / len(improvement_window)
            # If improving well, cool slower; if stalled, cool faster (inverted from original)
            cooling_rate = 0.95 + 0.15 * min(1.0, max(0.0, -improvement_rate * 15000))
            # ADDED: Ensure cooling rate doesn't drop below minimum
            cooling_rate = max(min_cooling_rate, cooling_rate)
        else:
            cooling_rate = 0.95  # Default
        
        # Calculate resistance metric as proxy
        resistance_metric = calculate_resistance_metric(current_score)
        # Updated targeting probability: cap increased to 0.65
        targeting_prob = min(0.65, 0.3 + 0.5 * resistance_metric)
        
        # Focus on points in smallest triangle with adaptive probability
        if np.random.random() < targeting_prob:
            _, (i, j, k) = find_smallest_triangle(current)
            idx = np.random.choice([i, j, k])
        else:
            idx = np.random.randint(0, 11)
        
        # Slower step size decay to maintain exploration capability
        step_size = 0.1 * (cooling_rate ** (iteration/20))
        
        candidate = current.copy()
        
        # Boundary-aware perturbation
        boundary_proximity = get_boundary_proximity(candidate[idx], A, B, C)
        resistance_metric = calculate_resistance_metric(current_score)
        # Updated perturbation scaling: (1 - resistance_metric**0.5) instead of (1 - resistance_metric**1.5)
        # Updated boundary scaling: sigmoid function instead of linear
        perturbation_scale = step_size * (1.5 + 0.5 * np.tanh(5 * (0.8 - boundary_proximity))) * (1 - resistance_metric**0.5)
        step = np.random.normal(0, perturbation_scale, size=2)
        candidate[idx] += step
        
        # Project to boundary if outside, instead of rejecting
        candidate[idx] = project_to_boundary(candidate[idx], A, B, C)

        score = get_smallest_triangle_area(candidate)
        
        # Simulated annealing acceptance
        delta = score - current_score
        if delta > 0 or np.random.random() < np.exp(delta / temp):
            current = candidate
            current_score = score
            
            if score > best_current_score:
                best_current = current.copy()
                best_current_score = score
                last_improvement = iteration

        # Cooling
        temp *= cooling_rate
        
        # Early stopping
        if iteration - last_improvement > early_stop_patience:
            break

    # Triangle area balancing to create 'flat' landscapes
    # Updated: replaced hard threshold with smooth transition
    balance_factor = max(0.0, min(1.0, (0.7 - resistance_metric)/0.1))
    if balance_factor > 0:
        # MODIFIED: Process top 5 triangles instead of just balancing two
        balanced = balance_triangle_areas(best_current, A, B, C, resistance_metric)
        balanced_score = get_smallest_triangle_area(balanced)
        if balanced_score > best_current_score:
            best_current = balanced
            best_current_score = balanced_score

    return best_current, best_current_score

def balance_triangle_areas(points, A, B, C, resistance_metric):
    """Create balanced configurations with multiple nearly-equal smallest triangles"""
    current = points.copy()
    current_score = get_smallest_triangle_area(current)
    
    # MODIFIED: Get top 5 smallest triangles instead of top 3
    smallest_triangles = find_k_smallest_triangles(current, k=5)
    
    # If we have multiple small triangles, try to balance them
    if len(smallest_triangles) >= 2:
        min_area = smallest_triangles[0][0]
        
        # MODIFIED: Distance-weighted balancing for multiple triangles
        # Calculate target area as weighted geometric mean
        weights = []
        areas = [t[0] for t in smallest_triangles]
        for area in areas:
            # Weight based on distance from minimum area
n            weights.append(1.0 / (area - min_area + 1e-10))
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w/total_weight for w in weights]
        
        # Calculate target area as weighted geometric mean
        target_area = 1.0
        for i in range(len(areas)):
            target_area *= areas[i] ** weights[i]
        
        # Process all small triangles
        for triangle_idx in range(len(smallest_triangles)):
            _, i1, j1, k1 = smallest_triangles[triangle_idx]
            
            # Create a set of points involved in this triangle
            triangle_indices = set([i1, j1, k1])
            
            # Calculate influence weights based on distance to target
            area_diff = target_area - smallest_triangles[triangle_idx][0]
            
            # Try to adjust points to balance the areas
            for idx in triangle_indices:
                # Only adjust interior points
                if get_boundary_proximity(current[idx], A, B, C) < 0.7:
                    # Compute direction to move point to increase triangle area
                    if idx == i1:
                        grad = np.array([current[j1,1] - current[k1,1], current[k1,0] - current[j1,0]])
                    elif idx == j1:
                        grad = np.array([current[k1,1] - current[i1,1], current[i1,0] - current[k1,0]])
                    else:  # idx == k1
                        grad = np.array([current[i1,1] - current[j1,1], current[j1,0] - current[i1,0]])
                    
                    # Normalize and scale direction
                    if np.linalg.norm(grad) > 1e-10:
                        direction = grad / np.linalg.norm(grad)
                        
                        # Adaptive step size with distance weighting
                        # Points in smaller triangles get larger adjustments
                        step_size = 0.02 * (1 + (min_area / smallest_triangles[triangle_idx][0])) * (1 - resistance_metric**0.5)
                        
                        # Apply movement
                        candidate = current.copy()
                        candidate[idx] += step_size * direction
                        
                        # Project to boundary if outside
                        candidate[idx] = project_to_boundary(candidate[idx], A, B, C)
                        
                        # Check if it improves balance
                        new_score = get_smallest_triangle_area(candidate)
                        if new_score > current_score:
                            current = candidate
                            current_score = new_score

    return current

def detect_rows(points, resistance_metric):
    """Detect rows using DBSCAN clustering on y-coordinates with adaptive eps"""
    y_coords = points[:, 1].reshape(-1, 1)
    
    # Adaptive eps based on interquartile range of y-coordinates
    q75, q25 = np.percentile(y_coords, [75, 25])
    iqr = q75 - q25
    # Updated eps formula: non-linear scaling with resistance_metric**1.5
    eps = (0.08 + 0.2 * resistance_metric**1.5) * iqr if iqr > 0 else 0.05  # Reduced base value and coefficient
    
    # Perform DBSCAN clustering
    clustering = DBSCAN(eps=eps, min_samples=1).fit(y_coords)
    labels = clustering.labels_
    
    # MODIFIED: Add secondary clustering within rows for intra-row structure
    row_structure = []
    intra_row_clusters = []
    row_labels = []
    
    for label in np.unique(labels):
        if label == -1:  # Skip noise points
            continue
            
        # Get points in this row
        row_points = points[labels == label]
        row_y = np.mean(row_points[:, 1])
        
        # Intra-row clustering using x-coordinates
        x_coords = row_points[:, 0].reshape(-1, 1)
        
        # Adaptive eps for intra-row clustering
        row_iqr = np.percentile(x_coords, 75) - np.percentile(x_coords, 25)
        intra_eps = max(0.01, 0.1 * row_iqr * (0.5 + 0.5 * resistance_metric))
        
        intra_clustering = DBSCAN(eps=intra_eps, min_samples=1).fit(x_coords)
        intra_labels = intra_clustering.labels_
        
        # Count points in each intra-row cluster
        cluster_counts = []
        for intra_label in np.unique(intra_labels):
            if intra_label == -1:  # Skip noise points
                continue
            cluster_counts.append(np.sum(intra_labels == intra_label))
        
        # Only add row if we have valid clusters
        if cluster_counts:
            row_structure.append(sum(cluster_counts))
            intra_row_clusters.append(cluster_counts)
            row_labels.append((label, row_y))
    
    # Sort rows by y-coordinate
    sorted_indices = np.argsort([y for _, y in row_labels])
    row_structure = [row_structure[i] for i in sorted_indices]
    intra_row_clusters = [intra_row_clusters[i] for i in sorted_indices]
    
    # Fallback: if we don't detect enough rows, try fixed eps
    if len(row_structure) < 2:
        clustering = DBSCAN(eps=0.08, min_samples=1).fit(y_coords)
        labels = clustering.labels_
        row_structure = []
        for label in np.unique(labels):
            if label != -1:  # Skip noise points
                row_structure.append(np.sum(labels == label))
        intra_row_clusters = [None] * len(row_structure)  # No intra-row info
    
    return row_structure, labels, intra_row_clusters

def optimize_row_spacing(points, row_structure, A, B, C, resistance_metric, intra_row_clusters=None):
    """Optimize row heights in addition to point positions"""
    rows = len(row_structure)
    current = points.copy()
    heights = np.ones(rows)  # Initial equal heights
    current_score = get_smallest_triangle_area(current)
    best_current = current.copy()
    best_heights = heights.copy()
    best_score = current_score
    
    # SA parameters for row spacing optimization
    temp = 0.1
    cooling_rate = 0.95
    max_iterations = 1000
    
    # ADDED: Minimum cooling rate for row optimization
    min_cooling_rate = 0.92 + 0.03 * resistance_metric
    
    for iteration in range(max_iterations):
        # Calculate resistance metric as proxy
        resistance_metric = calculate_resistance_metric(best_score)
        
        # Perturb row heights
        candidate_heights = heights.copy()
        row_to_perturb = np.random.randint(0, rows)
        candidate_heights[row_to_perturb] += np.random.normal(0, 0.1)
        # Ensure positive heights
        candidate_heights = np.maximum(candidate_heights, 0.1)
        
        # Generate points with new row heights
        candidate_points = []
        total_height = sum(candidate_heights)
        for i in range(rows):
            # v position based on cumulative height
            v = sum(candidate_heights[:i]) / total_height + 0.5 * candidate_heights[i] / total_height
            num_in_row = row_structure[i]
            
            # MODIFIED: If we have intra-row cluster information, use it
            if intra_row_clusters and intra_row_clusters[i]:
                intra_clusters = intra_row_clusters[i]
                cluster_start = 0
                
                for cluster_idx, cluster_size in enumerate(intra_clusters):
                    # Calculate u positions within this cluster
                    for j in range(cluster_size):
                        # Position within cluster
                        u_cluster = (j + 0.5) / cluster_size
                        # Position of cluster within row
                        cluster_pos = (cluster_idx + 0.5) / len(intra_clusters[i])
                        # Combined position
                        u = cluster_pos * (1 - v) * 0.9 + u_cluster * (1 - v) * 0.1
                        
                        P = (1 - u - v) * A + u * B + v * C
                        # Add some small perturbation
                        boundary_proximity = get_boundary_proximity(P, A, B, C)
                        resistance_metric = calculate_resistance_metric(best_score)
                        # Updated perturbation scaling: (1 - resistance_metric**0.5) instead of (1 - resistance_metric**1.5)
                        perturbation_scale = 0.01 * (1 - resistance_metric**0.5) * (1.5 + 0.5 * np.tanh(5 * (0.8 - boundary_proximity))) * ((1 - v) ** (0.5 + 0.5 * (1 - resistance_metric**0.5)))
                        perturbation = np.random.uniform(-perturbation_scale, perturbation_scale, size=2)
                        P_perturbed = P + perturbation
                        candidate_points.append(P_perturbed)
                    cluster_start += cluster_size
            else:
                # Default behavior if no intra-row cluster information
                for j in range(num_in_row):
                    u = (j + 0.5) / num_in_row * (1 - v)
                    P = (1 - u - v) * A + u * B + v * C
                    # Add some small perturbation
                    boundary_proximity = get_boundary_proximity(P, A, B, C)
                    resistance_metric = calculate_resistance_metric(best_score)
                    # Updated perturbation scaling: (1 - resistance_metric**0.5) instead of (1 - resistance_metric**1.5)
                    perturbation_scale = 0.01 * (1 - resistance_metric**0.5) * (1.5 + 0.5 * np.tanh(5 * (0.8 - boundary_proximity))) * ((1 - v) ** (0.5 + 0.5 * (1 - resistance_metric**0.5)))
                    perturbation = np.random.uniform(-perturbation_scale, perturbation_scale, size=2)
                    P_perturbed = P + perturbation
                    candidate_points.append(P_perturbed)
        
        candidate_points = np.array(candidate_points)
        
        # Project any out-of-bound points to nearest boundary
        for i in range(len(candidate_points)):
            candidate_points[i] = project_to_boundary(candidate_points[i], A, B, C)

        score = get_smallest_triangle_area(candidate_points)
        
        # Acceptance criteria
        delta = score - current_score
        if delta > 0 or np.random.random() < np.exp(delta / temp):
            current = candidate_points
            heights = candidate_heights
            current_score = score
            
            if score > best_score:
                best_current = candidate_points.copy()
                best_heights = candidate_heights.copy()
                best_score = score

        # Cooling - with minimum rate
        cooling_rate = max(min_cooling_rate, cooling_rate * 0.995)
        temp *= cooling_rate

    return best_current, best_score

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Global search phase: generate diverse configurations
    diverse_configs = generate_diverse_configs(A, B, C, num_configs=50)
    
    # Score configurations by initial min_area
    scores = [(config, get_smallest_triangle_area(config)) for config in diverse_configs]
    # Sort by score (highest first)
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # Calculate resistance metric as proxy for selection threshold
    scores_array = np.array([s for _, s in scores])
    mean_score = np.mean(scores_array)
    std_score = np.std(scores_array)
    best_score = scores[0][1] if scores else 0
    resistance_metric = calculate_resistance_metric(best_score) if best_score > 0 else 0.0
    
    # Relaxed selection threshold to include more diverse candidates
    selection_threshold = mean_score + (0.5 + 0.25 * resistance_metric) * std_score
    top_configs = [config for config, score in scores if score >= selection_threshold]
    # Ensure we have at least 5 configurations
    if len(top_configs) < 5:
        top_configs = [config for config, _ in scores[:5]]
    
    best_config = None
    best_score = -1
    
    # Refine top configurations
    for config in top_configs:
        # First optimize point positions
        refined, score = optimize_configuration(config, A, B, C, resistance_metric)
        
        # Update composition memory if this configuration is strong
        if score > 0.6 * MAX_THEORETICAL_AREA:
            # MODIFIED: Get intra-row cluster information
            row_structure, _, intra_row_clusters = detect_rows(refined, resistance_metric)
            if row_structure and len(row_structure) > 1:
                # Add to memory if not already present
                if row_structure not in COMPOSITION_MEMORY:
                    COMPOSITION_MEMORY.append(row_structure)
                # Keep memory size limited
                if len(COMPOSITION_MEMORY) > 15:  # INCREASED from 10 to 15
                    COMPOSITION_MEMORY.pop(0)
        
        # If this config has row structure, optimize row spacing
        if len(config) == 11:
            # Robust row detection using DBSCAN
            row_structure, _, intra_row_clusters = detect_rows(refined, resistance_metric)
            
            if len(row_structure) > 1:
                # MODIFIED: Pass intra_row_clusters to optimize_row_spacing
                refined, score = optimize_row_spacing(refined, row_structure, A, B, C, resistance_metric, intra_row_clusters)

        if score > best_score:
            best_config = refined
            best_score = score

    return best_config