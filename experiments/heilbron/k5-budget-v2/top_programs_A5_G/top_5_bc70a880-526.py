# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def generate_fps_config(A, B, C, n):
    points = []
    
    # First point: random inside triangle using barycentric coordinates
    u = random.random()
    v = random.random() * (1 - u)
    w = 1 - u - v
    p = u * A + v * B + w * C
    points.append(p)

    for _ in range(1, n):
        best_candidate = None
        best_min_dist_sq = -1
        
        # Sample 1000 candidate points
        for _ in range(1000):
            u = random.random()
            v = random.random() * (1 - u)
            w = 1 - u - v
            candidate = u * A + v * B + w * C
            
            # Compute min squared distance to existing points
            min_dist_sq = float('inf')
            for p in points:
                diff = candidate - p
                dist_sq = np.sum(diff ** 2)
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
            
            if min_dist_sq > best_min_dist_sq:
                best_min_dist_sq = min_dist_sq
                best_candidate = candidate

        points.append(best_candidate)
    
    return np.array(points)

def tournament_selection(population, k, A, B, C):
    selected = random.sample(population, k)
    return max(selected, key=lambda x: x[1])

def mutate(config, gen, max_gen, initial_step, A, B, C):
    n = len(config)
    new_config = config.copy()
    
    # Determine mutation focus
    if random.random() < 0.7:
        # Focus on critical triangles (smallest area triangles)
        areas = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = get_smallest_triangle_area(np.array([config[i], config[j], config[k]]))
                    areas.append((area, i, j, k))
        
        # Sort by area ascending and take top 3 smallest
        areas.sort(key=lambda x: x[0])
        critical_triangles = areas[:min(3, len(areas))]
        
        # Randomly select one critical triangle
        _, i, j, k = random.choice(critical_triangles)
        # Randomly select one point from the triangle
        idx = random.choice([i, j, k])
    else:
        # Random point mutation
        idx = random.randint(0, n-1)

    # Adaptive step size
    step_size = initial_step * (1 - gen / max_gen)
    
    # Generate displacement
    displacement = np.random.uniform(-1, 1, 2)
    if np.linalg.norm(displacement) > 0:
        displacement = displacement / np.linalg.norm(displacement) * step_size
    
    # Apply displacement with boundary and distinctness checks
    original_point = new_config[idx].copy()
    candidate = original_point + displacement
    
    # Boundary check
    if not is_inside_triangle(candidate, A, B, C):
        # Try reduced steps
        for _ in range(5):
            displacement *= 0.5
            candidate = original_point + displacement
            if is_inside_triangle(candidate, A, B, C):
                break
        else:
            # Fallback: random direction within triangle
            candidate = None
            for _ in range(10):
                offset = np.random.uniform(-step_size, step_size, 2)
                candidate = original_point + offset
                if is_inside_triangle(candidate, A, B, C):
                    break
            if candidate is None or not is_inside_triangle(candidate, A, B, C):
                candidate = original_point
    
    # Distinctness check (using squared distance)
    valid = True
    for i in range(n):
        if i == idx:
            continue
        diff = candidate - new_config[i]
        dist_sq = np.sum(diff ** 2)
        if dist_sq < 1e-10:  # 1e-5 squared
            valid = False
            break
    
    if valid:
        new_config[idx] = candidate
    
    return new_config

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    base_length = np.linalg.norm(B - A)
    
    # Parameters
    pop_size = 50
    n_generations = 100
    initial_step = 0.1 * base_length

    # Generate initial population
    population = []
    for _ in range(pop_size):
        config = generate_fps_config(A, B, C, 11)
        fitness = get_smallest_triangle_area(config)
        population.append((config, fitness))

    # Evolutionary loop
    for gen in range(n_generations):
        offspring = []
        for _ in range(pop_size):
            # Selection
            parent_config, _ = tournament_selection(population, 3, A, B, C)
            # Mutation
            child_config = mutate(parent_config, gen, n_generations, initial_step, A, B, C)
            child_fitness = get_smallest_triangle_area(child_config)
            offspring.append((child_config, child_fitness))

        # Combine and select next generation
        combined = population + offspring
        combined.sort(key=lambda x: x[1], reverse=True)
        population = combined[:pop_size]

    # Return best configuration
    best_config, _ = population[0]
    return best_config

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import random

