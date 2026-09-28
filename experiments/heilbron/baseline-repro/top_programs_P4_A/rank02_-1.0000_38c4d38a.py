import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def generate_symmetric_partition(n_points, min_layers=2, max_layers=10):
    """Generate partition with symmetry constraints for better resistance"""
    while True:
        num_layers = random.randint(min_layers, max_layers)
        # Ensure symmetry by having odd number of layers or symmetric structure
        if num_layers % 2 == 1:
            # Odd: symmetric around center
            partition = [1] * num_layers
            remaining = n_points - num_layers
            # Distribute symmetrically
            for i in range(remaining):
                pos = i % ((num_layers + 1) // 2)
                partition[pos] += 1
                if pos != num_layers - 1 - pos:  # Don't double count center
                    partition[num_layers - 1 - pos] += 1
        else:
            # Even: symmetric halves
            partition = [1] * num_layers
            remaining = n_points - num_layers
            for i in range(remaining):
                pos = i % (num_layers // 2)
                partition[pos] += 1
                partition[num_layers - 1 - pos] += 1
        
        # Validate partition
        if sum(partition) == n_points and all(x >= 1 for x in partition):
            return partition

def evaluate_resistance(points, A, B, C, n_samples=25):
    """Simulate opponent moves to estimate resistance"""
    base_min_area = get_smallest_triangle_area(points)
    n_points = len(points)
    
    # Try to find improvements using opponent-like strategies
    improvements_found = 0
    total_tries = 0
    
    # Strategy 1: Two-point coordinated moves (most common opponent strategy)
    for _ in range(n_samples // 3):
        idx1, idx2 = random.sample(range(n_points), 2)
        # Generate small opposite displacements
        step_size = 0.02
        dx = random.gauss(0, step_size)
        dy = random.gauss(0, step_size)
        P1_new = points[idx1] + np.array([dx, dy])
        P2_new = points[idx2] - np.array([dx, dy])
        
        if is_inside_triangle(P1_new, A, B, C) and is_inside_triangle(P2_new, A, B, C):
            candidate_points = np.copy(points)
            candidate_points[idx1] = P1_new
            candidate_points[idx2] = P2_new
            new_min_area = get_smallest_triangle_area(candidate_points)
            if new_min_area > base_min_area:
                improvements_found += 1
            total_tries += 1

    # Strategy 2: Single-point moves on critical points
    critical_indices = find_critical_points(points)
    for _ in range(n_samples // 3):
        if not critical_indices:
            continue
        idx = random.choice(critical_indices)
        step_size = 0.015
        dx = random.gauss(0, step_size)
        dy = random.gauss(0, step_size)
        P_new = points[idx] + np.array([dx, dy])
        
        if is_inside_triangle(P_new, A, B, C):
            candidate_points = np.copy(points)
            candidate_points[idx] = P_new
            new_min_area = get_smallest_triangle_area(candidate_points)
            if new_min_area > base_min_area:
                improvements_found += 1
            total_tries += 1

    # Strategy 3: Small perturbations to all points
    for _ in range(n_samples // 3):
        candidate_points = np.copy(points)
        improved = False
        for i in range(n_points):
            step_size = 0.005
            dx = random.gauss(0, step_size)
            dy = random.gauss(0, step_size)
            P_new = points[i] + np.array([dx, dy])
            
            if is_inside_triangle(P_new, A, B, C):
                candidate_points[i] = P_new
                
        new_min_area = get_smallest_triangle_area(candidate_points)
        if new_min_area > base_min_area:
            improvements_found += 1
        total_tries += 1

    # Return resistance score (fraction of attempts that failed to improve)
    return 1.0 - (improvements_found / total_tries) if total_tries > 0 else 0.0

def find_critical_points(points):
    """Identify points involved in smallest triangles"""
    n = len(points)
    min_area = float('inf')
    critical_indices = set()
    
    # Find minimum area
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                # Calculate triangle area
                area = 0.5 * abs(
                    points[i][0]*(points[j][1]-points[k][1]) +
                    points[j][0]*(points[k][1]-points[i][1]) +
                    points[k][0]*(points[i][1]-points[j][1])
                )
                if area < min_area:
                    min_area = area
    
    # Identify points in triangles with area close to minimum
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                area = 0.5 * abs(
                    points[i][0]*(points[j][1]-points[k][1]) +
                    points[j][0]*(points[k][1]-points[i][1]) +
                    points[k][0]*(points[i][1]-points[j][1])
                )
                if abs(area - min_area) < 1e-6:
                    critical_indices.add(i)
                    critical_indices.add(j)
                    critical_indices.add(k)
    
    return list(critical_indices)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    best_points = None
    best_resistance_score = -1

    for restart in range(15):  # Reduced restarts to focus on quality of each search
        seed_val = random.SystemRandom().randint(0, 100000)
        np.random.seed(seed_val)
        random.seed(seed_val)

        # Use symmetric partition for better resistance properties
        partition = generate_symmetric_partition(11)
        
        points = []

        for i, num_points in enumerate(partition):
            c_weight = (i + 0.5) / len(partition)
            total_span = 1.0 - c_weight
            half_span = total_span / 2.0
            base_step = total_span / num_points
            
            # Dynamic layer shift range based on layer position
            layer_shift_range = 0.20 + 0.15 * (1 - i / len(partition))
            layer_shift = random.uniform(-layer_shift_range, layer_shift_range)
            
            for j in range(num_points):
                offset = (j - (num_points - 1) / 2.0) * base_step
                a_weight = half_span + offset + layer_shift
                b_weight = total_span - a_weight

                # Fallback for invalid weights
                if a_weight < 0:
                    a_weight = 0
                    b_weight = total_span
                elif b_weight < 0:
                    b_weight = 0
                    a_weight = total_span

                P = a_weight * A + b_weight * B + c_weight * C
                points.append(P)

        points = np.array(points)
        
        # Initialize with resistance evaluation
        current_min_area = get_smallest_triangle_area(points)
        current_resistance = evaluate_resistance(points, A, B, C, n_samples=15)
        # Combined fitness: 0.6*quality + 0.4*resistance (emphasize resistance more)
        current_fitness = 0.6 * min(current_min_area / 0.0365, 1.0) + 0.4 * current_resistance
        
        n_points = len(points)
        T0 = 0.6  # Slightly higher initial temperature
        cooling_rate = 0.9985
        max_iter = 60000
        no_improve_count = 0
        resistance_stagnation = 0

        for iter in range(max_iter):
            T = T0 * (cooling_rate ** iter)
            
            # Exponential stagnation escape with upper bound
            base_step_mult = 0.18
            if resistance_stagnation > 800:
                # Power-law growth with upper bound
                step_growth = min((resistance_stagnation - 800) ** 1.4 / 8000, 4.0)
                step_mult = min(base_step_mult * step_growth, 0.6)
            else:
                step_mult = base_step_mult
            step_size = max(0.008, step_mult * math.sqrt(T))

            candidate_points = None
            candidate_min_area = None
            candidate_resistance = None

            # Enhanced two-point move probability with resistance awareness
            two_point_prob = 0.35 + 0.5 * (1 - math.exp(-resistance_stagnation / 150))
            if random.random() < two_point_prob and n_points >= 2:
                idx1, idx2 = random.sample(range(n_points), 2)
                # Generate small opposite displacements in Cartesian space
                dx = random.gauss(0, step_size * 0.35 * math.sqrt(T))
                dy = random.gauss(0, step_size * 0.35 * math.sqrt(T))
                P1_new = points[idx1] + np.array([dx, dy])
                P2_new = points[idx2] - np.array([dx, dy])
                
                if is_inside_triangle(P1_new, A, B, C) and is_inside_triangle(P2_new, A, B, C):
                    candidate_points = np.copy(points)
                    candidate_points[idx1] = P1_new
                    candidate_points[idx2] = P2_new
                    candidate_min_area = get_smallest_triangle_area(candidate_points)
                    # Only evaluate resistance if quality is sufficient
                    if candidate_min_area > current_min_area * 0.95:
                        candidate_resistance = evaluate_resistance(candidate_points, A, B, C, n_samples=8)
                    else:
                        candidate_resistance = 0.0

            # Single-point move if two-point failed or not attempted
            if candidate_points is None:
                idx = random.randrange(n_points)
                P_old = points[idx]
                
                # Convert to barycentric
                v0 = B - A
                v1 = C - A
                v2 = P_old - A
                d00 = np.dot(v0, v0)
                d01 = np.dot(v0, v1)
                d11 = np.dot(v1, v1)
                d20 = np.dot(v2, v0)
                d21 = np.dot(v2, v1)
                denom = d00 * d11 - d01 * d01
                if abs(denom) < 1e-10:
                    resistance_stagnation += 1
                    continue
                b0 = (d11 * d20 - d01 * d21) / denom
                c0 = (d00 * d21 - d01 * d20) / denom
                a0 = 1 - b0 - c0
                
                max_tries = 12
                found = False
                for _ in range(max_tries):
                    # Gaussian perturbations scaled by temperature
                    da = random.gauss(0, step_size * 0.8 * math.sqrt(T))
                    db = random.gauss(0, step_size * 0.8 * math.sqrt(T))
                    a1 = a0 + da
                    b1 = b0 + db
                    c1 = 1 - a1 - b1
                    if a1 >= 0 and b1 >= 0 and c1 >= 0:
                        found = True
                        break
                
                if not found:
                    resistance_stagnation += 1
                    continue
                
                P_new = a1 * A + b1 * B + c1 * C
                candidate_points = np.copy(points)
                candidate_points[idx] = P_new
                candidate_min_area = get_smallest_triangle_area(candidate_points)
                # Only evaluate resistance if quality is sufficient
                if candidate_min_area > current_min_area * 0.95:
                    candidate_resistance = evaluate_resistance(candidate_points, A, B, C, n_samples=8)
                else:
                    candidate_resistance = 0.0

            # Calculate combined fitness for candidate
            candidate_quality = min(candidate_min_area / 0.0365, 1.0)
            candidate_fitness = 0.6 * candidate_quality + 0.4 * candidate_resistance
            
            # Calculate combined fitness for current
            current_quality = min(current_min_area / 0.0365, 1.0)
            current_fitness = 0.6 * current_quality + 0.4 * current_resistance

            # Evaluate candidate move with resistance awareness
            if candidate_fitness > current_fitness:
                points = candidate_points
                current_min_area = candidate_min_area
                current_resistance = candidate_resistance
                current_fitness = candidate_fitness
                resistance_stagnation = 0
                no_improve_count = 0
            else:
                # Only consider acceptance if quality is at least 95% of current
                if candidate_min_area > current_min_area * 0.95:
                    delta = current_fitness - candidate_fitness
                    if delta < 0:
                        # Shouldn't happen, but just in case
                        continue
                    if random.random() < math.exp(-delta / T):
                        points = candidate_points
                        current_min_area = candidate_min_area
                        current_resistance = candidate_resistance
                        current_fitness = candidate_fitness
                        resistance_stagnation = 0
                        no_improve_count = 0
                    else:
                        resistance_stagnation += 1
                        no_improve_count += 1
                else:
                    resistance_stagnation += 1
                    no_improve_count += 1

            # Termination criteria based on resistance stagnation
            if resistance_stagnation >= 5000 or no_improve_count >= 5000:
                break

        # Enhanced local refinement focused on resistance-critical regions
        step = 0.06
        last_improvement = current_min_area
        no_improve_refine = 0
        critical_indices = find_critical_points(points)
        
        # Only refine critical points and their neighbors
        points_to_refine = set(critical_indices)
        for i in range(n_points):
            for j in critical_indices:
                if np.linalg.norm(points[i] - points[j]) < 0.15:
                    points_to_refine.add(i)
        
        points_to_refine = list(points_to_refine)
        
        for refine_iter in range(800):
            improved = False
            # Generate angles with global random rotation
            base_angles = np.linspace(0, 360, 96, endpoint=False)
            global_rotation = random.uniform(0, 5)
            angles = (base_angles + global_rotation) % 360
            
            # Multi-resolution step sizes
            factors = [0.92 ** i for i in range(12)]
            
            offsets = []
            for angle in angles:
                rad = math.radians(angle)
                for f in factors:
                    dx = f * step * math.cos(rad)
                    dy = f * step * math.sin(rad)
                    offsets.append((dx, dy))
            
            for idx in points_to_refine:
                P_old = points[idx]
                best_P = P_old
                best_area = get_smallest_triangle_area(points)
                best_resistance = evaluate_resistance(points, A, B, C, n_samples=5)
                best_fitness = 0.6 * min(best_area / 0.0365, 1.0) + 0.4 * best_resistance
                
                for (dx, dy) in offsets:
                    P_new = P_old + np.array([dx, dy])
                    if not is_inside_triangle(P_new, A, B, C):
                        continue
                    new_points = np.copy(points)
                    new_points[idx] = P_new
                    new_area = get_smallest_triangle_area(new_points)
                    
                    # Only evaluate resistance if quality is promising
n                    if new_area > best_area * 0.97:
                        new_resistance = evaluate_resistance(new_points, A, B, C, n_samples=5)
                        new_fitness = 0.6 * min(new_area / 0.0365, 1.0) + 0.4 * new_resistance
n                        if new_fitness > best_fitness:
                            best_fitness = new_fitness
                            best_area = new_area
                            best_resistance = new_resistance
                            best_P = P_new
                            improved = True
                    elif new_area > best_area:
                        # Quality improved but didn't check resistance - still accept for quality
                        best_area = new_area
                        best_P = P_new
                        improved = True

                if improved:
                    points[idx] = best_P
            
            # Adaptive termination based on improvement
            current_area = get_smallest_triangle_area(points)
            current_resistance = evaluate_resistance(points, A, B, C, n_samples=10)
            current_fitness = 0.6 * min(current_area / 0.0365, 1.0) + 0.4 * current_resistance
            
            if abs(current_fitness - last_improvement) < 1e-6:
                no_improve_refine += 1
            else:
                no_improve_refine = 0
                last_improvement = current_fitness
            
            if no_improve_refine >= 15:
                break

            step *= 0.998  # Slower decay

        # Calculate final resistance score for selection
        final_min_area = get_smallest_triangle_area(points)
        final_resistance = evaluate_resistance(points, A, B, C, n_samples=30)
        resistance_score = final_resistance + 0.5 * min(final_min_area / 0.0365, 1.0)
        
        if resistance_score > best_resistance_score:
            best_resistance_score = resistance_score
            best_points = points

    return best_points