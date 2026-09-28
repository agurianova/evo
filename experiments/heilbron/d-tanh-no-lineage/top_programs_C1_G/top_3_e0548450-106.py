import numpy as np
from helper import get_unit_triangle, is_inside_triangle, get_smallest_triangle_area

np.random.seed(42)

def entrypoint() -> np.ndarray:
    A, B, C = get_unit_triangle()
    
    def generate_initial_points(A, B, C):
        # 3 vertices
        points = [A, B, C]
        
        # Calculate inward normals for each edge
        edge_vector_AB = B - A
        normal_AB = np.array([-edge_vector_AB[1], edge_vector_AB[0]])
        normal_AB = normal_AB / np.linalg.norm(normal_AB)
        
        edge_vector_BC = C - B
        normal_BC = np.array([-edge_vector_BC[1], edge_vector_BC[0]])
        normal_BC = normal_BC / np.linalg.norm(normal_BC)
        
        edge_vector_CA = A - C
        normal_CA = np.array([-edge_vector_CA[1], edge_vector_CA[0]])
        normal_CA = normal_CA / np.linalg.norm(normal_CA)
        
        # Generate and perturb edge points (1/3 and 2/3 positions)
        epsilon = 0.001
        for t in [1/3, 2/3]:
            # AB edge
            P = (1-t)*A + t*B
            points.append(P + epsilon * normal_AB)
            # BC edge
            P = (1-t)*B + t*C
            points.append(P + epsilon * normal_BC)
            # CA edge
            P = (1-t)*C + t*A
            points.append(P + epsilon * normal_CA)
        
        # Add 2 interior points symmetric about centroid
        centroid = (A + B + C) / 3
        vec = A - centroid
        factor = 0.2
        points.append(centroid + factor * vec)
        points.append(centroid - factor * vec)
        
        return np.array(points)

    def optimize(points, A, B, C, max_iter=1000):
        n_points = len(points)
        for iter in range(max_iter):
            # Find top 3 smallest triangles
            min_triangles = []
            for i in range(n_points):
                for j in range(i+1, n_points):
                    for k in range(j+1, n_points):
                        Ax, Ay = points[i]
                        Bx, By = points[j]
                        Cx, Cy = points[k]
                        area = 0.5 * abs((Bx - Ax) * (Cy - Ay) - (Cx - Ax) * (By - Ay))
                        min_triangles.append((area, i, j, k))
            
            min_triangles.sort(key=lambda x: x[0])
            top3 = min_triangles[:3]

            # Aggregate displacement vectors for all points
            displacements = np.zeros((n_points, 2))
            for (area, i, j, k) in top3:
                # Displacement for i (opposite edge jk)
                base_jk = points[k] - points[j]
                normal_jk = np.array([-base_jk[1], base_jk[0]])
                norm_jk = np.linalg.norm(normal_jk)
                if norm_jk > 1e-8:
                    normal_jk = normal_jk / norm_jk
                    d_i = np.dot(points[i] - points[j], normal_jk)
                    displacements[i] += np.sign(d_i) * normal_jk

                # Displacement for j (opposite edge ik)
                base_ik = points[k] - points[i]
                normal_ik = np.array([-base_ik[1], base_ik[0]])
                norm_ik = np.linalg.norm(normal_ik)
                if norm_ik > 1e-8:
                    normal_ik = normal_ik / norm_ik
                    d_j = np.dot(points[j] - points[i], normal_ik)
                    displacements[j] += np.sign(d_j) * normal_ik

                # Displacement for k (opposite edge ij)
                base_ij = points[j] - points[i]
                normal_ij = np.array([-base_ij[1], base_ij[0]])
                norm_ij = np.linalg.norm(normal_ij)
                if norm_ij > 1e-8:
                    normal_ij = normal_ij / norm_ij
                    d_k = np.dot(points[k] - points[i], normal_ij)
                    displacements[k] += np.sign(d_k) * normal_ij

            # Normalize displacement vectors
            for i in range(n_points):
                norm = np.linalg.norm(displacements[i])
                if norm > 1e-8:
                    displacements[i] = displacements[i] / norm

            # Apply movement with boundary projection
            step = 0.01 * (0.99 ** iter)
            new_points = points.copy()
            for i in range(n_points):
                new_point = points[i] + step * displacements[i]
                if not is_inside_triangle(new_point.reshape(1, 2), A, B, C):
                    temp_step = step
                    while temp_step > 1e-8:
                        temp_point = points[i] + temp_step * displacements[i]
                        if is_inside_triangle(temp_point.reshape(1, 2), A, B, C):
                            new_point = temp_point
                            break
                        temp_step *= 0.5
                    else:
                        new_point = points[i]
                new_points[i] = new_point
            points = new_points
        return points

    # Run multiple restarts
    best_points = None
    best_min_area = -1
    for _ in range(5):
        points = generate_initial_points(A, B, C)
        # Apply small jitter
        jitter = np.random.uniform(-0.01, 0.01, (11, 2))
        for i in range(11):
            new_point = points[i] + jitter[i]
            if is_inside_triangle(new_point.reshape(1, 2), A, B, C):
                points[i] = new_point
        
        optimized_points = optimize(points, A, B, C)
        min_area = get_smallest_triangle_area(optimized_points)
        if min_area > best_min_area:
            best_min_area = min_area
            best_points = optimized_points

    return best_points