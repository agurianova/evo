import numpy as np
import random
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

np.random.seed(42)
random.seed(42)

def barycentric_projection(P, A, B, C):
    v0 = B - A
    v1 = C - A
    v2 = P - A
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-10:
        return A
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    
    if u < 0:
        u = 0
        total = v + w
        if total > 0:
            v /= total
            w /= total
        else:
            v = 0.5
            w = 0.5
    if v < 0:
        v = 0
        total = u + w
        if total > 0:
            u /= total
            w /= total
        else:
            u = 0.5
            w = 0.5
    if w < 0:
        w = 0
        total = u + v
        if total > 0:
            u /= total
            v /= total
        else:
            u = 0.5
            v = 0.5
    
    return u * A + v * B + w * C

def distance_to_line(p, a, b):
    ap = p - a
    ab = b - a
    t = np.dot(ap, ab) / (np.dot(ab, ab) + 1e-10)
    t = max(0, min(1, t))
    projection = a + t * ab
    return np.linalg.norm(p - projection)

def distance_to_boundary(point, A, B, C):
    d1 = distance_to_line(point, A, B)
    d2 = distance_to_line(point, B, C)
    d3 = distance_to_line(point, C, A)
    return min(d1, d2, d3)

def triangle_area(a, b, c):
    return 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

def generate_triangular_symmetric_initialization(A, B, C):
    # Center point with vertex-directed offset based on ring structure
    centroid = (A + B + C) / 3
    
    # Direction toward vertex B (right vertex)
    vertex_dir = (B - centroid)
    vertex_dir = vertex_dir / np.linalg.norm(vertex_dir)
    
    # Offset magnitude proportional to first ring radius
    offset_magnitude = 0.08
    points = [centroid + offset_magnitude * vertex_dir]

    # First ring: hexagonal pattern (6 points) aligned with triangular symmetry
    radius1 = 0.22
    for i in range(6):
        angle = 2 * math.pi * i / 6  # 60 degree increments
        x = centroid[0] + radius1 * math.cos(angle)
        y = centroid[1] + radius1 * math.sin(angle)
        points.append(np.array([x, y]))

    # Second ring: pentagonal pattern with vertex-aligned offset
    radius2 = 0.42
    # Vertex-aligned offsets: 0°, 72°, 144°, 216°, 288°
    offsets = [0, 72, 144, 216, 288]
    for i in range(5):
        angle = math.radians(offsets[i])
        x = centroid[0] + radius2 * math.cos(angle)
        y = centroid[1] + radius2 * math.sin(angle)
        points.append(np.array([x, y]))

    # Project all points to ensure inside triangle
    for i in range(len(points)):
        points[i] = barycentric_projection(points[i], A, B, C)
        
    # Add adaptive noise to break perfect symmetry
    for i in range(len(points)):
        # Noise magnitude decreases for outer rings
