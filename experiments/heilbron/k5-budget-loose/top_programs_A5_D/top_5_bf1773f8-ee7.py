from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np


def entrypoint():
    A, B, C = get_unit_triangle()

    def compute_area_gradient(p1, p2, p3, area):
        """Compute gradient of triangle area with respect to each point."""
        # For a triangle with vertices p1, p2, p3, the gradient of area
        # with respect to p1 is proportional to (p2 - p3) rotated by 90 degrees
        grad_p1 = np.array([-(p2[1] - p3[1]), p2[0] - p3[0]])
        grad_p2 = np.array([-(p3[1] - p1[1]), p3[0] - p1[0]])
        grad_p3 = np.array([-(p1[1] - p2[1]), p1[0] - p2[0]])
        
        # Normalize gradients to unit vectors
        if np.linalg.norm(grad_p1) > 1e-10:
            grad_p1 = grad_p1 / np.linalg.norm(grad_p1)
        if np.linalg.norm(grad_p2) > 1e-10:
            grad_p2 = grad_p2 / np.linalg.norm(grad_p2)
        if np.linalg.norm(grad_p3) > 1e-10:
            grad_p3 = grad_p3 / np.linalg.norm(grad_p3)
            
        return grad_p1, grad_p2, grad_p3

    def is_distinct(pts, tol=1e-5):
        n = pts.shape[0]
        for i in range(n):
            for j in range(i+1, n):
                if np.linalg.norm(pts[i] - pts[j]) < tol:
                    return False
        return True

    def improve(points: np.ndarray) -> np.ndarray:
        np.random.seed(42)
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        best_score_history = [best_score]

        # Local search with gradient-guided strategies
        for _round in range(50):
            min_area_val = best_score
            
            # Identify critical points with centrality scoring
            critical_scores = np.zeros(11)
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        p1, p2, p3 = best[i], best[j], best[k]
                        area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1]))
                        if abs(area - min_area_val) < 1e-5 * min_area_val:
                            # Points in smaller triangles get higher scores
                            score = 1.0 / (area + 1e-10)
                            critical_scores[i] += score
                            critical_scores[j] += score
                            critical_scores[k] += score

            # Get indices sorted by criticality (highest first)
            critical_indices = np.argsort(critical_scores)[::-1]
            # Take top N critical points (at least 1)
            num_critical = max(1, min(5, int(np.sum(critical_scores > 0))))
            critical_points = critical_indices[:num_critical].tolist()

            # Adaptive step sizing with exponential decay
            base_step = 0.5 * np.sqrt(best_score)  # Increased from 0.1 to 0.5
            current_step = base_step * (0.95 ** _round)  # Exponential decay
            
            # Adaptive component: if no improvement in last N rounds, increase step size
            if _round > 10 and (_round % 10 == 0) and len(best_score_history) > 10 and best_score_history[-1] == best_score_history[max(0, len(best_score_history)-11)]:
                current_step *= 1.5

            # Targeted point selection with increased multi-point frequency
            idx_list = []
            if np.random.rand() < 0.5:  # Increased from 0.2 to 0.5
                smallest_triangles = []
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            p1, p2, p3 = best[i], best[j], best[k]
                            area = 0.5 * abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1]))
                            if abs(area - min_area_val) < 1e-5 * min_area_val:
                                smallest_triangles.append((i, j, k))
                
                if smallest_triangles:
                    # Prioritize triangles with highest criticality score
                    triangle_scores = []
                    for tri in smallest_triangles:
                        score = critical_scores[tri[0]] + critical_scores[tri[1]] + critical_scores[tri[2]]
                        triangle_scores.append(score)
                    
                    # Select highest scoring triangle
                    best_triangle_idx = np.argmax(triangle_scores)
                    tri = smallest_triangles[best_triangle_idx]
                    
                    # Always perturb 2 or 3 points from the critical triangle
                    num_to_perturb = np.random.choice([2, 3], p=[0.6, 0.4])
                    idx_list = np.random.choice(tri, size=min(num_to_perturb, len(tri)), replace=False).tolist()
                else:
                    idx_list = [np.random.choice(critical_points)]
            else:
                idx_list = [np.random.choice(critical_points)]

            # Generate candidate with gradient-guided perturbations
            candidate = best.copy()
            for idx in idx_list:
                # For each point, compute its contribution to critical triangle gradients
                point_gradient = np.zeros(2)
                for i in range(11):
                    for j in range(i+1, 11):
                        for k in range(j+1, 11):
                            if idx in [i, j, k] and abs(get_smallest_triangle_area(best[[i,j,k]]) - min_area_val) < 1e-5:
                                p1, p2, p3 = best[i], best[j], best[k]
                                area = get_smallest_triangle_area(np.array([p1, p2, p3]))
                                grad_p1, grad_p2, grad_p3 = compute_area_gradient(p1, p2, p3, area)
                                if idx == i:
                                    point_gradient += grad_p1
                                elif idx == j:
                                    point_gradient += grad_p2
                                else:
                                    point_gradient += grad_p3
                
                # Normalize and scale the gradient
                if np.linalg.norm(point_gradient) > 1e-10:
                    point_gradient = point_gradient / np.linalg.norm(point_gradient)
                
                # Add some randomness to avoid getting stuck
                random_component = np.random.normal(0, 0.2, size=2)
                if np.linalg.norm(random_component) > 1e-10:
                    random_component = random_component / np.linalg.norm(random_component)
                
                # Blend gradient direction with some randomness
                move_direction = 0.7 * point_gradient + 0.3 * random_component
                if np.linalg.norm(move_direction) > 1e-10:
                    move_direction = move_direction / np.linalg.norm(move_direction)
                
                # Apply the move
                candidate[idx] += current_step * move_direction

            # Constraint validation
            if not is_inside_triangle(candidate, A, B, C) or not is_distinct(candidate, tol=1e-5):
                continue

            score = get_smallest_triangle_area(candidate)
            if score > best_score:
                best = candidate
                best_score = score
                
            best_score_history.append(best_score)

        return best

    return improve