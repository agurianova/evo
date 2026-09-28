import numpy as np
from itertools import combinations
from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
from scipy.stats import kurtosis
from scipy.spatial import Voronoi
from sklearn.cluster import DBSCAN

np.random.seed(42)

# Global constants for theoretical optimum
THEORETICAL_OPTIMUM = 0.0365

# Self-adaptive parameter system
class AdaptiveParameterSystem:
    def __init__(self):
        # Exponential moving average parameters
        self.alpha = 0.2  # Smoothing factor
        self.beta = 0.15  # Progress influence factor
        
        # Initialize EMA values
        self.improvement_ema = 0.0
        self.progress = 0.0  # Current progress toward optimum (0-1)
        
        # Base parameter values
        self.params = {
            'step_size_base': 0.015,
            'phase_transition_threshold': 0.0003,
            'temperature_base': 0.04,
            'gradient_exponent_range': (0.15, 1.3),
            'voronoi_perturbation_scale': 0.018,
            'cluster_perturbation_scale': 0.025,
            'min_cluster_size': 2,
            'max_cluster_eps': 0.15
        }

    def update(self, improvement, current_min_area):
        # Update improvement EMA
        self.improvement_ema = self.alpha * improvement + (1 - self.alpha) * self.improvement_ema
        
        # Update progress (0-1 scale)
        self.progress = min(1.0, current_min_area / THEORETICAL_OPTIMUM)
        
        # Dynamic adjustments based on progress
        progress_factor = 1.0 - self.progress
        
        # Phase transition threshold increases as we approach optimum
        self.params['phase_transition_threshold'] = 0.0001 + 0.0004 * progress_factor
        
        # Step size decreases as we approach optimum but maintains exploration
        self.params['step_size_base'] = 0.01 * (0.7 + 0.3 * progress_factor)
        
        # Temperature adapts based on both progress and improvement rate
        improvement_factor = max(0.1, min(1.0, abs(self.improvement_ema) * 500))
        self.params['temperature_base'] = 0.02 * (0.5 + 0.5 * progress_factor) * (1.5 - improvement_factor)
        
        # Gradient exponent range widens as difficulty increases
        self.params['gradient_exponent_range'] = (
            0.1 + 0.05 * progress_factor,
            1.2 + 0.1 * (1 - progress_factor)
        )
        
        # Voronoi perturbation scale increases when stuck
        if improvement_factor < 0.3:
            self.params['voronoi_perturbation_scale'] = 0.025
        else:
            self.params['voronoi_perturbation_scale'] = 0.012
        
        # Cluster perturbation adapts based on progress
        self.params['cluster_perturbation_scale'] = 0.02 * (1.0 + 0.5 * progress_factor)
        
        # Cluster size parameters adapt to density
        self.params['min_cluster_size'] = max(2, int(3 * (1.0 - progress_factor)))
        self.params['max_cluster_eps'] = 0.1 + 0.05 * progress_factor

    def get_step_size(self, phase):
        phase_multipliers = {1: 1.0, 2: 0.4, 3: 0.15}
        return self.params['step_size_base'] * phase_multipliers[phase]

    def get_phase_transition_threshold(self):
        return self.params['phase_transition_threshold']

    def get_temperature(self):
        return self.params['temperature_base']

    def get_gradient_exponent(self, difficulty_factor):
        min_exp, max_exp = self.params['gradient_exponent_range']
        return min_exp + (max_exp - min_exp) * (1 - difficulty_factor)

    def get_voronoi_perturbation_scale(self):
        return self.params['voronoi_perturbation_scale']

    def get_cluster_perturbation_params(self):
        return {
            'scale': self.params['cluster_perturbation_scale'],
            'min_size': self.params['min_cluster_size'],
            'max_eps': self.params['max_cluster_eps']
        }


