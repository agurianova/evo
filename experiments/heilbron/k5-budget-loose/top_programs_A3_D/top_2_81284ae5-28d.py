from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()
    
    def improve(points: np.ndarray) -> np.ndarray:
        best = points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Adaptive step size parameters
        step = 0.05
        decay = 0.95
        min_step = 0.001
        
        for _ in range(50):
            # Find the smallest triangle (bottleneck)
            min_area_val = float('inf')
            tri = None
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        a, b, c = best[i], best[j], best[k]
                        cross_val = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                        area_val = abs(cross_val)
                        if area_val < min_area_val:
                            min_area_val = area_val
                            tri = (i, j, k)
            
            if tri is None:
                step = max(min_step, step * decay)
                continue
                
            i0, i1, i2 = tri
            a, b, c = best[i0], best[i1], best[i2]
            
            # Compute sign of triangle orientation
            cross_val = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
            s = 1.0 if cross_val > 0 else -1.0
            
            # Compute directional gradients for each vertex
            dir0 = s * np.array([b[1]-c[1], c[0]-b[0]])
            dir1 = s * np.array([c[1]-a[1], a[0]-c[0]])
            dir2 = s * np.array([a[1]-b[1], b[0]-a[0]])
            
            # Normalize directions
            norm0 = np.linalg.norm(dir0)
            norm1 = np.linalg.norm(dir1)
            norm2 = np.linalg.norm(dir2)
            if norm0 > 1e-8:
                dir0 = dir0 / norm0
            if norm1 > 1e-8:
                dir1 = dir1 / norm1
            if norm2 > 1e-8:
                dir2 = dir2 / norm2

            # Apply directional perturbation
            candidate = best.copy()
            candidate[i0] += step * dir0
            candidate[i1] += step * dir1
            candidate[i2] += step * dir2

            # Check containment
            if not is_inside_triangle(candidate, A, B, C):
                step = max(min_step, step * decay)
                continue

            # Evaluate and accept if improvement
            new_score = get_smallest_triangle_area(candidate)
            if new_score > best_score:
                best = candidate
                best_score = new_score

            # Decay step size
            step = max(min_step, step * decay)

        return best
    
    return improve