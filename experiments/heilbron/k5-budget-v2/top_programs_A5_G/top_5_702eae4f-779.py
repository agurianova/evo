# --- G's code (entrypoint renamed to _g_entrypoint) ---
import random
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)
random.seed(42)

def generate_fps_config(A, B, C, n):
    points = []
    
    # First point: random inside triangle using barycentric coordinates
    u = random.random()
    v = random.random() * (1 - u)
    w = 1 - u - v
    p = u * A + v * B + w * C
    points.append(p)

    for _ in range(1, n):
        best_candidate = None
        best_min_dist_sq = -1
        
        # Sample 1000 candidate points
        for _ in range(1000):
            u = random.random()
            v = random.random() * (1 - u)
            w = 1 - u - v
            candidate = u * A + v * B + w * C
            
            # Compute min squared distance to existing points
            min_dist_sq = float('inf')
            for p in points:
                diff = candidate - p
                dist_sq = np.sum(diff ** 2)
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
            
            if min_dist_sq > best_min_dist_sq:
                best_min_dist_sq = min_dist_sq
                best_candidate = candidate

        points.append(best_candidate)
    
    return np.array(points)

def tournament_selection(population, k, A, B, C):
    selected = random.sample(population, k)
    return max(selected, key=lambda x: x[1])

def mutate(config, gen, max_gen, initial_step, A, B, C):
    n = len(config)
    new_config = config.copy()
    
    # Determine mutation focus
    if random.random() < 0.7:
        # Focus on critical triangles (smallest area triangles)
        areas = []
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    area = get_smallest_triangle_area(np.array([config[i], config[j], config[k]]))
                    areas.append((area, i, j, k))
        
        # Sort by area ascending and take top 3 smallest
        areas.sort(key=lambda x: x[0])
        critical_triangles = areas[:min(3, len(areas))]
        
        # Randomly select one critical triangle
        _, i, j, k = random.choice(critical_triangles)
        # Randomly select one point from the triangle
        idx = random.choice([i, j, k])
    else:
        # Random point mutation
        idx = random.randint(0, n-1)

    # Adaptive step size
    step_size = initial_step * (1 - gen / max_gen)
    
    # Generate displacement
    displacement = np.random.uniform(-1, 1, 2)
    if np.linalg.norm(displacement) > 0:
        displacement = displacement / np.linalg.norm(displacement) * step_size
    
    # Apply displacement with boundary and distinctness checks
    original_point = new_config[idx].copy()
    candidate = original_point + displacement
    
    # Boundary check
    if not is_inside_triangle(candidate, A, B, C):
        # Try reduced steps
        for _ in range(5):
            displacement *= 0.5
            candidate = original_point + displacement
            if is_inside_triangle(candidate, A, B, C):
                break
        else:
            # Fallback: random direction within triangle
            candidate = None
            for _ in range(10):
                offset = np.random.uniform(-step_size, step_size, 2)
                candidate = original_point + offset
                if is_inside_triangle(candidate, A, B, C):
                    break
            if candidate is None or not is_inside_triangle(candidate, A, B, C):
                candidate = original_point
    
    # Distinctness check (using squared distance)
    valid = True
    for i in range(n):
        if i == idx:
            continue
        diff = candidate - new_config[i]
        dist_sq = np.sum(diff ** 2)
        if dist_sq < 1e-10:  # 1e-5 squared
            valid = False
            break
    
    if valid:
        new_config[idx] = candidate
    
    return new_config