def compute_voronoi_centroids(points, A, B, C):
    """Compute Voronoi centroids for points inside the triangle with optimized containment check"""
    # Create bounding box that contains the triangle
    triangle = np.array([A, B, C])
    min_x, min_y = np.min(triangle, axis=0) - 0.1
    max_x, max_y = np.max(triangle, axis=0) + 0.1
    
    # Create extended points for Voronoi with bounding box
    bounding_box = np.array([
        [min_x, min_y],
        [max_x, min_y],
        [max_x, max_y],
        [min_x, max_y]
    ])
    all_points = np.vstack([points, bounding_box])
    
    # Compute Voronoi diagram
    vor = Voronoi(all_points)
    
    # Compute centroids of Voronoi regions within the triangle
    centroids = np.zeros_like(points)
    for i in range(len(points)):
        region = vor.regions[vor.point_region[i]]
        if -1 not in region and len(region) > 0:
            polygon = vor.vertices[region]
            
            # OPTIMIZATION: First check if polygon centroid is inside triangle
            polygon_centroid = np.mean(polygon, axis=0)
            if is_inside_triangle(polygon_centroid, A, B, C):
                centroids[i] = polygon_centroid
            else:
                # Only filter vertices if centroid is outside
                filtered_polygon = [p for p in polygon if is_inside_triangle(p, A, B, C)]
                if len(filtered_polygon) >= 3:
                    filtered_polygon = np.array(filtered_polygon)
                    centroid = np.mean(filtered_polygon, axis=0)
                    centroids[i] = centroid
                else:
                    centroids[i] = points[i]
        else:
            centroids[i] = points[i]
            
    return centroids

def project_point_to_triangle(p, A, B, C):
    """Project point p onto the triangle defined by A, B, C"""
    v0 = B - A
    v1 = C - A
    v2 = p - A
    
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
    
    if v < 0:
        v = 0
        w = max(0, min(1, w))
    if w < 0:
        w = 0
        v = max(0, min(1, v))
    if v + w > 1:
        total = v + w
        v /= total
        w /= total
        
    return A + v * v0 + w * v1

def identify_critical_clusters(points, top_triangles, params):
    """Identify spatial clusters of points involved in small triangles using DBSCAN"""
    # Get all points involved in top triangles
    critical_indices = set()
    for _, i, j, k, _ in top_triangles:
        critical_indices.add(i)
        critical_indices.add(j)
        critical_indices.add(k)
    
    critical_indices = list(critical_indices)
    if not critical_indices:
        return []
    
    # Extract critical points
    critical_points = points[critical_indices]
    
    # Scale coordinates for meaningful DBSCAN distance
    if len(critical_points) > 1:
        mean_point = np.mean(critical_points, axis=0)
        std_point = np.std(critical_points, axis=0)
        std_point = np.where(std_point < 1e-10, 1e-10, std_point)
        scaled_points = (critical_points - mean_point) / std_point
