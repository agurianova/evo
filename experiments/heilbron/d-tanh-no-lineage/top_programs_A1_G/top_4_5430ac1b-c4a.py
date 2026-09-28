import random
import numpy as np
import math
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    
    # Precompute triangle dimensions
    base = B[0] - A[0]
    height = C[1]

    def generate_hexagonal_lattice():
        """Generate points in an adaptive hexagonal lattice pattern within the triangle."""
        points = []
        # Determine optimal number of rows (between 3 and 5 for 11 points)
        n_rows = max(3, min(5, int(round(math.sqrt(11)))))
        # Calculate points per row to sum to 11 with decreasing counts
        points_per_row = []
        remaining = 11
        for i in range(n_rows):
            # More points in wider lower rows
            target = max(1, min(remaining, 5 - i))
            points_per_row.append(target)
            remaining -= target
        
        # Distribute any remaining points
        for i in range(remaining):
            points_per_row[i % n_rows] += 1
        
        for i in range(n_rows):
            y = (i + 0.5) * (height / n_rows)
            width = base * (1 - y / height)
            x0 = (base - width) / 2
            
            # Hexagonal pattern: alternate rows have horizontal offset
            offset = 0.125 * width if i % 2 == 1 else 0
            spacing = width / (points_per_row[i] - 1) if points_per_row[i] > 1 else 0
            
            for j in range(points_per_row[i]):
                x = x0 + j * spacing + offset
                
                # Add larger jitter to break regularity (±0.1)
                for _ in range(100):
                    dx = random.uniform(-0.1, 0.1)
                    dy = random.uniform(-0.1, 0.1)
                    candidate = np.array([x + dx, y + dy])
                    
                    if not is_inside_triangle([candidate], A, B, C):
                        continue
                    distinct = True
                    for p in points:
                        if np.linalg.norm(candidate - p) < 0.001:
                            distinct = False
                            break
                    if distinct:
                        points.append(candidate)
                        break
                else:
                    points.append(np.array([x, y]))
        
        return np.array(points)

    def geometric_rearrangement(points, A, B, C, base, height):
        """Rearrange points using geometric principles to enhance minimum triangle area."""
        # Sort points by y-coordinate
        sorted_indices = np.argsort(points[:, 1])
        sorted_points = points[sorted_indices]
        
        # Group points into rows based on y-coordinate proximity
        rows = []
        current_row = [sorted_points[0]]
        row_threshold = 0.075 * height  # 7.5% of height as threshold
        
        for i in range(1, len(sorted_points)):
            if sorted_points[i, 1] - current_row[-1][1] < row_threshold:
                current_row.append(sorted_points[i])
            else:
                rows.append(np.array(current_row))
                current_row = [sorted_points[i]]
        
        if current_row:
            rows.append(np.array(current_row))
        
        # Ensure we have reasonable rows (at least 2 points per row if possible)
        if len(rows) > 4:
            # Merge small rows
            merged_rows = []
            temp_row = []
            for row in rows:
                if len(temp_row) + len(row) <= 4 and len(temp_row) < 2:
                    temp_row.extend(row)
                else:
                    if temp_row:
                        merged_rows.append(np.array(temp_row))
                        temp_row = []
                    merged_rows.append(row)
            if temp_row:
                merged_rows.append(np.array(temp_row))
            rows = merged_rows

        # Rearrange each row with hexagonal pattern
        new_points = []
        for i, row in enumerate(rows):
            y = np.mean(row[:, 1])
            width = base * (1 - y / height)
            x0 = (base - width) / 2
            
            # Hexagonal pattern: alternate rows have offset
            offset = 0.125 * width if i % 2 == 1 else 0
            spacing = width / (len(row) - 1) if len(row) > 1 else 0
            
            for j in range(len(row)):
                x = x0 + j * spacing + offset
                # Add small vertical jitter to avoid perfect collinearity
                jitter_y = random.uniform(-0.01, 0.01)
                new_points.append([x, y + jitter_y])
        
        # Convert to array and validate
        new_points = np.array(new_points)
        
        # Check validity
        if not is_inside_triangle(new_points, A, B, C):
            return points  # Fallback to original
        
        min_dist = float('inf')
        for i in range(11):
            for j in range(i+1, 11):
                d = np.linalg.norm(new_points[i] - new_points[j])
                if d < min_dist:
                    min_dist = d
        if min_dist < 0.001:
            return points  # Fallback to original
        
        return new_points

    def simulated_annealing(initial_points, base_min_step, T0, num_iterations):
        points = initial_points.copy()
        current_min_area = get_smallest_triangle_area(points)
        
        for iter in range(num_iterations):
            # Track how many minimal triangles each point participates in
            point_counts = np.zeros(11, dtype=int)
            min_area_val = float('inf')
            critical_set = set()
            
            for i in range(11):
                for j in range(i+1, 11):
                    for k in range(j+1, 11):
                        a, b, c = points[i], points[j], points[k]
                        area = 0.5 * abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))
                        if area < min_area_val - 1e-9:
                            min_area_val = area
                            critical_set = {i, j, k}
                        elif abs(area - min_area_val) <= 1e-9:
                            critical_set.update([i, j, k])
            
            # Count participation in minimal triangles
            for idx in critical_set:
                point_counts[idx] += 1
            
            # Weighted selection: focus on geometrically critical points
            if np.sum(point_counts) > 0 and random.random() < 0.8:
                weights = point_counts / np.sum(point_counts)
                idx = np.random.choice(11, p=weights)
            else:
                idx = random.randint(0, 10)
            
            old_point = points[idx].copy()
            frac = iter / num_iterations
            # Adaptive step size: smaller when min_area is larger
            step_size = base_min_step * (1 - frac) * (0.0365 / max(min_area_val, 0.001))
            T = T0 * (1 - frac)

            delta = np.random.uniform(-step_size, step_size, size=2)
            candidate = old_point + delta
            
            if not is_inside_triangle([candidate], A, B, C):
                continue
            
            distinct = True
            for i in range(11):
                if i == idx:
                    continue
                if np.linalg.norm(candidate - points[i]) < 0.001:
                    distinct = False
                    break
            if not distinct:
                continue

            points[idx] = candidate
            new_min_area = get_smallest_triangle_area(points)
            if new_min_area <= 0:
                points[idx] = old_point
                continue

            delta_area = new_min_area - current_min_area
            if delta_area >= 0:
                current_min_area = new_min_area
            else:
                if T > 1e-9 and random.random() < math.exp(delta_area / T):
                    current_min_area = new_min_area
                else:
                    points[idx] = old_point

        return points

    best_config = None
    best_min_area = -1

    # More conservative parameters with adaptive behavior
    base_min_step = 0.05  # Reduced from 0.2
    T0 = 0.005  # Reduced from 0.01
    num_iterations = 5000

    for seed in range(10):
        np.random.seed(seed)
        random.seed(seed)
        
        # Generate hexagonal lattice instead of row patterns
        points = generate_hexagonal_lattice()
        
        if not is_inside_triangle(points, A, B, C):
            continue
        
        # First annealing phase
        points1 = simulated_annealing(points, base_min_step, T0, num_iterations)
        min_area1 = get_smallest_triangle_area(points1)
        
        # Geometric rearrangement phase
        points2 = geometric_rearrangement(points1, A, B, C, base, height)
        min_area2 = get_smallest_triangle_area(points2)
        
        # Second annealing phase on rearranged points
        points3 = simulated_annealing(points2, base_min_step, T0, num_iterations)
        min_area3 = get_smallest_triangle_area(points3)

        # Choose better configuration
        if min_area3 > min_area1:
            final_points = points3
        else:
            final_points = points1

        # Track best configuration across seeds
        final_area = get_smallest_triangle_area(final_points)
        if final_area > best_min_area:
            best_min_area = final_area
            best_config = final_points.copy()

    return best_config