from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import random

np.random.seed(42)
random.seed(42)

def project_to_triangle(point, A, B, C):
    """Project a point to the nearest point on or inside the triangle ABC."""
    if is_inside_triangle(point, A, B, C):
        return point

    def closest_point_on_segment(p, a, b):
        ap = p - a
        ab = b - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
        t = max(0, min(1, t))
        return a + t * ab

    p_ab = closest_point_on_segment(point, A, B)
    p_bc = closest_point_on_segment(point, B, C)
    p_ca = closest_point_on_segment(point, C, A)

    d_ab = np.linalg.norm(point - p_ab)
    d_bc = np.linalg.norm(point - p_bc)
    d_ca = np.linalg.norm(point - p_ca)

    if d_ab <= d_bc and d_ab <= d_ca:
        return p_ab
    elif d_bc <= d_ab and d_bc <= d_ca:
        return p_bc
    else:
        return p_ca

def get_critical_points(points, k=3):
    """Return indices of points involved in the k smallest triangles."""
    n = len(points)
    min_areas = []
    
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                area = 0.5 * abs(
                    points[i, 0] * (points[j, 1] - points[k, 1]) +
                    points[j, 0] * (points[k, 1] - points[i, 1]) +
                    points[k, 0] * (points[i, 1] - points[j, 1])
                )
                min_areas.append((area, i, j, k))
    
    min_areas.sort(key=lambda x: x[0])
    critical_indices = set()
    for _, i, j, k in min_areas[:k]:
        critical_indices.add(i)
        critical_indices.add(j)
        critical_indices.add(k)
    
    return list(critical_indices)

def entrypoint():
    """Return an improve(points) -> improved_points callable."""
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        step_size = 0.05
        temperature = max(0.001, 0.001 * best_score)
        no_improve_count = 0
        max_iterations = 500
        max_no_improve = 100
        
        for _ in range(max_iterations):
            critical_points = get_critical_points(best, k=3)
            
            if random.random() < 0.8 and critical_points:
                idx = random.choice(critical_points)
            else:
                idx = random.randint(0, 10)
            
            candidate = best.copy()
            perturbation = np.random.normal(0, step_size, size=2)
            candidate[idx] += perturbation
            
            candidate[idx] = project_to_triangle(candidate[idx], A, B, C)
            
            score = get_smallest_triangle_area(candidate)
            
            delta = score - best_score
            if delta > 0 or (temperature > 1e-5 and random.random() < np.exp(delta / temperature)):
                best = candidate
                best_score = score
                no_improve_count = 0
                
                step_size *= 0.95
                temperature *= 0.95
            else:
                no_improve_count += 1
            
            if no_improve_count >= max_no_improve:
                break
        
        return best

    return improve