n        # Adaptive DBSCAN parameters based on point density
        eps = params['max_eps'] * (0.5 + 0.5 * (1 - len(critical_points)/11))
        min_samples = max(2, min(params['min_size'], len(critical_points)//2))
        
        # Perform DBSCAN clustering
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(scaled_points)
        
        # Group points by cluster
        clusters = {}
        for idx, label in enumerate(clustering.labels_):
            if label != -1:  # Ignore noise points
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(critical_indices[idx])
        
        return list(clusters.values())
    else:
        # Single critical point case
        return [[critical_indices[0]]]

def apply_cluster_perturbation(points, clusters, params, A, B, C):
    """Apply coherent perturbation to identified critical clusters"""
    perturbed_points = points.copy()
    
    for cluster in clusters:
        # Calculate cluster properties
        cluster_points = points[cluster]
        centroid = np.mean(cluster_points, axis=0)
        
        # Adaptive perturbation magnitude (inverse to cluster size)
        magnitude = params['scale'] / (np.sqrt(len(cluster)) + 0.5)
        
        # Random direction (coherent for entire cluster)
        direction = np.random.normal(0, 1, size=2)
        direction = direction / (np.linalg.norm(direction) + 1e-10)
        
        # Apply perturbation to each point in cluster
        for idx in cluster:
            perturbation = magnitude * direction
            perturbed_points[idx] = points[idx] + perturbation
            
            # Project back to triangle if needed
            if not is_inside_triangle(perturbed_points[idx], A, B, C):
                perturbed_points[idx] = project_point_to_triangle(perturbed_points[idx], A, B, C)

    return perturbed_points

def entrypoint():
    A_tri, B_tri, C_tri = get_unit_triangle()

    def improve(points: np.ndarray) -> np.ndarray:
        current = points.copy()
        best = points.copy()
        best_score = get_smallest_triangle_area(points)
        current_score = best_score

        # Initialize adaptive parameter system
        adaptive_params = AdaptiveParameterSystem()
        adaptive_params.update(0, current_score)

        no_improve_count = 0
        temperature = adaptive_params.get_temperature()
        
        # Track optimization progress for adaptive phase transitions
        recent_improvements = []
        max_improvement_history = 50
        current_phase = 1

        # Track point involvement in small triangles for targeted perturbations
        point_involvement = np.zeros(11)

        for iteration in range(1000):
            # Find all triangles and their areas
            triangles = []
            for i, j, k in combinations(range(11), 3):
                ax, ay = current[i]
                bx, by = current[j]
                cx, cy = current[k]
                s_val = 0.5 * ((bx - ax) * (cy - ay) - (cx - ax) * (by - ay))
                abs_area = abs(s_val)
                triangles.append((abs_area, i, j, k, s_val))

            # Sort by area
            triangles.sort(key=lambda x: x[0])
            smallest_area = triangles[0][0]
            
            # Calculate standard deviation of triangle areas
            areas = [t[0] for t in triangles]
            area_std = np.std(areas)
            
            # Update adaptive parameter system
            improvement = current_score - best_score if iteration > 0 else 0
            adaptive_params.update(improvement, current_score)

            # Calculate difficulty factor based on area distribution
            difficulty_factor = max(0.1, min(1.0, area_std / (smallest_area + 1e-10)))
            
            # Adaptive gradient weight exponent
            gradient_weight_exponent = adaptive_params.get_gradient_exponent(difficulty_factor)

            # Dynamic threshold factor
            area_threshold_factor = 0.1 + 0.4 * (1 - min(1.0, area_std / (smallest_area + 1e-10)))
            area_threshold = smallest_area * (1 + area_threshold_factor)
            top_triangles = [t for t in triangles if t[0] <= area_threshold]

            # Track point involvement
            point_involvement = np.zeros(11)
            for _, i, j, k, _ in top_triangles:
                point_involvement[i] += 1
                point_involvement[j] += 1
                point_involvement[k] += 1

            # Normalize involvement
            max_involvement = np.max(point_involvement)
            if max_involvement > 1e-10:
                point_involvement /= max_involvement

            # Initialize gradient accumulators for all points
            gradients = np.zeros_like(current)
            
            # Process each top triangle
            for abs_area, i, j, k, s_val in top_triangles:
                # Use dynamic exponent for weighting
                weight = 1.0 / (abs_area + 1e-10) ** gradient_weight_exponent
                
                A = current[i]
                B = current[j]
                C = current[k]

                sign_S = 1.0 if s_val >= 0 else -1.0

                # Compute gradients
                grad_A = sign_S * np.array([B[1] - C[1], C[0] - B[0]])
                grad_B = sign_S * np.array([C[1] - A[1], A[0] - C[0]])
                grad_C = sign_S * np.array([A[1] - B[1], B[0] - A[0]])

                # Accumulate weighted gradients
                gradients[i] += weight * grad_A
                gradients[j] += weight * grad_B
                gradients[k] += weight * grad_C

            # Scale gradients by point involvement
            for i in range(11):
                if point_involvement[i] > 0:
                    scale_factor = 1.0 + 0.5 * point_involvement[i]
                    gradients[i] *= scale_factor

            # Adaptive phase determination based on improvement rate
            if iteration > max_improvement_history:
                # Calculate recent improvement rate
                improvement_rate = np.mean(recent_improvements)
                
                # Phase transitions based on adaptive threshold
                if current_phase == 1:
                    if improvement_rate < adaptive_params.get_phase_transition_threshold():
                        current_phase = 2
                elif current_phase == 2:
                    if improvement_rate < adaptive_params.get_phase_transition_threshold() * 0.7:
                        current_phase = 3

            # Determine step size based on current phase and adaptive system
            step_size = adaptive_params.get_step_size(current_phase)

            # Create candidate by moving all points
            candidate = current.copy()
            for i in range(11):
                if np.linalg.norm(gradients[i]) > 1e-10:
                    # Normalize gradient
                    norm = np.linalg.norm(gradients[i])
                    grad_dir = gradients[i] / norm
                    candidate[i] += step_size * grad_dir

            # Project any points outside the triangle back onto the boundary
            for i in range(11):
                if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                    candidate[i] = project_point_to_triangle(candidate[i], A_tri, B_tri, C_tri)

            new_score = get_smallest_triangle_area(candidate)

            # Update improvement history
            improvement = new_score - current_score
            recent_improvements.append(improvement)
            if len(recent_improvements) > max_improvement_history:
                recent_improvements.pop(0)

            # Update best solution if improvement found
            if new_score > best_score:
                best = candidate.copy()
                best_score = new_score
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0
            elif new_score > current_score:
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0
            else:
                delta = new_score - current_score
                if delta < 0:
                    prob = np.exp(delta / temperature)
                    if np.random.random() < prob:
                        current = candidate.copy()
                        current_score = new_score
                        no_improve_count = 0
                    else:
                        no_improve_count += 1
                else:
                    no_improve_count += 1

            # Update temperature based on adaptive system
            temperature = adaptive_params.get_temperature()

            # CLUSTER-BASED STRATEGY - key improvement
            # When gradient approach stagnates, use DBSCAN to identify and perturb critical clusters
            if no_improve_count >= 50:
                # Get cluster parameters from adaptive system
                cluster_params = adaptive_params.get_cluster_perturbation_params()
                
                # Identify critical clusters
                clusters = identify_critical_clusters(current, top_triangles, cluster_params)
                
                # Apply cluster-based perturbation
                if clusters:
                    cluster_candidate = apply_cluster_perturbation(
                        current, clusters, cluster_params, A_tri, B_tri, C_tri
                    )
                    cluster_score = get_smallest_triangle_area(cluster_candidate)
                    
                    if cluster_score > current_score:
                        current = cluster_candidate.copy()
                        current_score = cluster_score
                        no_improve_count = 0
                        continue

            # VORONOI-BASED STRATEGY - with efficiency improvements
            # As alternative strategy when gradient approach stagnates
            if no_improve_count >= 80:
                # Compute Voronoi centroids for current points
                centroids = compute_voronoi_centroids(current, A_tri, B_tri, C_tri)
                
                # Create candidate from Voronoi centroids with adaptive perturbation
                voronoi_candidate = centroids.copy()
                
                # Add small perturbation to avoid degenerate configurations
                perturbation_scale = adaptive_params.get_voronoi_perturbation_scale()
                voronoi_candidate += np.random.uniform(-perturbation_scale, perturbation_scale, size=voronoi_candidate.shape)
                
                # Project back to triangle if needed
                for i in range(11):
                    if not is_inside_triangle(voronoi_candidate[i], A_tri, B_tri, C_tri):
                        voronoi_candidate[i] = project_point_to_triangle(voronoi_candidate[i], A_tri, B_tri, C_tri)
                
                voronoi_score = get_smallest_triangle_area(voronoi_candidate)
                
                # Use Voronoi candidate if it's better
                if voronoi_score > current_score:
                    current = voronoi_candidate.copy()
                    current_score = voronoi_score
                    no_improve_count = 0
                    continue

            # Targeted global perturbation to escape deep local minima
            if no_improve_count >= 120:
                # Base perturbation
                perturbation = np.random.uniform(-0.03, 0.03, size=(11, 2))
                
                # Scale by point involvement
                for i in range(11):
                    perturbation[i] *= (0.5 + 0.5 * point_involvement[i])
                
                candidate = current + perturbation
                
                # Project back to triangle
                for i in range(11):
                    if not is_inside_triangle(candidate[i], A_tri, B_tri, C_tri):
                        candidate[i] = project_point_to_triangle(candidate[i], A_tri, B_tri, C_tri)
                
                new_score = get_smallest_triangle_area(candidate)
                
                if new_score > best_score:
                    best = candidate.copy()
                    best_score = new_score
                    
                current = candidate.copy()
                current_score = new_score
                no_improve_count = 0

        return best

    return improve