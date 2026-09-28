from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import math

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    
    # Precompute triangle edge normals for boundary handling
    AB = B - A
    BC = C - B
    CA = A - C
    normal_AB = np.array([-AB[1], AB[0]])
    normal_BC = np.array([-BC[1], BC[0]])
    normal_CA = np.array([-CA[1], CA[0]])
    # Normalize
    normal_AB = normal_AB / np.linalg.norm(normal_AB)
    normal_BC = normal_BC / np.linalg.norm(normal_BC)
    normal_CA = normal_CA / np.linalg.norm(normal_CA)

    def get_feasible_direction(point):
        """Return a random direction that keeps the point inside the triangle"""
        # Check which edges the point is close to
        to_A = A - point
        to_B = B - point
        to_C = C - point
        
        # Calculate distances to edges using dot product with normals
        dist_AB = np.dot(to_A, normal_AB)
        dist_BC = np.dot(to_B, normal_BC)
        dist_CA = np.dot(to_C, normal_CA)
        
        # If outside, project back (shouldn't happen with our checks but just in case)
        if dist_AB < 0 or dist_BC < 0 or dist_CA < 0:
            # Project back to nearest edge
            if dist_AB < dist_BC and dist_AB < dist_CA:
                return normal_AB
            elif dist_BC < dist_AB and dist_BC < dist_CA:
                return normal_BC
            else:
                return normal_CA
        
        # Generate random direction within feasible cone
        angle = np.random.uniform(0, 2*np.pi)
        direction = np.array([np.cos(angle), np.sin(angle)])
        
        # Check if direction would take us outside
        max_step = float('inf')
        if np.dot(direction, normal_AB) < 0:
            max_step = min(max_step, dist_AB / abs(np.dot(direction, normal_AB)))
        if np.dot(direction, normal_BC) < 0:
            max_step = min(max_step, dist_BC / abs(np.dot(direction, normal_BC)))
        if np.dot(direction, normal_CA) < 0:
            max_step = min(max_step, dist_CA / abs(np.dot(direction, normal_CA)))
        
        # If direction would take us outside, reflect it
        if max_step < 1e-10:
            # Find dominant constraint and reflect
            constraints = []
            if dist_AB < 1e-5:
                constraints.append(normal_AB)
            if dist_BC < 1e-5:
                constraints.append(normal_BC)
            if dist_CA < 1e-5:
                constraints.append(normal_CA)
            
            if constraints:
                # Average constraint normals to get reflection direction
                constraint_normal = np.mean(constraints, axis=0)
                constraint_normal = constraint_normal / np.linalg.norm(constraint_normal)
                # Reflect direction across constraint
                direction = direction - 2 * np.dot(direction, constraint_normal) * constraint_normal
        
        return direction

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        base_step = 0.01
        step = base_step
        max_iter = 300
        patience = 20
        no_improve_count = 0
        restarts = 0
        max_restarts = 5
        
        # Target improvement - we'll aim to improve by at least 10% of theoretical max
        target_improvement = best_score + 0.1 * (0.0365 - best_score)
        
        # Adaptive exploration rate - starts high, decreases as we approach target
        exploration_rate = max(0.2, 0.5 * (1 - best_score / target_improvement))
        
        for _ in range(max_iter):
            current_min, triplet = None, None
            
            # Recompute smallest triangle
            triangles = []
            n = best.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        x1, y1 = best[i]
                        x2, y2 = best[j]
                        x3, y3 = best[k]
                        area = 0.5 * abs((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1))
                        triangles.append((area, i, j, k))
            
            if not triangles:
                break
                
            triangles.sort(key=lambda x: x[0])
            current_min, i, j, k = triangles[0][0], triangles[0][1], triangles[0][2], triangles[0][3]
            
            # Check if we should do broad search
            do_broad_search = np.random.random() < exploration_rate
            
            if do_broad_search:
                # Analyze top 5 smallest triangles
                small_triangles = triangles[:5]

                # Count point occurrences in small triangles
                count = np.zeros(n, dtype=int)
                for _, i, j, k in small_triangles:
                    count[i] += 1
                    count[j] += 1
                    count[k] += 1
                
                # Select highest-impact point (break ties randomly)
                max_count = count.max()
                candidates = np.where(count == max_count)[0]
                candidate_point = np.random.choice(candidates)

                # Get feasible direction
                direction = get_feasible_direction(best[candidate_point])

                candidate = best.copy()
                candidate[candidate_point] += step * direction

                # Ensure we're still inside the triangle
                if not is_inside_triangle(candidate, A, B, C):
                    # Try projecting back if outside
                    for idx in range(n):
                        if not is_inside_triangle(candidate[idx], A, B, C):
                            # Find closest point on boundary
                            projections = []
                            # Project onto each edge
                            for edge_start, edge_end in [(A, B), (B, C), (C, A)]:
                                edge_vec = edge_end - edge_start
                                point_vec = candidate[idx] - edge_start
                                t = np.dot(point_vec, edge_vec) / np.dot(edge_vec, edge_vec)
                                t = max(0, min(1, t))
                                proj = edge_start + t * edge_vec