def _g_entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    base_length = np.linalg.norm(B - A)
    
    # Parameters
    pop_size = 50
    n_generations = 100
    initial_step = 0.1 * base_length

    # Generate initial population
    population = []
    for _ in range(pop_size):
        config = generate_fps_config(A, B, C, 11)
        fitness = get_smallest_triangle_area(config)
        population.append((config, fitness))

    # Evolutionary loop
    for gen in range(n_generations):
        offspring = []
        for _ in range(pop_size):
            # Selection
            parent_config, _ = tournament_selection(population, 3, A, B, C)
            # Mutation
            child_config = mutate(parent_config, gen, n_generations, initial_step, A, B, C)
            child_fitness = get_smallest_triangle_area(child_config)
            offspring.append((child_config, child_fitness))

        # Combine and select next generation
        combined = population + offspring
        combined.sort(key=lambda x: x[1], reverse=True)
        population = combined[:pop_size]

    # Return best configuration
    best_config, _ = population[0]
    return best_config

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def _d_entrypoint():
    A, B, C = get_unit_triangle()

    def triangle_area(a, b, c):
        return 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))

    def find_k_smallest_triangles(pts, k):
        n = pts.shape[0]
        triangles = []
        for i in range(n):
            for j in range(i+1, n):
                for k_idx in range(j+1, n):
                    area = triangle_area(pts[i], pts[j], pts[k_idx])
                    triangles.append((area, i, j, k_idx))
        triangles.sort(key=lambda x: x[0])
        return triangles[:k]

    def project_to_boundary(point, A, B, C):
        """Project a point to the closest point on the triangle boundary."""
        if is_inside_triangle(point, A, B, C):
            return point.copy()
        
        def point_to_line_distance(p, a, b):
            ab = b - a
            ap = p - a
            t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-12)
            t = max(0, min(1, t))
            projection = a + t * ab
            return projection, np.linalg.norm(p - projection)
        
        p_ab, d_ab = point_to_line_distance(point, A, B)
        p_bc, d_bc = point_to_line_distance(point, B, C)
        p_ca, d_ca = point_to_line_distance(point, C, A)
        
        if d_ab <= d_bc and d_ab <= d_ca:
            return p_ab
        elif d_bc <= d_ab and d_bc <= d_ca:
            return p_bc
        else:
            return p_ca

    def improve(points: np.ndarray) -> np.ndarray:
        # Make seed input-dependent to diversify exploration
        np.random.seed(hash(points.tobytes()) % (2**32))
        
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        initial_temp = 0.1  # Increased from 0.01 to allow more exploration
        cooling_rate = 0.995  # Adjusted from 0.999 for better balance
        current_temp = initial_temp
        rounds = 500

        for round in range(rounds):
            # Adaptive triangle selection based on area distribution
            all_triangles = find_k_smallest_triangles(current, 10)
            if len(all_triangles) > 1:
                smallest_area = all_triangles[0][0]
                next_smallest = all_triangles[1][0]
                ratio = smallest_area / (next_smallest + 1e-12)
                
                # If smallest areas are very close, select more triangles
                if ratio < 0.9:  # Areas are relatively close
                    num_triangles = min(5, len(all_triangles))
                elif ratio < 0.95:
                    num_triangles = min(3, len(all_triangles))
                else:
                    num_triangles = 1
            else:
                num_triangles = 1

            triangles = all_triangles[:num_triangles]
            
            # Track how many triangles each point is in for gradient normalization
            point_gradients = {}
            point_triangle_counts = {}
            for _, i, j, k in triangles:
                for idx in [i, j, k]:
                    point_triangle_counts[idx] = point_triangle_counts.get(idx, 0) + 1

                a, b, c = current[i], current[j], current[k]

                f = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                sign_f = 1.0 if f >= 0 else -1.0

                grad_a = np.array([b[1]-c[1], c[0]-b[0]]) * 0.5 * sign_f
                grad_b = np.array([c[1]-a[1], a[0]-c[0]]) * 0.5 * sign_f
                grad_c = np.array([a[1]-b[1], b[0]-a[0]]) * 0.5 * sign_f

                for idx, grad in [(i, grad_a), (j, grad_b), (k, grad_c)]:
                    if idx in point_gradients:
                        point_gradients[idx] += grad
                    else:
                        point_gradients[idx] = grad

            # Normalize gradients by triangle count
            for idx in point_gradients:
                point_gradients[idx] /= point_triangle_counts[idx]

            step_size_val = 0.01 * (0.99 ** round)  # Reduced initial size and increased decay

            def normalize_grad(grad, step_size):
                norm = np.linalg.norm(grad)
                if norm < 1e-8:
                    return np.zeros(2)
                return grad / norm * step_size

            candidate = current.copy()
            for idx, grad in point_gradients.items():
                delta = normalize_grad(grad, step_size_val)
                candidate[idx] += delta

            # Project each point to boundary if needed
            for idx in range(candidate.shape[0]):
                candidate[idx] = project_to_boundary(candidate[idx], A, B, C)

            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - current_score

            if delta > 0 or np.random.rand() < np.exp(delta / current_temp):
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score

            current_temp *= cooling_rate

        return best

    return improve

def entrypoint():
    """Lamarckian composition: D applied to G's output."""
    g_output = _g_entrypoint()
    d_callable = _d_entrypoint()
    return d_callable(g_output)