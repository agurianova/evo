from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import math


def entrypoint():
    """Return an improve(points) -> improved_points callable with advanced optimization."""
    A, B, C = get_unit_triangle()
    
    # Calculate triangle side length for parameter scaling
    triangle_side = np.linalg.norm(B - A)
    
    def project_to_triangle(point):
        """Project a point outside the triangle back to the nearest boundary point."""
        if is_inside_triangle(point, A, B, C):
            return point
            
        # Helper function to project to a line segment
        def project_to_segment(p, v1, v2):
            edge = v2 - v1
            edge_len_sq = np.dot(edge, edge)
            if edge_len_sq == 0:
                return v1
            t = max(0, min(1, np.dot(p - v1, edge) / edge_len_sq))
            return v1 + t * edge
            
        # Project to each edge
        proj_AB = project_to_segment(point, A, B)
        proj_AC = project_to_segment(point, A, C)
        proj_BC = project_to_segment(point, B, C)
        
        # Find closest projection
        dists = [
            np.linalg.norm(point - proj_AB),
            np.linalg.norm(point - proj_AC),
            np.linalg.norm(point - proj_BC)
        ]
        
        if dists[0] <= dists[1] and dists[0] <= dists[2]:
            return proj_AB
        elif dists[1] <= dists[0] and dists[1] <= dists[2]:
            return proj_AC
        else:
            return proj_BC
    
    def resolve_duplicates(point_idx, candidate, min_dist=1e-5):
        """Resolve duplicates by moving point away from nearest neighbor, with validation."""
        original_candidate = candidate.copy()
        original_score = get_smallest_triangle_area(candidate)
        
        closest_idx = -1
        min_dist_found = float('inf')
        
        for j in range(11):
            if j == point_idx:
                continue
            dist = np.linalg.norm(candidate[point_idx] - candidate[j])
            if dist < min_dist_found:
                min_dist_found = dist
                closest_idx = j
        
        if min_dist_found < min_dist and closest_idx != -1:
            # Move away from the closest point
            direction = candidate[point_idx] - candidate[closest_idx]
            if np.linalg.norm(direction) > 0:
                direction = direction / np.linalg.norm(direction)
                candidate[point_idx] += direction * (min_dist - min_dist_found)
            
        # Validate that resolution didn't degrade min_area
        if get_smallest_triangle_area(candidate) < original_score:
            return original_candidate
        
        return candidate

    def get_all_minimal_triangles(points, tolerance=1e-5):
        """Get indices of all triangles within tolerance of the smallest area and point frequencies."""
        n = len(points)
        min_area = float('inf')
        all_indices = []
        
        # First pass: find the minimum area
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    x1, y1 = points[i]
                    x2, y2 = points[j]
                    x3, y3 = points[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    
                    if area < min_area:
                        min_area = area
        
        # Second pass: collect all triangles within tolerance
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    x1, y1 = points[i]
                    x2, y2 = points[j]
                    x3, y3 = points[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    
                    if abs(area - min_area) < tolerance:
                        all_indices.append((i, j, k))
        
        # Calculate point frequencies in minimal triangles
        point_freq = np.zeros(n, dtype=int)
        for tri in all_indices:
            for idx in tri:
                point_freq[idx] += 1
        
        return all_indices, min_area, point_freq
    
    def improve(points: np.ndarray) -> np.ndarray:
        # Set seed based on configuration for deterministic but diverse search
        config_hash = hash(tuple(map(tuple, points)))
        np.random.seed(config_hash % (2**32 - 1))
        
        # Make a copy to avoid modifying the input
        points = points.copy()
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Simulated annealing parameters - scaled to triangle dimensions
        initial_temp = 0.05  # Increased from 0.01 to 0.05 based on problem scale
        temp = initial_temp
        cooling_rate = 0.995
        max_iterations = 1000
        no_improve_limit = 200  # Early stopping if no improvement
        
        # Adaptive step size parameters - scaled to triangle side length
        base_step_size = 0.03  # Reduced from 0.05 to 0.03 (2% of side length ~1.52)
        step_size = base_step_size
        acceptance_window = 50
        acceptance_history = []
        
        # Stagnation tracking for adaptive temperature
        stagnation_count = 0
        stagnation_threshold = 50
        
        no_improve_count = 0
        current = best.copy()
        current_score = best_score
        
        for i in range(max_iterations):
            # Track acceptance rate for step size adaptation
            if i > 0 and i % acceptance_window == 0:
                acceptance_rate = sum(acceptance_history) / len(acceptance_history)
                acceptance_history = []
                
                # Adapt step size based on acceptance rate
                if acceptance_rate > 0.4:
                    step_size = min(step_size * 1.2, base_step_size * 2)
                elif acceptance_rate < 0.2:
                    step_size = max(step_size * 0.8, base_step_size * 0.1)

            # Linear step size decay
            current_step_size = step_size * (1 - i / max_iterations)
            
            # 80% chance to perturb points involved in smallest triangles
            if np.random.random() < 0.8:
                # Find ALL triangles near the minimum area
                min_triangles, _, point_freq = get_all_minimal_triangles(current)
                
                if min_triangles:
                    # Use frequency-weighted selection of critical points
                    freq_sum = np.sum(point_freq)
                    if freq_sum > 0:
                        point_probs = point_freq / freq_sum
                        # Only consider points that appear in minimal triangles
                        valid_indices = np.where(point_freq > 0)[0]
                        valid_probs = point_probs[valid_indices]
                        valid_probs = valid_probs / np.sum(valid_probs)
                        
                        # Select one or two critical points based on frequency
                        if np.random.random() < 0.7:
                            # Select one point with probability proportional to frequency
                            idx = np.random.choice(valid_indices, p=valid_probs)
                            perturb_two = False
                        else:
                            # Select two distinct points with probability proportional to frequency
                            idx1 = np.random.choice(valid_indices, p=valid_probs)
                            # Remove selected index from options for second point
                            mask = valid_indices != idx1
                            if np.any(mask):
                                idx2 = np.random.choice(valid_indices[mask], p=valid_probs[mask]/np.sum(valid_probs[mask]))
                                perturb_two = True
                            else:
                                idx = idx1
                                perturb_two = False
                    else:
                        # Fallback to random point if frequency sum is zero
                        idx = np.random.randint(0, 11)
                        perturb_two = False
                else:
                    # Fallback to random point
                    idx = np.random.randint(0, 11)
                    perturb_two = False
            else:
                idx = np.random.randint(0, 11)
                perturb_two = False

            # Generate perturbation in a random direction
            angle = np.random.uniform(0, 2 * np.pi)
            radius = np.random.uniform(0, current_step_size)
            perturbation = np.array([radius * np.cos(angle), radius * np.sin(angle)])
            
            candidate = current.copy()
            
            # Apply perturbation to one or two points
            if perturb_two:
                candidate[idx1] += perturbation
                # Second point gets a different perturbation
                angle2 = np.random.uniform(0, 2 * np.pi)
                perturbation2 = np.array([
                    current_step_size * 0.5 * np.cos(angle2),
                    current_step_size * 0.5 * np.sin(angle2)
                ])
                candidate[idx2] += perturbation2
            else:
                candidate[idx] += perturbation

            # Project points to triangle if outside
            for j in range(11):
                candidate[j] = project_to_triangle(candidate[j])

            # Resolve duplicates with validation
            for j in range(11):
                candidate = resolve_duplicates(j, candidate)

            # Check if we're still inside triangle (should be, but double-check)
            if not is_inside_triangle(candidate, A, B, C):
                acceptance_history.append(0)
                no_improve_count += 1
                continue

            score = get_smallest_triangle_area(candidate)
            delta_score = score - current_score

            # Track acceptance for adaptation
            accepted = False

            # Always accept improvements
            if score > current_score:
                current, current_score = candidate.copy(), score
                no_improve_count = 0
                stagnation_count = 0
                accepted = True
                
                # Update best if better
                if score > best_score:
                    best, best_score = candidate.copy(), score
            else:
                # Accept worse solutions with probability based on temperature
                acceptance_prob = math.exp(delta_score / temp)
                
                if np.random.random() < acceptance_prob:
                    current, current_score = candidate.copy(), score
                    no_improve_count = 0
                    stagnation_count = 0
                    accepted = True
                else:
                    no_improve_count += 1
                    stagnation_count += 1

            # Record acceptance for step size adaptation
            acceptance_history.append(1 if accepted else 0)

            # Adaptive temperature: increase when stuck in deep local optima
            if stagnation_count >= stagnation_threshold:
                temp = min(temp * 1.1, initial_temp * 2)  # Boost temperature to escape
                stagnation_count = 0

            # Cooling
            temp = max(initial_temp * (cooling_rate ** i), 0.001)  # Prevent temp from getting too low
            
            # Early stopping - only count SA rejections (not duplicate handling)
            if no_improve_count > no_improve_limit:
                break
        
        return best

    return improve