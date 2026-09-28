from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import hashlib

class TriangleCache:
    def __init__(self, points):
        self.points = points
        self.n = len(points)
        self.min_area = float('inf')
        self.min_triangles = []
        self.areas = np.zeros((self.n, self.n, self.n))
        
        # Precompute all triangle areas
        self._precompute_all()
    
    def _precompute_all(self):
        for i in range(self.n):
            for j in range(i+1, self.n):
                for k in range(j+1, self.n):
                    self._compute_triangle(i, j, k)
    
    def _compute_triangle(self, i, j, k):
        # Calculate area of triangle i,j,k
        area = 0.5 * abs((self.points[j,0]-self.points[i,0])*(self.points[k,1]-self.points[i,1]) - 
                       (self.points[k,0]-self.points[i,0])*(self.points[j,1]-self.points[i,1]))
        
        self.areas[i,j,k] = area
        
        # Track minimum area triangles
        if area < self.min_area - 1e-10:
            self.min_area = area
            self.min_triangles = [(i, j, k)]
        elif abs(area - self.min_area) < 1e-10:
            self.min_triangles.append((i, j, k))
        
        return area
    
    def update_for_point(self, point_idx, new_point):
        """Update cache for a single point movement, only recalculating affected triangles."""
        old_point = self.points[point_idx].copy()
        self.points[point_idx] = new_point
        
        # Reset min area tracking
        old_min_area = self.min_area
        self.min_area = float('inf')
        self.min_triangles = []
        
        # Update all triangles involving the moved point
        for i in range(self.n):
            if i == point_idx:
                continue
            for j in range(i+1, self.n):
                if j == point_idx:
                    continue
                # Order indices to match cache structure
                a, b, c = sorted([i, j, point_idx])
                self._compute_triangle(a, b, c)
        
        # Return whether min area improved
        return self.min_area > old_min_area
    
    def get_min_area(self):
        return self.min_area
    
    def get_bottleneck_triangles(self, threshold):
        """Return triangles within threshold of minimum area."""
        bottleneck = []
        for i, j, k in self.min_triangles:
            if self.areas[i,j,k] - self.min_area < threshold * self.min_area:
                bottleneck.append((i, j, k))
        return bottleneck
    
    def get_bottleneck_points(self, threshold):
        """Return points participating in bottleneck triangles."""
        bottleneck_triangles = self.get_bottleneck_triangles(threshold)
        bottleneck_points = set()
        for i, j, k in bottleneck_triangles:
            bottleneck_points.update([i, j, k])n        return list(bottleneck_points)

def entrypoint():
    """Return an improve(points) -> improved_points callable with bottleneck-focused optimization."""
    A, B, C = get_unit_triangle()
    
    # Constants for the annealing process
    INITIAL_TEMP = 0.015
    COOLING_RATE = 0.97
    MIN_TEMP = 1e-5
    MAX_ITERATIONS = 250
    RESTARTS = 4
    THEORETICAL_MAX_AREA = 0.0365  # Known theoretical maximum for 11 points

    def get_bottleneck_threshold(current_min_area):
        """Adaptive bottleneck threshold inversely proportional to current min_area."""
        base_threshold = 0.05
        # Scale threshold inversely with current_min_area, but with bounds
        scale_factor = min(2.0, max(0.5, THEORETICAL_MAX_AREA / (current_min_area + 1e-8)))
        return base_threshold * scale_factor

    def project_to_triangle(point):
        """Project a point to the nearest point inside the triangle with boundary repulsion."""
        # Convert to barycentric coordinates
        v0 = B - A
        v1 = C - A
        v2 = point - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        if abs(denom) < 1e-10:  # Degenerate triangle, shouldn't happen
            return (A + B + C) / 3
        
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w
        
        # Clamp to triangle
        if u < 0:
            # Project to edge BC
