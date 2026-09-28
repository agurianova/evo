import numpy as np
from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle
import itertools
import random

def entrypoint() -> np.ndarray:
    # Get triangle vertices
    A, B, C = get_unit_triangle()
    
    # Generate multiple candidate configurations and pick the best
    best_points = None
    best_min_area = -1
    
    # Try multiple random starts to avoid bad local optima
    for start_idx in range(25):
        # Create a configuration based on known good patterns for Heilbronn problem
        points = []
        
        # Base configuration (from known results for Heilbronn problem)
        # Avoiding vertices as research shows optimal configurations exclude them
        barycentric_points = [
            (0.2, 0.2, 0.6),     # Near C
            (0.2, 0.6, 0.2),     # Near B
            (0.6, 0.2, 0.2),     # Near A
            (0.3, 0.3, 0.4),     # Inner point 1
            (0.3, 0.4, 0.3),     # Inner point 2
            (0.4, 0.3, 0.3),     # Inner point 3
            (0.5, 0.4, 0.1),     # Near AB
            (0.4, 0.1, 0.5),     # Near AC
            (0.1, 0.5, 0.4),     # Near BC
            (0.75, 0.2, 0.05),   # Near A
            (0.2, 0.75, 0.05)    # Near B
        ]
        
        # Add calibrated perturbations to avoid perfect symmetry
        perturbation_magnitude = 0.04
        for i in range(len(barycentric_points)):
            u, v, w = barycentric_points[i]
            # Ensure sum remains 1 after perturbation
            du = random.uniform(-perturbation_magnitude, perturbation_magnitude)
            dv = random.uniform(-perturbation_magnitude, perturbation_magnitude)
            dw = -du - dv
            
            u_new, v_new, w_new = u + du, v + dv, w + dw
            # Ensure non-negative coordinates
            if u_new < 0 or v_new < 0 or w_new < 0:
                scale = min(1.0, 0.5 / max(abs(du/u) if u > 0 else 1, 
                                         abs(dv/v) if v > 0 else 1, 
                                         abs(dw/w) if w > 0 else 1))
                du, dv, dw = du * scale, dv * scale, dw * scale
                u_new, v_new, w_new = u + du, v + dv, w + dw
            
            # Convert to Cartesian
            point = u_new * A + v_new * B + w_new * C
            points.append(point)
        
        current_points = np.array(points)
        
        # Local search to improve min_area
        current_min_area = get_smallest_triangle_area(current_points)
        max_iter = 800
        initial_step = 0.09
        step_decay = 0.994
        min_step = 0.00015
        
        # Simulated annealing parameters
        temp = 0.03
        cooling_rate = 0.997
        
        for iter in range(max_iter):
            step_size = initial_step * (step_decay ** iter)
            if step_size < min_step:
                break
                
            # Find the smallest triangles (bottlenecks)
            triangle_areas = []
            for triplet in itertools.combinations(range(11), 3):
                i, j, k = triplet
                A_pt = current_points[i]
                B_pt = current_points[j]
                C_pt = current_points[k]
                signed_area = (B_pt[0]-A_pt[0])*(C_pt[1]-A_pt[1]) - (B_pt[1]-A_pt[1])*(C_pt[0]-A_pt[0])
                abs_area = 0.5 * abs(signed_area)
                triangle_areas.append((abs_area, triplet))
            
            # Sort and get the smallest triangles
            triangle_areas.sort(key=lambda x: x[0])
            smallest_triplets = [ta[1] for ta in triangle_areas[:8]]
            
            improved = False
            for triplet in smallest_triplets:
                i, j, k = triplet
                
                # For each point in the triplet, calculate improvement direction
                for idx in [i, j, k]:
                    others = [x for x in triplet if x != idx]
                    P = current_points[idx]
                    Q = current_points[others[0]]
                    R = current_points[others[1]]
                    
                    # Compute direction to move P to increase triangle area
                    qr = R - Q
                    # Perpendicular vector (gradient for area)
                    perp = np.array([-qr[1], qr[0]])
                    if np.linalg.norm(perp) > 1e-10:
                        perp = perp / np.linalg.norm(perp)
                    else:
                        continue
                    
                    # The sign depends on the orientation
                    s = (Q[0]-P[0])*(R[1]-P[1]) - (Q[1]-P[1])*(R[0]-P[0])
                    direction = np.sign(s) * perp
                    
                    # Try this direction
                    new_point = P + step_size * direction
                    
                    # Project to triangle if needed
                    if not is_inside_triangle(new_point, A, B, C):
                        # Sophisticated boundary projection
                        edges = [(A, B), (B, C), (C, A)]
                        min_dist = float('inf')
                        closest_point = None
                        
                        for (E1, E2) in edges:
                            edge_vec = E2 - E1
                            point_vec = new_point - E1
                            t = np.dot(point_vec, edge_vec) / np.dot(edge_vec, edge_vec)
                            t = max(0, min(1, t))
                            proj_point = E1 + t * edge_vec
                            
                            dist = np.linalg.norm(new_point - proj_point)
                            if dist < min_dist:
                                min_dist = dist
                                closest_point = proj_point
                        
                        new_point = closest_point
                    
                    # Create new configuration
                    new_points = current_points.copy()
                    new_points[idx] = new_point
                    new_min_area = get_smallest_triangle_area(new_points)
                    
                    # Simulated annealing acceptance
                    delta = new_min_area - current_min_area
                    if delta > 0 or (temp > 0.0005 and random.random() < np.exp(delta / temp)):
                        current_points = new_points
                        current_min_area = new_min_area
                        improved = True
        
            # Update temperature
            temp *= cooling_rate
        
        # Update best configuration if this start was better
        if current_min_area > best_min_area:
            best_points = current_points
            best_min_area = current_min_area

    return best_points