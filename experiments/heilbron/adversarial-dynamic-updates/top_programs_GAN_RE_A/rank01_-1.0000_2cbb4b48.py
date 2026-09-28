import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area
import os
import json
import time
from scipy.spatial import Delaunay

# PERSISTENT RESISTANCE HISTORY
HISTORY_FILE = 'resistance_history.json'

try:
    with open(HISTORY_FILE, 'r') as f:
        resistance_history = json.load(f)
        # Convert string keys back to float
        resistance_history = {float(k): v for k, v in resistance_history.items()}
except (FileNotFoundError, json.JSONDecodeError):
    resistance_history = {0.0: {'count': 0, 'resistance': 0.5}}

# Track current run's resistance improvements
run_resistance_history = []

np.random.seed(42)

def save_resistance_history():
    with open(HISTORY_FILE, 'w') as f:
        # Convert float keys to string for JSON
        serializable = {str(k): v for k, v in resistance_history.items()}
        json.dump(serializable, f)

def calculate_triangle_gradient(points, i, j, k):
    """Calculate gradient to increase area of triangle (i,j,k)."""
    a, b, c = points[i], points[j], points[k]
    
    # Area = 0.5 * |(b-a) × (c-a)|
    # Partial derivatives for area maximization:
    grad_a = np.array([c[1] - b[1], b[0] - c[0]]) * 0.5
    grad_b = np.array([a[1] - c[1], c[0] - a[0]]) * 0.5
    grad_c = np.array([b[1] - a[1], a[0] - b[0]]) * 0.5
    
    # Normalize gradients
    for grad in [grad_a, grad_b, grad_c]:
        norm = np.linalg.norm(grad)
        if norm > 1e-10:
            grad /= norm
            
    return grad_a, grad_b, grad_c

def simulate_opponent_attack(points, n_attempts=15, step_size=0.03):
    """Simulate opponent's improvement attempts and return resistance score."""
    A, B, C = get_unit_triangle()
    original_min_area = get_smallest_triangle_area(points)
    improvements = 0
    total_attempts = 0
    
    for _ in range(n_attempts):
        # Identify smallest triangles (top 3)
        n = points.shape[0]
        areas = []
        indices = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                    areas.append(area)
                    indices.append((i, j, k))
        
        if not areas:
            continue
        
        # Sort by area and take top 3 smallest
        sorted_indices = [idx for _, idx in sorted(zip(areas, indices))[:3]]
        
        # Try improving each smallest triangle
        for triangle_idx in sorted_indices:
            total_attempts += 1
            i, j, k = triangle_idx
            
            # Calculate gradients to increase area
            grad_i, grad_j, grad_k = calculate_triangle_gradient(points, i, j, k)
            
            # 70% chance to perturb one point, 30% to perturb all three
            if np.random.rand() < 0.7:
                # Perturb one random point
                point_idx = np.random.choice([i, j, k])
                candidate = points.copy()
                
                if point_idx == i:
                    candidate[i] += grad_i * step_size
                elif point_idx == j:
                    candidate[j] += grad_j * step_size
                else:
                    candidate[k] += grad_k * step_size
                
                # Project back to triangle if needed
                if not is_inside_triangle(candidate[point_idx], A, B, C):
                    # Simple projection toward centroid
                    centroid = (A + B + C) / 3
                    direction = centroid - candidate[point_idx]
                    if np.linalg.norm(direction) > 1e-10:
                        direction = direction / np.linalg.norm(direction)
                        candidate[point_idx] += direction * 0.001
            else:
                # Perturb all three points
                candidate = points.copy()
                candidate[i] += grad_i * step_size * 0.7
                candidate[j] += grad_j * step_size * 0.7
                candidate[k] += grad_k * step_size * 0.7
                
                # Project back to triangle if needed
                for idx in [i, j, k]:
                    if not is_inside_triangle(candidate[idx], A, B, C):
                        centroid = (A + B + C) / 3
                        direction = centroid - candidate[idx]
                        if np.linalg.norm(direction) > 1e-10:
                            direction = direction / np.linalg.norm(direction)
                            candidate[idx] += direction * 0.001

            # Check if improvement was successful
            candidate_min_area = get_smallest_triangle_area(candidate)
            if candidate_min_area > original_min_area:
                improvements += 1

    # Resistance = 1 - (improvements / total_attempts)
    # But ensure it's in [0,1] range
    resistance = max(0.0, min(1.0, 1.0 - (improvements / max(1, total_attempts))))
    return resistance

