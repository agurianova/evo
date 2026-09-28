import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area
import heapq

np.random.seed(42)

# Global resistance history tracker
RESISTANCE_HISTORY = []
BASE_REHEAT_THRESHOLD = 500


def clip_to_triangle(p, A, B, C):
    v0 = B - A
    v1 = C - A
    v2 = p - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-10:
        return p
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1 - v - w

    u, v, w = max(u, 0), max(v, 0), max(w, 0)
    total = u + v + w
    if total == 0:
        u, v, w = 1/3, 1/3, 1/3
    else:
        u, v, w = u/total, v/total, w/total

    return u * A + v * B + w * C

def get_resistance_history_avg(window=5):
    if not RESISTANCE_HISTORY:
        return 0.5
    return np.mean(RESISTANCE_HISTORY[-window:])

def evaluate_with_resistance(config, A, B, C, num_perturbations=10):
    """Evaluate configuration by simulating opponent perturbations"""
    base_area = get_smallest_triangle_area(config)
    worst_area = base_area
    
    # Track historical opponent improvement directions
    opp_history = getattr(evaluate_with_resistance, 'opp_history', [])
    
    for _ in range(num_perturbations):
        candidate = config.copy()
        # Select point to perturb (weighted toward points in smallest triangles)
        min_triangles = find_min_area_triangles(config)
        affected_points = set()
        for tri in min_triangles[:3]:
            affected_points.update(tri)
        idx = np.random.choice(list(affected_points)) if affected_points else np.random.randint(0, 11)
        
        # Create perturbation - biased by historical opponent moves if available
        step = np.random.uniform(-0.02, 0.02, 2)
        if opp_history and np.random.rand() < 0.7:
            # Use historical opponent improvement direction
            hist_dir, _ = opp_history[np.random.randint(0, len(opp_history))]
            step = hist_dir * 0.015 + np.random.normal(0, 0.005, 2)
        
        candidate[idx] += step
        candidate[idx] = clip_to_triangle(candidate[idx], A, B, C)
        
        new_area = get_smallest_triangle_area(candidate)
        if new_area > worst_area:
            worst_area = new_area
            
            # Record successful opponent move for future bias
            if not hasattr(evaluate_with_resistance, 'opp_history'):
                evaluate_with_resistance.opp_history = []
            opp_dir = step / np.linalg.norm(step) if np.linalg.norm(step) > 1e-5 else step
            evaluate_with_resistance.opp_history.append((opp_dir, new_area - base_area))
            # Keep only top 20 historical improvements
            if len(evaluate_with_resistance.opp_history) > 20:
                evaluate_with_resistance.opp_history = heapq.nlargest(
                    20, evaluate_with_resistance.opp_history, key=lambda x: x[1])

    return worst_area

def find_min_area_triangles(config):
    """Find triangles with area close to the minimum"""
    n = len(config)
    min_area = get_smallest_triangle_area(config)
    min_triangles = []
    
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Calculate triangle area
                area = 0.5 * abs(
                    (config[i,0]*(config[j,1]-config[k,1]) + 
                     config[j,0]*(config[k,1]-config[i,1]) + 
                     config[k,0]*(config[i,1]-config[j,1]))
                )
                if abs(area - min_area) < 1e-6:
                    min_triangles.append((i, j, k))
    
    return min_triangles

def generate_balanced_grid(A, B, C, rows):
    total_rows = len(rows)
    points = []
    for row_idx, num_points in enumerate(rows):
        v = (row_idx + 0.5) / total_rows
        for i in range(num_points):
            u = (i + 0.5) / num_points * (1 - v)
            w = 1 - u - v
            P = w * A + u * B + v * C
            points.append(P)
        if len(points) >= 11:
            break
    return np.array(points[:11])