n            total = v + w
            if total > 0:
                v, w = v / total, w / total
            else:
                v, w = 0.5, 0.5  # Midpoint of BC
            u = 0
        if v < 0:
            # Project to edge AC
            total = u + w
            if total > 0:
                u, w = u / total, w / total
            else:
                u, w = 0.5, 0.5  # Midpoint of AC
            v = 0
        if w < 0:
            # Project to edge AB
            total = u + v
            if total > 0:
                u, v = u / total, v / total
            else:
                u, v = 0.5, 0.5  # Midpoint of AB
            w = 0
        
        # Ensure coordinates sum to 1
        total = u + v + w
        if total > 0:
            u, v, w = u/total, v/total, w/total
        else:
            # If all coordinates are zero (shouldn't happen), use centroid
            u, v, w = 1/3, 1/3, 1/3
        
        return u * A + v * B + w * C

    def compute_gradient(points, base_score, temp=None):
        """Compute gradient of min_area using central differences only for bottleneck points."""
        n_points = len(points)
        gradient = np.zeros_like(points)
        
        # Create triangle cache for efficient area calculations
        triangle_cache = TriangleCache(points.copy())
        current_min_area = triangle_cache.get_min_area()
        
        # Adaptive bottleneck threshold
        bottleneck_threshold = get_bottleneck_threshold(current_min_area)
        bottleneck_points = triangle_cache.get_bottleneck_points(bottleneck_threshold)
        
        # Adaptive epsilon based on temperature and current score
        if temp is not None:
            epsilon = max(1e-7, 0.01 * base_score * (temp / INITIAL_TEMP) ** 0.5)
        else:
            epsilon = max(1e-7, 0.01 * base_score)
        
        for i in bottleneck_points:
            for j in range(2):  # x and y dimensions
                # Create candidates with small perturbations in both directions
                candidate_pos = points.copy()
                candidate_neg = points.copy()
                
                candidate_pos[i, j] += epsilon
                candidate_neg[i, j] -= epsilon
                
                # Ensure points stay inside triangle
                if not is_inside_triangle(candidate_pos[i], A, B, C):
                    candidate_pos[i] = project_to_triangle(candidate_pos[i])
                if not is_inside_triangle(candidate_neg[i], A, B, C):
                    candidate_neg[i] = project_to_triangle(candidate_neg[i])
                
                # Use triangle cache for efficient area calculation
                cache_pos = TriangleCache(candidate_pos)
                cache_neg = TriangleCache(candidate_neg)
                
                score_pos = cache_pos.get_min_area()
                score_neg = cache_neg.get_min_area()
                
                # Compute central difference gradient component
                gradient[i, j] = (score_pos - score_neg) / (2 * epsilon)
        
        return gradient

    def repair_collinear_points(candidate, temp, min_area):
        """Identify and repair collinear points using adaptive step size based on severity."""
        n = len(candidate)
        
        # Create triangle cache for efficient area calculations
        triangle_cache = TriangleCache(candidate.copy())
        current_min_area = triangle_cache.get_min_area()
        
        # Adaptive bottleneck threshold
        bottleneck_threshold = get_bottleneck_threshold(current_min_area)
        problematic_triangles = triangle_cache.get_bottleneck_triangles(bottleneck_threshold)
        
        # Filter for truly degenerate triangles (area < 1e-5)
        degenerate_triangles = []
        degenerate_areas = []
        for tri in problematic_triangles:
            i, j, k = tri
            area = triangle_cache.areas[i,j,k]
            if area < 1e-5:
                degenerate_triangles.append(tri)
                degenerate_areas.append(area)

        if not degenerate_triangles:
            return candidate, min_area
        
        # Compute gradient for bottleneck points only
        gradient = compute_gradient(candidate, min_area, temp=temp)
        
        # For each problematic triangle, move ONLY the point with highest gradient magnitude
        repaired = candidate.copy()
        max_repair = 0
        
        for (i, j, k), area in zip(degenerate_triangles, degenerate_areas):
            # Adaptive repair step size based on severity of degeneracy
            repair_factor = 1.0 / (area + 1e-8)
            repair_step = min(0.01, 0.001 * repair_factor)  # Cap maximum step size
            
            # Find the point with highest gradient magnitude (most potential for improvement)
            grads = [gradient[i], gradient[j], gradient[k]]
            magnitudes = [np.linalg.norm(g) for g in grads]
            max_idx = [i, j, k][np.argmax(magnitudes)]
            
            # Only move the point with highest gradient magnitude
            if magnitudes[np.argmax(magnitudes)] > 1e-8:
                step = grads[np.argmax(magnitudes)] / magnitudes[np.argmax(magnitudes)] * repair_step
                repaired[max_idx] += step
                max_repair = max(max_repair, np.linalg.norm(step))
            
            # Ensure point stays inside triangle
            if not is_inside_triangle(repaired[max_idx], A, B, C):
                repaired[max_idx] = project_to_triangle(repaired[max_idx])

        # Check if repair was successful
        repaired_min_area = get_smallest_triangle_area(repaired)
        if repaired_min_area < min_area:
            return candidate, min_area  # Keep original if repair made things worse
        
        return repaired, repaired_min_area

    def improve(points: np.ndarray) -> np.ndarray:
        # Create a local RNG seeded by a hash of the input points for determinism per input
        points_hash = hashlib.sha256(points.tobytes()).hexdigest()
        seed = int(points_hash[:8], 16)  # Take first 8 hex chars as seed
        rng = np.random.RandomState(seed)
        
        # Initial setup
        current = points.copy()
        best = points.copy()
        current_score = get_smallest_triangle_area(current)
        best_score = current_score
        
        # Track improvement history for adaptive strategies
        improvement_history = []
        
        # Simulated annealing parameters
        temp = INITIAL_TEMP
        no_improve_count = 0
        restart_count = 0
        iteration = 0
        
        # Dynamic restart threshold based on temperature and restart count
        BASE_NO_IMPROVEMENT_LIMIT = 25
        
        while iteration < MAX_ITERATIONS and restart_count < RESTARTS:
            # Dynamic threshold: increases with restarts and correlates with temperature
            NO_IMPROVEMENT_LIMIT = int(BASE_NO_IMPROVEMENT_LIMIT * (1 + 0.5 * restart_count) * 
                                     (temp / INITIAL_TEMP + 0.1))
            
            # Generate candidate by perturbing 1-3 random points
            candidate = current.copy()
            
            # Adjusted perturbation probabilities to maintain multi-point capability
            temp_factor = temp / INITIAL_TEMP
            p1 = 0.4 + 0.3 * (1 - temp_factor)  # Reduced single-point bias
            p2 = 0.35 * temp_factor
            p3 = 0.25 * temp_factor
            total = p1 + p2 + p3
            p1, p2, p3 = p1/total, p2/total, p3/total
            
            # Determine how many points to perturb (1-3)
            num_perturb = rng.choice([1, 2, 3], p=[p1, p2, p3])
            
            # Create triangle cache for efficient area calculations
            triangle_cache = TriangleCache(current.copy())
            current_min_area = triangle_cache.get_min_area()
            
            # Adaptive bottleneck threshold
            bottleneck_threshold = get_bottleneck_threshold(current_min_area)
            bottleneck_points = triangle_cache.get_bottleneck_points(bottleneck_threshold)
            
            # Bias perturbation probability toward bottleneck points using softmax of gradient magnitudes
            if bottleneck_points:
                # Compute gradient for bottleneck points
                gradient = compute_gradient(current, current_score, temp=temp)
                
                # Calculate gradient magnitudes for bottleneck points
                magnitudes = [np.linalg.norm(gradient[i]) for i in bottleneck_points]
                
                # Apply softmax to get probabilities
                exp_magnitudes = np.exp(magnitudes - np.max(magnitudes))
                probs = exp_magnitudes / np.sum(exp_magnitudes)
                
                # Select indices with probability proportional to gradient magnitudes
                indices = rng.choice(bottleneck_points, size=num_perturb, replace=False, p=probs)
            else:
                indices = rng.choice(11, size=num_perturb, replace=False)
            
            # Dynamic step size exponent based on improvement rate
            if no_improve_count > 10:
                # Stuck - increase exploration
                step_size_exponent = 0.5
            else:
                # Making progress - fine-tune
                step_size_exponent = 0.2

            # Adaptive step size with dynamic exponent
            step_size = 0.06 * (temp / INITIAL_TEMP) ** step_size_exponent
            
            for idx in indices:
                # Gaussian perturbation with adaptive step size
                perturbation = rng.normal(0, step_size, size=2)
                candidate[idx] += perturbation
                
                # Ensure point stays inside triangle
                if not is_inside_triangle(candidate[idx], A, B, C):
                    candidate[idx] = project_to_triangle(candidate[idx])

            # Check for near-collinear points and attempt repair
            candidate_score = get_smallest_triangle_area(candidate)
            candidate, candidate_score = repair_collinear_points(candidate, temp, candidate_score)
            
            # Simulated annealing acceptance
            delta = candidate_score - current_score
            if delta > 0 or (delta > -1e-5 and rng.rand() < np.exp(delta / temp)):
                current = candidate
                current_score = candidate_score
                
                if candidate_score > best_score:
                    best = candidate.copy()
                    best_score = candidate_score
                    no_improve_count = 0
                    # Track successful improvements
                    improvement_history.append(delta)
                    if len(improvement_history) > 20:
                        improvement_history.pop(0)
                else:
                    no_improve_count += 1
            else:
                no_improve_count += 1
            
            # Directional search when stuck in local optimum
            if no_improve_count > NO_IMPROVEMENT_LIMIT * 0.5:
                # Compute gradient only for bottleneck points
                gradient = compute_gradient(current, current_score, temp=temp)
                
                # Check if gradient is useful
                gradient_magnitude = np.linalg.norm(gradient)
                if gradient_magnitude > 1e-5:
                    # Scale step by gradient magnitude with temperature-dependent factor
                    step_direction = gradient * (0.01 * temp / INITIAL_TEMP / gradient_magnitude)
                    
                    # Create candidate in gradient direction
                    gradient_candidate = current + step_direction
                    
                    # Project any points that moved outside the triangle
                    for i in range(11):
                        if not is_inside_triangle(gradient_candidate[i], A, B, C):
                            gradient_candidate[i] = project_to_triangle(gradient_candidate[i])
                    
                    # Repair collinear points if needed
                    gradient_score = get_smallest_triangle_area(gradient_candidate)
                    gradient_candidate, gradient_score = repair_collinear_points(
                        gradient_candidate, temp, gradient_score)
                    
                    # Accept if it improves the score
                    if gradient_score > current_score:
                        current = gradient_candidate
                        current_score = gradient_score
                        no_improve_count = 0
                        if gradient_score > best_score:
                            best = gradient_candidate.copy()
                            best_score = gradient_score
                else:
                    # Random direction search for flat regions
                    # Adaptive radius based on temperature and improvement history
                    avg_improvement = np.mean(improvement_history) if improvement_history else 1e-5
                    radius = max(0.005, 0.02 * (temp / INITIAL_TEMP) * np.sqrt(avg_improvement))
                    
                    # Scale direction count with restart_count to increase exploration depth
                    direction_count = max(3, 3 + restart_count * 2)
                    
                    # Try multiple random directions to find promising ascent
                    best_random_candidate = None
                    best_random_score = current_score
                    
                    for _ in range(direction_count):
                        random_direction = rng.normal(0, 1, size=(11, 2))
                        random_direction = random_direction / (np.linalg.norm(random_direction) + 1e-8) * radius
                        
                        random_candidate = current + random_direction
                        
                        # Project points outside triangle
                        for i in range(11):
                            if not is_inside_triangle(random_candidate[i], A, B, C):
                                random_candidate[i] = project_to_triangle(random_candidate[i])
                        
                        # Repair collinear points
                        random_score = get_smallest_triangle_area(random_candidate)
                        random_candidate, random_score = repair_collinear_points(
                            random_candidate, temp, random_score)
                        
                        if random_score > best_random_score:
                            best_random_score = random_score
                            best_random_candidate = random_candidate

                    # Accept best random candidate if it improves score
                    if best_random_candidate is not None and best_random_score > current_score:
                        current = best_random_candidate
                        current_score = best_random_score
                        no_improve_count = 0
                        if best_random_score > best_score:
                            best = best_random_candidate.copy()
                            best_score = best_random_score

            # Adjust cooling rate based on recent improvement rate
            if len(improvement_history) > 5:
                avg_improvement = np.mean(improvement_history[-5:])
                # Slower cooling when improvements frequent, faster when stuck
                adaptive_cooling_rate = COOLING_RATE * (0.9 + 0.2 * min(1.0, avg_improvement / 1e-5))
                temp = max(MIN_TEMP, temp * adaptive_cooling_rate)
            else:
                temp = max(MIN_TEMP, temp * COOLING_RATE)
            
            iteration += 1
            
            # Early stopping if stuck for too long
            if no_improve_count >= NO_IMPROVEMENT_LIMIT:
                # Progressive focusing - gradually narrow the search space based on improvement history
                if improvement_history:
                    avg_improvement = np.mean(improvement_history)
                    exploration_factor = max(0.3, 0.7 ** restart_count * (1 + 0.5 * avg_improvement))
                else:
                    exploration_factor = 0.7 ** restart_count
                
                # Implement temperature reset after RESTARTS/2 consecutive failed restarts
                if restart_count > RESTARTS / 2 and no_improve_count >= NO_IMPROVEMENT_LIMIT:
                    # Reset temperature more aggressively to escape deep basins
                    temp = INITIAL_TEMP * 0.8
                else:
                    # Restart from best configuration
                    temp = max(MIN_TEMP, INITIAL_TEMP * exploration_factor)
                
                current = best.copy()
                current_score = best_score
                
                no_improve_count = 0
                restart_count += 1
        
        # Final validation check
        if not is_inside_triangle(best, A, B, C) or get_smallest_triangle_area(best) < 1e-6:
            return points  # Return original if our improvement is invalid
        
        return best

    return improve