n                                dist = np.linalg.norm(candidate[idx] - proj)
                                projections.append((dist, proj))
                            
                            # Use closest projection
                            _, closest_proj = min(projections, key=lambda x: x[0])
                            candidate[idx] = closest_proj

                score = get_smallest_triangle_area(candidate)
                if score > best_score:
                    best = candidate
                    best_score = score
                    no_improve_count = 0
                    # Increase step size slightly when we find improvements
                    step = min(base_step * 1.1, step * 1.05)
                    # Update exploration rate - decrease as we improve
                    target_improvement = best_score + 0.1 * (0.0365 - best_score)
                    exploration_rate = max(0.2, 0.5 * (1 - best_score / target_improvement))
                else:
                    no_improve_count += 1
                    if no_improve_count >= patience:
                        # More aggressive step reduction when stuck
                        step *= 0.85
                        no_improve_count = 0

            else:
                a, b, c = best[i], best[j], best[k]

                # Compute signed area for direction correction
                x1, y1 = a
                x2, y2 = b
                x3, y3 = c
                signed_area = 0.5 * ((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1))
                sign = 1.0 if signed_area >= 0 else -1.0

                # Corrected gradients with sign
                grad_a = sign * np.array([b[1] - c[1], c[0] - b[0]])
                if np.linalg.norm(grad_a) > 1e-8:
                    grad_a = grad_a / np.linalg.norm(grad_a)

                grad_b = sign * np.array([c[1] - a[1], a[0] - c[0]])
                if np.linalg.norm(grad_b) > 1e-8:
                    grad_b = grad_b / np.linalg.norm(grad_b)

                grad_c = sign * np.array([a[1] - b[1], b[0] - a[0]])
                if np.linalg.norm(grad_c) > 1e-8:
                    grad_c = grad_c / np.linalg.norm(grad_c)

                candidate = best.copy()
                candidate[i] += step * grad_a
                candidate[j] += step * grad_b
                candidate[k] += step * grad_c

                # Ensure we're still inside the triangle
                if not is_inside_triangle(candidate, A, B, C):
                    # Project points back inside if necessary
                    for idx in range(n):
                        if not is_inside_triangle(candidate[idx], A, B, C):
                            # Find closest point on boundary
                            projections = []
                            # Project onto each edge
                            for edge_start, edge_end in [(A, B), (B, C), (C, A)]:
                                edge_vec = edge_end - edge_start
                                point_vec = candidate[idx] - edge_start
                                t = np.dot(point_vec, edge_vec) / np.dot(edge_vec, edge_vec)
                                t = max(0, min(1, t))
                                proj = edge_start + t * edge_vec
                                dist = np.linalg.norm(candidate[idx] - proj)
                                projections.append((dist, proj))
                            
                            # Use closest projection
                            _, closest_proj = min(projections, key=lambda x: x[0])
                            candidate[idx] = closest_proj

                score = get_smallest_triangle_area(candidate)
                if score > best_score:
                    best = candidate
                    best_score = score
                    no_improve_count = 0
                    # Increase step size slightly when we find improvements
                    step = min(base_step * 1.1, step * 1.05)
                    # Update exploration rate - decrease as we improve
                    target_improvement = best_score + 0.1 * (0.0365 - best_score)
                    exploration_rate = max(0.2, 0.5 * (1 - best_score / target_improvement))
                else:
                    no_improve_count += 1
                    if no_improve_count >= patience:
                        # More aggressive step reduction when stuck
                        step *= 0.85
                        no_improve_count = 0

            # Check for restart condition
            if no_improve_count >= patience * 2 and restarts < max_restarts:
                # Perturb top points from smallest triangles
                perturb_points = set()
                for _, i, j, k in triangles[:3]:  # Top 3 smallest triangles
                    perturb_points.add(i)
                    perturb_points.add(j)
                    perturb_points.add(k)
                
                candidate = best.copy()
                restart_step = step * (0.5 ** restarts)  # Decreasing noise with restarts
                for idx in perturb_points:
                    direction = get_feasible_direction(candidate[idx])
                    candidate[idx] += restart_step * direction
                    
                    # Ensure still inside triangle
                    if not is_inside_triangle(candidate[idx], A, B, C):
                        # Project back
                        projections = []
                        for edge_start, edge_end in [(A, B), (B, C), (C, A)]:
                            edge_vec = edge_end - edge_start
                            point_vec = candidate[idx] - edge_start
                            t = np.dot(point_vec, edge_vec) / np.dot(edge_vec, edge_vec)
                            t = max(0, min(1, t))
                            proj = edge_start + t * edge_vec
                            dist = np.linalg.norm(candidate[idx] - proj)
                            projections.append((dist, proj))
                        
                        _, closest_proj = min(projections, key=lambda x: x[0])
                        candidate[idx] = closest_proj

                score = get_smallest_triangle_area(candidate)
                if score > best_score:
                    best = candidate
                    best_score = score
                
                restarts += 1
                no_improve_count = 0
                step = base_step * (0.7 ** restarts)  # Start smaller after restarts

            if step < 1e-7:
                break

        return best

    return improve