def generate_optimal_row_patterns(A, B, C, num_patterns=3, max_rows=5):
    candidates = []
    
    # Bias toward historically successful patterns
    historical_patterns = [
        [2, 2, 2, 2, 3],  # Pattern with high resistance in previous runs
        [1, 2, 3, 3, 2],
        [1, 3, 3, 2, 2],
        [2, 3, 2, 2, 2]
    ]
    
    # Use historical patterns with 60% probability
    for _ in range(50):
        if np.random.rand() < 0.6 and historical_patterns:
            counts = historical_patterns[np.random.randint(0, len(historical_patterns))].copy()
            # Small random variation
            if np.random.rand() < 0.7:
                idx = np.random.randint(0, len(counts))
                counts[idx] = max(1, counts[idx] + np.random.choice([-1, 1]))
        else:
            num_rows = np.random.randint(2, max_rows + 1)
            if num_rows == 1:
                counts = [11]
            else:
                splits = np.sort(np.random.choice(10, num_rows - 1, replace=False))
                counts = np.diff(np.concatenate(([0], splits, [11])))
        
        config = generate_balanced_grid(A, B, C, counts)
        # Evaluate with resistance simulation
        area = evaluate_with_resistance(config, A, B, C, num_perturbations=5)
        candidates.append((area, config))
    
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [config for (_, config) in candidates[:num_patterns]]

def symmetric_restart(A, B, C):
    M = np.array([(A[0] + B[0]) / 2, 0])  # Midpoint of AB
    points = []
    
    # Introduce controlled asymmetry based on resistance history
    resistance_avg = get_resistance_history_avg()
    asymmetry_factor = 0.1 * (1 - resistance_avg)  # More asymmetry when resistance is low
    
    # Generate 5 points in left half (triangle A, C, M)
    for _ in range(5):
        r1, r2 = np.random.rand(2)
        if r1 + r2 > 1:
            r1, r2 = 1 - r1, 1 - r2
        r3 = 1 - r1 - r2
        p = r1 * A + r2 * C + r3 * M
        points.append(p)
    
    # Reflect with controlled asymmetry
    for i in range(5):
        p = points[i]
        x_ref = 2 * M[0] - p[0]
        # Add asymmetry noise
        x_ref += np.random.uniform(-asymmetry_factor * (C[0] - A[0]), asymmetry_factor * (C[0] - A[0]))
        points.append(np.array([x_ref, p[1]]))
    
    # Center point with vertical variation
    center_y = np.random.uniform(0.3 * C[1], 0.7 * C[1])
    points.append(np.array([M[0], center_y]))
    
    config = np.array(points)
    initial_area = evaluate_with_resistance(config, A, B, C, num_perturbations=5)
    gap = max(0, 0.0365 - initial_area)
    noise_scale = gap * 0.1
    
    for i in range(11):
        noise = noise_scale * np.random.uniform(-1, 1, 2)
        config[i] = clip_to_triangle(config[i] + noise, A, B, C)
    
    return config

def boundary_focused_configuration(A, B, C):
    centroid = (A + B + C) / 3
    points = []
    
    # Parameterize boundary positions based on resistance history
    resistance_avg = get_resistance_history_avg()
    # More extreme boundary points when resistance is low
    boundary_positions = [
        0.15 + 0.1 * resistance_avg,
        0.5,
        0.85 - 0.1 * resistance_avg
    ]
    
    # 3 boundary points on AB
    for pos in boundary_positions:
        points.append(A + pos * (B - A))
    
    # 1 boundary point on BC, 1 on CA (also parameterized)
    points.append(B + (0.25 + 0.2 * resistance_avg) * (C - B))
    points.append(C + (0.25 + 0.2 * resistance_avg) * (A - C))
    
    # 6 interior points with adaptive spacing
    spacing_factor = 0.12 * (1 - resistance_avg) + 0.05
    points.append(centroid + spacing_factor * (B - A) + spacing_factor/2 * (C - A))
    points.append(centroid + spacing_factor/2 * (B - A) + spacing_factor * (C - A))
    points.append(centroid - spacing_factor/2 * (B - A) + spacing_factor * (C - A))
    points.append(centroid - spacing_factor * (B - A) - spacing_factor/2 * (C - A))
    points.append(centroid - spacing_factor/2 * (B - A) - spacing_factor * (C - A))
    points.append(centroid + spacing_factor/2 * (B - A) - spacing_factor * (C - A))
    
    return np.array(points)

