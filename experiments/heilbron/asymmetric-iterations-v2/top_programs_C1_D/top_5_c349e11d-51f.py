from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import numpy as np

np.random.seed(42)

def entrypoint():
    A, B, C = get_unit_triangle()
    edges = [(A, B), (B, C), (C, A)]

    def project_point_to_line_segment(p, a, b):
        ab = b - a
        ap = p - a
        t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
        t = max(0.0, min(1.0, t))
        return a + t * ab

    def project_point_to_triangle(p):
        if is_inside_triangle(p, A, B, C):
            return p
        min_dist = float('inf')
        closest = None
        for (a, b) in edges:
            proj = project_point_to_line_segment(p, a, b)
            dist = np.linalg.norm(p - proj)
            if dist < min_dist:
                min_dist = dist
                closest = proj
        return closest

    def improve(points):
        current = points.copy()
        current_score = get_smallest_triangle_area(current)
        best = current.copy()
        best_score = current_score

        step_size = 0.05
        temperature = 0.01  # Increased initial temperature
        max_iter = 1000
        patience = 100
        degeneracy_tol = 1e-9
        no_improve_count = 0

        for _ in range(max_iter):
            min_area_helper = get_smallest_triangle_area(current)
            critical_triplets = []
            n = current.shape[0]
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        area_val = 0.5 * abs((current[j,0]-current[i,0])*(current[k,1]-current[i,1]) - 
                                          (current[k,0]-current[i,0])*(current[j,1]-current[i,1]))
                        if area_val <= min_area_helper + 1e-5:  # Increased tolerance
                            critical_triplets.append((i, j, k, area_val))
            
            if not critical_triplets:
                i, j, k = 0, 1, 2
                s = 0.5 * ((current[j,0]-current[i,0])*(current[k,1]-current[i,1]) - 
                          (current[k,0]-current[i,0])*(current[j,1]-current[i,1]))
                grad_i = np.array([-(current[j,1]-current[k,1]), current[j,0]-current[k,0]])
                grad_j = np.array([current[k,1]-current[i,1], -(current[k,0]-current[i,0])])
                grad_k = np.array([-(current[j,1]-current[i,1]), current[j,0]-current[i,0]])
                dir_i = np.sign(s) * grad_i
                dir_j = np.sign(s) * grad_j
                dir_k = np.sign(s) * grad_k
                mag_i = np.linalg.norm(dir_i)
                mag_j = np.linalg.norm(dir_j)
                mag_k = np.linalg.norm(dir_k)
                mags = [mag_i, mag_j, mag_k]
                idx_in_triplet = np.argmax(mags)
                if idx_in_triplet == 0:
                    idx = i
                    direction = dir_i
                    mag = mag_i
                elif idx_in_triplet == 1:
                    idx = j
                    direction = dir_j
                    mag = mag_j
                else:
                    idx = k
                    direction = dir_k
                    mag = mag_k
            else:
                critical_triplets.sort(key=lambda x: x[3])
                i, j, k, _ = critical_triplets[0]
                s = 0.5 * ((current[j,0]-current[i,0])*(current[k,1]-current[i,1]) - 
                          (current[k,0]-current[i,0])*(current[j,1]-current[i,1]))
                grad_i = np.array([-(current[j,1]-current[k,1]), current[j,0]-current[k,0]])
                grad_j = np.array([current[k,1]-current[i,1], -(current[k,0]-current[i,0])])
                grad_k = np.array([-(current[j,1]-current[i,1]), current[j,0]-current[i,0]])
                dir_i = np.sign(s) * grad_i
                dir_j = np.sign(s) * grad_j
                dir_k = np.sign(s) * grad_k
                mag_i = np.linalg.norm(dir_i)
                mag_j = np.linalg.norm(dir_j)
                mag_k = np.linalg.norm(dir_k)
                mags = [mag_i, mag_j, mag_k]
                idx_in_triplet = np.argmax(mags)
                if idx_in_triplet == 0:
                    idx = i
                    direction = dir_i
                    mag = mag_i
                elif idx_in_triplet == 1:
                    idx = j
                    direction = dir_j
                    mag = mag_j
                else:
                    idx = k
                    direction = dir_k
                    mag = mag_k

            base_perturbation = np.random.normal(0, step_size, size=2)
            if mag > 1e-8:
                direction = direction / mag
                perturbation = 0.7 * step_size * direction + 0.3 * base_perturbation
            else:
                perturbation = base_perturbation

            candidate = current.copy()
            candidate[idx] += perturbation
            candidate[idx] = project_point_to_triangle(candidate[idx])

            new_score = get_smallest_triangle_area(candidate)
            if new_score < degeneracy_tol:
                no_improve_count += 1
                temperature = max(temperature * 0.995, 1e-8)
                continue

            delta = new_score - current_score
            if delta > 0 or np.random.rand() < np.exp(delta / temperature):
                current = candidate
                current_score = new_score
                if new_score > best_score:
                    best = candidate.copy()
                    best_score = new_score
                    step_size = max(step_size * 0.95, 1e-5)
                    no_improve_count = 0
                else:
                    no_improve_count += 1
            else:
                no_improve_count += 1

            # Adaptive step size recovery when stuck
            if no_improve_count > patience / 2:
                step_size = min(step_size * 1.1, 0.05)

            # Slower temperature decay
            temperature = max(temperature * 0.995, 1e-8)

            if no_improve_count >= patience:
                break

        return best

    return improve