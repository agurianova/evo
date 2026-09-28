import random
import math
import numpy as np
import scipy.optimize
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle

def entrypoint() -> np.ndarray:
    tri = get_unit_triangle()
    A, B, C = tri

    def project_to_triangle(P, A, B, C):
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
            return (A + B + C) / 3
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1 - v - w
        
        if u < 0:
            u = 0
            total = v + w
            if total < 1e-10:
                return (A + B + C) / 3
            v /= total
            w /= total
        if v < 0:
            v = 0
            total = u + w
            if total < 1e-10:
                return (A + B + C) / 3
            u /= total
            w /= total
        if w < 0:
            w = 0
            total = u + v
            if total < 1e-10:
                return (A + B + C) / 3
            u /= total
            v /= total
        return u * A + v * B + w * C

    def generate_random_points(n):
        points = []
        while len(points) < n:
            u = random.random()
            v = random.random()
            if u + v > 1:
                u, v = 1 - u, 1 - v
            w = 1 - u - v
            P = u * A + v * B + w * C
            
            distinct = True
            for p in points:
                if np.linalg.norm(P - p) < 1e-5:
                    distinct = False
                    break
            
            if distinct and is_inside_triangle(P, A, B, C):
                points.append(P)
        return np.array(points)

    def generate_structured_points(restart, total_restarts, current_min=0.0):
        points = [A, B, C]
        # Adaptive barycentric constraint: start conservative, gradually relax
        min_bary = max(0.02, 0.05 - 0.03 * restart / total_restarts)
        
        # Adaptive perturbation scale based on current solution quality
        scale = 1.0 + 0.5 * (0.0365 - current_min) / 0.0365
        radial_range = (0.01 * scale, 0.03 * scale)
        tangential_range = (-0.02 * scale, 0.02 * scale)

        for _ in range(8):
            while True:
                u = random.uniform(min_bary, 1 - 2*min_bary)
                v = random.uniform(min_bary, 1 - u - min_bary)
                w = 1 - u - v
                if w >= min_bary:
                    break
            base_point = u * A + v * B + w * C
            
            current_centroid = np.mean(points, axis=0)
            direction = base_point - current_centroid
            if np.linalg.norm(direction) > 1e-5:
                direction = direction / np.linalg.norm(direction)
            else:
                direction = np.array([1, 0])
            
            radial_component = random.uniform(*radial_range)
            tangential_component = random.uniform(*tangential_range)
            perp = np.array([-direction[1], direction[0]])
            perturbation = radial_component * direction + tangential_component * perp
            point = base_point + perturbation
            
            point = project_to_triangle(point, A, B, C)
            points.append(point)
        
        return np.array(points)

    total_restarts = 50
    best_min_area = -1
    best_points = None
    
    # Track success rates for adaptive restart allocation
    structured_success = 0
    random_success = 0
    success_window = 5  # Track last 5 restarts
    recent_methods = []

    for restart in range(total_restarts):
        seed = 42 + restart * 1000003
        np.random.seed(seed)
        random.seed(seed)

        # Adaptive restart allocation based on recent performance
        if restart < 2 or len(recent_methods) < success_window:
            # Initial restarts: 70% structured
            use_structured = random.random() < 0.7
        else:
            # Calculate recent success rates
            structured_count = recent_methods.count('structured')
            random_count = recent_methods.count('random')
            
            structured_rate = structured_success / max(1, structured_count) if structured_count > 0 else 0.5
            random_rate = random_success / max(1, random_count) if random_count > 0 else 0.5
            
            # Favor the better-performing method
            use_structured = structured_rate >= random_rate

        if use_structured:
            candidate_points = generate_structured_points(restart, total_restarts, best_min_area if best_min_area > 0 else 0.0)
        else:
            candidate_points = generate_random_points(11)
            perturbation = np.random.uniform(-0.02, 0.02, (11, 2))
            candidate_points += perturbation

        for i in range(11):
            candidate_points[i] = project_to_triangle(candidate_points[i], A, B, C)

        for i in range(11):
            for j in range(i + 1, 11):
                if np.linalg.norm(candidate_points[i] - candidate_points[j]) < 1e-5:
                    angle = random.uniform(0, 2 * math.pi)
                    dx = 0.001 * math.cos(angle)
                    dy = 0.001 * math.sin(angle)
                    candidate_points[j] += np.array([dx, dy])
                    candidate_points[j] = project_to_triangle(candidate_points[j], A, B, C)

        current_points = candidate_points.copy()
        current_min = get_smallest_triangle_area(current_points)
        
        T = 0.1
        cooling_rate = 0.9999
        min_temp = 1e-6
        step_size = 0.05
        min_step = 1e-5
        max_iterations_restart = 100000
        
        best_min_restart = current_min
        best_points_restart = current_points.copy()
        acceptance_history = []
        stall_count = 0  # Track iterations without best-restart improvement
        improvement_rate = 0.0
