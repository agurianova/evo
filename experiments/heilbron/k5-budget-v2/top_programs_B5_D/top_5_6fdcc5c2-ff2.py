from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        # Set up RNG with per-configuration seed
        rounded_points = np.round(points, 8)
        seed = hash(tuple(map(tuple, rounded_points))) % (2**32)
        rng = np.random.default_rng(seed)

        # Simulated annealing parameters - increased for better exploration
        n_iterations = 1000  # Increased from 500
        initial_temp = 0.01   # Increased from 0.005
        decay = 0.995         # Slightly slower decay
        base_step = 0.1       # Increased from 0.05
        temp = initial_temp
        tol = 1e-12

        current = points.copy()
        current_score = get_smallest_triangle_area(current)

        # Track recent improvements for adaptive step size
        recent_improvements = []

        for _ in range(n_iterations):
            # Find all triangles achieving minimal area
            min_area = float('inf')
            min_triangles = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        a, b, c = current[i], current[j], current[k]
                        area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        if area < min_area - tol:
                            min_area = area
                            min_triangles = [(i, j, k)]
                        elif abs(area - min_area) <= tol:
                            min_triangles.append((i, j, k))
            
            # Count how many minimal triangles each point appears in (for weighting)
            point_counts = np.zeros(11, dtype=int)
            for i, j, k in min_triangles:
                point_counts[i] += 1
                point_counts[j] += 1
                point_counts[k] += 1
            
            # Weight selection by critical points (points in many min triangles)
            triangle_weights = []
            for i, j, k in min_triangles:
                weight = point_counts[i] + point_counts[j] + point_counts[k]
                triangle_weights.append(weight)
            
            # Normalize weights for probability distribution
            total_weight = sum(triangle_weights)
            if total_weight > 0:
                triangle_weights = [w / total_weight for w in triangle_weights]
            else:
                triangle_weights = [1 / len(min_triangles)] * len(min_triangles)
            
            # Select one minimal triangle with weighted probability
            triangle_idx = rng.choice(len(min_triangles), p=triangle_weights)
            triangle = min_triangles[triangle_idx]
            i, j, k = triangle

            # Compute directional perturbation:
            # For points i,j,k, we'll move point k perpendicular to line ij
            # But we want to be able to move any of the three points, so we'll choose one randomly
            move_idx = rng.choice([i, j, k])
            fixed_idx1, fixed_idx2 = [idx for idx in triangle if idx != move_idx]
            
            # Vector between the two fixed points
            v = current[fixed_idx2] - current[fixed_idx1]
            # Perpendicular vector (height direction)
            normal = np.array([-v[1], v[0]])
            norm_norm = np.linalg.norm(normal)
            if norm_norm < 1e-10:
                # Degenerate case - use isotropic as fallback
                direction = rng.normal(0, 1, size=2)
                direction = direction / np.linalg.norm(direction)
            else:
                normal = normal / norm_norm
                # Decide direction: we want to move away from the line to increase area
                # Compute signed distance from move point to line
                d = np.dot(normal, current[move_idx] - current[fixed_idx1])
                direction = normal if d >= 0 else -normal
            
            # Create candidate by perturbing just one point in the height direction
            candidate = current.copy()
            step_size = base_step * (temp / initial_temp)
            
            # Adaptive step size based on recent improvements
            if len(recent_improvements) > 10:
                avg_improvement = np.mean(recent_improvements[-10:])
                if avg_improvement < 1e-6:  # Very small improvements
                    step_size *= 1.2  # Increase exploration
                elif avg_improvement > 1e-4:  # Good improvements
                    step_size *= 0.8  # Refine current area
            
            # Perturb in the height direction
            candidate[move_idx] += step_size * direction * rng.uniform(0.5, 1.5)

            # Check containment
            if not is_inside_triangle(candidate, A, B, C):
                # Try smaller steps if outside
                for attempt in range(3):
                    candidate[move_idx] -= (step_size * 0.3 * direction * rng.uniform(0.5, 1.5))
                    if is_inside_triangle(candidate, A, B, C):
                        break
                else:
                    temp *= decay
                    continue

            # Evaluate candidate
            new_score = get_smallest_triangle_area(candidate)

            # Track improvements for adaptive step size
            if new_score > current_score:
                recent_improvements.append(new_score - current_score)
                if len(recent_improvements) > 50:
                    recent_improvements.pop(0)

            # Simulated annealing acceptance
            if new_score > current_score:
                current, current_score = candidate, new_score
            else:
                delta = new_score - current_score
                if rng.random() < np.exp(delta / temp):
                    current, current_score = candidate, new_score

            # Cool down
            temp *= decay

        return current

    return improve