n        ring_index = 0 if i == 0 else 1 if i <= 6 else 2
        noise_magnitude = 0.03 / (ring_index + 1)
        noise = np.random.uniform(-noise_magnitude, noise_magnitude, 2)
        points[i] += noise
        points[i] = barycentric_projection(points[i], A, B, C)

    return np.array(points)

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    num_points = 11
    num_starts = 25  # Slightly reduced due to higher quality starts

    best_config = None
    best_min_area = -1

    for start in range(num_starts):
        # Use triangular-symmetry-biased initialization
        points = generate_triangular_symmetric_initialization(A, B, C)

        # Simulated annealing parameters
        initial_temp = 0.18  # Slightly increased to match larger search space
        temp = initial_temp
        cooling_rate = 0.994
        min_temp = 1e-6
        base_step = 0.055
        max_no_improve = 70
        no_improve_count = 0

        current_min_area = get_smallest_triangle_area(points)

        # Annealing loop
        while temp > min_temp and no_improve_count < max_no_improve:
            # Track continuous boundary influence for each point
            boundary_influence = np.zeros(num_points)
            boundary_threshold = 0.1  # Unified boundary distance threshold
            for idx in range(num_points):
                dist = distance_to_boundary(points[idx], A, B, C)
                # Continuous scaling from 1.0 (on boundary) to 0.0 (interior)
                boundary_influence[idx] = max(0.0, 1.0 - dist / boundary_threshold)

            # Adaptive selection of critical triangles based on temperature
            # More triangles considered when temperature is high (early optimization)
            # Fewer triangles when temperature is low (late optimization)
            adaptive_k = max(3, min(10, int(8 * (temp / initial_temp) + 2)))
            
            # Find smallest triangles
            min_areas = []
            for i in range(num_points):
                for j in range(i+1, num_points):
                    for k in range(j+1, num_points):
                        area_val = triangle_area(points[i], points[j], points[k])
                        min_areas.append((area_val, i, j, k))

            # Sort and take top k smallest
            min_areas.sort(key=lambda x: x[0])
            k_smallest = min_areas[:adaptive_k]

            # Aggregate gradients from all k smallest triangles
            grad_updates = np.zeros((num_points, 2))
            total_weight = 0
            
            for area_val, i, j, k in k_smallest:
                a, b, c = points[i], points[j], points[k]

                # Compute signed area for gradient direction
                s_val = 0.5 * ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                if s_val < 0:
                    b, c = c, b
                    j, k = k, j
                    s_val = -s_val

                # Compute gradient directions
                grad_a = np.array([b[1] - c[1], c[0] - b[0]])
                grad_b = np.array([c[1] - a[1], a[0] - c[0]])
                grad_c = np.array([a[1] - b[1], b[0] - a[0]])

                # Normalize gradients
                norm_a = np.linalg.norm(grad_a)
                norm_b = np.linalg.norm(grad_b)
                norm_c = np.linalg.norm(grad_c)
                
                if norm_a > 1e-5:
                    grad_a = grad_a / norm_a
                if norm_b > 1e-5:
                    grad_b = grad_b / norm_b
                if norm_c > 1e-5:
                    grad_c = grad_c / norm_c

                # Weight by how critical the triangle is (smaller = more critical)
                weight = 1.0 / (area_val + 1e-10)
                total_weight += weight

                grad_updates[i] += weight * grad_a
                grad_updates[j] += weight * grad_b
                grad_updates[k] += weight * grad_c

            # Normalize aggregated gradients
            if total_weight > 0:
                for idx in range(num_points):
                    if np.linalg.norm(grad_updates[idx]) > 1e-5:
                        grad_updates[idx] = grad_updates[idx] / np.linalg.norm(grad_updates[idx])

            # Apply updates with temperature-scaled step size and continuous boundary awareness
            candidate = points.copy()
            step_size = base_step * (temp / initial_temp)
            improved = False

            for idx in range(num_points):
                # Smooth boundary step modulation using cubic easing
                boundary_factor = 1.0 - 0.7 * (boundary_influence[idx] ** 3)
                candidate[idx] = points[idx] + step_size * boundary_factor * grad_updates[idx]
                candidate[idx] = barycentric_projection(candidate[idx], A, B, C)

            # Check validity
            if not is_inside_triangle(candidate, A, B, C):
                temp *= cooling_rate
                no_improve_count += 1
                continue

            candidate_min_area = get_smallest_triangle_area(candidate)

            # Simulated annealing acceptance
            if candidate_min_area > current_min_area:
                points = candidate
                current_min_area = candidate_min_area
                no_improve_count = 0
                improved = True
            else:
                delta = current_min_area - candidate_min_area
                if random.random() < math.exp(-delta / temp):
                    points = candidate
                    current_min_area = candidate_min_area
                    no_improve_count = 0
                    improved = True
                else:
                    no_improve_count += 1

            # Cool down
            if improved:
                temp *= cooling_rate

        # Track best configuration
        if current_min_area > best_min_area:
            best_min_area = current_min_area
            best_config = points.copy()

    return best_config