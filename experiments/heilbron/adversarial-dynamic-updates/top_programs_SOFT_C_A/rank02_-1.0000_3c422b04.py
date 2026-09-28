import random
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.spatial import Delaunay

np.random.seed(42)
random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    # Precompute denominator for barycentric conversion (2 * area of ABC)
    denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
    
    # Precompute side length for geometry-aware step sizing
    side_length = np.linalg.norm(B - A)
    
    # Helper functions for barycentric conversion
    def to_bary(p):
        u = ((B[1] - C[1]) * (p[0] - C[0]) + (C[0] - B[0]) * (p[1] - C[1])) / denom
        v = ((C[1] - A[1]) * (p[0] - C[0]) + (A[0] - C[0]) * (p[1] - C[1])) / denom
        return u, v

    def to_cart(u, v):
        w = 1 - u - v
        return u * A + v * B + w * C

    def get_boundary_projection(p, grad):
        """Project gradient to be tangent to nearest boundary with stable epsilon handling."""
        u, v = to_bary(p)
        w = 1 - u - v
        
        # Stable boundary detection epsilon (maintains reasonable value even near optimum)
        epsilon = max(1e-5, 0.0001 * (1.0 - min(0.0365, best_score) / 0.0365))
        
        # Find closest boundary
        min_coord = min(u, v, w)
        
        if min_coord < epsilon:
            if u <= v and u <= w:  # Closest to BC edge (u=0)
                # Project gradient to be parallel to BC edge
                bc_dir = C - B
                bc_dir = bc_dir / (np.linalg.norm(bc_dir) + 1e-9)
                proj = np.dot(grad, bc_dir) * bc_dir
                return proj
            elif v <= u and v <= w:  # Closest to AC edge (v=0)
                # AC edge direction: C - A
                ac_dir = C - A
                ac_dir = ac_dir / (np.linalg.norm(ac_dir) + 1e-9)
                proj = np.dot(grad, ac_dir) * ac_dir
                return proj
            else:  # Closest to AB edge (w=0)
                # AB edge direction: B - A
                ab_dir = B - A
                ab_dir = ab_dir / (np.linalg.norm(ab_dir) + 1e-9)
                proj = np.dot(grad, ab_dir) * ab_dir
                return proj
        
        return grad

    def calculate_triangle_properties(points, i, j, k):
        """Calculate area and perimeter of triangle formed by three points."""
        x1, y1 = points[i]
        x2, y2 = points[j]
        x3, y3 = points[k]
        
        # Area calculation
        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
        
        # Perimeter calculation
        d1 = np.linalg.norm(points[i] - points[j])
        d2 = np.linalg.norm(points[j] - points[k])
        d3 = np.linalg.norm(points[k] - points[i])
        perimeter = d1 + d2 + d3
        
        return area, perimeter

    # Compute side length for boundary distance calculations
    side_length = np.linalg.norm(B - A)
    
    # Generate adaptive geometric progression pattern based on fitness landscape
    # Instead of fixed [2,3,3,2,1], create flexible row distribution
    points = []
    
    # Adaptive row generation based on current fitness landscape understanding
    def generate_adaptive_rows(total_points=11):
        # Base ratio that adapts as we approach optimum
        base_ratio = 0.7 + 0.2 * (best_score / 0.0365) if 'best_score' in globals() else 0.7
        rows = []
        current = 2  # Start with at least 2 points in first row
        
        while sum(rows) + current <= total_points:
            rows.append(int(current))
            current = max(1, min(5, int(current * base_ratio)))  # Cap rows between 1-5 points
        
        # Distribute remaining points to balance the pattern
        remaining = total_points - sum(rows)
        for i in range(min(remaining, len(rows))):
            rows[i] += 1
        
        # Ensure we have at least 3 rows for stability
        while len(rows) < 3 and sum(rows) < total_points:
            rows.append(1)
            
        return rows

    rows = generate_adaptive_rows()
    total_rows = len(rows)
    
    # Dynamic height scaling proportional to fitness gap
    height_margin = 0.05 + 0.1 * (0.0365 - 0.00123) / 0.0365
    
    for i, count in enumerate(rows):
        # Adjust height position with margin to avoid boundary issues
        v = (i + height_margin) / (total_rows + 2 * height_margin - 1)
        
        # Adjust horizontal spacing based on row position
        for j in range(count):
            u = (j + 0.5) / count * (1 - v)
            P = to_cart(u, v)
            points.append(P)
    
    # Population-based (1+λ) evolution strategy
    POP_SIZE = 12
    OFFSPRING_PER_PARENT = 2

    # Initialize population with perturbed versions of the base configuration
    population = []
    for _ in range(POP_SIZE):
        individual = np.array(points).copy()
        # Apply random perturbations in barycentric space
        for i in range(len(individual)):
            u, v = to_bary(individual[i])
            du = np.random.uniform(-0.05, 0.05)
            dv = np.random.uniform(-0.05, 0.05)
            u_new, v_new = u + du, v + dv
            
            # Clamp to simplex
            u_new = max(0.0, min(1.0, u_new))
            v_new = max(0.0, min(1.0, v_new))
            if u_new + v_new > 1.0:
                scale = 1.0 / (u_new + v_new)
                u_new *= scale
                v_new *= scale
            
            individual[i] = to_cart(u_new, v_new)
        population.append(individual)

    # Evaluate initial population
    scores = [get_smallest_triangle_area(ind) for ind in population]
    best_idx = np.argmax(scores)
    best_points = population[best_idx].copy()
    best_score = scores[best_idx]

    # Main optimization loop
    max_iter = 150
    stagnation_threshold = 25
    stagnation_count = 0

    # Initialize triangle area cache for all combinations
    all_triangles = [(i, j, k) for i in range(11) for j in range(i+1, 11) for k in range(j+1, 11)]
    
    # Momentum tracking for gradient history
    momentum = np.zeros((11, 2))
    momentum_decay = 0.85

    for _ in range(max_iter):
        # Generate offspring through different strategies
        offspring = []
        
        # Strategy 1: Coordinated multi-point gradient moves (fixing single_point_gradient rigidity)
        for parent_idx in range(POP_SIZE):
            parent = population[parent_idx]
            min_area = get_smallest_triangle_area(parent)
            
            # Compute fitness gap for adaptive step sizing
            fitness_gap = max(0.0, 0.0365 - min_area)
            step_factor = fitness_gap / 0.0365
            
            # Use Delaunay triangulation to identify candidate minimal triangles
            try:
                tri = Delaunay(parent)
                candidate_triples = []
                
                for simplex in tri.simplices:
                    i, j, k = simplex
                    area, _ = calculate_triangle_properties(parent, i, j, k)
                    candidate_triples.append((i, j, k, area))
                
                # Sort by area and take top candidates
                candidate_triples.sort(key=lambda x: x[3])
                min_triples = [(i, j, k) for i, j, k, a in candidate_triples[:5]]
            except:
                # Fallback to exhaustive search if Delaunay fails
                min_triples = []
                min_area = float('inf')
                all_areas = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            area, _ = calculate_triangle_properties(parent, i, j, k)
                            all_areas.append(area)
                            if area < min_area - 1e-9:
                                min_area = area
                                min_triples = [(i, j, k)]
                            elif abs(area - min_area) < 1e-9:
                                min_triples.append((i, j, k))

            # Calculate global minimum area across all triangles
            global_min_area = min_area
            
            # Calculate mean perimeter for weighting
            mean_perimeter = 0
            count = 0
            for i, j, k in min_triples:
                _, perimeter = calculate_triangle_properties(parent, i, j, k)
                mean_perimeter += perimeter
                count += 1
            mean_perimeter = mean_perimeter / count if count > 0 else 1.0

            # Apply coordinated multi-point gradient moves
            for triplet in min_triples:
                i, j, k = triplet
                p_i, p_j, p_k = parent[i], parent[j], parent[k]

                # Calculate area and perimeter of this triangle
                area, perimeter = calculate_triangle_properties(parent, i, j, k)
                
                # Weight based on proximity to global minimum and perimeter (skinny triangles prioritized)
                area_weight = 1.0 / (area - global_min_area + 1e-10)
                perimeter_weight = perimeter / mean_perimeter
                total_weight = area_weight * perimeter_weight

                # Calculate gradients for area increase
                grad_i = 0.5 * np.array([p_k[1] - p_j[1], p_j[0] - p_k[0]]) * total_weight
                grad_j = 0.5 * np.array([p_i[1] - p_k[1], p_k[0] - p_i[0]]) * total_weight
                grad_k = 0.5 * np.array([p_j[1] - p_i[1], p_i[0] - p_j[0]]) * total_weight

                # Normalize gradients
                norm_i = np.linalg.norm(grad_i)
                norm_j = np.linalg.norm(grad_j)
                norm_k = np.linalg.norm(grad_k)

                # Apply momentum to gradients
                if norm_i > 0:
                    grad_i = grad_i / norm_i
