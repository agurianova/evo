import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np
import math

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Define expanded symmetric and asymmetric partitions for n=11 - GEOMETRICALLY DERIVED
    symmetric_partitions = [
        (1, 2, 2, 2, 4),
        (1, 2, 4, 4),
        (1, 4, 6),
        (3, 4, 4),
        (5, 6),
        (2, 3, 6),
        (2, 4, 5),
        (3, 3, 5),
        (4, 4, 3),    # ADDED: Geometrically promising configuration
        (3, 3, 3, 2)   # ADDED: Another promising configuration
    ]
    asymmetric_partitions = [
        (4, 3, 2, 2),
        (5, 3, 2, 1),
        (4, 4, 2, 1),
        (3, 3, 3, 2),
        (2, 3, 6),
        (2, 4, 5),
        (3, 4, 4),
        (2, 3, 3, 3),
        (4, 3, 4)      # ADDED: Hybrid configuration
    ]
    partition_list = symmetric_partitions + asymmetric_partitions
    
    # Thompson sampling initialization with per-partition best tracking - ADAPTIVE WEIGHTING
    successes = {p: 0 for p in partition_list}
    trials = {p: 0 for p in partition_list}
    best_for_partition = {p: -1.0 for p in partition_list}
    global_best = -1
    best_points = None
    top_partitions = []  # Track top performing partitions for evolution
    
    # Helper: generate points from partition and row heights
    def generate_points(partition, h=None, symmetric=False):
        points = []
        m = len(partition)
        for i in range(m):
            c_weight = h[i] if h is not None else (i + 0.5) / m
            num_points = partition[i]
            
            if symmetric:
                # Trigonometric spacing with boundary margin
                for j in range(num_points):
                    if num_points > 1:
                        boundary_margin = 0.1 / (num_points - 1 + 0.2)
                    else:
                        boundary_margin = 0.0
                    t = boundary_margin + (1 - 2 * boundary_margin) * (j + 0.5) / num_points
                    a_weight = (1 - t) * (1 - c_weight)
                    b_weight = t * (1 - c_weight)
                    P = a_weight * A + b_weight * B + c_weight * C
                    points.append(P)
            else:
                # Original asymmetric row generation
                for j in range(num_points):
                    b_weight = (j + 0.5) / num_points * (1 - c_weight)
                    a_weight = 1 - c_weight - b_weight
                    P = a_weight * A + b_weight * B + c_weight * C
                    points.append(P)
        return np.array(points)

    # Helper: get all triangle areas for distribution analysis
    def get_all_triangle_areas(points):
        n = len(points)
        areas = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area_val = 0.5 * abs(np.cross(points[j] - points[i], points[k] - points[i]))
                    areas.append(area_val)
        return np.array(areas)

    # Helper: calculate entropy of triangle area distribution
    def calculate_area_entropy(points, min_area_val):
        areas = get_all_triangle_areas(points)
        # Normalize areas relative to min_area
        normalized = areas / min_area_val
