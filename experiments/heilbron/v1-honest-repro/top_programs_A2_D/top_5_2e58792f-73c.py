from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.spatial import Voronoi
import math

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    triangle_side = np.linalg.norm(B - A)  # Unit triangle side length ~1.52

    def compute_min_triangles(pts):
        n = pts.shape[0]
        min_area_val = float('inf')
        min_triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = 0.5 * abs(
                        pts[i,0]*(pts[j,1]-pts[k,1]) +
                        pts[j,0]*(pts[k,1]-pts[i,1]) +
                        pts[k,0]*(pts[i,1]-pts[j,1])
                    )
                    if area < min_area_val - 1e-10:
                        min_area_val = area
                        min_triangles = [(i, j, k)]
                    elif abs(area - min_area_val) < 1e-10:
                        min_triangles.append((i, j, k))
        return min_area_val, min_triangles

    def compute_voronoi_centers(pts):
        # Add boundary points to constrain Voronoi diagram within the triangle
        boundary_points = np.array([A, B, C])
        extended_pts = np.vstack([pts, boundary_points])
        
        # Compute Voronoi diagram
        vor = Voronoi(extended_pts)
        
        # For each point in original set, find the center of its largest Voronoi region
        voronoi_centers = np.zeros_like(pts)
        for i in range(len(pts)):
            region_index = vor.point_region[i]
            if region_index == -1:
                # Point has no region (shouldn't happen with boundary points)
                voronoi_centers[i] = pts[i]
                continue
                
            region = vor.regions[region_index]
            if -1 in region or len(region) == 0:
                # Unbounded region or empty - use centroid of visible area
                voronoi_centers[i] = pts[i]
                continue

            # Get vertices of the Voronoi region
            vertices = np.array([vor.vertices[r] for r in region])
            
            # Calculate centroid of the region
            centroid = np.mean(vertices, axis=0)
            voronoi_centers[i] = centroid
            
        return voronoi_centers

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        # Enhanced parameters based on insights
        initial_temp = 0.5
        cooling_rate = 0.995
        max_consecutive_failures = 2000
        reheating_threshold = 500  # Lowered from 1500
        reheating_factor = 0.7
        max_steps = 10000  # Increased from 5000
        
        # Track success rates of different move types
        move_success = {
            'gradient': 0.01,
            'height': 0.01,
            'base': 0.01,
            'voronoi': 0.01
        }
        move_attempts = {
            'gradient': 1,
            'height': 1,
            'base': 1,
            'voronoi': 1
        }

        consecutive_failures = 0
        step_count = 0
        current_temp = initial_temp

        # Cache for triangle areas
        triangle_cache = {}

        def get_triangle_area(i, j, k):
            key = tuple(sorted([i, j, k]))
            if key in triangle_cache:
                return triangle_cache[key]
            
            pts = [current[i], current[j], current[k]]
            area = 0.5 * abs(
                pts[0][0]*(pts[1][1]-pts[2][1]) +
                pts[1][0]*(pts[2][1]-pts[0][1]) +
                pts[2][0]*(pts[0][1]-pts[1][1])
            )
            triangle_cache[key] = area
            return area

        def update_cache_for_point(idx):
            # Remove all triangles involving this point from cache
            for i in range(11):
                for j in range(i+1, 11):
                    if i == idx or j == idx:
                        key = tuple(sorted([i, j, idx]))
                        if key in triangle_cache:
                            del triangle_cache[key]

        def compute_min_triangles_cached():
            min_area_val = float('inf')
            min_triangles = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area = get_triangle_area(i, j, k)
                        if area < min_area_val - 1e-10:
                            min_area_val = area
                            min_triangles = [(i, j, k)]
                        elif abs(area - min_area_val) < 1e-10:
                            min_triangles.append((i, j, k))
            return min_area_val, min_triangles

        while consecutive_failures < max_consecutive_failures and step_count < max_steps:
            factor = cooling_rate ** step_count
            step_count += 1

            # Dynamic step size: aggressive early, precise late
            phase = step_count / max_steps
            if phase < 0.3:  # First 30% of iterations
                step_scale = 0.03
            else:
                step_scale = 0.005

            # Update move probabilities based on success rates
            if step_count % 100 == 0:
                for move_type in move_success:
                    if move_attempts[move_type] > 5:
                        # Smoothed success rate
                        success_rate = move_success[move_type] / move_attempts[move_type]
                        # Avoid zero probabilities
                        move_success[move_type] = max(success_rate, 0.01)

            # Calculate probabilities using softmax
            total = sum(move_success.values())
            move_probs = {k: v/total for k, v in move_success.items()}

            # 30% chance to use Voronoi-based exploration for non-minimal points
            if np.random.rand() < move_probs['voronoi']:
                all_indices = set(range(11))
                _, min_triangles = compute_min_triangles_cached()
                min_indices = set()
                for tri in min_triangles:
                    min_indices.update(tri)
                candidate_indices = list(all_indices - min_indices)
                
                if candidate_indices:
                    # Compute Voronoi centers
                    voronoi_centers = compute_voronoi_centers(current)
                    
                    # Select point with largest potential improvement
                    best_improvement = -1
                    best_idx = None
                    for idx in candidate_indices:
                        # How far is this point from its Voronoi center?
                        distance = np.linalg.norm(voronoi_centers[idx] - current[idx])
                        if distance > best_improvement:
                            best_improvement = distance
                            best_idx = idx
                    
                    if best_idx is not None:
                        candidate = current.copy()
                        # Move toward Voronoi center
                        direction = voronoi_centers[best_idx] - current[best_idx]
                        if np.linalg.norm(direction) > 1e-10:
                            direction = direction / np.linalg.norm(direction)
                            candidate[best_idx] += direction * step_scale * 2
                            
                            if is_inside_triangle(candidate, A, B, C):
                                new_score = get_smallest_triangle_area(candidate)
                                if new_score > current_score:
                                    # Update success tracking
                                    move_success['voronoi'] += 1
                                    move_attempts['voronoi'] += 1
                                    
                                    current = candidate
                                    current_score = new_score
                                    consecutive_failures = 0
                                    update_cache_for_point(best_idx)
                                    if new_score > best_score:
                                        best = candidate
                                        best_score = new_score
                                else:
                                    move_attempts['voronoi'] += 1
                                    consecutive_failures += 1
                                continue

            min_area_val, min_triangles = compute_min_triangles_cached()
            if not min_triangles:
                break
            
            # Sort minimal triangles by aspect ratio (height/base) to prioritize flattest
            triangle_data = []
            for tri in min_triangles:
                i0, i1, i2 = tri
                p0, p1, p2 = current[i0], current[i1], current[i2]
                d01 = np.linalg.norm(p0 - p1)
                d02 = np.linalg.norm(p0 - p2)
                d12 = np.linalg.norm(p1 - p2)
                base_length = max(d01, d02, d12)
                
                # Calculate height
                if base_length > 1e-10:
                    if d01 == base_length:
                        base_i, base_j, apex_i = i0, i1, i2
                    elif d02 == base_length:
                        base_i, base_j, apex_i = i0, i2, i1
                    else:
                        base_i, base_j, apex_i = i1, i2, i0
                    
                    base_vec = current[base_j] - current[base_i]
                    base_norm = np.linalg.norm(base_vec)
                    if base_norm > 1e-10:
                        base_unit = base_vec / base_norm
                        apex = current[apex_i]
                        vec_apex_to_base_i = apex - current[base_i]
                        proj = np.dot(vec_apex_to_base_i, base_unit)
                        foot = current[base_i] + proj * base_unit
                        height_vec = apex - foot
                        height = np.linalg.norm(height_vec)
                        aspect_ratio = height / base_length
                        triangle_data.append((aspect_ratio, tri))

            # Sort by aspect ratio (ascending - flattest first)
            triangle_data.sort(key=lambda x: x[0])
            min_triangles = [tri for _, tri in triangle_data]

            # Weighted selection proportional to 1/aspect_ratio
            if triangle_data:
                weights = [1.0 / (aspect_ratio + 1e-10) for aspect_ratio, _ in triangle_data]
                weights = np.array(weights) / sum(weights)  # Normalize to probabilities
                tri_idx = np.random.choice(len(min_triangles), p=weights)
                i0, i1, i2 = min_triangles[tri_idx]
            else:
                i0, i1, i2 = min_triangles[0]

            p0, p1, p2 = current[i0], current[i1], current[i2]
            d01 = np.linalg.norm(p0 - p1)
            d02 = np.linalg.norm(p0 - p2)
            d12 = np.linalg.norm(p1 - p2)
            sides = [(d01, (i0, i1), i2), (d02, (i0, i2), i1), (d12, (i1, i2), i0)]
            sides.sort(key=lambda x: x[0], reverse=True)
            base_length, (base_i, base_j), apex_i = sides[0]
            min_side = min(d01, d02, d12)

            base_vec = current[base_j] - current[base_i]
            base_norm = np.linalg.norm(base_vec)
            if base_norm < 1e-10:
                consecutive_failures += 1
                continue

            base_unit = base_vec / base_norm
            apex = current[apex_i]
            vec_apex_to_base_i = apex - current[base_i]
            proj = np.dot(vec_apex_to_base_i, base_unit)
            foot = current[base_i] + proj * base_unit
            height_vec = apex - foot
            height = np.linalg.norm(height_vec)
            if height < 1e-10:
                consecutive_failures += 1
                continue

            height_unit = height_vec / height
            
            # Adaptive step size based on triangle geometry
            triangle_size = np.sqrt(base_length * height)
            step = step_scale * factor * triangle_size
            
            # Special handling for very flat triangles (collinearity)
            aspect_ratio = height / base_length
            if aspect_ratio < 0.05:  # Very flat triangle - high risk of collinearity
                step *= 2.0  # Apply larger step to directly target collinearity

            # Use gradient estimation with adaptive probability
            use_gradient = np.random.rand() < move_probs['gradient']
            
            if np.random.rand() < 0.95 if aspect_ratio < 0.2 else 0.75:
                candidate = current.copy()
                move_type = 'height'
                
                if use_gradient:
                    # Estimate gradient for apex point
                    base_score = current_score
                    
                    # Try small perturbations in x and y directions
                    dx = np.zeros_like(current)
                    dx[apex_i, 0] = 1e-5
                    score_x = get_smallest_triangle_area(current + dx)
                    
                    dy = np.zeros_like(current)
                    dy[apex_i, 1] = 1e-5
                    score_y = get_smallest_triangle_area(current + dy)
                    
                    # Calculate gradient components
                    grad_x = (score_x - base_score) / 1e-5
                    grad_y = (score_y - base_score) / 1e-5
                    
                    grad = np.array([grad_x, grad_y])
                    if np.linalg.norm(grad) > 1e-5:
                        # Normalize and scale gradient
                        grad = grad / np.linalg.norm(grad) * step
                        candidate[apex_i] += grad
                        move_type = 'gradient'
                    else:
                        # Fall back to height direction if gradient is negligible
                        candidate[apex_i] = apex + step * height_unit
                else:
                    candidate[apex_i] = apex + step * height_unit

                if not is_inside_triangle(candidate, A, B, C):
                    consecutive_failures += 1
                    continue
            else:
                M = (current[base_i] + current[base_j]) / 2
                disp_i = current[base_i] - M
                disp_j = current[base_j] - M
                
                disp_i_norm = np.linalg.norm(disp_i)
                disp_j_norm = np.linalg.norm(disp_j)
                if disp_i_norm < 1e-10 or disp_j_norm < 1e-10:
                    consecutive_failures += 1
                    continue
                
                new_base_i = current[base_i] + step * (disp_i / disp_i_norm)
                new_base_j = current[base_j] + step * (disp_j / disp_j_norm)
                
                candidate = current.copy()
                candidate[base_i] = new_base_i
                candidate[base_j] = new_base_j
                move_type = 'base'

                if not (is_inside_triangle(new_base_i.reshape(1,2), A, B, C) and 
                        is_inside_triangle(new_base_j.reshape(1,2), A, B, C)):
                    consecutive_failures += 1
                    continue

            new_score = get_smallest_triangle_area(candidate)
            
            # CORRECTED: Standard decreasing temperature schedule
            current_temp = initial_temp * factor

            if new_score > current_score:
                # Update success tracking
                move_success[move_type] += 1
                move_attempts[move_type] += 1
                
                current = candidate
                current_score = new_score
                consecutive_failures = 0
                # Update cache for affected points
                if move_type == 'gradient' or move_type == 'height':
                    update_cache_for_point(apex_i)
                elif move_type == 'base':
                    update_cache_for_point(base_i)
                    update_cache_for_point(base_j)
                
                if new_score > best_score:
                    best = candidate
                    best_score = new_score
            else:
                move_attempts[move_type] += 1
                delta = current_score - new_score
                if np.random.rand() < np.exp(-delta / current_temp):
                    current = candidate
                    current_score = new_score
                    consecutive_failures = 0
                    # Update cache for affected points
                    if move_type == 'gradient' or move_type == 'height':
                        update_cache_for_point(apex_i)
                    elif move_type == 'base':
                        update_cache_for_point(base_i)
                        update_cache_for_point(base_j)
                else:
                    consecutive_failures += 1

            # Reheating mechanism for escaping deep local minima
            if consecutive_failures >= reheating_threshold:
                current_temp = initial_temp * reheating_factor
                step_scale *= 1.2  # Slightly increase step size
                consecutive_failures = 0
                step_count = 0  # Reset step count to restart cooling schedule

        return best

    return improve