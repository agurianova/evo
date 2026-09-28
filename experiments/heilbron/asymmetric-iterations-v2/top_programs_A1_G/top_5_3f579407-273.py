import numpy as np

# G's original point configuration
_G_POINTS = np.array([[0.1958728758055439, 0.2705861879457113], [0.5437927358197259, 0.08758019908608287], [0.312671078254004, 0.4987903642792214], [0.8111641813060229, 0.7237090805945348], [1.176459566306493, 0.2911376863153415], [0.8829460903854373, 0.029717761131200483], [0.20502969409041183, 0.03318888856510269], [0.25368950765856574, 0.18533435442907195], [0.4645280398762167, 0.04031126725460093], [1.345301864102166, 0.1850080886669241], [1.1496213632804997, 0.33984013720004197]], dtype=np.float64)

# --- D's code (entrypoint renamed to _d_entrypoint) ---
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
import random


def _d_entrypoint():
    A, B, C = get_unit_triangle()

    def project_to_triangle(point, a, b, c):
        """Project point to triangle using barycentric coordinates"""
        v0 = b - a
        v1 = c - a
        v2 = point - a
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        if abs(denom) < 1e-10:
            return (a + b + c) / 3
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))
        w = max(0.0, min(1.0, w))
        total = u + v + w
        if total < 1e-10:
            return (a + b + c) / 3
        return (u * a + v * b + w * c) / total

    def improve(points: np.ndarray) -> np.ndarray:
        decay = 0.999
        max_iter = 10000
        k_smallest = 5  # Number of smallest triangles to consider

        current = points.copy()
        best_score = get_smallest_triangle_area(current)
        best_config = current.copy()
        no_improve_count = 0
        step_counter = 0
        
        # Initialize adaptive temperature for simulated annealing
        initial_temp = best_score * 3.0  # Reduced from 10.0 for better balance
        temp_decay = 0.9999

        for _ in range(max_iter):
            # Compute all triangle areas and find k smallest
            n = 11
            triangles = []
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        p0, p1, p2 = current[i], current[j], current[k]
                        v1 = p1 - p0
                        v2 = p2 - p0
                        cross = v1[0] * v2[1] - v1[1] * v2[0]
                        signed = 0.5 * cross
                        abs_val = abs(signed)
                        triangles.append((abs_val, signed, i, j, k))
            
            triangles.sort(key=lambda x: x[0])
            smallest_list = triangles[:k_smallest]
            min_abs_area = smallest_list[0][0]

            # Compute composite gradient for all points
            gradients = np.zeros_like(current)
            for _, signed, i, j, k in smallest_list:
                # Gradient directions for absolute area increase
                dir_i = np.sign(signed) * np.array([current[j,1] - current[k,1], current[k,0] - current[j,0]])
                dir_j = np.sign(signed) * np.array([current[k,1] - current[i,1], current[i,0] - current[k,0]])
                dir_k = np.sign(signed) * np.array([current[i,1] - current[j,1], current[j,0] - current[i,0]])
                
                # Add to composite gradients without normalizing first
                gradients[i] += dir_i
                gradients[j] += dir_j
                gradients[k] += dir_k

            # Normalize composite gradients after summing
            for i in range(n):
                norm = np.linalg.norm(gradients[i])
                if norm > 1e-10:
                    gradients[i] /= norm

            # Adaptive step size
            step = min_abs_area * 0.5 * (decay ** step_counter)

            # Generate candidate by moving along composite gradients
            candidate = current + step * gradients

            # Project all points to triangle boundary
            for i in range(n):
                candidate[i] = project_to_triangle(candidate[i], A, B, C)

            # Global exploration every 500 iterations (was 1000)
            if step_counter % 500 == 0 and step_counter > 0:
                global_step = step * 0.3  # Increased from 0.1 for larger exploration steps
                for i in range(n):
                    candidate[i] += global_step * (np.random.rand(2) - 0.5)
                    candidate[i] = project_to_triangle(candidate[i], A, B, C)

            # Evaluate candidate
            new_score = get_smallest_triangle_area(candidate)
            
            # Simulated annealing acceptance
            if new_score > best_score:
                current = candidate
                best_score = new_score
                best_config = candidate
                no_improve_count = 0
            else:
                delta = best_score - new_score
                temp = initial_temp * (temp_decay ** step_counter)
                if temp > 1e-8 and random.random() < np.exp(-delta / temp):
                    current = candidate
                no_improve_count += 1

            step_counter += 1

            # Dynamic stagnation threshold based on problem difficulty
            max_no_improve = max(200, 200 + int(300 * best_score / 0.0365))

            # Restart with perturbation if stuck
            if no_improve_count >= max_no_improve:
                # Perturb best_config with 8% of triangle size (was 5%)
                max_dim = max(B[0] - A[0], C[1] - A[1])
                current = best_config.copy()
                for i in range(n):
                    current[i] += max_dim * 0.08 * (np.random.rand(2) - 0.5)
                    current[i] = project_to_triangle(current[i], A, B, C)
                no_improve_count = 0

        return best_config

    return improve

def entrypoint():
    """D's improvement of G's points, as a valid G program."""
    improve_fn = _d_entrypoint()
    improved = improve_fn(_G_POINTS.copy())
    return np.asarray(improved, dtype=np.float64)