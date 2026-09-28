import random
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    base_seed = 42
    n_chains = 30
    best_points = None
    best_min_area = -1

    # Track performance of initialization methods for adaptive weighting
    init_success = [0.0, 0.0, 0.0]  # literature, heuristic, random
    init_counts = [1, 1, 1]  # Avoid division by zero
    alpha = 0.2  # EMA smoothing factor

    def random_initialization(n=11):
        points = []
        max_attempts = 1000
        for i in range(n):
            attempt = 0
            while attempt < max_attempts:
                u = random.random()
                v = random.random()
                if u + v > 1:
                    u = 1 - u
                    v = 1 - v
                x = A[0] + u * (B[0] - A[0]) + v * (C[0] - A[0])
                y = A[1] + u * (B[1] - A[1]) + v * (C[1] - A[1])
                p = np.array([x, y])
                
                if any(np.linalg.norm(p - q) < 1e-5 for q in points):
                    attempt += 1
                    continue
                    
                if i >= 2:
                    collinear = False
                    for j in range(i):
                        for k in range(j+1, i):
                            area = 0.5 * abs(
                                points[j][0]*(points[k][1]-p[1]) + 
                                points[k][0]*(p[1]-points[j][1]) + 
                                p[0]*(points[j][1]-points[k][1])
                            )
                            if area < 1e-5:
                                collinear = True
                                break
                        if collinear:
                            break
                    if collinear:
                        attempt += 1
                        continue
                
                points.append(p)
                break
            
            if attempt == max_attempts and len(points) < n:
                last = points[-1]
                dx = random.uniform(-0.01, 0.01)
                dy = random.uniform(-0.01, 0.01)
                p = last + np.array([dx, dy])
                if is_inside_triangle(p, A, B, C) and not any(np.linalg.norm(p - q) < 1e-5 for q in points):
                    points.append(p)
        return np.array(points)
    
    def project_to_boundary(point, A, B, C):
        """Project a point outside the triangle to the nearest point on the boundary"""
        # If already inside, return as is
        if is_inside_triangle(point, A, B, C):
            return point
        
        # Calculate distances to each edge and find the closest point
        def point_to_line_dist(p, a, b):
            # Vector AB
            ab = b - a
            # Vector AP
            ap = p - a
            # Length of AB
            ab_length = np.linalg.norm(ab)
            if ab_length < 1e-10:  # Avoid division by zero
                return a, np.linalg.norm(p - a)
            # Unit vector in direction of AB
            ab_unit = ab / ab_length
            # Projection of AP onto AB
            proj = np.dot(ap, ab_unit)
            # Clamp projection to [0, ab_length]
            proj = max(0, min(ab_length, proj))
            # Nearest point on line
            nearest = a + proj * ab_unit
            return nearest, np.linalg.norm(p - nearest)
        
        # Check all three edges
        nearest_ab, dist_ab = point_to_line_dist(point, A, B)
        nearest_bc, dist_bc = point_to_line_dist(point, B, C)
        nearest_ca, dist_ca = point_to_line_dist(point, C, A)
        
        # Find the closest boundary point
        if dist_ab <= dist_bc and dist_ab <= dist_ca:
            return nearest_ab
        elif dist_bc <= dist_ab and dist_bc <= dist_ca:
            return nearest_bc
        else:
            return nearest_ca

    def literature_initialization(n=11):
        """Create a configuration based on balanced Heilbronn patterns for 11 points"""
        points = []
        
        # Points along edges using balanced 3-3-3 distribution
        # Base edge (A-B)
        points.append(0.2 * A + 0.8 * B)
        points.append(0.5 * A + 0.5 * B)
        points.append(0.8 * A + 0.2 * B)
        
        # Left edge (A-C)
        points.append(0.2 * A + 0.8 * C)
        points.append(0.5 * A + 0.5 * C)
        points.append(0.8 * A + 0.2 * C)
        
        # Right edge (B-C)
        points.append(0.2 * B + 0.8 * C)
        points.append(0.5 * B + 0.5 * C)
        points.append(0.8 * B + 0.2 * C)
        
        # Two strategic interior points using median blending
        # First interior point: golden ratio along median from A
        median_point1 = (B + C) / 2
        strategic_point1 = A + 0.618 * (median_point1 - A)
        
        # Second interior point: golden ratio along median from B
        median_point2 = (A + C) / 2
        strategic_point2 = B + 0.618 * (median_point2 - A)
        
        # Blend the two interior points to create optimal placement
        strategic_point = 0.5 * strategic_point1 + 0.5 * strategic_point2
        points.append(strategic_point)
        
        # Add controlled perturbations to all points
        perturbed_points = []
        for i, p in enumerate(points[:n]):
            # Determine if point is on boundary
            is_boundary = (i < 9)  # First 9 points are on boundary
            
            if is_boundary:
                max_perturb = 0.025  # Standard perturbation for boundary
            else:
                max_perturb = 0.015  # Standard perturbation for interior
            
            dx = random.uniform(-max_perturb, max_perturb)
            dy = random.uniform(-max_perturb, max_perturb)
            candidate = p + np.array([dx, dy])
            
            # Project to boundary if needed
            candidate = project_to_boundary(candidate, A, B, C)
            
            perturbed_points.append(candidate)
        
        return np.array(perturbed_points)

    def heuristic_initialization(n=11):
        points = literature_initialization(n-1)
        center = np.array([(A[0]+B[0]+C[0])/3, (A[1]+B[1]+C[1])/3])
        new_point = center
        attempt = 0
        while attempt < 100:
            dx = random.uniform(-0.015, 0.015)  # Smaller perturbations
            dy = random.uniform(-0.015, 0.015)
            candidate = center + np.array([dx, dy])
            
            # Project to boundary if needed
            candidate = project_to_boundary(candidate, A, B, C)
            
            if any(np.linalg.norm(candidate - p) < 1e-5 for p in points):
                attempt += 1
                continue

            collinear = False
            for i in range(len(points)):
                for j in range(i+1, len(points)):
                    area = 0.5 * abs(
                        points[i][0]*(points[j][1]-candidate[1]) + 
                        points[j][0]*(candidate[1]-points[i][1]) + 
                        candidate[0]*(points[i][1]-points[j][1])
                    )
                    if area < 1e-5:
                        collinear = True
                        break
                if collinear:
                    break
            
            if not collinear:
                new_point = candidate
                break
            attempt += 1
        
        if attempt == 100:
            new_point = random_initialization(1)[0]
        
        return np.vstack([points, new_point])

    def get_min_triangle_area_with_indices(points):
        n = len(points)
        min_area = float('inf')
        min_indices = None
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        points[i,0]*(points[j,1]-points[k,1]) + 
                        points[j,0]*(points[k,1]-points[i,1]) + 
                        points[k,0]*(points[i,1]-points[j,1])
                    )
                    if area < min_area:
                        min_area = area
                        min_indices = (i, j, k)
        return min_area, min_indices

    # Adaptive strategy weights based on historical success
    strategy_weights = [0.5, 0.3, 0.2]  # literature, heuristic, random

    # Track recent improvement for adaptive parameters
    recent_improvements = []
    max_improvement_history = 100
    
    for chain in range(n_chains):
        random.seed(base_seed + chain)
        np.random.seed(base_seed + chain)

        # Update strategy weights based on historical performance
        total_success = sum([init_success[i] / init_counts[i] for i in range(3)])
        if total_success > 0:
            strategy_weights = [init_success[i] / (init_counts[i] * total_success) for i in range(3)]
        else:
            strategy_weights = [0.5, 0.3, 0.2]  # Default if no data

        # Weighted selection of initialization method
        init_type = random.choices([0, 1, 2], weights=strategy_weights, k=1)[0]
        
        if init_type == 0:
            points = literature_initialization()
        elif init_type == 1:
            points = heuristic_initialization()
        else:
            points = random_initialization()

        if not is_inside_triangle(points, A, B, C):
            points = literature_initialization()

        current_points = points
        best_chain_points = current_points.copy()
        best_chain_min_area = get_smallest_triangle_area(current_points)

        # Initialize adaptive parameters
        initial_T = 0.1
        n_iter = 10000
        base_step = 0.03
        no_improve_count = 0
        max_no_improve = 1000
        
        # Adaptive cooling rate controller
        current_cooling_rate = 0.999
        target_acceptance_rate = 0.5
        acceptance_rate_window = 100
        recent_acceptances = []

        # Track improvement rate for adaptive parameters
        improvement_rate = 0.0
        improvement_window = 50
        recent_improvements = []

        for iter in range(n_iter):
            current_min_area, min_indices = get_min_triangle_area_with_indices(current_points)
            
            # Update improvement rate tracking
            if iter > 0:
                recent_improvements.append(current_min_area - prev_min_area)
                if len(recent_improvements) > improvement_window:
                    recent_improvements.pop(0)
                improvement_rate = np.mean(recent_improvements) if recent_improvements else 0.0
            prev_min_area = current_min_area

            # Adaptive multi-point perturbation
            # Simplified decay exponent based only on iteration progress
            decay_exponent = 0.3 * (1 - iter/n_iter)**0.5
            decay_exponent = max(0.15, min(0.45, decay_exponent))
            
            multi_point_prob = 0.7 * (1 - iter/n_iter)**decay_exponent
            num_points_to_perturb = 1
            if random.random() < multi_point_prob:
                num_points_to_perturb = random.randint(2, min(3, len(min_indices)))
            
            # 25% base chance of global perturbation (increased from 15%)
            base_global_prob = 0.25
            global_perturb_prob = max(0.1, min(0.4, base_global_prob + 0.05 * improvement_rate))
            
            if random.random() < global_perturb_prob:
                points_to_perturb = [random.randint(0, 10)]
            else:
                # Select points to perturb from the smallest triangle
                points_to_perturb = random.sample(min_indices, num_points_to_perturb)
            
            # Calculate adaptive step size - based on iteration count
            base_step_size = 0.03
            step_size = base_step_size * (1 - iter/n_iter)**decay_exponent
            step_size = max(0.005, min(step_size, 0.05))
            
            # Boundary relaxation with soft constraints
            boundary_tolerance = 0.01 * np.exp(-0.001 * iter)
            
            # Create candidate configuration with perturbed points
            candidate_points = current_points.copy()
            valid_candidate = True
            
            for idx in points_to_perturb:
                dx = random.uniform(-step_size, step_size)
                dy = random.uniform(-step_size, step_size)
                new_point = current_points[idx] + np.array([dx, dy])
                
                # Boundary relaxation with soft constraints
                if not is_inside_triangle(new_point, A, B, C):
                    # Allow temporary boundary violations with controlled tolerance
                    dist_to_boundary = np.linalg.norm(new_point - project_to_boundary(new_point, A, B, C))
                    if dist_to_boundary > boundary_tolerance:
                        new_point = project_to_boundary(new_point, A, B, C)
                
                # Check distinctness
                if any(np.linalg.norm(new_point - p) < 1e-5 for i, p in enumerate(candidate_points) if i != idx):
                    valid_candidate = False
                    break
                
                candidate_points[idx] = new_point
            
            if not valid_candidate:
                continue
                
            # Check collinearity only for relevant triangles
            collinear = False
            for idx in points_to_perturb:
                for i in range(len(candidate_points)):
                    if i == idx:
                        continue
                    for j in range(i+1, len(candidate_points)):
                        if j == idx:
                            continue
                        area = 0.5 * abs(
                            candidate_points[i,0]*(candidate_points[j,1]-candidate_points[idx,1]) + 
                            candidate_points[j,0]*(candidate_points[idx,1]-candidate_points[i,1]) + 
                            candidate_points[idx,0]*(candidate_points[i,1]-candidate_points[j,1])
                        )
                        if area < 1e-5:
                            collinear = True
                            break
                    if collinear:
                        break
                if collinear:
                    break
            
            if collinear:
                continue
            
            new_min_area = get_smallest_triangle_area(candidate_points)

            # Track acceptance for adaptive cooling
            if new_min_area >= current_min_area:
                recent_acceptances.append(1)
            else:
                recent_acceptances.append(0)
            
            if len(recent_acceptances) > acceptance_rate_window:
                recent_acceptances.pop(0)
            
            # Adaptive cooling rate based on acceptance rate
            if len(recent_acceptances) > 0:
                acceptance_rate = sum(recent_acceptances) / len(recent_acceptances)
                # Adjust cooling rate to target 50% acceptance
                cooling_adjustment = 0.0005 * (acceptance_rate - target_acceptance_rate)
                current_cooling_rate = max(0.995, min(0.9995, 0.999 + cooling_adjustment))

            if new_min_area > best_chain_min_area:
                best_chain_min_area = new_min_area
                best_chain_points = candidate_points.copy()
                no_improve_count = 0
                
                # Update success tracking for this initialization method
                init_success[init_type] += alpha * (new_min_area - init_success[init_type]/init_counts[init_type])
                init_counts[init_type] += 1
            else:
                no_improve_count += 1

            # Reheating mechanism when stuck
            if no_improve_count > max_no_improve:
                T = initial_T
                no_improve_count = 0
            else:
                T = initial_T * (current_cooling_rate ** iter)

            delta = new_min_area - current_min_area
            if delta > 0 or (T > 1e-5 and random.random() < np.exp(delta / T)):
                current_points = candidate_points

        if best_chain_min_area > best_min_area:
            best_min_area = best_chain_min_area
            best_points = best_chain_points.copy()

    return best_points