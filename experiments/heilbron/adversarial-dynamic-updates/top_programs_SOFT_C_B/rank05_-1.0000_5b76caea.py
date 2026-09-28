from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.spatial import Delaunay
import math

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    side_length = np.linalg.norm(B - A)
    
    # Precompute denominator for barycentric conversion (2 * area of ABC)
    denom = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
    
    # Helper functions for barycentric conversion
    def to_bary(p):
        u = ((B[1] - C[1]) * (p[0] - C[0]) + (C[0] - B[0]) * (p[1] - C[1])) / denom
        v = ((C[1] - A[1]) * (p[0] - C[0]) + (A[0] - C[0]) * (p[1] - C[1])) / denom
        return u, v
    
    def to_cart(u, v):
        w = 1 - u - v
        return u * A + v * B + w * C

    def compute_gradient(points, idx, min_area, min_triplets):
        # Compute finite difference gradient for point idx
        eps = 1e-6
        base_score = min_area
        
        # Try moving in 4 directions (x+, x-, y+, y-)
        directions = [
            np.array([eps, 0]),
            np.array([-eps, 0]),
            np.array([0, eps]),
            np.array([0, -eps])
        ]
        
        scores = []
        for d in directions:
            candidate = points.copy()
            candidate[idx] = candidate[idx] + d
            # Ensure point stays inside triangle
            if not is_inside_triangle(candidate[idx], A, B, C):
                scores.append(-np.inf)
                continue
            
            # Check if this breaks any minimal triangles
            score = base_score
            for i, j, k in min_triplets:
                if idx == i or idx == j or idx == k:
                    # Recompute area of this triangle
                    x1, y1 = candidate[i]
                    x2, y2 = candidate[j]
                    x3, y3 = candidate[k]
                    area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                    if area < score:
                        score = area
            scores.append(score)
        
        # Compute gradient (steepest ascent direction)
        dx = (scores[0] - scores[1]) / (2 * eps)
        dy = (scores[2] - scores[3]) / (2 * eps)
        
        # Normalize and scale
        grad = np.array([dx, dy])
        grad_norm = np.linalg.norm(grad)
        if grad_norm > 0:
            grad = grad / grad_norm
        return grad

    def find_minimal_triangles(points):
        # Use Delaunay triangulation to efficiently find candidate minimal triangles
        try:
            tri = Delaunay(points)
            min_area = float('inf')
            min_triplets = []
            
            # Check all triangles in the Delaunay triangulation
            for simplex in tri.simplices:
                i, j, k = simplex
                x1, y1 = points[i]
                x2, y2 = points[j]
                x3, y3 = points[k]
                area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                if area < min_area:
                    min_area = area
                    min_triplets = [(i, j, k)]
                elif abs(area - min_area) < 1e-9:
                    min_triplets.append((i, j, k))
            
            # Also check boundary cases (Delaunay might miss some with collinear points)
            n = len(points)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        if (i,j,k) not in min_triplets:
                            x1, y1 = points[i]
                            x2, y2 = points[j]
                            x3, y3 = points[k]
                            area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                            if area < min_area:
                                min_area = area
                                min_triplets = [(i, j, k)]
                            elif abs(area - min_area) < 1e-9:
                                min_triplets.append((i, j, k))
            
            return min_area, min_triplets
        except:
            # Fallback to brute force if Delaunay fails
            min_area = float('inf')
            min_triplets = []
            n = len(points)
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = points[i]
                        x2, y2 = points[j]
                        x3, y3 = points[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
                        if area < min_area:
                            min_area = area
                            min_triplets = [(i, j, k)]
                        elif abs(area - min_area) < 1e-9:
                            min_triplets.append((i, j, k))
            return min_area, min_triplets

    def find_clusters(min_triplets):
        # Build graph of connected triangles (sharing ≥2 points)
        from collections import defaultdict, deque
        graph = defaultdict(list)
        n = 11
        
        # Create adjacency list for points
        point_graph = defaultdict(list)
        for triplet in min_triplets:
            i, j, k = triplet
            point_graph[i].extend([j, k])
            point_graph[j].extend([i, k])
            point_graph[k].extend([i, j])
        
        # Find connected components (clusters)
        visited = [False] * n
        clusters = []
        for i in range(n):
            if not visited[i]:
                cluster = []
                queue = deque([i])
                visited[i] = True
                while queue:
                    node = queue.popleft()
                    cluster.append(node)
                    for neighbor in point_graph[node]:
                        if not visited[neighbor]:
                            visited[neighbor] = True
                            queue.append(neighbor)
                clusters.append(cluster)
        
        # Filter clusters with at least 3 points (meaningful clusters)
        clusters = [c for c in clusters if len(c) >= 3]
        return clusters

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        initial_step = 0.05
        step_size = initial_step
        stagnation_count = 0
        restart_multiplier = 1.0
        max_iterations = 500
        tol = 1e-9
        n = 11
        min_step_size = 1e-5 * side_length

        for _ in range(max_iterations):
            # Find minimal triangles efficiently
            min_area, min_triplets = find_minimal_triangles(best)
            
            # Find clusters of minimal triangles
            clusters = find_clusters(min_triplets)
            
            # Determine which points to perturb
            if clusters:
                # If we have clusters, perturb the largest cluster
                largest_cluster = max(clusters, key=len)
                perturb_indices = largest_cluster
                
                # Calculate cluster center for scaling
                cluster_center = np.mean(best[largest_cluster], axis=0)
                distances = np.linalg.norm(best[largest_cluster] - cluster_center, axis=1)
                max_dist = max(distances) if max(distances) > 0 else 1.0
                
                # Scale steps based on distance to cluster center
                scales = 1.0 / (1.0 + distances / max_dist)
            else:
                # Count vertex frequencies in minimal triangles
n                freq = [0] * n
                for triplet in min_triplets:
                    for idx in triplet:
                        freq[idx] += 1
                
                # Select vertex with highest frequency
                max_freq = max(freq)
                candidates = [i for i in range(n) if freq[i] == max_freq]
                perturb_indices = [np.random.choice(candidates)]
                scales = [1.0]  # No scaling needed for single point

            # Apply perturbations to selected points
            candidate = best.copy()
            improved = False
            
            for idx, scale in zip(perturb_indices, scales):
                # Dynamic step size based on current best_score
                dynamic_step = 0.1 * math.sqrt(best_score)
                current_step = min(step_size, dynamic_step)
                
                # Compute gradient for directional move
                grad = compute_gradient(best, idx, min_area, min_triplets)
                
                # Generate Cauchy-distributed perturbation with directional bias
                cauchy_scale = current_step * scale
                perturbation = np.random.standard_cauchy(2) * cauchy_scale
                
                # Blend with gradient direction (70% gradient, 30% random)
                if np.linalg.norm(grad) > 0:
                    perturbation = 0.7 * grad * current_step * scale + 0.3 * perturbation
                else:
                    perturbation = perturbation

                # Convert to barycentric for constraint handling
                u, v = to_bary(best[idx])
                du, dv = perturbation[0] / side_length, perturbation[1] / side_length
                u_new, v_new = u + du, v + dv

                # Clamp to simplex [0,1] and adjust for u+v<=1
                u_new = max(0.0, min(1.0, u_new))
                v_new = max(0.0, min(1.0, v_new))
                if u_new + v_new > 1.0:
                    scale_factor = 1.0 / (u_new + v_new)
                    u_new *= scale_factor
                    v_new *= scale_factor

                # Convert back to Cartesian
                new_point = to_cart(u_new, v_new)
                candidate[idx] = new_point

            # Check and evaluate candidate
            score = get_smallest_triangle_area(candidate)
            if score > best_score:
                best = candidate
                best_score = score
                stagnation_count = 0
                restart_multiplier = 1.0  # Reset on success
                improved = True
            else:
                stagnation_count += 1

            # Adaptive step decay (slower than before)
            step_size *= 0.99

            # Step size reset with adaptive threshold
            if stagnation_count >= 15 and step_size < initial_step * 0.1:
                step_size = 0.2 * initial_step
                stagnation_count = 0

            # Global restart after prolonged stagnation
            if stagnation_count >= 30:
                # Generate restart candidate with increased step size
                candidate_restart = best.copy()
                restart_step = restart_multiplier * 0.2 * initial_step
                restart_multiplier *= 1.5  # Increase for next time

                for i in range(n):
                    u, v = to_bary(best[i])
                    # Use Cauchy distribution for restarts too
                    du = np.random.standard_cauchy() * (restart_step / side_length)
                    dv = np.random.standard_cauchy() * (restart_step / side_length)
                    u_new, v_new = u + du, v + dv

                    # Clamp to simplex
                    u_new = max(0.0, min(1.0, u_new))
                    v_new = max(0.0, min(1.0, v_new))
                    if u_new + v_new > 1.0:
                        scale = 1.0 / (u_new + v_new)
                        u_new *= scale
                        v_new *= scale

                    candidate_restart[i] = to_cart(u_new, v_new)

                # Evaluate restart candidate
                score_restart = get_smallest_triangle_area(candidate_restart)
                if score_restart > best_score:
                    best = candidate_restart
                    best_score = score_restart
                    stagnation_count = 0
                    restart_multiplier = 1.0

            # Early termination if step size gets too small
            if step_size < min_step_size:
                break

        return best

    return improve