n        # Bin the normalized areas for entropy calculation
        bins = np.histogram_bin_edges(normalized, bins='fd')
        counts, _ = np.histogram(normalized, bins=bins)
        probs = counts / len(normalized)
        # Add small epsilon to avoid log(0)
        probs = probs[probs > 0] + 1e-10
        entropy = -np.sum(probs * np.log2(probs))
        return entropy

    # Helper: get triangle area statistics for adaptive thresholds
    def get_triangle_area_stats(points):
        areas = get_all_triangle_areas(points)
        return np.std(areas), np.mean(areas), np.min(areas)

    for restart in range(30):
        # Thompson sampling for partition selection with increased exploration - ADAPTIVE EXPLORATION
        chosen_p = None
        best_sample = -1
        for p in partition_list:
            # INCREASED EXPLORATION: Using alpha=successes+2, beta=trials-successes+2 for more exploration
            alpha = successes[p] + 2
            beta = trials[p] - successes[p] + 2
            sample = np.random.beta(alpha, beta)
            if sample > best_sample:
                best_sample = sample
                chosen_p = p
        
        # CONSERVATIVE PARTITION EVOLUTION: 20% chance to mutate top performers
        if random.random() < 0.2 and top_partitions:
            base_p = random.choice(top_partitions)
            mutated_p = list(base_p)
            if len(mutated_p) > 1:
                i = random.randint(0, len(mutated_p)-2)
                if mutated_p[i] > 1 and mutated_p[i+1] < 10:
                    mutated_p[i] -= 1
                    mutated_p[i+1] += 1
                chosen_p = tuple(mutated_p)

        trials[chosen_p] += 1

        # CYCLICAL PERTURBATION SCHEDULE - EXPLORATION BURSTS
        cycle_length = 10
        cycle_position = restart % cycle_length
        if cycle_position == 0:  # Reset perturbation at start of each cycle
            perturbation = 0.15
        else:
            perturbation = 0.15 * (0.9 ** (cycle_position / cycle_length))
        
        # Coarse scale: optimize row heights for symmetric partitions
        if chosen_p in symmetric_partitions:
            m = len(chosen_p)
            h = np.array([(i + 0.5) / m for i in range(m)])
            current_min_area = get_smallest_triangle_area(generate_points(chosen_p, h, True))
            
            # Simulated annealing for row heights with ADAPTIVE ITERATION LIMITS
            T0 = 0.1
            cooling_rate = 0.995
            max_iter = 6000  # INCREASED from 2000 to 6000
            no_improve_count = 0
            recent_improvements = []
            improvement_window = 1000
            
            for iter in range(max_iter):
                T = T0 * (cooling_rate ** iter)
                i = random.randint(0, m - 1)
                low = 0 if i == 0 else h[i - 1] + 1e-5
                high = 1 if i == m - 1 else h[i + 1] - 1e-5
                step = 0.1 * math.sqrt(T)
                h_new_val = h[i] + random.uniform(-step, step)
                h_new_val = max(low, min(high, h_new_val))
                
                h_new = h.copy()
                h_new[i] = h_new_val
                points = generate_points(chosen_p, h_new, True)
                new_min_area = get_smallest_triangle_area(points)

                if new_min_area > current_min_area:
                    improvement = new_min_area - current_min_area
                    recent_improvements.append(improvement)
                    h = h_new
                    current_min_area = new_min_area
                    no_improve_count = 0
                else:
                    delta = current_min_area - new_min_area
                    if delta < 0:
                        continue
                    if random.random() < math.exp(-delta / T):
                        h = h_new
                        current_min_area = new_min_area
                        no_improve_count = 0
                    else:
                        no_improve_count += 1

                # ADAPTIVE STAGNATION DETECTION - VARIANCE-BASED THRESHOLDS
                if iter % 100 == 0 and iter > 0:  # Calculate stats periodically
                    std_dev, mean_area, min_area_val = get_triangle_area_stats(points)
                    relative_progress = min_area_val / 0.0365
                    
                    # ADAPTIVE THRESHOLDS BASED ON VARIANCE AND PROGRESS
                    if no_improve_count >= 500 and (min_area_val < 0.025 or std_dev < 0.001 * mean_area):
                        break
                    if no_improve_count >= 2000 and (min_area_val < 0.032 or std_dev < 0.0005 * mean_area):
                        break
                    if no_improve_count >= 5000 and std_dev < 0.0001 * mean_area:
                        break

            points = generate_points(chosen_p, h, True)
            
        else:
            # Asymmetric partition: optimize row heights first
            m = len(chosen_p)
            h = np.array([(i + 0.5) / m for i in range(m)])
            current_min_area = get_smallest_triangle_area(generate_points(chosen_p, h, False))
            
            # Simulated annealing for row heights with ADAPTIVE ITERATION LIMITS
            T0 = 0.1
            cooling_rate = 0.995
            max_iter = 6000  # INCREASED from 2000 to 6000
            no_improve_count = 0
            recent_improvements = []
            improvement_window = 1000
            
            for iter in range(max_iter):
                T = T0 * (cooling_rate ** iter)
                i = random.randint(0, m - 1)
                low = 0 if i == 0 else h[i - 1] + 1e-5
                high = 1 if i == m - 1 else h[i + 1] - 1e-5
                step = 0.1 * math.sqrt(T)
                h_new_val = h[i] + random.uniform(-step, step)
                h_new_val = max(low, min(high, h_new_val))
                
                h_new = h.copy()
                h_new[i] = h_new_val
                points = generate_points(chosen_p, h_new, False)
                new_min_area = get_smallest_triangle_area(points)

                if new_min_area > current_min_area:
                    improvement = new_min_area - current_min_area
                    recent_improvements.append(improvement)
                    h = h_new
                    current_min_area = new_min_area
                    no_improve_count = 0
                else:
                    delta = current_min_area - new_min_area
                    if delta < 0:
                        continue
                    if random.random() < math.exp(-delta / T):
                        h = h_new
                        current_min_area = new_min_area
                        no_improve_count = 0
                    else:
                        no_improve_count += 1

                # ADAPTIVE STAGNATION DETECTION - VARIANCE-BASED THRESHOLDS
                if iter % 100 == 0 and iter > 0:
                    std_dev, mean_area, min_area_val = get_triangle_area_stats(points)
                    relative_progress = min_area_val / 0.0365
                    
                    if no_improve_count >= 500 and (min_area_val < 0.025 or std_dev < 0.001 * mean_area):
                        break
                    if no_improve_count >= 2000 and (min_area_val < 0.032 or std_dev < 0.0005 * mean_area):
                        break
                    if no_improve_count >= 5000 and std_dev < 0.0001 * mean_area:
                        break

            # Now apply adaptive perturbation with optimized row heights
            points = []
            for i, num_points in enumerate(chosen_p):
                c_weight = h[i]
                for j in range(num_points):
                    b_weight = (j + 0.5) / num_points * (1 - c_weight)
                    a_weight = 1 - c_weight - b_weight
                    
                    # Apply adaptive perturbation
                    max_tries = 10
                    for _ in range(max_tries):
                        da = random.uniform(-perturbation, perturbation)
                        db = random.uniform(-perturbation, perturbation)
                        a1 = a_weight + da
                        b1 = b_weight + db
                        c1 = 1 - a1 - b1
                        if a1 >= 0 and b1 >= 0 and c1 >= 0:
                            break
                    else:
                        a1, b1, c1 = a_weight, b_weight, 1 - a_weight - b_weight
                    
                    P = a1 * A + b1 * B + c1 * C
                    points.append(P)
            points = np.array(points)

        # Fine scale refinement with ADAPTIVE ITERATION LIMITS
        current_min_area = get_smallest_triangle_area(points)
        n_points = len(points)
        T0 = 0.3
        cooling_rate = 0.999
        max_iter = 150000  # INCREASED from 50000 to 150000
        no_improve_count = 0
        recent_improvements = []
        improvement_window = 1000

        for iter in range(max_iter):
            T = T0 * (cooling_rate ** iter)
            idx = random.randrange(n_points)
            P_old = points[idx]
            
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
                continue
            b0 = (d11 * d20 - d01 * d21) / denom
            c0 = (d00 * d21 - d01 * d20) / denom
            a0 = 1 - b0 - c0
            
            step_size = max(0.01, 0.15 * math.sqrt(T))
            max_tries = 10
            found = False
            for _ in range(max_tries):
                da = random.uniform(-step_size, step_size)
                db = random.uniform(-step_size, step_size)
                a1 = a0 + da
                b1 = b0 + db
                c1 = 1 - a1 - b1
                if a1 >= 0 and b1 >= 0 and c1 >= 0:
                    found = True
                    break
            
            if not found:
                no_improve_count += 1
                continue
            
            P_new = a1 * A + b1 * B + c1 * C
            
            new_points = np.copy(points)
            new_points[idx] = P_new
            new_min_area = get_smallest_triangle_area(new_points)
            
            if new_min_area > current_min_area:
                improvement = new_min_area - current_min_area
                recent_improvements.append(improvement)
                points = new_points
                current_min_area = new_min_area
                no_improve_count = 0
            else:
                delta = current_min_area - new_min_area
                if delta < 0:
                    continue
                if random.random() < math.exp(-delta / T):
                    improvement = new_min_area - current_min_area
                    recent_improvements.append(improvement)
                    points = new_points
                    current_min_area = new_min_area
                    no_improve_count = 0
                else:
                    no_improve_count += 1

            # ADAPTIVE STAGNATION DETECTION - VARIANCE-BASED THRESHOLDS
            if iter % 100 == 0 and iter > 0:
                std_dev, mean_area, min_area_val = get_triangle_area_stats(points)
                relative_progress = min_area_val / 0.0365
                
                if no_improve_count >= 500 and (min_area_val < 0.025 or std_dev < 0.001 * mean_area):
                    break
                if no_improve_count >= 2000 and (min_area_val < 0.032 or std_dev < 0.0005 * mean_area):
                    break
                if no_improve_count >= 5000 and std_dev < 0.0001 * mean_area:
                    break

        # Adaptive gradient refinement with STAGE-DEPENDENT THRESHOLD
        step = 0.01
        for _ in range(100):
            improved = False
            current_min_area_val = get_smallest_triangle_area(points)
            n_points = len(points)
            
            # ADAPTIVE CRITICAL THRESHOLD - ENTROPY-BASED
            area_entropy = calculate_area_entropy(points, current_min_area_val)
            # Higher entropy means more uniform distribution, need tighter threshold
            if area_entropy > 3.0:  # High entropy - many triangles near minimum
                critical_threshold = max(1e-7, current_min_area_val * 0.02)  # Tighter threshold
            elif area_entropy > 2.0:  # Medium entropy
                critical_threshold = max(1e-7, current_min_area_val * 0.05)
            else:  # Low entropy - few triangles near minimum
                critical_threshold = max(1e-7, current_min_area_val * 0.1)  # Looser threshold
            
            for idx in range(n_points):
                P_old = points[idx]
                candidates = []
                
                # Find critical triangles involving this point
                critical_dirs = []
                for i in range(n_points):
                    if i == idx:
                        continue
                    for j in range(i+1, n_points):
                        if j == idx:
                            continue
                        Q = points[i]
                        R = points[j]
                        # Compute area of triangle P_old, Q, R
                        area_val = 0.5 * abs(np.cross(Q - P_old, R - P_old))
                        if area_val <= current_min_area_val + critical_threshold:
                            v = R - Q
                            n = np.array([-v[1], v[0]])
                            if np.linalg.norm(n) < 1e-10:
                                continue
                            n = n / np.linalg.norm(n)
                            d = np.dot(P_old - Q, n)
                            critical_dirs.append(np.sign(d) * n)
                
                if critical_dirs:
                    composite_dir = np.mean(critical_dirs, axis=0)
                    if np.linalg.norm(composite_dir) > 1e-10:
                        composite_dir = composite_dir / np.linalg.norm(composite_dir)
                        candidates.append(composite_dir)
                else:
                    # Boundary-aware fallback direction
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
                        dir_vec = np.random.randn(2)
                        dir_vec = dir_vec / np.linalg.norm(dir_vec)
                    else:
                        b0_val = (d11 * d20 - d01 * d21) / denom
                        c0_val = (d00 * d21 - d01 * d20) / denom
                        a0_val = 1 - b0_val - c0_val
                        coords = [a0_val, b0_val, c0_val]
                        min_coord = min(coords)
                        if min_coord == a0_val:
                            dir_vec = np.array([B[1]-C[1], C[0]-B[0]])
                        elif min_coord == b0_val:
                            dir_vec = np.array([C[1]-A[1], A[0]-C[0]])
                        else:
                            dir_vec = np.array([A[1]-B[1], B[0]-A[0]])
                        if np.linalg.norm(dir_vec) < 1e-10:
                            dir_vec = np.random.randn(2)
                        else:
                            dir_vec = dir_vec / np.linalg.norm(dir_vec)
                    candidates.append(dir_vec)
                
                # Add random exploration directions
                for _ in range(2):
                    r = np.random.randn(2)
                    r = r / np.linalg.norm(r)
                    candidates.append(r)

                # Generate offsets from candidate directions
                offsets = []
                factors = [1.0, 0.8, 0.6, 0.4, 0.2, 0.1]
                for dir_vec in candidates:
                    for f in factors:
                        dx = f * step * dir_vec[0]
                        dy = f * step * dir_vec[1]
                        offsets.append((dx, dy))

                # Evaluate candidate moves
                best_P = P_old
                best_area = current_min_area_val
                for (dx, dy) in offsets:
                    P_new = P_old + np.array([dx, dy])
                    if not is_inside_triangle(P_new, A, B, C):
                        continue
                    new_points = np.copy(points)
                    new_points[idx] = P_new
                    new_area = get_smallest_triangle_area(new_points)
                    if new_area > best_area:
                        best_area = new_area
                        best_P = P_new
                        improved = True
                if improved:
                    points[idx] = best_P

            step *= 0.99
            if not improved:
                continue

        # Boundary optimization step with DYNAMIC THRESHOLD
        for idx in range(n_points):
            P = points[idx]
            # Compute barycentric coordinates
            v0 = B - A
            v1 = C - A
            v2 = P - A
            d00 = np.dot(v0, v0)
            d01 = np.dot(v0, v1)
            d11 = np.dot(v1, v1)
            d20 = np.dot(v2, v0)
            d21 = np.dot(v2, v1)
            denom = d00 * d11 - d01 * d01
            if abs(denom) < 1e-10:
                continue
            b0_val = (d11 * d20 - d01 * d21) / denom
            c0_val = (d00 * d21 - d01 * d20) / denom
            a0_val = 1 - b0_val - c0_val

            min_coord = min(a0_val, b0_val, c0_val)
            if min_coord < 0.05:  # Expanded boundary detection range from 1e-3 to 0.05
                current_area = get_smallest_triangle_area(points)
                # Project to nearest boundary
                if min_coord == a0_val:
                    total = b0_val + c0_val
                    if total < 1e-10:
                        continue
                    b0_new = b0_val / total
                    c0_new = c0_val / total
                    a0_new = 0.0
                elif min_coord == b0_val:
                    total = a0_val + c0_val
                    if total < 1e-10:
                        continue
                    a0_new = a0_val / total
                    c0_new = c0_val / total
                    b0_new = 0.0
                else:
                    total = a0_val + b0_val
                    if total < 1e-10:
                        continue
                    a0_new = a0_val / total
                    b0_new = b0_val / total
                    c0_new = 0.0

                P_new = a0_new * A + b0_new * B + c0_new * C
                if not is_inside_triangle(P_new, A, B, C):
                    continue

                new_points = np.copy(points)
                new_points[idx] = P_new
                new_area = get_smallest_triangle_area(new_points)
                # DYNAMIC THRESHOLD based on current min_area
                if new_area > current_area + max(1e-6, current_area * 1e-5):
                    points = new_points

        min_area = get_smallest_triangle_area(points)
        # ADAPTIVE WEIGHTING BASED ON QUALITY STAGE - DYNAMIC BALANCE
        quality_ratio = min_area / 0.0365
        if quality_ratio < 0.7:  # Early stage, quality < 0.0255
            quality_weight = 0.8
        elif quality_ratio < 0.88:  # Mid stage, 0.0255 <= quality < 0.032
            quality_weight = 0.65
        else:  # Late stage, quality >= 0.032
            quality_weight = 0.5
        
        resistance_weight = 1.0 - quality_weight
        
        if min_area > best_for_partition[chosen_p] + 1e-5:
            # Calculate quality improvement score (continuous value)
            quality_improvement = min_area - best_for_partition[chosen_p]
            # Apply adaptive weighting based on quality stage
            weighted_score = quality_weight * (quality_improvement / 0.005) + resistance_weight
            # Apply damping to prevent extreme weights
            damped_score = max(0, min(1, weighted_score))
            successes[chosen_p] += damped_score
            best_for_partition[chosen_p] = min_area
        
        # Update top partitions for evolution
        if min_area > 0.025:  # Only consider reasonably good configurations
            if len(top_partitions) < 5 or min_area > np.percentile([get_smallest_triangle_area(generate_points(p, None, p in symmetric_partitions)) for p in top_partitions], 75):
                if chosen_p not in top_partitions:
                    top_partitions.append(chosen_p)
                # Keep only top 5
                if len(top_partitions) > 5:
                    # Sort by performance
                    top_partitions.sort(key=lambda p: best_for_partition.get(p, -1), reverse=True)
                    top_partitions = top_partitions[:5]

        if min_area > global_best:
            global_best = min_area
            best_points = points

    return best_points