n        for iteration in range(max_iterations_restart):
            i = random.randint(0, 10)
            angle = random.uniform(0, 2 * math.pi)
            dx = step_size * math.cos(angle)
            dy = step_size * math.sin(angle)
            new_point = current_points[i] + np.array([dx, dy])
            new_point = project_to_triangle(new_point, A, B, C)

            distinct = True
            for j in range(11):
                if j == i:
                    continue
                if np.linalg.norm(new_point - current_points[j]) < 1e-5:
                    distinct = False
                    break
            if not distinct:
                continue

            new_points = current_points.copy()
            new_points[i] = new_point
            new_min = get_smallest_triangle_area(new_points)

            if new_min < 1e-10:
                acceptance_history.append(False)
                continue

            if new_min > current_min:
                accepted = True
            else:
                delta = new_min - current_min
                if random.random() < math.exp(delta / T):
                    accepted = True
                else:
                    accepted = False

            if accepted:
                current_points = new_points
                current_min = new_min
                acceptance_history.append(True)
                
                if current_min > best_min_restart:
                    best_min_restart = current_min
                    best_points_restart = current_points.copy()
                    stall_count = 0  # Reset stall counter on improvement
                    improvement_rate = min(1.0, improvement_rate + 0.01)
                else:
                    stall_count += 1
            else:
                acceptance_history.append(False)
                stall_count += 1

            # Adaptive step size adjustment
            if len(acceptance_history) >= 100:
                recent_accepts = acceptance_history[-100:]
                acceptance_rate = sum(recent_accepts) / 100.0
                if acceptance_rate > 0.5:
                    step_size *= 1.05  # Reduced from 1.10 for stability
                elif acceptance_rate < 0.2:
                    step_size *= 0.95  # Increased from 0.90 for stability
                step_size = max(min_step, min(step_size, 0.1))

            # Enhanced reheating mechanism: trigger earlier with adaptive temperature
            if stall_count > 10000 and T < 0.01:
                # Adaptive temperature based on improvement rate
                T = 0.05 + 0.05 * (1 - improvement_rate)
                stall_count = 0

            T *= cooling_rate
            if step_size < min_step or T < min_temp:
                break

        # Track success for adaptive restart allocation
        if use_structured:
            if best_min_restart > 0.030:
                structured_success += 1
            recent_methods.append('structured')
        else:
            if best_min_restart > 0.030:
                random_success += 1
            recent_methods.append('random')
        
        # Maintain window size
        if len(recent_methods) > success_window:
            recent_methods.pop(0)

        if best_min_restart > best_min_area:
            best_min_area = best_min_restart
            best_points = best_points_restart.copy()

    # Lower threshold for Nelder-Mead to 0.030 and increase iterations
    if best_min_area > 0.030:
        x0 = best_points.flatten()
        
        def objective(x):
            points = x.reshape(11, 2)
            for i in range(11):
                points[i] = project_to_triangle(points[i], A, B, C)
            min_area = get_smallest_triangle_area(points)
            return -min_area

        res = scipy.optimize.minimize(
            objective, x0, method='Nelder-Mead',
            options={'maxiter': 1000, 'xatol': 1e-6, 'fatol': 1e-6}
        )
        if res.success:
            candidate_points = res.x.reshape(11, 2)
            for i in range(11):
                candidate_points[i] = project_to_triangle(candidate_points[i], A, B, C)
            candidate_min = get_smallest_triangle_area(candidate_points)
            if candidate_min > best_min_area:
                best_min_area = candidate_min
                best_points = candidate_points

    return best_points