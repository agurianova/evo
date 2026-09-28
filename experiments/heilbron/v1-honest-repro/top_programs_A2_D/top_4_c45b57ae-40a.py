from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def find_smallest_triangles(pts, current_score=None):
        n = len(pts)
        triangles = []  # (indices, area)
        
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    a, b, c = pts[i], pts[j], pts[k]
                    area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                    triangles.append(((i, j, k), area))
        
        # Sort by area and take top k
        triangles.sort(key=lambda x: x[1])
        
        # Adaptive k: more triangles when farther from optimal
        if current_score is not None:
            target = 0.0365
            # Make k adaptive to both score gap and area distribution
            score_gap = (target - current_score) / target
            # Use variance of small triangle areas to determine how many to consider
            small_areas = [area for _, area in triangles[:15]]
            area_variance = np.var(small_areas) if len(small_areas) > 1 else 0
            k = min(15, max(3, int(10 * score_gap + 2 * np.sqrt(area_variance))))
        else:
            k = 5  # Default
            
        return [t[0] for t in triangles[:k]]

    def get_min_distance(pts):
        """Calculate minimum distance between any two points"""
        n = len(pts)
        min_dist = float('inf')
        for i in range(n):
            for j in range(i+1, n):
                dist = np.linalg.norm(pts[i] - pts[j])
                if dist < min_dist:
                    min_dist = dist
        return min_dist

    def random_point_move(current, no_improve_count, max_no_improve=500):
        """Perform a random move on a random point, with probability increasing with stagnation"""
        rng = np.random.default_rng()
        # Probability scales from 0.05 to 0.3 as we approach max stagnation
        p = 0.05 + 0.25 * min(no_improve_count / max_no_improve, 1.0)
        
        if rng.random() < p:
            i = rng.integers(0, 11)
            # Random direction
            angle = rng.random() * 2 * np.pi
            # Step size proportional to min distance
            min_dist = get_min_distance(current)
            step = min_dist * (0.05 + 0.15 * rng.random())
            
            dx = step * np.cos(angle)
            dy = step * np.sin(angle)
            candidate_point = current[i] + np.array([dx, dy])
            
            if is_inside_triangle(candidate_point, A, B, C):
                # Check distinctness
                too_close = False
                for j in range(11):
                    if j == i:
                        continue
                    if np.linalg.norm(candidate_point - current[j]) < 1e-5:
                        too_close = True
                        break
                
                if not too_close:
                    candidate_config = current.copy()
                    candidate_config[i] = candidate_point
                    return candidate_config
        
        return None

    def compute_multi_triangle_gradient(current, smallest_triangles, area_scores):
        """Compute gradient considering impact on multiple triangles with weighted contributions"""
        gradient = np.zeros((11, 2))
        total_weight = 0
        
        # Use inverse area as weight (smaller triangles have higher priority)
        weights = [1.0 / (area + 1e-10) for area in area_scores]
        total_weight = sum(weights)
        
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(area_scores)] * len(area_scores)

        for weight, (i, j, k) in zip(weights, smallest_triangles):
            a, b, c = current[i], current[j], current[k]
            
            # Compute signed area for gradient direction
            signed_area = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
            s = np.sign(signed_area)
            
            # Compute gradients for all three points
            grad_i = s * np.array([b[1] - c[1], c[0] - b[0]])
            grad_j = s * np.array([c[1] - a[1], a[0] - c[0]])
            grad_k = s * np.array([a[1] - b[1], b[0] - a[0]])
            
            # Normalize gradients
            for grad in [grad_i, grad_j, grad_k]:
                norm = np.linalg.norm(grad)
                if norm > 1e-10:
                    grad /= norm

            # Add weighted contributions
            gradient[i] += weight * grad_i
            gradient[j] += weight * grad_j
            gradient[k] += weight * grad_k

        # Normalize per-point gradients
        for i in range(11):
            norm = np.linalg.norm(gradient[i])
            if norm > 1e-10:
                gradient[i] /= norm

        return gradient

    def improve(points: np.ndarray) -> np.ndarray:
        rng = np.random.default_rng(seed=42)
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        T = 10 * current_score  # Initial temperature
        iterations = 6000  # Slightly increased from 5000
        no_improve_count = 0
        last_best_score = current_score
        
        # Track recent improvement success for adaptive step sizing
        recent_successes = []
        success_window = 100
        step_factor_base = 0.05  # Will adapt based on success rate
        
        # Adaptive cooling parameters
        base_cooling_rate = 0.999
        min_cooling_rate = 0.998
        max_cooling_rate = 0.9995
        
        for iter_idx in range(iterations):
            # Adaptive k based on current score and area distribution
            smallest_triangles = find_smallest_triangles(current, current_score)
            candidates = []
            
            # Calculate minimum distance for adaptive step sizing
            min_dist = get_min_distance(current)
            
            # Get area scores for the smallest triangles
            area_scores = []
            for (i, j, k) in smallest_triangles:
                a, b, c = current[i], current[j], current[k]
                area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                area_scores.append(area)
            
            # Compute multi-triangle gradient
            gradient = compute_multi_triangle_gradient(current, smallest_triangles, area_scores)
            
            # Adaptive step factor based on proximity to target, min distance, and recent success rate
            target = 0.0365
            score_gap = max(0.0, target - current_score)
            
            # Adjust step_factor_base based on recent success rate
            if len(recent_successes) > 0:
                success_rate = sum(recent_successes) / len(recent_successes)
                # Scale between 0.03 and 0.08 based on success rate
                step_factor_base = 0.03 + 0.05 * success_rate
            
            step_factor = step_factor_base * (1.0 - current_score/target) * min_dist
            
            # Add global exploration move
            random_move = random_point_move(current, no_improve_count)
            if random_move is not None:
                random_score = get_smallest_triangle_area(random_move)
                if random_score > 1e-10:
                    candidates.append((random_move, random_score))

            # Use multi-triangle gradient for targeted moves
            for idx in range(11):
                if np.linalg.norm(gradient[idx]) < 1e-10:
                    continue
                
                direction = gradient[idx]
                step = step_factor * T * direction
                candidate_point = current[idx] + step
                
                if not is_inside_triangle(candidate_point, A, B, C):
                    continue
                
                too_close = False
                for other_idx in range(11):
                    if other_idx == idx:
                        continue
                    if np.linalg.norm(candidate_point - current[other_idx]) < 1e-5:
                        too_close = True
                        break
                if too_close:
                    continue
                
                candidate_config = current.copy()
                candidate_config[idx] = candidate_point
                candidate_score = get_smallest_triangle_area(candidate_config)
                
                if candidate_score < 1e-10:
                    continue
                
                candidates.append((candidate_config, candidate_score))

            # Coordinated multi-point moves with adaptive threshold
            coord_threshold = max(100, 300 * (1.0 - current_score/target))
            if no_improve_count > coord_threshold:
                # Move all three points of the small triangle simultaneously
                for (i, j, k) in smallest_triangles[:3]:  # Only top 3 smallest triangles
                    a, b, c = current[i], current[j], current[k]
                    
                    # Compute signed area for gradient direction
                    signed_area = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                    s = np.sign(signed_area)
                    
                    directions = []
                    for idx, pt in zip([i, j, k], [a, b, c]):
                        if idx == i:
                            grad_x = b[1] - c[1]
                            grad_y = c[0] - b[0]
                        elif idx == j:
                            grad_x = c[1] - a[1]
                            grad_y = a[0] - c[0]
                        else:
                            grad_x = a[1] - b[1]
                            grad_y = b[0] - a[0]
                        
                        direction = s * np.array([grad_x, grad_y])
                        norm = np.linalg.norm(direction)
                        if norm < 1e-10:
                            directions.append(np.zeros(2))
                        else:
                            directions.append(direction / norm)
                    
                    # Apply coordinated step
                    coord_step = step_factor * 0.5 * T
                    candidate_config = current.copy()
                    valid_move = True
                    
                    for idx, direction in zip([i, j, k], directions):
                        candidate_point = current[idx] + coord_step * direction
                        
                        if not is_inside_triangle(candidate_point, A, B, C):
                            valid_move = False
                            break
                        
                        for other_idx in range(11):
                            if other_idx == idx:
                                continue
                            if np.linalg.norm(candidate_point - current[other_idx]) < 1e-5:
                                valid_move = False
                                break
                        if not valid_move:
                            break
                    
                    if valid_move:
                        for idx, direction in zip([i, j, k], directions):
                            candidate_config[idx] = current[idx] + coord_step * direction
                        
                        candidate_score = get_smallest_triangle_area(candidate_config)
                        if candidate_score > 1e-10:
                            candidates.append((candidate_config, candidate_score))

            if not candidates:
                # Adaptive cooling: faster when stuck
                T *= base_cooling_rate
                
                # Track stagnation
                no_improve_count += 1
                continue

            # Select candidate with highest min_area
            candidate_config, candidate_score = max(candidates, key=lambda x: x[1])

            if candidate_score > current_score:
                # Record success for adaptive step sizing
                recent_successes.append(1)
                if len(recent_successes) > success_window:
                    recent_successes.pop(0)

                current = candidate_config
                current_score = candidate_score
                no_improve_count = 0
                
                # Increase temperature slightly after improvement
                T = min(T * (1.05 + 0.05 * (current_score/target)), 10 * target)
                
                if current_score > best_score:
                    best = current
                    best_score = current_score
            else:
                # Record failure
                recent_successes.append(0)
                if len(recent_successes) > success_window:
                    recent_successes.pop(0)

                delta = current_score - candidate_score
                if rng.random() < np.exp(-delta / T):
                    current = candidate_config
                    current_score = candidate_score
                no_improve_count += 1

            # Adaptive cooling rate based on recent progress
            if len(recent_successes) > 0:
                success_rate = sum(recent_successes) / len(recent_successes)
                # Slower cooling when making progress
                cooling_rate = min_cooling_rate + (max_cooling_rate - min_cooling_rate) * (1.0 - success_rate)
            else:
                cooling_rate = base_cooling_rate
            
            T *= cooling_rate

            # Early termination if temperature too low or diminishing returns
            if T < 1e-7 or (iter_idx > 1000 and no_improve_count > 500 and current_score < 0.9 * target):
                break

        return best

    return improve