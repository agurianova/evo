import random
import numpy as np
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    def cartesian_to_barycentric(p, A, B, C):
        def signed_area(a, b, c):
            return 0.5 * (a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
        u = signed_area(p, B, C)
        v = signed_area(A, p, C)
        w = signed_area(A, B, p)
        total = u + v + w
        if abs(total) < 1e-10:
            return (1/3, 1/3, 1/3)
        return (u/total, v/total, w/total)

    def compute_bottleneck_gradients(points, num_bottlenecks=5):
        """Calculate directional gradients to maximize bottleneck triangle areas."""
        n = len(points)
        triangles = []
        
        # Calculate all triangle areas
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(points[i][0]*(points[j][1]-points[k][1]) + 
                                    points[j][0]*(points[k][1]-points[i][1]) + 
                                    points[k][0]*(points[i][1]-points[j][1]))
                    triangles.append((area, i, j, k))
        
        # Sort by area and take top num_bottlenecks smallest triangles
        triangles.sort(key=lambda x: x[0])
        relevant_triangles = triangles[:num_bottlenecks]
        
        # Initialize displacement for each point with weights
        displacement = np.zeros((n, 2))
        point_weight = np.zeros(n)
        
        for (area, i, j, k) in relevant_triangles:
            a, b, c = points[i], points[j], points[k]
            f = (b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1])
            sign = 1 if f >= 0 else -1
            
            # Calculate directional vectors to push points apart
            dir_a = np.array([b[1]-c[1], c[0]-b[0]]) * sign
            dir_b = np.array([c[1]-a[1], a[0]-c[0]]) * sign
            dir_c = np.array([a[1]-b[1], b[0]-a[0]]) * sign
            
            # Weight by importance (inverse of area difference)
            weight = 1.0 / np.sqrt(area - triangles[0][0] + 1e-8)
            displacement[i] += weight * dir_a
            displacement[j] += weight * dir_b
            displacement[k] += weight * dir_c
            
            point_weight[i] += weight
            point_weight[j] += weight
            point_weight[k] += weight
        
        # Normalize displacements
        for i in range(n):
            if point_weight[i] > 1e-10:
                displacement[i] /= point_weight[i]
        
        return displacement

    def generate_initial_configuration(method):
        n = 11
        
        if method == 0:  # Original lattice with improved step calculation
            # Determine grid size for approximately n points
            k = 1
            while k*(k+1)//2 < n:
                k += 1
            step = 1.0 / (k-1) if k > 1 else 1.0
            
            points_bary = []
            for i in range(k):
                u = i * step
                if u > 1.0:
                    break
                for j in range(k):
                    v = j * step
                    if u + v > 1.0:
                        break
                    w = 1.0 - u - v
                    points_bary.append((u, v, w))
            
            # Add 11th point at asymmetric location if needed
            if len(points_bary) < 11:
                points_bary.append((0.5, 0.3, 0.2))
            
        elif method == 1:  # Symmetric lattice with proper symmetry handling
            points_bary = []
            step_sym = 0.25
            # Generate all symmetric points first
            symmetric_points = []
            for i in range(5):
                u = i * step_sym
                if u > 1.0:
                    break
                for j in range(5):
                    v = j * step_sym
                    if u + v > 1.0:
                        break
                    w = 1.0 - u - v
                    if w < 0:
                        continue
                    if u == v:
                        symmetric_points.append((u, v, w))
                    else:
                        symmetric_points.append((u, v, w))
                        symmetric_points.append((v, u, w))
            # Then trim to exactly 11 points
            points_bary = symmetric_points[:11]
            
        elif method == 2:  # Random asymmetric with proper boundary handling
            points_bary = []
            # Determine grid size for approximately n points
            k = 1
            while k*(k+1)//2 < n:
                k += 1
            step = 1.0 / (k-1) if k > 1 else 1.0
            
            for i in range(k):
                u = i * step
                if u > 1.0:
                    break
                for j in range(k):
                    v = j * step
                    if u + v > 1.0:
                        break
                    w = 1.0 - u - v
                    points_bary.append((u, v, w))
            
            # Add random 11th point with proper simplex projection
            u_rand = random.uniform(0.1, 0.6)
            v_rand = random.uniform(0.1, 0.6)
            w_rand = 1.0 - u_rand - v_rand
            if w_rand < 0:
                coords = np.array([u_rand, v_rand, abs(w_rand)])
                coords /= coords.sum()
                u_rand, v_rand, w_rand = coords
            points_bary.append((u_rand, v_rand, w_rand))

        elif method == 3:  # Literature-based configuration (method 3)
            points_bary = []
            # Boundary layer (3 points)
            points_bary.append((0.95, 0.025, 0.025))
            points_bary.append((0.025, 0.95, 0.025))
            points_bary.append((0.025, 0.025, 0.95))
            
            # Middle layer (4 points)
            points_bary.append((0.7, 0.2, 0.1))
            points_bary.append((0.2, 0.7, 0.1))
            points_bary.append((0.2, 0.1, 0.7))
            points_bary.append((0.1, 0.2, 0.7))
            
            # Inner layer (4 points)
            points_bary.append((0.5, 0.3, 0.2))
            points_bary.append((0.3, 0.5, 0.2))
            points_bary.append((0.3, 0.2, 0.5))
            points_bary.append((0.2, 0.3, 0.5))

        elif method == 4:  # Hexagonal lattice (k=5)
            points_bary = []
            # Generate hexagonal lattice points in barycentric coordinates
            for i in range(5):
                for j in range(5 - i):
                    u = i * 0.2
                    v = j * 0.2
                    w = 1.0 - u - v
                    if w >= 0:
                        points_bary.append((u, v, w))
            
            # Add additional points if needed
            if len(points_bary) < 11:
                points_bary.append((0.1, 0.1, 0.8))
                points_bary.append((0.1, 0.8, 0.1))
                points_bary.append((0.8, 0.1, 0.1))

        else:  # Literature-inspired with randomized layer offsets (method 5)
            points_bary = []
            # Boundary layer (3 points) with random offsets
            offset = random.uniform(-0.05, 0.05)
            points_bary.append((0.95+offset, 0.025-offset/2, 0.025-offset/2))
            points_bary.append((0.025-offset/2, 0.95+offset, 0.025-offset/2))
            points_bary.append((0.025-offset/2, 0.025-offset/2, 0.95+offset))
            
            # Middle layer (4 points) with random offsets
            offset = random.uniform(-0.05, 0.05)
            points_bary.append((0.7+offset, 0.2-offset/2, 0.1-offset/2))
            points_bary.append((0.2-offset/2, 0.7+offset, 0.1-offset/2))
            points_bary.append((0.2-offset/2, 0.1-offset/2, 0.7+offset))
            points_bary.append((0.1-offset/2, 0.2-offset/2, 0.7+offset))
            
            # Inner layer (4 points) with random offsets
            offset = random.uniform(-0.05, 0.05)
            points_bary.append((0.5+offset, 0.3-offset/2, 0.2-offset/2))
            points_bary.append((0.3-offset/2, 0.5+offset, 0.2-offset/2))
            points_bary.append((0.3-offset/2, 0.2-offset/2, 0.5+offset))
            points_bary.append((0.2-offset/2, 0.3-offset/2, 0.5+offset))
        
        # Convert to Cartesian with phase-based perturbation
        points_cart = []
        for (u, v, w) in points_bary:
            # Apply smaller perturbation in barycentric space
            du = random.gauss(0, 0.02)
            dv = random.gauss(0, 0.02)
            u_new, v_new = u + du, v + dv
            w_new = 1.0 - u_new - v_new
            
            # Project back to simplex if needed
            if u_new < 0 or v_new < 0 or w_new < 0:
                coords = np.array([u_new, v_new, w_new])
                coords = np.maximum(coords, 0)
                total = coords.sum()
                if total > 0:
                    coords /= total
                else:
                    coords = np.array([1/3, 1/3, 1/3])
                u_new, v_new, w_new = coords
            
            point = u_new * A + v_new * B + w_new * C
            points_cart.append(point)
        
        return np.array(points_cart[:11])  # Ensure exactly 11 points

    def simulated_annealing(points, max_iter=1000, initial_temp=0.005, base_noise=0.1):
        current_points = points.copy()
        current_min_area = get_smallest_triangle_area(current_points)
        best_points = current_points.copy()
        best_min_area = current_min_area
        current_temp = initial_temp
        
        # Dynamic phase transition parameters
        improvement_threshold = 0.001  # 0.1% improvement threshold
        stagnation_counter = 0
        max_stagnation = 100
        
        for iter_num in range(max_iter):
            # Focus on top 5 bottleneck triangles
            bottleneck_displacement = compute_bottleneck_gradients(current_points, num_bottlenecks=5)
            
            # Determine move type: adaptive probability for bottleneck moves
            bottleneck_prob = max(0.7, 0.95 * (1.0 - current_min_area / 0.0365))
            
            # Create candidate solution
            candidate_points = current_points.copy()
            
            # Dynamic phase transition
            if stagnation_counter < max_stagnation and current_min_area < 0.03:
                # High exploration phase
                noise_mag = base_noise * (1.0 - (current_min_area / 0.0365) ** 0.3)
                use_gradients = True
            else:
                # Fine-tuning phase
                noise_mag = base_noise * 0.15 * (1.0 - (current_min_area / 0.0365) ** 0.3)
                use_gradients = True  # Always use gradients in fine-tuning
            
            # Apply perturbations
            if random.random() < bottleneck_prob and use_gradients:
                # Apply gradient-based displacement for bottleneck triangles
                step_length = noise_mag * 2.0  # Scale step length with noise magnitude
                
                for i in range(len(candidate_points)):
                    if np.linalg.norm(bottleneck_displacement[i]) > 1e-10:
                        # Scale displacement by step length
                        move_vector = bottleneck_displacement[i] * step_length
                        
                        # Binary search for maximum valid step (maintain triangle containment)
                        low, high = 0.0, 1.0
                        for _ in range(10):
                            mid = (low + high) / 2
                            test_point = current_points[i] + mid * move_vector
                            if is_inside_triangle(test_point, A, B, C):
                                low = mid
                            else:
                                high = mid
                        
                        candidate_points[i] = current_points[i] + low * move_vector
            else:
                # Random perturbation (fallback)
                idx_to_perturb = [random.randint(0, 10)]
                for idx in idx_to_perturb:
                    p = candidate_points[idx]
                    u, v, w = cartesian_to_barycentric(p, A, B, C)
                    
                    # Apply Gaussian perturbation
                    du = random.gauss(0, noise_mag)
                    dv = random.gauss(0, noise_mag)
                    u_new, v_new = u + du, v + dv
                    w_new = 1.0 - u_new - v_new
                    
                    # Project to simplex
                    if u_new < 0 or v_new < 0 or w_new < 0:
                        coords = np.array([u_new, v_new, w_new])
                        coords = np.maximum(coords, 0)
                        total = coords.sum()
                        if total > 0:
                            coords /= total
                        else:
                            coords = np.array([1/3, 1/3, 1/3])
                        u_new, v_new, w_new = coords
                    
                    # Convert back to Cartesian
                    candidate_points[idx] = u_new * A + v_new * B + w_new * C
            
            # Evaluate candidate
            candidate_min_area = get_smallest_triangle_area(candidate_points)
            
            # Track improvement for dynamic phase transition
            if candidate_min_area > current_min_area * (1 + improvement_threshold):
                stagnation_counter = 0
            else:
                stagnation_counter += 1
            
            # Simulated annealing acceptance
            delta = candidate_min_area - current_min_area
            if delta > 0 or random.random() < math.exp(delta / current_temp):
                current_points = candidate_points
                current_min_area = candidate_min_area
                if candidate_min_area > best_min_area:
                    best_points = candidate_points.copy()
                    best_min_area = candidate_min_area
            
            # Adjusted cooling schedule
            adaptive_cooling = 0.98 + 0.015 * (1.0 - current_min_area / 0.0365)
            current_temp *= adaptive_cooling
        
        return best_points

    def opponent_improve_strategy(points):
        """Mimic the most effective opponent's improvement strategy to test resistance."""
        A, B, C = get_unit_triangle()
        
        def compute_triangle_area(a, b, c):
            return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
        
        n_points = 11
        max_rounds = 500
        initial_min_area = get_smallest_triangle_area(points)
        initial_temp = 0.5 * initial_min_area
        cooling_rate = 0.995
        
        best_found = points.copy()
        best_score = initial_min_area
        current = points.copy()
        current_score = best_score
        temperature = initial_temp
        
        # Track rounds without improvement for restarts
        rounds_without_improvement = 0
        max_stagnation_rounds = 100

        for round_idx in range(max_rounds):
            # Focus ONLY on the absolute worst triangles (top 5 smallest)
            n = len(current)
            triangles = []
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area = compute_triangle_area(current[i], current[j], current[k])
                        triangles.append((area, i, j, k))
            
            # Sort by area and take only top 5 smallest triangles
            triangles.sort(key=lambda x: x[0])
            relevant_triangles = triangles[:5]  # Focus on absolute worst
            
            # Initialize displacement for each point with weights
            displacement = np.zeros((n, 2))
            point_weight = np.zeros(n)

            for (area, i, j, k) in relevant_triangles:
                a, b, c = current[i], current[j], current[k]
                f = (b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1])
                sign = 1 if f >= 0 else -1

                dir_a = np.array([b[1]-c[1], c[0]-b[0]]) * sign
                dir_b = np.array([c[1]-a[1], a[0]-c[0]]) * sign
                dir_c = np.array([a[1]-b[1], b[0]-a[0]]) * sign

                # Use sqrt-stabilized weighting
                weight = 1.0 / np.sqrt(area - triangles[0][0] + 1e-4)
                displacement[i] += weight * dir_a
                displacement[j] += weight * dir_b
                displacement[k] += weight * dir_c
                
                point_weight[i] += weight
                point_weight[j] += weight
                point_weight[k] += weight

            # Apply displacements
            candidate = current.copy()
            step_length = 0.1 * current_score

            for i in range(n):
                if point_weight[i] > 1e-10:
                    # Scale by weight and current score
                    move_vector = displacement[i] * (step_length / point_weight[i])
                    
                    # Binary search for maximum valid step
                    low, high = 0.0, 1.0
                    for _ in range(10):
                        mid = (low + high) / 2
                        test_point = current[i] + mid * move_vector
                        if is_inside_triangle(test_point, A, B, C):
                            low = mid
                        else:
                            high = mid
                    
                    candidate[i] = current[i] + low * move_vector

            # Evaluate candidate
            new_score = get_smallest_triangle_area(candidate)

            # Acceptance criterion
            delta = new_score - current_score
            if delta > 0 or (temperature > 1e-8 and random.random() < math.exp(delta / temperature)):
                current = candidate
                current_score = new_score
                
                if new_score > best_score:
                    best_score = new_score
                    best_found = candidate
                    rounds_without_improvement = 0
                else:
                    rounds_without_improvement += 1
            else:
                rounds_without_improvement += 1

            # Stagnation handling
            if rounds_without_improvement >= max_stagnation_rounds:
                # Perturb best_found
                perturbed = best_found.copy()
                for i in range(n):
                    if random.random() < 0.3:
                        angle = random.random() * 2 * math.pi
                        radius = 0.05 * initial_min_area
                        dx = radius * math.cos(angle)
                        dy = radius * math.sin(angle)
                        test_point = best_found[i] + np.array([dx, dy])
                        if is_inside_triangle(test_point, A, B, C):
                            perturbed[i] = test_point
                
                current = perturbed
                current_score = get_smallest_triangle_area(current)
                temperature = initial_temp
                rounds_without_improvement = 0

            # Cooling
            temperature *= cooling_rate

        return best_found

    def is_resistant_to_opponent(points, opponent_improve, num_tests=5):
        """Test if configuration resists the specific opponent improvement strategy."""
        current_min_area = get_smallest_triangle_area(points)
        
        # Apply opponent's improvement strategy
        improved_points = opponent_improve(points)
        improved_min_area = get_smallest_triangle_area(improved_points)
        
        # If opponent can improve, we're not resistant
        if improved_min_area > current_min_area:
            return False, improved_points
        
        # Additional tests with small perturbations
        for _ in range(num_tests-1):
            candidate = points.copy()
            for i in range(len(candidate)):
                p = candidate[i]
                u, v, w = cartesian_to_barycentric(p, A, B, C)
                du = random.gauss(0, 0.005)
                dv = random.gauss(0, 0.005)
                u_new, v_new = u + du, v + dv
                w_new = 1.0 - u_new - v_new
                if u_new < 0 or v_new < 0 or w_new < 0:
                    coords = np.array([u_new, v_new, w_new])
                    coords = np.maximum(coords, 0)
                    total = coords.sum()
                    if total > 0:
                        coords /= total
                    else:
                        coords = np.array([1/3, 1/3, 1/3])
                    u_new, v_new, w_new = coords
                candidate[i] = u_new * A + v_new * B + w_new * C
            
            improved_points = opponent_improve(candidate)
            improved_min_area = get_smallest_triangle_area(improved_points)
            if improved_min_area > current_min_area:
                return False, improved_points
        
        return True, points

    best_min_area = -1
    best_points = None

    # Run with diversified restarts using 6 initialization methods
    for restart in range(100):
        method = restart % 6  # Now using 6 methods
        points = generate_initial_configuration(method)
        points = simulated_annealing(points)
        min_area = get_smallest_triangle_area(points)
        
        if min_area > best_min_area:
            best_min_area = min_area
            best_points = points

    # Verify resistance to opponent's specific improvement strategy
    opponent_strategy = opponent_improve_strategy

    # ENHANCED remediation with opponent-aware optimization
    for _ in range(5):  # More remediation rounds
        resistant, candidate = is_resistant_to_opponent(best_points, opponent_strategy)
        if resistant:
            break
        
        # If not resistant, use the improved version from opponent as starting point for further optimization
        points = simulated_annealing(
            candidate,
            max_iter=1000,  # Increased iterations
            initial_temp=0.005,  # Slightly higher temperature
            base_noise=0.015  # Significantly higher noise
        )
        min_area = get_smallest_triangle_area(points)
        if min_area > best_min_area:
            best_min_area = min_area
            best_points = points

    return best_points