n                    momentum[i] = momentum_decay * momentum[i] + (1 - momentum_decay) * grad_i
                    grad_i = momentum[i] * (norm_i if norm_i > 0 else 0)
                if norm_j > 0:
                    grad_j = grad_j / norm_j
                    momentum[j] = momentum_decay * momentum[j] + (1 - momentum_decay) * grad_j
                    grad_j = momentum[j] * (norm_j if norm_j > 0 else 0)
                if norm_k > 0:
                    grad_k = grad_k / norm_k
                    momentum[k] = momentum_decay * momentum[k] + (1 - momentum_decay) * grad_k
                    grad_k = momentum[k] * (norm_k if norm_k > 0 else 0)

                # Set step size based on geometry (side_length/50)
                step_size = side_length / 50.0 * step_factor

                # Apply boundary-aware projection to all gradients
                grad_i = get_boundary_projection(p_i, grad_i)
                grad_j = get_boundary_projection(p_j, grad_j)
                grad_k = get_boundary_projection(p_k, grad_k)

                # Create candidate by moving all critical points
                candidate = parent.copy()
                candidate[i] += grad_i * step_size
                candidate[j] += grad_j * step_size
                candidate[k] += grad_k * step_size

                # Check containment with boundary awareness
                if is_inside_triangle(candidate, A, B, C):
                    offspring.append(candidate)

        # Strategy 2: Adaptive vertex selection with perimeter weighting
        for parent_idx in range(POP_SIZE):
            parent = population[parent_idx]
            min_area = get_smallest_triangle_area(parent)
            fitness_gap = max(0.0, 0.0365 - min_area)
            
            # Adaptive perturbation range with sqrt scaling
            perturb_range = 0.1 * np.sqrt(fitness_gap / 0.0365 + 1e-5)
            
            # Count vertex frequencies with weighted contribution (including perimeter)
            freq = [0] * 11
            min_triples = []
            min_area = float('inf')
            all_perimeters = []
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        area, perimeter = calculate_triangle_properties(parent, i, j, k)
                        all_perimeters.append(perimeter)
                        if area < min_area - 1e-9:
                            min_area = area
                            min_triples = [(i, j, k)]
                        elif abs(area - min_area) < 1e-9:
                            min_triples.append((i, j, k))
                        # Weighted frequency based on inverse area and perimeter
                        weight = (1.0 / (area + 1e-10)) * (perimeter / (np.mean(all_perimeters) + 1e-10))
                        freq[i] += weight
                        freq[j] += weight
                        freq[k] += weight
            
            # Adaptive count of vertices to perturb based on fitness gap
            adaptive_vertex_count = max(3, min(6, int(3 + 5 * (fitness_gap / 0.0365))))
            
            # Select top vertices to perturb based on weighted frequency
            top_vertices = np.argsort(freq)[-adaptive_vertex_count:]
            
            for idx in top_vertices:
                candidate = parent.copy()
                u, v = to_bary(candidate[idx])
                
                # Adaptive perturbation magnitude
                du = np.random.normal(0, perturb_range)
                dv = np.random.normal(0, perturb_range)
                u_new, v_new = u + du, v + dv
                
                # Clamp to simplex
                u_new = max(0.0, min(1.0, u_new))
                v_new = max(0.0, min(1.0, v_new))
                if u_new + v_new > 1.0:
                    scale = 1.0 / (u_new + v_new)
                    u_new *= scale
                    v_new *= scale
                
                candidate[idx] = to_cart(u_new, v_new)
                offspring.append(candidate)

        # Strategy 3: Bounded restart with adaptive intensity
        for parent_idx in range(POP_SIZE):
            parent = population[parent_idx]
            min_area = get_smallest_triangle_area(parent)
            fitness_gap = max(0.0, 0.0365 - min_area)
            
            # Bounded restart intensity with sigmoid scaling
            # Original: 0.2 * (1 + 15 * fitness_gap)
            # New: capped at 0.5 with smoother transition
            sigmoid_factor = 1 / (1 + np.exp(-15 * (fitness_gap / 0.0365 - 0.5)))
            restart_intensity = 0.2 + 0.3 * sigmoid_factor
            
            candidate = parent.copy()
            for i in range(11):
                u, v = to_bary(parent[i])
                du = np.random.normal(0, restart_intensity * 0.05)
                dv = np.random.normal(0, restart_intensity * 0.05)
                u_new, v_new = u + du, v + dv
                
                # Clamp to simplex
                u_new = max(0.0, min(1.0, u_new))
                v_new = max(0.0, min(1.0, v_new))
                if u_new + v_new > 1.0:
                    scale = 1.0 / (u_new + v_new)
                    u_new *= scale
                    v_new *= scale
                
                candidate[i] = to_cart(u_new, v_new)
            offspring.append(candidate)

        # Evaluate all offspring
        offspring_scores = [get_smallest_triangle_area(child) for child in offspring]
        
        # Combine population and offspring for selection
        all_individuals = population + offspring
        all_scores = scores + offspring_scores
        
        # Select top POP_SIZE individuals
        sorted_indices = np.argsort(all_scores)[::-1]  # Descending order
        population = [all_individuals[i] for i in sorted_indices[:POP_SIZE]]
        scores = [all_scores[i] for i in sorted_indices[:POP_SIZE]]

        # Update best solution if improved
        if scores[0] > best_score:
            best_points = population[0].copy()
            best_score = scores[0]
            stagnation_count = 0
        else:
            stagnation_count += 1

        # Check for stagnation and apply diversity preservation
        if stagnation_count >= stagnation_threshold:
            # Introduce diversity with adaptive perturbation size
            adaptive_perturb = 0.1 * (1 - best_score / 0.0365)
            for i in range(POP_SIZE):
                if i > 0:  # Keep the best solution mostly intact
                    for j in range(11):
                        u, v = to_bary(population[i][j])
                        du = np.random.normal(0, adaptive_perturb)
                        dv = np.random.normal(0, adaptive_perturb)
                        u_new, v_new = u + du, v + dv
                        
                        # Clamp to simplex
                        u_new = max(0.0, min(1.0, u_new))
                        v_new = max(0.0, min(1.0, v_new))
                        if u_new + v_new > 1.0:
                            scale = 1.0 / (u_new + v_new)
                            u_new *= scale
                            v_new *= scale
                        
                        population[i][j] = to_cart(u_new, v_new)
                    
            # Recompute scores after diversity preservation
            scores = [get_smallest_triangle_area(ind) for ind in population]
            stagnation_count = 0

    return best_points