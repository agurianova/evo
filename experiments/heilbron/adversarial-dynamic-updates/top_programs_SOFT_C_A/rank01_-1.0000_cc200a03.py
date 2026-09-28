import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
from scipy.spatial import Voronoi, ConvexHull
import matplotlib.path as mpath

np.random.seed(42)

def entrypoint() -> np.ndarray:
    # Get the unit triangle vertices
    A, B, C = get_unit_triangle()
    
    # Precompute denominator for barycentric conversion
    denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
    
    def to_bary(p):
        u = ((B[1] - C[1]) * (p[0] - C[0]) + (C[0] - B[0]) * (p[1] - C[1])) / denom
        v = ((C[1] - A[1]) * (p[0] - C[0]) + (A[0] - C[0]) * (p[1] - C[1])) / denom
        return np.array([u, v])
    
    def to_cart(u, v):
        w = 1 - u - v
        return u * A + v * B + w * C
    
    def clamp_bary(u, v):
        """Clamp barycentric coordinates to be inside the triangle."""
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))
        if u + v > 1.0:
            scale = 1.0 / (u + v)
            u *= scale
            v *= scale
        return u, v

    def get_boundary_projection(p, grad):
        """Project gradient to be tangent to nearest boundary if point is near edge."""
        u, v = to_bary(p)
        w = 1 - u - v
        
        # Find closest boundary
        min_coord = min(u, v, w)
        epsilon = 1e-5
        
        if min_coord < epsilon:
            if u <= v and u <= w:  # Closest to BC edge (u=0)
                # Project gradient to be parallel to BC edge
                bc_dir = C - B
                bc_dir = bc_dir / np.linalg.norm(bc_dir)
                proj = np.dot(grad, bc_dir) * bc_dir
                return proj
            elif v <= u and v <= w:  # Closest to AC edge (v=0)
                # AC edge direction: C - A
                ac_dir = C - A
                ac_dir = ac_dir / np.linalg.norm(ac_dir)
                proj = np.dot(grad, ac_dir) * ac_dir
                return proj
            else:  # Closest to AB edge (w=0)
                # AB edge direction: B - A
                ab_dir = B - A
                ab_dir = ab_dir / np.linalg.norm(ab_dir)
                proj = np.dot(grad, ab_dir) * ab_dir
                return proj
        
        return grad

    def generate_voronoi_interior_points(boundary_points, n_interior, max_iter=10):
        """Generate interior points using Voronoi tessellation with Lloyd's algorithm."""
        # Create triangular boundary path for clipping
        triangle = np.array([A, B, C])
        path = mpath.Path(triangle)
        
        # Start with random interior points
        interior_points = []
        for _ in range(n_interior):
            while True:
                u = np.random.uniform(0.1, 0.9)
                v = np.random.uniform(0, 1 - u)
                point = to_cart(u, v)
                if path.contains_point(point):
                    interior_points.append(point)
                    break
        
        all_points = np.vstack([boundary_points, interior_points])
        
        # Apply Lloyd's algorithm for centroidal Voronoi tessellation
        for _ in range(max_iter):
            # Generate Voronoi diagram
            vor = Voronoi(all_points)
            
            # Calculate centroids of Voronoi regions within triangle
            new_interior = []
            for i in range(len(boundary_points), len(all_points)):
                region = vor.regions[vor.point_region[i]]
                if -1 not in region and len(region) > 0:
                    # Get vertices of the Voronoi region
                    vertices = vor.vertices[region]
                    
                    # Clip region to triangle
                    clipped = []
                    for vertex in vertices:
                        if path.contains_point(vertex):
                            clipped.append(vertex)
                    
                    # Calculate centroid of clipped region
                    if len(clipped) >= 3:
                        try:
                            hull = ConvexHull(clipped)
                            centroid = np.mean(np.array(clipped)[hull.vertices], axis=0)
                            new_interior.append(centroid)
                        except:
                            # Fallback to simple mean if ConvexHull fails
                            new_interior.append(np.mean(clipped, axis=0))
                    else:
                        # Keep original point if region is invalid
                        new_interior.append(all_points[i])
                else:
                    # Keep original point if region is unbounded or empty
                    new_interior.append(all_points[i])
            
            # Update interior points
            interior_points = new_interior
            all_points = np.vstack([boundary_points, interior_points])
        
        return np.array(interior_points)

    def calculate_gradient(triangle_points):
        """Calculate analytical gradients for maximizing triangle area."""
        p1, p2, p3 = triangle_points
        
        # Gradient for p1: 0.5 * (p3 - p2) rotated 90 degrees
        grad1 = 0.5 * np.array([p3[1] - p2[1], p2[0] - p3[0]])
        
        # Gradient for p2: 0.5 * (p1 - p3) rotated 90 degrees
        grad2 = 0.5 * np.array([p1[1] - p3[1], p3[0] - p1[0]])
        
        # Gradient for p3: 0.5 * (p2 - p1) rotated 90 degrees
        grad3 = 0.5 * np.array([p2[1] - p1[1], p1[0] - p2[0]])
        
        # Normalize gradients
        norm1 = np.linalg.norm(grad1)
        norm2 = np.linalg.norm(grad2)
        norm3 = np.linalg.norm(grad3)
        
        if norm1 > 1e-10:
            grad1 = grad1 / norm1
        if norm2 > 1e-10:
            grad2 = grad2 / norm2
        if norm3 > 1e-10:
            grad3 = grad3 / norm3

        return grad1, grad2, grad3

    def generate_initial_config(pattern='balanced'):
        """Generate initial configurations with strategic placement based on pattern type."""
        points = []
        
        if pattern == 'vertex-focused':
            # 1 point near each vertex (total 3)
            offset = np.random.uniform(0.02, 0.04)
            points.append(to_cart(offset, offset))  # Near A
            points.append(to_cart(1-offset, offset))  # Near B
            points.append(to_cart(offset, 1-offset))  # Near C
            
            # 4 points along edges (total 4)
            edge_points = [
                (0.25, 0),
                (0.75, 0),
                (0, 0.25),
                (0.25, 0.75)
            ]
            for u, v in edge_points:
                u += np.random.uniform(-0.03, 0.03)
                v += np.random.uniform(-0.03, 0.03)
                u, v = clamp_bary(u, v)
                points.append(to_cart(u, v))
            
            # 4 interior points using Voronoi tessellation
            boundary_points = np.array(points)
            interior_points = generate_voronoi_interior_points(boundary_points, 4)
            points.extend(interior_points)

        elif pattern == 'edge-focused':
            # 1 point near each vertex (total 3)
            offset = np.random.uniform(0.05, 0.1)
            points.append(to_cart(offset, offset))  # Near A
            points.append(to_cart(1-offset, offset))  # Near B
            points.append(to_cart(offset, 1-offset))  # Near C
            
            # 5 points along edges (total 5)
            edge_points = [
                (0.2, 0),
                (0.4, 0),
                (0.6, 0),
                (0, 0.3),
                (0.3, 0.7)
            ]
            for u, v in edge_points:
                u += np.random.uniform(-0.03, 0.03)
                v += np.random.uniform(-0.03, 0.03)
                u, v = clamp_bary(u, v)
                points.append(to_cart(u, v))
            
            # 3 interior points using Voronoi tessellation
            boundary_points = np.array(points)
            interior_points = generate_voronoi_interior_points(boundary_points, 3)
            points.extend(interior_points)

        else:  # 'balanced' or default
            # 1 point near each vertex (total 3)
            offset = np.random.uniform(0.03, 0.07)
            points.append(to_cart(offset, offset))  # Near A
            points.append(to_cart(1-offset, offset))  # Near B
            points.append(to_cart(offset, 1-offset))  # Near C
            
            # 3 points along edges (total 3)
            edge_points = [
                (0.35, 0),
                (0, 0.35),
                (0.35, 0.65)
            ]
            for u, v in edge_points:
                u += np.random.uniform(-0.03, 0.03)
                v += np.random.uniform(-0.03, 0.03)
                u, v = clamp_bary(u, v)
                points.append(to_cart(u, v))
            
            # 5 interior points using Voronoi tessellation
            boundary_points = np.array(points)
            interior_points = generate_voronoi_interior_points(boundary_points, 5)
            points.extend(interior_points)

        return np.array(points)

    def optimize_configuration(initial_points):
        # Convert all points to barycentric for internal processing
        bary_points = np.array([to_bary(p) for p in initial_points])
        best_bary = bary_points.copy()
        best_points = initial_points.copy()
        best_score = get_smallest_triangle_area(best_points)
        
        # Parameters for local search
        initial_step = 0.05
        gradient_step = initial_step  # For gradient-based moves
        random_step = initial_step * 0.8  # For random exploration moves
        stagnation_count = 0
        max_iterations = 800  # Increased from 600
        tol = 1e-10
        n = 11
        min_area = best_score
        area_threshold_factor = 1.03  # Reduced from 1.1 for sharper focus
        improvement_window = 20
        improvement_history = [0] * improvement_window
        improvement_idx = 0

        for _ in range(max_iterations):
            # Find all triangles with area < area_threshold_factor * min_area
            min_area = float('inf')
            min_triplets = []
            
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = best_points[i]
                        x2, y2 = best_points[j]
                        x3, y3 = best_points[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area < min_area - tol:
                            min_area = area
                            min_triplets = [(i, j, k)]
                        elif abs(area - min_area) < tol or area < area_threshold_factor * min_area:
                            min_triplets.append((i, j, k))
            
            if not min_triplets:
                break

            # Count vertex frequencies in relevant triangles
            freq = [0] * n
            for triplet in min_triplets:
                for idx in triplet:
                    freq[idx] += 1
            
            # Calculate analytical gradients for each minimal triangle
            gradient_vectors = np.zeros((n, 2))
            for triplet in min_triplets:
                i, j, k = triplet
                p1, p2, p3 = best_points[i], best_points[j], best_points[k]
                
                # Calculate analytical gradients for area maximization
                grad1, grad2, grad3 = calculate_gradient([p1, p2, p3])
                
                # Weight gradients by frequency
                weight = 1.0 / (len(min_triplets) * freq[i] * freq[j] * freq[k]) ** 0.33
                gradient_vectors[i] += weight * grad1
                gradient_vectors[j] += weight * grad2
                gradient_vectors[k] += weight * grad3

            # Normalize gradient vectors
            for i in range(n):
                norm = np.linalg.norm(gradient_vectors[i])
                if norm > 1e-10:
                    gradient_vectors[i] = gradient_vectors[i] / norm

            # Try perturbations for the most problematic points
            improvement_found = False
            best_candidate_bary = None
            best_candidate_score = best_score
            
            # Adaptive perturbation count
            base_perturbations = 12
            adaptive_perturbations = max(5, int(base_perturbations * (gradient_step / initial_step) * 2))
            
            # Minimum exploration guarantee
            random_scale = max(0.2, 0.5 - 0.4 * (1 - gradient_step / initial_step))

            # Only consider points with non-zero frequency
            for idx in range(n):
                if freq[idx] == 0:
                    continue
                
                # Current position in barycentric
                u, v = best_bary[idx]
                
                # Adaptive minimum distance threshold
                min_distance_bary = min(0.03, 0.8 * min_area)
                
                # First try gradient-based moves
                grad = gradient_vectors[idx]
                candidate_points = best_points.copy()
                
                # Move point along gradient direction
                candidate_points[idx] += grad * gradient_step
                
                # Boundary-aware projection
                candidate_points[idx] = get_boundary_projection(candidate_points[idx], grad) + candidate_points[idx]
                
                # Convert to barycentric for distance checking
                candidate_bary = np.array([to_bary(p) for p in candidate_points])
                u_new, v_new = candidate_bary[idx]
                
                # Check minimum distance to other points in barycentric space
                too_close = False
                for i in range(n):
                    if i == idx:
                        continue
                    dist = np.linalg.norm(candidate_bary[i] - np.array([u_new, v_new]))
                    if dist < min_distance_bary:
                        too_close = True
                        break
                
                if not too_close and is_inside_triangle(candidate_points, A, B, C):
                    score = get_smallest_triangle_area(candidate_points)
                    if score > best_candidate_score:
                        best_candidate_bary = candidate_bary
                        best_candidate_score = score
                        improvement_found = True

                # If gradient move didn't work, try random perturbations
                if not improvement_found:
                    for _ in range(adaptive_perturbations):
                        # Base perturbation in random direction
                        angle = np.random.uniform(0, 2 * np.pi)
                        base_perturbation = np.array([np.cos(angle), np.sin(angle)]) * random_step
                        
                        # Add adaptive randomness
                        random_perturbation = np.random.normal(0, random_step * random_scale, size=2)
                        
                        # Combine
                        total_perturbation = base_perturbation + random_perturbation
                        
                        # Apply to Cartesian coordinates
                        candidate_points = best_points.copy()
                        candidate_points[idx] += total_perturbation
                        
                        # Boundary-aware projection
                        candidate_points[idx] = get_boundary_projection(candidate_points[idx], total_perturbation) + candidate_points[idx]
                        
                        # Convert to barycentric for distance checking and clamping
                        candidate_bary = np.array([to_bary(p) for p in candidate_points])
                        u_new, v_new = candidate_bary[idx]
                        u_new, v_new = clamp_bary(u_new, v_new)
                        candidate_points[idx] = to_cart(u_new, v_new)
                        
                        # Check minimum distance to other points in barycentric space
                        too_close = False
                        for i in range(n):
                            if i == idx:
                                continue
                            dist = np.linalg.norm(candidate_bary[i] - np.array([u_new, v_new]))
                            if dist < min_distance_bary:
                                too_close = True
                                break
                        
                        if too_close:
                            continue
                        
                        if is_inside_triangle(candidate_points, A, B, C):
                            score = get_smallest_triangle_area(candidate_points)
                            if score > best_candidate_score:
                                best_candidate_bary = candidate_bary
                                best_candidate_score = score
                                improvement_found = True
                                break

            if improvement_found:
                best_bary = best_candidate_bary
                best_points = np.array([to_cart(u, v) for u, v in best_bary])
                best_score = best_candidate_score
                stagnation_count = 0
                
                # Update improvement history
                improvement_history[improvement_idx] = 1
                improvement_idx = (improvement_idx + 1) % improvement_window
                
                # Asymmetric step adaptation: faster growth for gradient moves
                gradient_step = min(gradient_step * 1.05, initial_step)
                random_step = min(random_step * 1.03, initial_step * 0.8)
            else:
                # Update improvement history
                improvement_history[improvement_idx] = 0
                improvement_idx = (improvement_idx + 1) % improvement_window
                
                stagnation_count += 1
                
                # Calculate recent improvement rate
                improvement_rate = sum(improvement_history) / improvement_window
                
                # Asymmetric step decay with improvement rate adaptation
                gradient_step *= (0.92 + 0.05 * improvement_rate)  # Increased decay rate
                random_step *= (0.95 + 0.04 * improvement_rate)

            # Step size reset on extended stagnation
            if stagnation_count >= 40:  # Increased from 30
                gradient_step = min(gradient_step * 1.8, initial_step)
                random_step = min(random_step * 1.8, initial_step * 0.8)
                stagnation_count = 0
            
            # Termination condition: small step size with no improvement
            if gradient_step < 1e-8 and stagnation_count > 20:
                break
        
        # Final simulated annealing phase for deep local optima
        if best_score < 0.032:
            temperature = 0.0015
            cooling_rate = 0.95
            sa_iterations = 150
            
            current = best_points.copy()
            current_score = best_score
            current_bary = best_bary.copy()
            
            for _ in range(sa_iterations):
                # Randomly select a point to perturb
                idx = np.random.randint(0, n)
                u, v = current_bary[idx]
                
                # Larger perturbation for exploration
                du = np.random.normal(0, 0.1)
                dv = np.random.normal(0, 0.1)
                u_new, v_new = clamp_bary(u + du, v + dv)
                
                # Create candidate
                candidate = current.copy()
                candidate[idx] = to_cart(u_new, v_new)
                
                if is_inside_triangle(candidate, A, B, C):
                    score = get_smallest_triangle_area(candidate)
                    
                    # Metropolis criterion
                    delta = score - current_score
n                    if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                        current = candidate
                        current_score = score
                        current_bary[idx] = [u_new, v_new]
                        
                        if score > best_score:
                            best_points = candidate.copy()
                            best_score = score
                            best_bary = current_bary.copy()

                    # Cool temperature
                    temperature *= cooling_rate

        return best_points, best_score

    # Run multiple restarts with diverse initial configurations
    best_overall = None
    best_score_overall = -1
    
    # 25 restarts with balanced pattern distribution: 4 vertex-focused, 7 edge-focused, 14 balanced
    patterns = ['vertex-focused'] * 4 + ['edge-focused'] * 7 + ['balanced'] * 14
    
    for pattern in patterns:
        initial_points = generate_initial_config(pattern)
        candidate, score = optimize_configuration(initial_points)
        
        if score > best_score_overall:
            best_overall = candidate
            best_score_overall = score

    return best_overall