def literature_heuristic_configuration(A, B, C):
    # Base pattern from literature
    points0 = np.array([
        [0.0000, 0.0000],
        [1.0000, 0.0000],
        [0.5000, 0.8660],
        [0.2000, 0.1732],
        [0.8000, 0.1732],
        [0.5100, 0.3464],
        [0.1000, 0.4330],
        [0.9000, 0.4330],
        [0.3000, 0.5196],
        [0.7000, 0.5196],
        [0.4900, 0.6062]
    ])
    
    # Adaptive scaling based on resistance history
    resistance_avg = get_resistance_history_avg()
    # Scale more aggressively when resistance is low
    k = np.sqrt(4 / np.sqrt(3)) * (0.95 + 0.1 * (1 - resistance_avg))
    return points0 * k

def simulated_annealing(initial, A, B, C, niter=100000, T0=0.5, alpha=0.9999):
    current = initial.copy()
    # Use resistance-aware evaluation
    current_area = evaluate_with_resistance(current, A, B, C, num_perturbations=3)
    best = current
    best_area = current_area
    last_improvement = 0

    for i in range(niter):
        T = T0 * (alpha ** i)
        gap = max(0, 0.0365 - best_area)
        
        # Dynamic reheat threshold based on resistance history
        resistance_avg = get_resistance_history_avg()
        threshold = BASE_REHEAT_THRESHOLD * (1 + 2 * (1 - resistance_avg))
        
        if i - last_improvement > threshold:
            T = T0 * 0.5
            last_improvement = i
        
        # Adaptive directional sampling
        resistance_impact = 1 - resistance_avg
        direction_count = min(20, 8 + int(12 * resistance_impact))
        
        # Gradient estimation every 1000 steps at low temperature
        if i % 1000 == 0 and T < 0.1:
            idx = np.random.randint(0, 11)
            best_new_area = current_area - 1e10
            best_candidate = None
            
            # Get historical opponent improvement directions
            opp_history = getattr(evaluate_with_resistance, 'opp_history', [])
            
            # Create adaptive direction set
            directions = []
            # Primary directions (more when resistance is low)
            for _ in range(max(4, int(direction_count * 0.6))):
                d = np.random.normal(0, 1, 2)
                d = d / np.linalg.norm(d)
                directions.append(d)
            
            # Historical opponent directions (biased toward successful past attacks)
            if opp_history:
                for _ in range(min(8, int(direction_count * 0.4))):
                    hist_dir, _ = opp_history[np.random.randint(0, len(opp_history))]
                    noise = np.random.normal(0, 0.2, 2)
                    d = hist_dir + noise
