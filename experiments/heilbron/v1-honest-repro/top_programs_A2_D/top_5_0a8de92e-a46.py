from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

def entrypoint():
    A, B, C = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        rng = np.random.default_rng(seed=42)
        
        def find_smallest_triangle(pts):
            n = len(pts)
            min_area = float('inf')
            best_indices = None
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        a, b, c = pts[i], pts[j], pts[k]
                        area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        if area < min_area:
                            min_area = area
                            best_indices = (i, j, k)
            return best_indices, min_area

        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score
        
        T = 1.0 * current_score
        
        for _ in range(2000):
            (i1, i2, i3), _ = find_smallest_triangle(current)
            
            candidate = current.copy()
            step_size_val = 0.2 * np.sqrt(current_score)
            
            # Get the three points of the smallest triangle
            i, j, k = i1, i2, i3
            a, b, c = current[i], current[j], current[k]

            # Compute signed area for triangle (a,b,c)
            signed_area = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
            
            # Randomly select one point to move
            point_to_move = rng.choice([i, j, k])
            if point_to_move == i:
                grad = np.array([b[1]-c[1], c[0]-b[0]])
            elif point_to_move == j:
                grad = np.array([c[1]-a[1], a[0]-c[0]])
            else:  # k
                grad = np.array([a[1]-b[1], b[0]-a[0]])

            # Apply sign of area to get direction that increases area
            direction = np.sign(signed_area) * grad
            
            # Normalize direction vector
            norm = np.linalg.norm(direction)
            if norm > 1e-8:
                direction = direction / norm
            else:
                # Fallback to random direction if gradient is zero (shouldn't happen)
                direction = rng.normal(0, 1, size=2)
                direction = direction / np.linalg.norm(direction)

            # Move the selected point
            candidate[point_to_move] += step_size_val * direction

            # Check if inside triangle
            if not is_inside_triangle(candidate, A, B, C):
                continue

            candidate_score = get_smallest_triangle_area(candidate)

            if candidate_score > current_score:
                current = candidate
                current_score = candidate_score
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score
            else:
                delta = current_score - candidate_score
                if rng.random() < np.exp(-delta / T):
                    current = candidate
                    current_score = candidate_score

            T *= 0.99

        return best

    return improve