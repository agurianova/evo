import random
import math
import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri
    mid_x = (A[0] + B[0]) / 2.0

    def build_full_configuration(base_points, mid_x, asymmetric_indices):
        points = []
        # Axis point (base_points[0])
        points.append(base_points[0])
        # Right points (base_points[1:6])
        for i in range(1, 6):
            points.append(base_points[i])
        
        # Left points
        left_points = []
        asymmetric_counter = 0
        for i in range(1, 6):
            if i in asymmetric_indices:
                # Use pre-generated asymmetric left point
                left_points.append(base_points[6 + asymmetric_counter])
                asymmetric_counter += 1
            else:
                # Mirror symmetric points
                x, y = base_points[i]
                mirror_x = 2 * mid_x - x
                left_points.append(np.array([mirror_x, y]))
        points.extend(left_points)
        return np.array(points)

    def generate_boundary_point():
        """Generate point within 0.1 of triangle boundary with min distance 0.05"""
        while True:
            # Choose random edge
            edge = random.choice(['AB', 'BC', 'CA'])
            if edge == 'AB':
                # Bottom edge
                t = random.random()
                P = (1-t)*A + t*B
                # Offset perpendicular to edge (upwards)
                normal = np.array([0, 1])  # Since AB is horizontal
                offset = 0.1 * random.random() * normal
                P += offset
            elif edge == 'BC':
                # Right edge
                t = random.random()
                P = (1-t)*B + t*C
                # Perpendicular vector (left-up)
                normal = np.array([-(C[1]-B[1]), C[0]-B[0]])
                normal = normal / np.linalg.norm(normal) * 0.1 * random.random()
                P += normal
            else:  # 'CA'
                # Left edge
                t = random.random()
                P = (1-t)*C + t*A
                # Perpendicular vector (right-up)
                normal = np.array([C[1]-A[1], -(C[0]-A[0])])
                normal = normal / np.linalg.norm(normal) * 0.1 * random.random()
                P += normal
            
            if is_inside_triangle(P, A, B, C):
                return P

    def generate_hexagonal_grid():
        """Generate hexagonal grid pattern scaled to triangle"""
        grid_points = []
        # Hexagonal grid parameters
        rows = 3
        cols = 4
        spacing = 0.3
        for i in range(rows):
            for j in range(cols):
                x = j * spacing * 0.866  # cos(30)
                y = i * spacing + (j % 2) * spacing * 0.5
                # Map to triangle using barycentric coordinates
                u = x / 1.5
                v = y / 1.3
                if u + v <= 1:
                    P = (1 - u - v) * A + u * B + v * C
                    if is_inside_triangle(P, A, B, C):
                        grid_points.append(P)
        return grid_points[:5]  # Return up to 5 points

    restarts = 10
    best_min_area = -1
    best_points = None

    for restart in range(restarts):
        # Set deterministic seed per restart
        np.random.seed(42 + restart)
        random.seed(42 + restart)

        # Choose restart type with weights
        restart_type = random.choices(['random', 'boundary', 'hexagonal'], 
                                    weights=[0.5, 0.3, 0.2])[0]
        
        # Choose asymmetric configuration (0,1, or 2 asymmetric points)
        k = random.choices([0, 1, 2], weights=[0.5, 0.3, 0.2])[0]
        asymmetric_indices = random.sample(range(1, 6), k) if k > 0 else []

        base_points = []
        
        # Axis point (index0): random on midline from (mid_x,0) to C
        u0 = random.random()
        base_points.append((1 - u0) * np.array([mid_x, 0]) + u0 * C)
        
        # Right points (indices 1-5)
        for _ in range(5):
            while True:
                if restart_type == 'boundary':
                    P = generate_boundary_point()
                    # Ensure right half
                    if P[0] <= mid_x:
                        P = np.array([2 * mid_x - P[0], P[1]])
                elif restart_type == 'hexagonal':
                    # Will fill later if needed
                    P = None
                else:  # 'random'
                    u = random.random()
                    v = random.random() * (1 - u)
                    P = (1 - u - v) * A + u * B + v * C
                    # Force right half
                    if P[0] <= mid_x:
                        P = np.array([2 * mid_x - P[0], P[1]])

                # Skip if too close to midline
                if P is not None and P[0] <= mid_x + 1e-5:
                    continue
                
                # Check distinctness
                distinct = True
                for p in base_points:
                    if np.linalg.norm(P - p) < 0.05:  # Minimum distance constraint
                        distinct = False
                        break
                if distinct:
                    base_points.append(P)
                    break

        # Fill hexagonal grid if needed
        if restart_type == 'hexagonal':
            hex_points = generate_hexagonal_grid()
            for i in range(5):
                if i < len(hex_points):
                    base_points[i+1] = hex_points[i]
                else:
                    # Fallback to random
                    while True:
                        u = random.random()
                        v = random.random() * (1 - u)
                        P = (1 - u - v) * A + u * B + v * C
                        if P[0] > mid_x + 1e-5:
                            base_points[i+1] = P
                            break

        # Asymmetric left points (if any)
        for _ in range(k):
            while True:
                if restart_type == 'boundary':
                    P = generate_boundary_point()
                    # Ensure left half
                    if P[0] >= mid_x:
                        P = np.array([2 * mid_x - P[0], P[1]])
                else:
                    u = random.random()
                    v = random.random() * (1 - u)
                    P = (1 - u - v) * A + u * B + v * C
                    # Force left half
                    if P[0] >= mid_x:
                        P = np.array([2 * mid_x - P[0], P[1]])

                if P[0] >= mid_x - 1e-5:
                    continue

                distinct = True
                for p in base_points:
                    if np.linalg.norm(P - p) < 0.05:
                        distinct = False
                        break
                if distinct:
                    base_points.append(P)
                    break

        base_points = [np.array(p) for p in base_points]
        full_points = build_full_configuration(base_points, mid_x, asymmetric_indices)
        current_min = get_smallest_triangle_area(full_points)

        # Simulated annealing parameters
        T = 0.005  # Fixed initial temperature (10% of target 0.0365)
        cooling_rate = 0.9995
        min_temp = 1e-6
        step_size = 0.05  # Increased initial step size
        min_step = 1e-5
        max_no_improve = 500
        no_improve_count = 0
        max_iterations_restart = 50000
        best_min_so_far = current_min

        for iteration in range(max_iterations_restart):
            # Move any base point (0 to 5+k)
            i = random.randint(0, len(base_points) - 1)

            if i == 0:
                # Axis point: allow temporary horizontal movement with projection
                angle = random.uniform(0, 2 * math.pi)
                dx = step_size * math.cos(angle)
                dy = step_size * math.sin(angle)
                new_point = base_points[0] + np.array([dx, dy])
                # Project to axis
                new_point = np.array([mid_x, new_point[1]])
            else:
                # Right or asymmetric left points
                angle = random.uniform(0, 2 * math.pi)
                dx = step_size * math.cos(angle)
                dy = step_size * math.sin(angle)
                new_point = base_points[i] + np.array([dx, dy])

                # Handle boundary cases
                if i <= 5:  # Right point
                    if new_point[0] < mid_x:
                        new_point[0] = 2 * mid_x - new_point[0]  # Reflect to right
                else:  # Asymmetric left point
                    if new_point[0] > mid_x:
                        new_point[0] = 2 * mid_x - new_point[0]  # Reflect to left

            # Validate new position
            if not is_inside_triangle(new_point, A, B, C):
                # Project to triangle
                if not is_inside_triangle(new_point, A, B, C):
                    u = random.random()
                    v = random.random() * (1 - u)
                    new_point = (1 - u - v) * A + u * B + v * C

            # Check distinctness
            distinct = True
            for j in range(len(base_points)):
                if j == i:
                    continue
                if np.linalg.norm(new_point - base_points[j]) < 0.05:
                    distinct = False
                    break
            if not distinct:
                # Adaptive step adjustment on failure
                step_size = max(step_size * 0.9, min_step)
                no_improve_count += 1
                T *= cooling_rate
                continue

            # Attempt move
            old_point = base_points[i].copy()
            base_points[i] = new_point
            full_points = build_full_configuration(base_points, mid_x, asymmetric_indices)
            new_min = get_smallest_triangle_area(full_points)

            # Simulated annealing acceptance
            if new_min > current_min:
                current_min = new_min
                best_min_so_far = max(best_min_so_far, new_min)
                no_improve_count = 0
                # Adaptive step increase on improvement
                step_size = min(step_size * 1.1, 0.1)
                accepted = True
            else:
                delta = new_min - current_min
                if random.random() < math.exp(delta / T):
                    current_min = new_min
                    no_improve_count = 0
                    step_size = min(step_size * 1.1, 0.1)
                    accepted = True
                else:
                    accepted = False

            if not accepted:
                base_points[i] = old_point
                no_improve_count += 1
                # Adaptive step decrease on stagnation
                step_size = max(step_size * 0.9, min_step)

            # Stagnation recovery with large perturbations
            if no_improve_count >= max_no_improve:
                # 5% chance of large perturbation
                if random.random() < 0.05:
                    i_large = random.randint(0, len(base_points) - 1)
                    old_large = base_points[i_large].copy()
                    
                    # Large step (10x current step_size)
                    angle = random.uniform(0, 2 * math.pi)
                    dx = 10 * step_size * math.cos(angle)
                    dy = 10 * step_size * math.sin(angle)
                    new_large = base_points[i_large] + np.array([dx, dy])

                    # Project to triangle if needed
n                    if not is_inside_triangle(new_large, A, B, C):
                        u = random.random()
                        v = random.random() * (1 - u)
                        new_large = (1 - u - v) * A + u * B + v * C

                    # Check distinctness
                    distinct_large = True
                    for j in range(len(base_points)):
                        if j == i_large:
                            continue
                        if np.linalg.norm(new_large - base_points[j]) < 0.05:
                            distinct_large = False
                            break
                    
                    if distinct_large:
                        base_points[i_large] = new_large
                        full_points = build_full_configuration(base_points, mid_x, asymmetric_indices)
                        new_min_large = get_smallest_triangle_area(full_points)
                        if new_min_large > current_min:
                            current_min = new_min_large
                            best_min_so_far = max(best_min_so_far, new_min_large)
                            step_size = min(step_size * 1.1, 0.1)
                            no_improve_count = 0
                        else:
                            base_points[i_large] = old_large
                
                no_improve_count = 0

            # Cool temperature
            T *= cooling_rate

            # Termination conditions
            if step_size < min_step or T < min_temp:
                break

        # Track best configuration across restarts
        if current_min > best_min_area:
            best_min_area = current_min
            best_points = build_full_configuration(base_points, mid_x, asymmetric_indices)

    return best_points