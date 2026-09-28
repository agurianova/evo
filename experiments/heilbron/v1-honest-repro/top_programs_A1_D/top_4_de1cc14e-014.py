from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.spatial import Delaunay
import random
import scipy.stats

np.random.seed(42)

def entrypoint():
    A_big, B_big, C_big = get_unit_triangle()

    def reflect_point(p, a, b):
        """Reflect point p across the line defined by points a and b."""
        ab = b - a
        if np.linalg.norm(ab) < 1e-10:
            return p
        ab_norm = ab / np.linalg.norm(ab)
        ap = p - a
        proj = np.dot(ap, ab_norm) * ab_norm
        return a + 2 * proj - ap

    def break_symmetry(config, critical_points=None):
        """Break symmetry by perturbing points away from symmetry axes, focusing on critical points if provided."""
        if critical_points is None:
            critical_points = list(range(len(config)))  # Default: all points

        # For equilateral triangle, symmetry axes go from vertices to midpoints of opposite sides
        mid_BC = (B_big + C_big) / 2
        mid_AC = (A_big + C_big) / 2
        mid_AB = (A_big + B_big) / 2
        
        axes = [
            (A_big, mid_BC),
            (B_big, mid_AC),
            (C_big, mid_AB)
        ]
        
        # Choose the axis most relevant to critical points (the one that creates most symmetry among them)
        best_axis_idx = 0
        max_symmetry_score = -1
        
        for idx, (a, b) in enumerate(axes):
            # Reflect critical points
            reflected = np.array([reflect_point(config[i], a, b) for i in critical_points])
            
            # Calculate distance between original and reflected points for critical points
            distances = np.linalg.norm(config[critical_points] - reflected, axis=1)
            symmetry_score = np.mean(distances)
            
            if symmetry_score > max_symmetry_score:
                max_symmetry_score = symmetry_score
                best_axis_idx = idx
        
        a, b = axes[best_axis_idx]
        
        # Calculate reflection of each point
        reflected = np.array([reflect_point(p, a, b) for p in config])
        
        # Move points away from their reflections (breaking symmetry)
        perturbed = config.copy()
        for i in range(len(perturbed)):
            # Only perturb critical points
            if i not in critical_points:
                continue
                
            # Direction away from reflection
            direction = config[i] - reflected[i]
            if np.linalg.norm(direction) > 1e-10:
                direction = direction / np.linalg.norm(direction)
                # Apply perturbation proportional to current symmetry
                perturbation = direction * 0.005 * (1.0 + np.random.random())
                perturbed[i] = config[i] + perturbation

        # Ensure all points are inside the triangle
        for i in range(len(perturbed)):
            if not is_inside_triangle(perturbed[i], A_big, B_big, C_big):
                # Project to boundary if outside
                centroid = (A_big + B_big + C_big) / 3
                direction = centroid - perturbed[i]
                step = 0.1
                while not is_inside_triangle(perturbed[i], A_big, B_big, C_big) and step > 1e-5:
                    perturbed[i] += step * direction
                    step *= 0.5
        
        return perturbed

    def project_to_boundary(point, A, B, C):
        """Project a point to the nearest boundary if outside the triangle."""
        if is_inside_triangle(point, A, B, C):
            return point.copy()
        
        # Check distance to each edge and project to closest one
        edges = [(A, B), (B, C), (C, A)]
        min_dist = float('inf')
        closest_point = point.copy()
        
        for (p1, p2) in edges:
            # Vector from p1 to p2
            v = p2 - p1
            # Vector from p1 to point
            w = point - p1
            # Project w onto v
            c1 = np.dot(w, v)
            c2 = np.dot(v, v)
            if c2 == 0:
                continue
            b = c1 / c2
            
            # Find closest point on line segment
            if b < 0:
                proj = p1
            elif b > 1:
                proj = p2
            else:
                proj = p1 + b * v
            
            # Check if this is closer than previous best
            dist = np.linalg.norm(point - proj)
            if dist < min_dist:
                min_dist = dist
                closest_point = proj
        
        return closest_point

    def boundary_move(point, edge, direction, step_size, A, B, C):
        """Move a point along a specific edge of the triangle."""
        p1, p2 = edge
        edge_vec = p2 - p1
        edge_length = np.linalg.norm(edge_vec)
        if edge_length < 1e-10:
            return point.copy()
        
        # Normalize edge vector
        edge_unit = edge_vec / edge_length
        
        # Project point onto edge line
        p1_to_point = point - p1
        projection = np.dot(p1_to_point, edge_unit)
        
        # Clamp to segment
        projection = max(0, min(edge_length, projection))
        on_edge = p1 + projection * edge_unit
        
        # Move along edge
        new_point = on_edge + direction * step_size * edge_unit
        
        # Ensure point stays on the edge segment
        p1_to_new = new_point - p1
        new_projection = np.dot(p1_to_new, edge_unit)
        if new_projection < 0:
            new_projection = 0
        elif new_projection > edge_length:
            new_projection = edge_length
        
        return p1 + new_projection * edge_unit

    def calculate_triangle_connectivity(indices, all_triangles):
        """Calculate how interconnected a triangle is with other small triangles."""
        # Count how many other triangles share points with this one
        shared_points_count = 0
        for other_indices in all_triangles:
            if other_indices == indices:
                continue
            # Count shared points
            shared = len(set(indices) & set(other_indices))
            if shared >= 2:  # Triangles sharing an edge are highly relevant
                shared_points_count += 2
            elif shared == 1:  # Triangles sharing a vertex are somewhat relevant
                shared_points_count += 1
                
        return shared_points_count

    def get_adaptive_k_smallest_triangles(config, current_min_area, base_proportion=0.1):
        """Select triangles with area below an adaptively determined threshold based on area distribution and problem difficulty."""
        areas = []
        indices = []
        n = config.shape[0]
        for i in range(n):
            for j in range(i + 1, n):
                for l in range(j + 1, n):
                    p1, p2, p3 = config[i], config[j], config[l]
                    area2_val = abs(p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1]))
                    areas.append(area2_val)
                    indices.append((i, j, l))
        
        if not areas:
            return [indices[0]] if indices else []
        
        # Calculate difficulty metric: how close we are to theoretical maximum
        difficulty = 1.0 - (current_min_area / 0.0365)
        # INCREASED MIN PROPORTION TO BETTER EXPLORE HARD PROBLEMS
        min_proportion = 0.03 + 0.015 * difficulty
        max_proportion = 0.1 + 0.05 * difficulty
        
        # Calculate skewness of log-transformed areas for better stability with small values
        log_areas = np.log(areas)
        skewness = scipy.stats.skew(log_areas)
        
        # Adaptive target proportion based on skewness, clamped to problem difficulty range
        target_proportion = base_proportion + 0.08 * skewness
        target_proportion = max(min_proportion, min(max_proportion, target_proportion))
        
        # Sort areas
        sorted_indices = np.argsort(areas)
        sorted_areas = np.array(areas)[sorted_indices]
        
        # NEW: Calculate triangle connectivity for interdependence awareness
        # Get the k smallest triangles for connectivity analysis
        k_for_connectivity = max(1, int(len(areas) * 0.05))  # Analyze top 5% smallest triangles
        smallest_triangle_indices = [indices[sorted_indices[i]] for i in range(min(k_for_connectivity, len(sorted_indices)))]
        
        # Calculate connectivity scores
        connectivity_scores = []
        for idx in sorted_indices:
            connectivity = calculate_triangle_connectivity(indices[idx], smallest_triangle_indices)
            connectivity_scores.append(connectivity)
        
        # Normalize connectivity scores
        max_conn = max(connectivity_scores) if connectivity_scores else 1
        if max_conn > 0:
            connectivity_scores = [score / max_conn for score in connectivity_scores]
        else:
            connectivity_scores = [0] * len(connectivity_scores)
        
        # Calculate potential improvement (area deficit from current min)
        area_deficit = current_min_area - sorted_areas
        # NEW: Weight by both improvement potential and connectivity
        # Triangles that are both small AND highly connected to other small triangles get higher weight
        combined_score = 0.7 * area_deficit + 0.3 * np.array(connectivity_scores[:len(area_deficit)])
        
        # Use softmax to weight selection toward triangles with higher combined score
        temperature = 0.1 * (1.0 + difficulty)
        weights = np.exp(combined_score / temperature)
        weights = weights / np.sum(weights)
        
        # Select triangles probabilistically based on combined score
        num_to_select = max(1, int(len(areas) * target_proportion))
        selected_indices = np.random.choice(
            len(sorted_indices), 
            size=num_to_select, 
            replace=False,
            p=weights
        )
        
        result = [indices[sorted_indices[i]] for i in selected_indices]
        
        # Ensure we return at least one triangle
        return result if result else [indices[sorted_indices[0]]]

    def move_point_inside(point, direction, step, A, B, C):
        candidate = point + step * direction
        if is_inside_triangle(candidate, A, B, C):
            return candidate, step
        else:
            # Binary search to find the maximum valid step
            low, high = 0.0, step
            for _ in range(10):
                mid = (low + high) / 2
                candidate = point + mid * direction
                if is_inside_triangle(candidate, A, B, C):
                    low = mid
                else:
                    high = mid
            return point + low * direction, low

    def generate_adaptive_directions(triangle_points, num_directions=8):
        """Generate directions based on the geometry of the triangle."""
        directions = []
        
        # Get the three edges of the triangle
        p1, p2, p3 = triangle_points
        edges = [(p2 - p1), (p3 - p2), (p1 - p3)]
        
        # For each edge, compute normal directions
        for edge in edges:
            if np.linalg.norm(edge) > 1e-10:
                normal = np.array([-edge[1], edge[0]])
                normal = normal / np.linalg.norm(normal)
                
                # Add the normal and some variations around it
                for i in range(num_directions // 3):
                    angle = (i - num_directions // 6) * np.pi / (num_directions // 3)
                    rotated = np.array([
                        normal[0] * np.cos(angle) - normal[1] * np.sin(angle),
                        normal[0] * np.sin(angle) + normal[1] * np.cos(angle)
                    ])
                    directions.append(rotated)
        
        # Add some random exploration directions
        for _ in range(num_directions - len(directions)):
            angle = np.random.uniform(0, 2 * np.pi)
            directions.append(np.array([np.cos(angle), np.sin(angle)]))
        
        return directions

    def calculate_symmetry_score(config):
        """Calculate how close the configuration is to being symmetric."""
        # For equilateral triangle, symmetry axes go from vertices to midpoints of opposite sides
        mid_BC = (B_big + C_big) / 2
        mid_AC = (A_big + C_big) / 2
        mid_AB = (A_big + B_big) / 2
        
        axes = [
            (A_big, mid_BC),
            (B_big, mid_AC),
            (C_big, mid_AB)
        ]
        
        total_variance = 0
        for a, b in axes:
            # Reflect all points
            reflected = np.array([reflect_point(p, a, b) for p in config])
            
            # Calculate distance between original and reflected points
            distances = np.linalg.norm(config - reflected, axis=1)
            total_variance += np.mean(distances)
        
        # Lower variance means more symmetric
        # Normalize to [0,1] where 1 is perfectly symmetric
        return 1.0 / (1.0 + total_variance)

    def identify_sparse_regions(points):
        """Use Delaunay triangulation to identify sparse regions in the point configuration."""
        try:
            # Create Delaunay triangulation
            tri = Delaunay(points)
            
            # Calculate circumradius for each triangle
            circumradii = []
            for simplex in tri.simplices:
                pts = points[simplex]
                a = np.linalg.norm(pts[1] - pts[0])
                b = np.linalg.norm(pts[2] - pts[1])
                c = np.linalg.norm(pts[0] - pts[2])
                s = (a + b + c) / 2.0
                area = np.sqrt(s * (s - a) * (s - b) * (s - c))
                if area > 1e-10:
                    circumradius = (a * b * c) / (4 * area)
                else:
                    circumradius = float('inf')
                circumradii.append(circumradius)
            
            # Find triangles with largest circumradii (sparse regions)
            if circumradii:
                sorted_indices = np.argsort(circumradii)
                # Return indices of points in the most sparse regions
                sparse_region_indices = set()
                for i in sorted_indices[-3:]:  # Take top 3 sparse regions
                    for idx in tri.simplices[i]:
                        sparse_region_indices.add(idx)
                return list(sparse_region_indices)
            
        except:
            # Fallback: return random indices
            return np.random.choice(len(points), size=3, replace=False).tolist()
        
        return list(range(len(points)))

    def improve(points: np.ndarray) -> np.ndarray:
        # Calculate initial difficulty metrics
        initial_min_area = get_smallest_triangle_area(points)
        symmetry_score = calculate_symmetry_score(points)
        
        # Calculate adaptive number of runs based on problem difficulty
        # REVERSED TO ALLOCATE MORE RUNS TO HARDER PROBLEMS (LOWER initial_min_area)
        max_runs = 4 + 8 * (1 - initial_min_area / 0.0365)
        num_runs = int(max_runs)
        
        # If symmetry score is high, we need more runs to escape symmetry traps
        if symmetry_score > 0.7:
            num_runs = min(10, num_runs + 2)

        best_overall = points.copy()
        best_overall_score = initial_min_area

        for run in range(num_runs):
            # Each run starts from a different configuration
            if run == 0:
                current = points.copy()
            else:
                # Perturb the original points for diversity
                if run % 2 == 0:
                    # Regular perturbation
                    current = points.copy() + np.random.uniform(-0.02, 0.02, points.shape)
                else:
                    # Delaunay-based structured perturbation targeting sparse regions
                    current = points.copy()
                    sparse_indices = identify_sparse_regions(points)
                    for idx in sparse_indices:
                        # Apply larger perturbation to points in sparse regions
                        direction = np.random.uniform(-1, 1, 2)
                        direction = direction / (np.linalg.norm(direction) + 1e-10)
                        current[idx] += direction * 0.03

                # Ensure all points are inside the triangle
                for i in range(len(current)):
                    if not is_inside_triangle(current[i], A_big, B_big, C_big):
                        current[i] = project_to_boundary(current[i], A_big, B_big, C_big)

            # Parameters for simulated annealing
            initial_temp = 0.1
            # INCREASED CAP TO 0.5 TO ALLOW FOR BETTER FINE-TUNING NEAR OPTIMUM
            step_size_factor = 10.0 * (1.0 - min(0.5, (initial_min_area / 0.0365)))**2
            # Slower cooling for harder problems
            base_cooling_rate = 0.93 + 0.04 * (1 - initial_min_area / 0.0365)
            min_temp = 1e-6
            
            # Adaptive cooling parameters
            recent_improvements = []
            max_recent = 20
            
            # Parameters for multi-triangle targeting
            base_symmetry_prob = 0.3
            symmetry_attempts = 0
            symmetry_successes = 0
            prev_ema_success_rate = 0.0
            
            # Track best for this run
            best = current.copy()
            current_score = get_smallest_triangle_area(current)
            best_score = current_score
            
            # Track improvement history for restarts
            no_improve_count = 0
            max_no_improve = 30

            # Simulated annealing main loop
            temp = initial_temp
            while temp > min_temp:
                # Select triangles adaptively based on area distribution and current difficulty
                top_triangles = get_adaptive_k_smallest_triangles(current, current_score)
                
                # NEW: Identify critical points (those in smallest triangles)
                critical_points = set()
                for triangle_indices in top_triangles[:3]:  # Consider top 3 smallest triangles
                    for idx in triangle_indices:
                        critical_points.add(idx)
                critical_points = list(critical_points)
                
                # Randomly select a triangle from the targeted set
                triangle_indices = random.choice(top_triangles)
                
                # Get the triangle points
                triangle_points = [current[i] for i in triangle_indices]
                
                # Calculate aspect ratio of the triangle (1 = equilateral, <1 = elongated)
                edges = [
                    np.linalg.norm(triangle_points[1] - triangle_points[0]),
                    np.linalg.norm(triangle_points[2] - triangle_points[1]),
                    np.linalg.norm(triangle_points[0] - triangle_points[2])
                ]
                aspect_ratio = min(edges) / max(edges)
                
                # Adjust step size based on aspect ratio - smaller for elongated triangles
                aspect_factor = 0.5 + 0.5 * aspect_ratio
                
                # Generate adaptive directions
                directions = generate_adaptive_directions(triangle_points)
                
                # Try moving each point in the triangle
                improved_this_step = False
                for idx in triangle_indices:
                    for direction in directions:
                        # Try different step sizes with geometry-aware scaling
                        step_size = step_size_factor * temp * aspect_factor
                        while step_size > 1e-5:
                            candidate_points = current.copy()
                            new_point, actual_step = move_point_inside(
                                current[idx], direction, step_size, A_big, B_big, C_big
                            )
                            candidate_points[idx] = new_point
                            
                            candidate_score = get_smallest_triangle_area(candidate_points)
                            
                            # Record improvement for adaptive cooling
                            delta = candidate_score - current_score
                            if delta > 0:
                                recent_improvements.append(1)
                            else:
                                recent_improvements.append(0)
                            
                            if len(recent_improvements) > max_recent:
                                recent_improvements.pop(0)
                            
                            # Simulated annealing acceptance criterion
                            if delta > 0 or (delta > -1e-7 and np.random.rand() < np.exp(delta / temp)):
                                current = candidate_points
                                current_score = candidate_score
                                if current_score > best_score:
                                    best = current.copy()
                                    best_score = current_score
                                    no_improve_count = 0
                                improved_this_step = True
                                break  # Move to next direction after accepting a move
                            
                            if actual_step < step_size * 0.9:  # If we hit the boundary
                                break
                            
                            step_size *= 0.75  # REDUCED AGGRESSIVENESS OF STEP SIZE REDUCTION
                        
                # Calculate adaptive cooling rate based on recent improvements and problem difficulty
                if recent_improvements:
                    improvement_rate = sum(recent_improvements) / len(recent_improvements)
                    
                    # NEW: Make coefficient tunable based on difficulty and historical patterns
                    # Higher difficulty (closer to optimum) needs more careful cooling
                    difficulty_factor = current_score / 0.0365
                    
                    # Historical pattern: if we've been making consistent improvements, cool slower
                    historical_trend = 0.5  # Default
                    if len(recent_improvements) >= 5:
                        recent_trend = sum(recent_improvements[-5:]) / 5
                        historical_trend = 0.3 + 0.7 * recent_trend
                    
                    # Calculate adaptive coefficient (was fixed at 0.10)
                    adaptive_coefficient = 0.05 + 0.15 * difficulty_factor * historical_trend
                    
                    adaptive_rate = base_cooling_rate + adaptive_coefficient * (1.0 - improvement_rate)
                    # Clamp to stable range
                    adaptive_rate = max(0.85, min(0.99, adaptive_rate))
                else:
                    adaptive_rate = base_cooling_rate

                # Periodically try symmetry-breaking when high symmetry is detected
                # ADJUSTED SYMMETRY THRESHOLD TO INCREASE BREAKING NEAR OPTIMUM
                symmetry_score = calculate_symmetry_score(current)
                symmetry_threshold = 0.45 + 0.2 * (current_score / 0.0365)
                
                # ADAPTIVE SYMMETRY PROBABILITY BASED ON SUCCESS RATE
                if symmetry_attempts > 0:
                    success_rate = symmetry_successes / symmetry_attempts
                    symmetry_prob = base_symmetry_prob * (1 + success_rate)
                else:
                    symmetry_prob = base_symmetry_prob
                
                if symmetry_score > symmetry_threshold and np.random.random() < symmetry_prob:
                    # Actively break symmetry, focusing on critical points
                    symmetry_attempts += 1
                    asymmetric_points = break_symmetry(current, critical_points)
                    asymmetric_score = get_smallest_triangle_area(asymmetric_points)
                    if asymmetric_score > current_score:
                        symmetry_successes += 1
                        current = asymmetric_points
                        current_score = asymmetric_score
                        if current_score > best_score:
                            best = current.copy()
                            best_score = current_score
                        improved_this_step = True

                # INCREASED BOUNDARY EXPLORATION PROBABILITY TO BETTER EXPLOIT STRATEGIC POSITIONS
                boundary_prob = 0.2 + 0.25 * (current_score / 0.0365)
                if np.random.random() < boundary_prob:  # Probability increases as we get closer to optimum
                    # Choose a random edge
                    edges = [(A_big, B_big), (B_big, C_big), (C_big, A_big)]
                    edge = random.choice(edges)
                    # Choose a random point
                    idx = random.randint(0, 10)
                    # Move along edge with random direction
                    direction = 1 if np.random.random() > 0.5 else -1
                    step_size = 0.01 * (1.0 + np.random.random())
                    boundary_point = boundary_move(current[idx], edge, direction, step_size, A_big, B_big, C_big)
                    
                    # Create candidate configuration
                    candidate_points = current.copy()
                    candidate_points[idx] = boundary_point
                    candidate_score = get_smallest_triangle_area(candidate_points)
                    
                    # Accept if improvement or via simulated annealing
                    delta = candidate_score - current_score
                    if delta > 0 or (delta > -1e-7 and np.random.rand() < np.exp(delta / temp)):
                        current = candidate_points
                        current_score = candidate_score
                        if current_score > best_score:
                            best = current.copy()
                            best_score = current_score
                        improved_this_step = True

                # Track improvement for restart logic
                if not improved_this_step:
                    no_improve_count += 1
                    if no_improve_count >= max_no_improve:
                        # Perturb to escape local optimum
                        # INTEGRATE SPARSE REGION IDENTIFICATION INTO RESTART LOGIC
                        sparse_indices = identify_sparse_regions(current)
                        perturbation = np.random.uniform(-0.02, 0.02, current.shape)
                        # Apply larger perturbations to points in sparse regions
                        for idx in sparse_indices:
                            direction = np.random.uniform(-1, 1, 2)
                            direction = direction / (np.linalg.norm(direction) + 1e-10)
                            perturbation[idx] += direction * 0.03
                        
                        current = best.copy() + perturbation
                        # Ensure points stay inside
                        for i in range(len(current)):
                            if not is_inside_triangle(current[i], A_big, B_big, C_big):
                                current[i] = project_to_boundary(current[i], A_big, B_big, C_big)
                        current_score = get_smallest_triangle_area(current)
                        no_improve_count = 0
                else:
                    no_improve_count = 0

                # Cool the temperature with adaptive rate
                temp *= adaptive_rate

            # Update overall best if this run was better
            if best_score > best_overall_score:
                best_overall = best.copy()
                best_overall_score = best_score

        return best_overall

    return improve