def get_historical_opponent_strength():
    """Calculate historical opponent strength based on resistance history."""
    if not resistance_history:
        return 0.5  # Default medium strength
    
    # Weight recent history more heavily
    total_weight = 0
    weighted_resistance = 0
    
    for min_area, data in resistance_history.items():
        # More recent = higher min_area
        weight = min_area + 0.01  # Avoid zero weight
        total_weight += weight
        weighted_resistance += weight * data['resistance']
    
    if total_weight > 0:
        return weighted_resistance / total_weight
    return 0.5

def update_resistance_history(points, resistance_score):
    """Update resistance history with new configuration data."""
    min_area = get_smallest_triangle_area(points)
    
    # Add to run history for this execution
    run_resistance_history.append((min_area, resistance_score))
    
    # Update persistent history
    if min_area in resistance_history:
        # Exponential moving average
        alpha = 0.3  # Weight for new observation
        resistance_history[min_area]['resistance'] = (
            alpha * resistance_score + 
            (1 - alpha) * resistance_history[min_area]['resistance']
        )
        resistance_history[min_area]['count'] += 1
    else:
        resistance_history[min_area] = {
            'resistance': resistance_score,
            'count': 1
        }
    
    # Periodically save to disk (every 5 updates)
    if len(run_resistance_history) % 5 == 0:
        save_resistance_history()

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Theoretical optimum for reference (0.0365)
    OPTIMUM = 0.0365
    
    # Track historical opponent strength
    historical_opponent_strength = get_historical_opponent_strength()

    def get_adaptive_params(resistance=None):
        """Dynamically determine optimization parameters based on resistance."""
        params = {
            'vertex_scale': 0.07,
            'edge_ratios': [0.45, 0.55, 0.65],
            'boundary_buffer': 0.05,
            'step_size_factor': 1.5,
            'cooling_factor': 0.995,
            'min_triangles_percentile': 0.15,
            'convergence_threshold': 0.0005
        }
        
        # Adjust based on historical opponent strength
        params['vertex_scale'] = 0.03 + 0.07 * historical_opponent_strength
        params['boundary_buffer'] = max(0.0, 0.05 * (1 - historical_opponent_strength))
        params['step_size_factor'] = 0.8 + 0.7 * (1 - historical_opponent_strength)
        params['cooling_factor'] = 0.997 + 0.002 * historical_opponent_strength
        params['min_triangles_percentile'] = 0.05 + 0.1 * (1 - historical_opponent_strength)
        
        # Create asymmetric edge ratios based on opponent strength
        base = 0.5
        spread = 0.2 * (1 - historical_opponent_strength)
        params['edge_ratios'] = [
            base - spread * 0.5,
            base + spread * 0.3,
            base + spread * 0.7
        ]
        
        return params

    # PHASE 1: Resistance-adaptive vertex-proximate points (3 points)
    def place_vertex_proximate_points(params):
        points = []
        scale = params['vertex_scale']
        
        # Points near vertices - allow closer to vertices for high resistance
        points.append(A + (B - A) * scale + (C - A) * scale)
        points.append(B + (A - B) * (scale * 0.9) + (C - B) * (scale * 1.1))
        points.append(C + (A - C) * (scale * 1.1) + (B - C) * (scale * 0.9))
        
        return points
    
    # PHASE 2: Adaptive edge distribution with asymmetric ratios (6 points total - 2 per edge)
    def place_adaptive_edge_points(params):
        points = []
        ratios = params['edge_ratios']
        
        # AB edge: 2 points with asymmetric spacing
        for t in [ratios[0], ratios[2]]:
            points.append((1-t) * A + t * B)
        
        # BC edge: 2 points
        for t in [ratios[1], ratios[0]]:
            points.append((1-t) * B + t * C)
        
        # CA edge: 2 points
        for t in [ratios[2], ratios[1]]:
            points.append((1-t) * C + t * A)
        
        return points
    
    # PHASE 3: Delaunay-guided interior placement with resistance-aware criteria (2 points)
    def get_largest_empty_space(current_points, params):
        # Add triangle vertices to ensure bounded triangulation
        all_points = np.vstack([current_points, A, B, C])
        
        try:
            tri = Delaunay(all_points)
        except:
            # Fallback if Delaunay fails
            return [current_points[0].copy() * 0.95, current_points[1].copy() * 1.05]
        
        # Find triangles with area above threshold (inverse of smallest)
        min_area_threshold = params['min_triangles_percentile'] * OPTIMUM
        candidate_triangles = []
        
        for simplex in tri.simplices:
            # Skip triangles that include the original triangle vertices
            if any(idx >= len(current_points) for idx in simplex):
                continue
                
            pts = all_points[simplex]
            area = 0.5 * abs(
                (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1]) -
                (pts[2][0] - pts[0][0]) * (pts[1][1] - pts[0][1])
            )
            
            # Only consider triangles larger than threshold
            if area > min_area_threshold:
                candidate_triangles.append((area, simplex))
        
        # If no valid triangle found, return fallback points
        if not candidate_triangles:
            return [
                A + 0.3 * (B - A) + 0.3 * (C - A),
                A + 0.6 * (B - A) + 0.6 * (C - A)
            ]

        # Sort by area (largest first)
        candidate_triangles.sort(key=lambda x: x[0], reverse=True)
        largest_tri = all_points[candidate_triangles[0][1]]
        
        # Return centroid of largest triangle as new point
        centroid = np.mean(largest_tri, axis=0)
        
        # Second point: offset from centroid with resistance-aware strategy
        if len(candidate_triangles) > 1:
            second_tri = all_points[candidate_triangles[1][1]]
            second_centroid = np.mean(second_tri, axis=0)
            direction = second_centroid - centroid
            if np.linalg.norm(direction) > 1e-5:
                direction = direction / np.linalg.norm(direction)
                second_point = centroid + 0.3 * direction * np.linalg.norm(largest_tri[0] - largest_tri[1])
            else:
                second_point = centroid + np.array([0.01, 0.01])
        else:
            edges = [
                (largest_tri[0], largest_tri[1]),
                (largest_tri[1], largest_tri[2]),
                (largest_tri[2], largest_tri[0])
            ]
            max_edge_len = -1
            max_edge = None
            for e in edges:
                length = np.linalg.norm(e[0] - e[1])
                if length > max_edge_len:
                    max_edge_len = length
                    max_edge = e
            
            if max_edge:
                edge_mid = (max_edge[0] + max_edge[1]) / 2
                direction = edge_mid - centroid
                if np.linalg.norm(direction) > 1e-5:
                    direction = direction / np.linalg.norm(direction)
                    second_point = centroid + 0.3 * direction * max_edge_len
                else:
                    second_point = centroid + np.array([0.01, 0.01])
            else:
                second_point = centroid + np.array([0.01, 0.01])

        return [centroid, second_point]

    def project_to_triangle(point, params=None):
        """Project point to triangle with adaptive boundary handling."""
        if params is None:
            params = get_adaptive_params()
            
        # Simple check and projection toward centroid
        if not is_inside_triangle(point, A, B, C):
            centroid = (A + B + C) / 3
            direction = centroid - point
            if np.linalg.norm(direction) > 1e-10:
                direction = direction / np.linalg.norm(direction)
                # Project inward by a small amount
                point = point + direction * 0.001
        return point

    # MULTI-STRATEGY OPTIMIZATION ENSEMBLE
    def run_optimization_chain(initial_points, strategy='balanced'):
        points = initial_points.copy()
        params = get_adaptive_params()

        # Strategy-specific parameter adjustments
        if strategy == 'boundary':
            # Focus on boundary improvements
            params['boundary_buffer'] = max(0.0, params['boundary_buffer'] * 0.5)
            params['vertex_scale'] = min(0.12, params['vertex_scale'] * 1.2)
        elif strategy == 'gradient':
            # Focus on gradient-based refinement
            params['min_triangles_percentile'] = max(0.03, params['min_triangles_percentile'] * 0.7)
        
        # Adaptive convergence criteria
        resistance_plateau_threshold = 0.005  # 0.5% relative improvement
        resistance_plateau_count = 0
        max_plateau_count = 15
        min_iterations = 50
        iteration = 0
        
        # Track best resistance found during optimization
        best_points = points.copy()
        best_resistance = 0.0

        while True:
            iteration += 1
            
            # Get adaptively selected smallest triangles
            n = points.shape[0]
            areas = []
            indices = []
            
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = points[i], points[j], points[k]
                        area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                        areas.append(area)
                        indices.append((i, j, k))
            
            if not areas:
                break
                
            # Sort by area and take top percentile
            sorted_indices = [idx for _, idx in sorted(zip(areas, indices))]
            percentile_idx = min(int(len(areas) * params['min_triangles_percentile']), len(areas)-1)
            smallest_triangles = sorted_indices[:max(1, percentile_idx)]
            
            # For each point, calculate direction to move away from problematic triangles
            move_directions = np.zeros_like(points)
            for tri_indices in smallest_triangles:
                i, j, k = tri_indices
                # For each point in the triangle, calculate outward direction
                for idx in [i, j, k]:
                    # Direction away from the centroid of the other two points
                    other_indices = [x for x in [i, j, k] if x != idx]
                    centroid = np.mean(points[other_indices], axis=0)
                    direction = points[idx] - centroid
                    if np.linalg.norm(direction) > 1e-5:
                        direction = direction / np.linalg.norm(direction)
                        move_directions[idx] += direction

            # Apply the directed perturbations
            for i in range(len(points)):
                if np.linalg.norm(move_directions[i]) > 1e-5:
                    direction = move_directions[i] / np.linalg.norm(move_directions[i])
                    
                    # Adaptive step size based on current resistance
                    step_size = 0.01 * params['step_size_factor']
                    
                    new_point = points[i] + direction * step_size
                    # Project back to triangle if needed
                    points[i] = project_to_triangle(new_point, params)

            # Periodically test resistance
            if iteration % 10 == 0:
                current_resistance = simulate_opponent_attack(points)
                if current_resistance > best_resistance:
                    best_resistance = current_resistance
                    best_points = points.copy()

            # Check for resistance plateau
            if iteration > min_iterations:
                # We're tracking resistance, not min_area directly
                resistance_plateau_count += 1

            if resistance_plateau_count >= max_plateau_count:
                break

            # Safety break
            if iteration > 200:
                break

        return best_points, best_resistance

    # Generate initial configuration with adaptive parameters
    initial_params = get_adaptive_params()
    points = []
    points.extend(place_vertex_proximate_points(initial_params))
    points.extend(place_adaptive_edge_points(initial_params))
    interior_points = get_largest_empty_space(np.array(points), initial_params)
    points.extend(interior_points)
    points = np.array(points)

    # Run multiple optimization chains with different strategies
    chains = []
    
    # Chain 1: Boundary-focused strategy
    boundary_chain, boundary_resistance = run_optimization_chain(
        points.copy(), 
        strategy='boundary'
    )
    chains.append((boundary_chain, boundary_resistance))

    # Chain 2: Gradient-focused strategy
    gradient_chain, gradient_resistance = run_optimization_chain(
        points.copy(), 
        strategy='gradient'
    )
    chains.append((gradient_chain, gradient_resistance))

    # Chain 3: Balanced strategy (default)
    balanced_chain, balanced_resistance = run_optimization_chain(
        points.copy(),
        strategy='balanced'
    )
    chains.append((balanced_chain, balanced_resistance))

    # Select the most resistant configuration
    best_chain = max(chains, key=lambda x: x[1])
    final_points = best_chain[0]
    
    # Final resistance test and update history
    final_resistance = simulate_opponent_attack(final_points)
    update_resistance_history(final_points, final_resistance)

    # Final validation and minor adjustments
    for i in range(len(final_points)):
        if not is_inside_triangle(final_points[i], A, B, C):
            final_points[i] = project_to_triangle(final_points[i], initial_params)
    
    # Check for distinctness and apply minimal perturbations if needed
    for i in range(len(final_points)):
        for j in range(i+1, len(final_points)):
            if np.linalg.norm(final_points[i] - final_points[j]) < 1e-5:
                # Apply small random perturbation
                angle = np.random.rand() * 2 * np.pi
                perturbation = np.array([0.001 * np.cos(angle), 0.001 * np.sin(angle)])
                final_points[j] += perturbation
                # Re-project if needed
                if not is_inside_triangle(final_points[j], A, B, C):
                    final_points[j] = project_to_triangle(final_points[j], initial_params)

    return final_points

# Save history when module is imported
import atexit
atexit.register(save_resistance_history)