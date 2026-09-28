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

    def get_min_triangle_indices(points, top_k=5):
        n = len(points)
        triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = points[i], points[j], points[k]
                    area_val = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                    triangles.append((area_val, i, j, k))
        
        triangles.sort(key=lambda x: x[0])
        top_triangles = triangles[:top_k]
        
        # Count how many small triangles each point is involved in
        point_frequency = [0] * n
        for _, i, j, k in top_triangles:
            point_frequency[i] += 1
            point_frequency[j] += 1
            point_frequency[k] += 1
            
        return top_triangles, point_frequency

    def generate_initial_configuration(method):
        n = 11
        # Compute optimal step for triangular lattice density (parameterized by triangle area)
        step = math.sqrt(2 * 1.0 / (n * math.sqrt(3)))
        
        if method == 0:  # Original lattice with density-matched step
            points_bary = []
            for i in range(4):
                u = i * step
                if u > 1.0:
                    break
                for j in range(4):
                    v = j * step
                    if u + v > 1.0:
                        break
                    w = 1.0 - u - v
                    points_bary.append((u, v, w))
            
            # Add 11th point at asymmetric location
            points_bary.append((0.5, 0.3, 0.2))
            
        elif method == 1:  # Symmetric lattice with proper handling
            points_bary = []
            step_sym = 0.25
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
                    # Add symmetric variants
                    symmetric_points.append((u, v, w))
                    if u != v and u != w and v != w:
                        symmetric_points.append((v, u, w))
                        symmetric_points.append((w, v, u))
                        symmetric_points.append((u, w, v))
                        symmetric_points.append((v, w, u))
                        symmetric_points.append((w, u, v))

            # Trim to exactly 11 unique points with higher precision
            unique_points = set()
            for point in symmetric_points:
                # Round to higher precision to preserve near-symmetry
                rounded = (round(point[0], 10), round(point[1], 10), round(point[2], 10))
                unique_points.add(rounded)
                
            points_bary = list(unique_points)[:11]
            
        elif method == 2:  # Random asymmetric 11th point
            points_bary = []
            for i in range(4):
                u = i * step
                if u > 1.0:
                    break
                for j in range(4):
                    v = j * step
                    if u + v > 1.0:
                        break
                    w = 1.0 - u - v
                    points_bary.append((u, v, w))
            
            # Add random 11th point
            u_rand = random.uniform(0.1, 0.6)
            v_rand = random.uniform(0.1, 0.6)
            w_rand = 1.0 - u_rand - v_rand
            if w_rand < 0:
                w_rand = 0
                total = u_rand + v_rand
                u_rand /= total
                v_rand /= total
            points_bary.append((u_rand, v_rand, w_rand))

        elif method == 3:  # Hexagonal lattice with strategic point removal (BROKEN - REVERSED)
            points_bary = []
            # Create denser hexagonal grid
            for i in range(5):
                for j in range(5):
                    u = i * 0.2
                    v = j * 0.2
                    if u + v > 1.0:
                        continue
                    w = 1.0 - u - v
                    if w >= 0:
                        points_bary.append((u, v, w))
            
            # REVERSED STRATEGY: Keep boundary points, remove interior points first
            boundary_points = []
            interior_points = []
            for p in points_bary:
                # Boundary points have at least one coordinate < 0.1
                if min(p[0], p[1], p[2]) < 0.1:
                    boundary_points.append(p)
                else:
                    interior_points.append(p)
            
            # Keep all boundary points first
            points_bary = boundary_points[:11]
            if len(points_bary) < 11:
                # Then add interior points as needed
                points_bary.extend(interior_points[:11-len(points_bary)])

        else:  # New method: Boundary-focused strategic placement (method 4)
            points_bary = []
            # 3 vertex points
            points_bary.append((1.0, 0.0, 0.0))
            points_bary.append((0.0, 1.0, 0.0))
            points_bary.append((0.0, 0.0, 1.0))
            
            # 4 edge points (1/3 and 2/3 along each edge)
            points_bary.append((0.666, 0.333, 0.0))
            points_bary.append((0.333, 0.666, 0.0))
            points_bary.append((0.0, 0.666, 0.333))
            points_bary.append((0.0, 0.333, 0.666))
            points_bary.append((0.666, 0.0, 0.333))
            points_bary.append((0.333, 0.0, 0.666))
            
            # 2 interior points optimized for min triangle area
            points_bary.append((0.3, 0.3, 0.4))
            points_bary.append((0.4, 0.3, 0.3))

        # Convert to Cartesian with symmetry-preserving perturbation
        points_cart = []
        for (u, v, w) in points_bary:
            # Apply smaller perturbation in barycentric space
            du = random.gauss(0, 0.01)
            dv = random.gauss(0, 0.01)
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

    def simulated_annealing(points, max_iter=1000, initial_temp=0.005, base_noise=0.05):
        current_points = points.copy()
        current_min_area = get_smallest_triangle_area(current_points)
        best_points = current_points.copy()
        best_min_area = current_min_area
        current_temp = initial_temp

        # Phase-based noise scheduling
        exploration_phase = max_iter // 2

        for iter in range(max_iter):
            # Improved bottleneck targeting with multi-triangle awareness
            _, point_frequency = get_min_triangle_indices(current_points, top_k=5)
            
            # Calculate probability of perturbing each point based on frequency in small triangles
            total_freq = sum(point_frequency)
            if total_freq > 0:
                point_probs = [freq / total_freq for freq in point_frequency]
            else:
                point_probs = [1.0/len(point_frequency)] * len(point_frequency)
            
            # Determine move type: adaptive probability for bottleneck moves
            if random.random() < 0.8:  # Higher probability for bottleneck moves
                # Select points based on their involvement in small triangles
                idx_to_perturb = []
                # Select up to 3 points with highest frequency
                for _ in range(min(3, len(points))):
                    idx = np.random.choice(len(points), p=point_probs)
                    if idx not in idx_to_perturb:
                        idx_to_perturb.append(idx)
            else:
                # Single random point move
                idx_to_perturb = [random.randint(0, 10)]

            # Create candidate solution
            candidate_points = current_points.copy()
            
            # Phase-based noise magnitude with slower decay
            if iter < exploration_phase:
                # High variance during exploration phase
                noise_mag = 0.05
            else:
                # Low variance during exploitation phase
                noise_mag = 0.01

            # Slower noise decay with exponent 0.2 instead of 0.5
            noise_mag = noise_mag * (1.0 - (current_min_area / 0.0365) ** 0.2)
            noise_mag = max(0.001, min(0.05, noise_mag))

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
            
            # Simulated annealing acceptance
            delta = candidate_min_area - current_min_area
            if delta > 0 or random.random() < math.exp(delta / current_temp):
                current_points = candidate_points
                current_min_area = candidate_min_area
                if candidate_min_area > best_min_area:
                    best_points = candidate_points.copy()
                    best_min_area = candidate_min_area

            # Adaptive cooling schedule inversely proportional to progress
            adaptive_cooling = 0.95 + 0.045 * (current_min_area / 0.0365)
            current_temp *= adaptive_cooling

        return best_points

    best_min_area = -1
    best_points = None

    # Run with diversified restarts using 5 initialization methods
    for restart in range(100):
        method = restart % 5  # Now using 5 methods
        points = generate_initial_configuration(method)
        points = simulated_annealing(points)
        min_area = get_smallest_triangle_area(points)
        
        if min_area > best_min_area:
            best_min_area = min_area
            best_points = points

    # Enhanced resistance verification that specifically targets known attack patterns
    def is_resistant(points, num_tests=50, noise_mag=0.005):
        current_min_area = get_smallest_triangle_area(points)
        for _ in range(num_tests):
            candidate = points.copy()
            
            # Target top 5 smallest triangles like the most effective Improver
            top_triangles, _ = get_min_triangle_indices(candidate, top_k=5)
            
            # Calculate weighted displacement for points in small triangles
            displacement = np.zeros((11, 2))
            point_weight = np.zeros(11)

            for (area, i, j, k) in top_triangles:
                a, b, c = candidate[i], candidate[j], candidate[k]
                f = (b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1])
                sign = 1 if f >= 0 else -1

                dir_a = np.array([b[1]-c[1], c[0]-b[0]]) * sign
                dir_b = np.array([c[1]-a[1], a[0]-c[0]]) * sign
                dir_c = np.array([a[1]-b[1], b[0]-a[0]]) * sign

                # Use stabilized weighting
                weight = 1.0 / np.sqrt(area - top_triangles[0][0] + 1e-4)
                displacement[i] += weight * dir_a
                displacement[j] += weight * dir_b
                displacement[k] += weight * dir_c
                
                point_weight[i] += weight
                point_weight[j] += weight
                point_weight[k] += weight

            # Apply displacements with binary search to stay within triangle
            step_length = 0.05 * current_min_area
            for i in range(11):
                if point_weight[i] > 1e-10:
                    move_vector = displacement[i] * (step_length / point_weight[i])
                    
                    # Binary search for maximum valid step
                    low, high = 0.0, 1.0
                    for _ in range(10):
                        mid = (low + high) / 2
                        test_point = candidate[i] + mid * move_vector
                        if is_inside_triangle(test_point, A, B, C):
                            low = mid
                        else:
                            high = mid
                    
                    candidate[i] = candidate[i] + low * move_vector

            candidate_min_area = get_smallest_triangle_area(candidate)
            if candidate_min_area > current_min_area:
                return False
        return True

    # Enhanced remediation with strength scaled by resistance
    for _ in range(5):
        if is_resistant(best_points):
            break
        # Use stronger parameters when resistance is low
        best_points = simulated_annealing(
            best_points,
            max_iter=2000,  # Increased from 500
            initial_temp=0.01,  # Increased from 0.003
            base_noise=0.02  # Increased from 0.005
        )

    return best_points