n                    d = d / np.linalg.norm(d)
                    directions.append(d)

            # Add cardinal directions for stability
            directions.extend([
                np.array([1,0]), np.array([-1,0]), np.array([0,1]), np.array([0,-1])
            ])

            for d in directions:
                step_vec = T * d
                candidate_config = current.copy()
                candidate_config[idx] += step_vec
                candidate_config[idx] = clip_to_triangle(candidate_config[idx], A, B, C)
                new_area = evaluate_with_resistance(candidate_config, A, B, C, num_perturbations=2)
                if new_area > best_new_area:
                    best_new_area = new_area
                    best_candidate = candidate_config
            
            if best_new_area > current_area:
                candidate = best_candidate
                new_area = best_new_area
            else:
                idx = np.random.randint(0, 11)
                step = np.random.uniform(-T, T, size=2)
                candidate = current.copy()
                candidate[idx] += step
                candidate[idx] = clip_to_triangle(candidate[idx], A, B, C)
                new_area = evaluate_with_resistance(candidate, A, B, C, num_perturbations=2)
        else:
            idx = np.random.randint(0, 11)
            step = np.random.uniform(-T, T, size=2)
            candidate = current.copy()
            candidate[idx] += step
            candidate[idx] = clip_to_triangle(candidate[idx], A, B, C)
            new_area = evaluate_with_resistance(candidate, A, B, C, num_perturbations=2)
        
        if new_area > current_area:
            current = candidate
            current_area = new_area
            if new_area > best_area:
                best = candidate
                best_area = new_area
                last_improvement = i
        else:
            delta = new_area - current_area
            if np.random.rand() < np.exp(delta / T):
                current = candidate
                current_area = new_area

    # Update resistance history
    global RESISTANCE_HISTORY
    RESISTANCE_HISTORY.append(best_area / 0.0365)
    if len(RESISTANCE_HISTORY) > 10:
        RESISTANCE_HISTORY = RESISTANCE_HISTORY[-10:]
        
    return best, best_area

def local_search(config, A, B, C, steps=20, initial_step_size=0.01):
    current = config.copy()
    current_area = evaluate_with_resistance(current, A, B, C, num_perturbations=3)
    step_size = initial_step_size
    
    # Get resistance history for adaptive search
    resistance_avg = get_resistance_history_avg()
    # More aggressive search when resistance is low
    direction_count = min(16, 4 + int(12 * (1 - resistance_avg)))

    for _ in range(steps):
        improved = False
        ratio = min(current_area, 0.0365) / 0.0365
        decay_factor = 0.95 + 0.04 * (1 - ratio)
        
        # Create adaptive direction set
        directions = []
        # Cardinal directions
        directions.extend([
            (step_size, 0), (-step_size, 0), (0, step_size), (0, -step_size)
        ])
        # Diagonal directions (more when resistance is low)
        if direction_count > 4:
            extra_diagonals = direction_count - 4
            for _ in range(extra_diagonals):
                angle = np.random.uniform(0, 2 * np.pi)
                directions.append((
                    step_size * np.cos(angle),
                    step_size * np.sin(angle)
                ))
        
        for idx in range(11):
            for (dx, dy) in directions:
                candidate = current.copy()
                candidate[idx] += [dx, dy]
                candidate[idx] = clip_to_triangle(candidate[idx], A, B, C)
                new_area = evaluate_with_resistance(candidate, A, B, C, num_perturbations=2)
                if new_area > current_area:
                    current = candidate
                    current_area = new_area
                    improved = True
        
        if not improved:
            break
        step_size *= decay_factor
        
    return current, current_area

def entrypoint():
    A, B, C = get_unit_triangle()
    restarts = []
    restarts.extend(generate_optimal_row_patterns(A, B, C, num_patterns=3))
    restarts.append(symmetric_restart(A, B, C))
    restarts.append(literature_heuristic_configuration(A, B, C))
    restarts.append(boundary_focused_configuration(A, B, C))

    best_config = None
    best_area = -1

    for i, initial in enumerate(restarts):
        rng = np.random.RandomState(42 + i)
        # Adaptive perturbation magnitude based on resistance history
        resistance_avg = get_resistance_history_avg()
        perturbation_magnitude = 0.05 * (1 + 2 * (1 - resistance_avg))
        perturbation = rng.uniform(-perturbation_magnitude, perturbation_magnitude, (11, 2))
        initial += perturbation
        for j in range(11):
            initial[j] = clip_to_triangle(initial[j], A, B, C)

        config, area = simulated_annealing(initial, A, B, C)
        config, area = local_search(config, A, B, C)
        
        if area > best_area:
            best_area = area
            best_config = config

    return best_config