def _d_entrypoint():
    A, B, C = get_unit_triangle()

    def triangle_area(a, b, c):
        return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))

    def find_min_triangle(pts):
        n = pts.shape[0]
        min_area = float('inf')
        min_indices = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = triangle_area(pts[i], pts[j], pts[k])
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        return min_area, min_indices

    def project_to_boundary(p, A, B, C, gradient=None):
        """Project point p to boundary with distance-proportional correction."""
        if is_inside_triangle(p, A, B, C):
            return p
        
        def closest_point_on_segment(p, a, b, gradient=None):
            ap = p - a
            ab = b - a
            t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
            t = max(0, min(1, t))
            projected = a + t * ab
            
            if gradient is not None and np.linalg.norm(gradient) > 1e-8:
                # Calculate distance to boundary for proportional correction
                dist_to_boundary = np.linalg.norm(p - projected)
                edge_dir = ab / (np.linalg.norm(ab) + 1e-8)
                grad_proj = np.dot(gradient, edge_dir) * edge_dir
                
                if np.linalg.norm(grad_proj) > 1e-8:
                    direction = 1.0 if np.dot(grad_proj, edge_dir) > 0 else -1.0
                    # Scale step by distance to boundary
                    step = 0.01 * dist_to_boundary * np.linalg.norm(gradient)
                    new_point = projected + direction * step * edge_dir
                    
                    t_new = np.dot(new_point - a, ab) / np.dot(ab, ab)
                    if 0 <= t_new <= 1:
                        return new_point
            
            return projected
        
        p_ab = closest_point_on_segment(p, A, B, gradient)
        p_bc = closest_point_on_segment(p, B, C, gradient)
        p_ca = closest_point_on_segment(p, C, A, gradient)
        
        d_ab = np.linalg.norm(p - p_ab)
        d_bc = np.linalg.norm(p - p_bc)
        d_ca = np.linalg.norm(p - p_ca)
        
        min_dist = min(d_ab, d_bc, d_ca)
        if min_dist == d_ab:
            return p_ab
        elif min_dist == d_bc:
            return p_bc
        else:
            return p_ca

    def improve(points: np.ndarray) -> np.ndarray:
        # Use input-dependent seed to diversify exploration
        np.random.seed(int(hash(points.tobytes()) % (2**32)))
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        initial_temp = 0.015
        cooling_rate = 0.999
        current_temp = initial_temp
        rounds = 750
        stagnation_threshold = 50
        stagnation_count = 0
        best_score_prev = best_score

        for round in range(rounds):
            # Adaptive step size based on progress
            if best_score > best_score_prev:
                step_size_factor = 0.997
                stagnation_count = max(0, stagnation_count - 2)
            else:
                step_size_factor = 0.995
                stagnation_count += 1
            
            step_size_val = 0.02 * (step_size_factor ** round)
            best_score_prev = best_score

            # Calculate all triangle areas to determine dynamic dual-triangle probability
            areas = []
            indices = []
            n = current.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = triangle_area(current[i], current[j], current[k])
                        areas.append(area)
                        indices.append((i, j, k))
            
            # Sort by area to find smallest triangles
            sorted_pairs = sorted(zip(areas, indices))
            min_area, (i1, j1, k1) = sorted_pairs[0]
            
            # Dynamic probability for dual triangle optimization
            if len(sorted_pairs) > 1:
                second_min_area, (i2, j2, k2) = sorted_pairs[1]
                # Calculate probability based on area ratio
                dual_prob = 0.5 * (1 - min_area / (second_min_area + 1e-10))
                dual_prob = min(0.8, max(0.1, dual_prob))  # Clamp between 0.1 and 0.8
            else:
                dual_prob = 0.2

            # With adaptive probability, optimize two smallest triangles
            if np.random.rand() < dual_prob:
                # Get gradients for both triangles with area-based weighting
                a1, b1, c1 = current[i1], current[j1], current[k1]
                f1 = (b1[0]-a1[0])*(c1[1]-a1[1]) - (b1[1]-a1[1])*(c1[0]-a1[0])
                sign_f1 = 1.0 if f1 >= 0 else -1.0
                # Weight by relative area deficit (theoretical max - current area)
                weight1 = (0.0365 - min_area)
                grad_a1 = np.array([b1[1]-c1[1], c1[0]-b1[0]]) * 0.5 * sign_f1 * weight1
                grad_b1 = np.array([c1[1]-a1[1], a1[0]-c1[0]]) * 0.5 * sign_f1 * weight1
                grad_c1 = np.array([a1[1]-b1[1], b1[0]-a1[0]]) * 0.5 * sign_f1 * weight1
                
                a2, b2, c2 = current[i2], current[j2], current[k2]
                f2 = (b2[0]-a2[0])*(c2[1]-a2[1]) - (b2[1]-a2[1])*(c2[0]-a2[0])
                sign_f2 = 1.0 if f2 >= 0 else -1.0
                weight2 = (0.0365 - second_min_area)
                grad_a2 = np.array([b2[1]-c2[1], c2[0]-b2[0]]) * 0.5 * sign_f2 * weight2
                grad_b2 = np.array([c2[1]-a2[1], a2[0]-c2[0]]) * 0.5 * sign_f2 * weight2
                grad_c2 = np.array([a2[1]-b2[1], b2[0]-a2[0]]) * 0.5 * sign_f2 * weight2
                
                # Initialize all deltas to zero
                deltas = np.zeros((11, 2))
                
                # Add weighted gradients for first triangle
                deltas[i1] += grad_a1
                deltas[j1] += grad_b1
                deltas[k1] += grad_c1
                
                # Add weighted gradients for second triangle
                deltas[i2] += grad_a2
                deltas[j2] += grad_b2
                deltas[k2] += grad_c2
                
                # Normalize and apply
                for idx in range(11):
                    if np.linalg.norm(deltas[idx]) > 1e-8:
                        deltas[idx] = deltas[idx] / np.linalg.norm(deltas[idx]) * step_size_val
                
                candidate = current.copy()
                for idx in range(11):
                    candidate[idx] += deltas[idx]
            else:
                # Standard approach with just the smallest triangle
                min_area, (i, j, k) = find_min_triangle(current)
                a, b, c = current[i], current[j], current[k]

                f = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                sign_f = 1.0 if f >= 0 else -1.0

                # Weight gradient by relative area deficit
                weight = (0.0365 - min_area)
                grad_a = np.array([b[1]-c[1], c[0]-b[0]]) * 0.5 * sign_f * weight
                grad_b = np.array([c[1]-a[1], a[0]-c[0]]) * 0.5 * sign_f * weight
                grad_c = np.array([a[1]-b[1], b[0]-a[0]]) * 0.5 * sign_f * weight

                # Create gradient vector for the candidate point update
                deltas = np.zeros((11, 2))
                deltas[i] = grad_a
                deltas[j] = grad_b
                deltas[k] = grad_c

                # Normalize and apply
                for idx in [i, j, k]:
                    if np.linalg.norm(deltas[idx]) > 1e-8:
                        deltas[idx] = deltas[idx] / np.linalg.norm(deltas[idx]) * step_size_val

                candidate = current.copy()
                for idx in [i, j, k]:
                    candidate[idx] += deltas[idx]

            # ADDITIONAL EXPLORATION: 5% chance to move random non-critical points
            if np.random.rand() < 0.05:
                all_indices = set(range(11))
                critical_indices = set([i, j, k])
                if np.random.rand() < 0.2 and 'i2' in locals():
                    critical_indices.update([i2, j2, k2])
                
                non_critical = list(all_indices - critical_indices)
                if non_critical:
                    num_to_move = min(3, len(non_critical))
                    move_indices = random.sample(non_critical, num_to_move)
                    for idx in move_indices:
                        direction = np.random.uniform(-1, 1, 2)
                        direction = direction / (np.linalg.norm(direction) + 1e-8)
                        candidate[idx] += direction * (step_size_val * 0.5)

            # Boundary projection - now with distance-proportional correction
            for idx in range(candidate.shape[0]):
                # Calculate gradient direction for boundary movement
                gradient_dir = None
                if idx in [i, j, k]:
                    gradient_dir = deltas[idx]
                
                if not is_inside_triangle(candidate[idx:idx+1], A, B, C):
                    candidate[idx] = project_to_boundary(candidate[idx], A, B, C, gradient_dir)

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - current_score

            # Adaptive temperature: increase if stuck
            if stagnation_count > stagnation_threshold:
                current_temp = min(initial_temp, current_temp * 1.05)
                stagnation_count = 0

            if delta > 0 or np.random.rand() < np.exp(delta / current_temp):
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score

            # Update temperature
            current_temp *= cooling_rate

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)