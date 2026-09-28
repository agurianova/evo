from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.spatial import Delaunay

np.random.seed(42)

class ParameterTuner:
    def __init__(self):
        # Track parameter performance history
        self.gradient_scale_history = []
        self.sigmoid_steepness_history = []
        self.improvement_history = []
        
        # Initial parameter ranges (will adapt over time)
        self.gradient_base_min, self.gradient_base_max = 0.02, 0.04
        self.gradient_factor_min, self.gradient_factor_max = 0.15, 0.25
        self.sigmoid_base_min, self.sigmoid_base_max = 2.5, 3.5
        self.sigmoid_factor_min, self.sigmoid_factor_max = 3.5, 4.5

    def get_parameters(self, quality_factor):
        # If we have historical data, use it to select better parameters
        if len(self.improvement_history) > 5:
            # Find parameters that led to best improvements
            best_idx = np.argmax(self.improvement_history[-5:])
            base = self.gradient_scale_history[-5:][best_idx][0]
            factor = self.gradient_scale_history[-5:][best_idx][1]
            sigmoid_base = self.sigmoid_steepness_history[-5:][best_idx][0]
            sigmoid_factor = self.sigmoid_steepness_history[-5:][best_idx][1]
            
            # Slightly perturb for exploration
            base += np.random.normal(0, 0.002)
            factor += np.random.normal(0, 0.02)
            sigmoid_base += np.random.normal(0, 0.2)
            sigmoid_factor += np.random.normal(0, 0.2)
            
            # Clamp to reasonable ranges
            base = np.clip(base, self.gradient_base_min, self.gradient_base_max)
            factor = np.clip(factor, self.gradient_factor_min, self.gradient_factor_max)
            sigmoid_base = np.clip(sigmoid_base, self.sigmoid_base_min, self.sigmoid_base_max)
            sigmoid_factor = np.clip(sigmoid_factor, self.sigmoid_factor_min, self.sigmoid_factor_max)
        else:
            # Start with middle values
            base = (self.gradient_base_min + self.gradient_base_max) / 2
            factor = (self.gradient_factor_min + self.gradient_factor_max) / 2
            sigmoid_base = (self.sigmoid_base_min + self.sigmoid_base_max) / 2
            sigmoid_factor = (self.sigmoid_factor_min + self.sigmoid_factor_max) / 2

        return base, factor, sigmoid_base, sigmoid_factor

    def record_improvement(self, base, factor, sigmoid_base, sigmoid_factor, improvement):
        self.gradient_scale_history.append((base, factor))
        self.sigmoid_steepness_history.append((sigmoid_base, sigmoid_factor))
        self.improvement_history.append(improvement)
        
        # Keep history bounded
        if len(self.improvement_history) > 50:
            self.gradient_scale_history.pop(0)
            self.sigmoid_steepness_history.pop(0)
            self.improvement_history.pop(0)

class ChainManager:
    def __init__(self):
        self.chain_history = []
        self.performance_history = []
        
    def get_initial_chains(self, quality_factor):
        # Create diverse parameter sets based on quality factor
        chains = []
        
        # Conservative chain
        chains.append({
            'base_step': 0.02 * (1 + 0.3 * quality_factor),
            'T0': 0.007 * (1 + 0.3 * quality_factor),
            'T_decay_base': 0.9972,
            'step_decay_base': 0.9982,
            'min_ratio': 0.005,
            'weight': 1.0
        })
        
        # Balanced chain
        chains.append({
            'base_step': 0.05 * (1 + 0.8 * quality_factor),
            'T0': 0.01 * (1 + 0.8 * quality_factor),
            'T_decay_base': 0.9977,
            'step_decay_base': 0.9987,
            'min_ratio': 0.08,
            'weight': 1.0
        })
        
        # Aggressive chain
        chains.append({
            'base_step': 0.08 * (1 + 1.2 * quality_factor),
            'T0': 0.012 * (1 + 1.2 * quality_factor),
            'T_decay_base': 0.9981,
            'step_decay_base': 0.9991,
            'min_ratio': 0.25,
            'weight': 1.0
        })
        
        # Specialized for high difficulty
        if quality_factor > 0.6:
            chains.append({
                'base_step': 0.1 * (1 + 1.8 * quality_factor),
                'T0': 0.014 * (1 + 1.8 * quality_factor),
                'T_decay_base': 0.9983,
                'step_decay_base': 0.9993,
                'min_ratio': 0.35,
                'weight': 1.0
            })
        
        return chains

    def evaluate_chains(self, chains, scores, current_round):
        # Only evaluate periodically
        if current_round % 50 != 0 or current_round == 0:
            return chains
        
        # Calculate relative improvement rates
        improvements = []
        for i, chain in enumerate(chains):
            if i < len(scores) - 1:
                improvement = scores[i+1] - scores[i]
            else:
                improvement = 0
            improvements.append(improvement)
        
        # Normalize improvements
        max_improve = max(improvements) if max(improvements) > 0 else 1e-10
        normalized_improves = [imp / max_improve for imp in improvements]
        
        # Update weights based on performance
        for i, chain in enumerate(chains):
            # Exponential weighting for recent performance
            chain['weight'] = 0.7 * chain['weight'] + 0.3 * normalized_improves[i]
        
        # Sort chains by weight
        chains.sort(key=lambda x: x['weight'], reverse=True)
        
        # Prune underperforming chains (keep at least 2)
        if len(chains) > 2:
            threshold = np.percentile([c['weight'] for c in chains], 30)
            chains = [c for c in chains if c['weight'] > threshold or c['weight'] == max(c['weight'] for c in chains)]
        
        # Ensure we have at least 2 chains
        if len(chains) < 2:
            chains = self.get_initial_chains(0.5)  # Fallback
        
        return chains

def calculate_difficulty_score(points, min_area):
    """Calculate composite difficulty score incorporating multiple geometric features"""
    n = points.shape[0]
    
    # 1. Normalized minimum area (0-1 scale)
    normalized_min_area = min_area / 0.0365
    
    # 2. Count of triangles near minimum area (within 1.05x)
    small_triangle_count = 0
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                a, b, c = points[i], points[j], points[k]
                area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                if area <= min_area * 1.05:
                    small_triangle_count += 1
    
    # 3. Spatial clustering metric (using Delaunay triangulation)
    try:
        tri = Delaunay(points)
        # Calculate variance of triangle areas in Delaunay triangulation
        delauanay_areas = []
        for simplex in tri.simplices:
            a, b, c = points[simplex]
            area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
            delauanay_areas.append(area)
        clustering_metric = np.var(delauanay_areas) / (np.mean(delauanay_areas) + 1e-10) if delauanay_areas else 0
    except:
        # Fallback if Delaunay fails
        clustering_metric = 0.5
    
    # 4. Boundary proximity of critical points
    A, B, C = get_unit_triangle()
    boundary_proximity = 0
    for i in range(n):
        # Get barycentric coordinates
        v0 = C - A
        v1 = B - A
        v2 = points[i] - A
        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)
        denom = d00 * d11 - d01 * d01
        
        if abs(denom) < 1e-10:
            u, v, w = 1/3, 1/3, 1/3
        else:
            v = (d11 * d20 - d01 * d21) / denom
            w = (d00 * d21 - d01 * d20) / denom
            u = 1 - v - w
        
        # Distance to nearest boundary
        dist_to_boundary = min(u, v, w)
        if dist_to_boundary < 0.1:  # If very close to boundary
            boundary_proximity += 1
    
    # Combine metrics into composite difficulty score (0-1 scale, higher = harder)
    # Weights are adaptive based on observed patterns
    area_weight = 0.3
    count_weight = 0.25
    clustering_weight = 0.25
    boundary_weight = 0.2
    
    # Adjust weights based on minimum area (harder problems have different characteristics)
    if normalized_min_area < 0.3:
        area_weight = 0.4
        count_weight = 0.2
        clustering_weight = 0.2
        boundary_weight = 0.2
    elif normalized_min_area > 0.6:
        area_weight = 0.2
        count_weight = 0.3
        clustering_weight = 0.3
        boundary_weight = 0.2

    difficulty_score = (
        area_weight * (1 - normalized_min_area) +
        count_weight * min(1.0, small_triangle_count / 15) +
        clustering_weight * min(1.0, clustering_metric * 2) +
        boundary_weight * min(1.0, boundary_proximity / 5)
    )
    
    return min(1.0, max(0.1, difficulty_score))

def entrypoint():
    A, B, C = get_unit_triangle()
    param_tuner = ParameterTuner()
    chain_manager = ChainManager()

    def barycentric_project(point):
        """Project a point back into the triangle using barycentric coordinates."""
        v0 = B - A
        v1 = C - A
        v2 = point - A
        
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
        u = 1.0 - v - w
        
        # Clip to [0,1] and renormalize if outside
        if u < 0:
            u = 0
            sum_vw = v + w
            if sum_vw > 0:
                v, w = v/sum_vw, w/sum_vw
            else:
                v, w = 0.5, 0.5
        if v < 0:
            v = 0
            sum_uw = u + w
            if sum_uw > 0:
                u, w = u/sum_uw, w/sum_uw
            else:
                u, w = 0.5, 0.5
        if w < 0:
            w = 0
            sum_uv = u + v
            if sum_uv > 0:
                u, v = u/sum_uv, v/sum_uv
            else:
                u, v = 0.5, 0.5
        
        # Ensure sum is 1 (numerical stability)
        total = u + v + w
        if total > 0:
            u, v, w = u/total, v/total, w/total
        else:
            u, v, w = 1/3, 1/3, 1/3
        
        return u * A + v * B + w * C

    def get_adaptive_triangle_indices(pts, min_area, difficulty_score, improvement_history=None, k_max=5):
        """Get indices of triangles with area <= adaptive_threshold*min_area, up to k_max."""
        n = pts.shape[0]
        areas = []
        indices = []
        
        for i in range(n):
            for j in range(i+1, n):
                for k_idx in range(j+1, n):
                    a, b, c = pts[i], pts[j], pts[k_idx]
                    area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
                    areas.append(area)
                    indices.append((i, j, k_idx))
        
        if not areas:
            return [(0, 1, 2)]
            
        # Calculate adaptive threshold based on problem difficulty AND recent progress
        # Track historical success to tune thresholds
        base_threshold = 1.02
        
        # Adjust based on difficulty score
        base_threshold += 0.02 * difficulty_score
        
        if improvement_history and len(improvement_history) > 5:
            avg_improvement = np.mean(improvement_history[-5:])
            # If progress is slow, tighten the threshold to focus on truly problematic triangles
            if avg_improvement < 1e-6:
                base_threshold *= 0.98
            # If making good progress, loosen the threshold to explore more options
            else:
                base_threshold *= 1.02
        
        # Adjust adaptive factor based on difficulty score
        adaptive_factor = 0.1 + 0.3 * difficulty_score
        
        adaptive_threshold = base_threshold + adaptive_factor * difficulty_score
        threshold = adaptive_threshold * min_area
        
        # Get all triangles below threshold, up to k_max
        relevant_indices = [idx for area, idx in zip(areas, indices) if area <= threshold]
        
        # If none found (shouldn't happen), return top k_max
        if not relevant_indices:
            sorted_indices = [idx for _, idx in sorted(zip(areas, indices))]
            return sorted_indices[:min(k_max, len(sorted_indices))]
        
        # Return up to k_max relevant indices
        return relevant_indices[:min(k_max, len(relevant_indices))]

    def calculate_area_gradient(points, triangle_indices, gradient_base, gradient_factor):
        """Calculate gradient of triangle area with respect to each vertex position with exponential distance weighting."""
        i, j, k = triangle_indices
        a, b, c = points[i], points[j], points[k]
        
        # Calculate distances between points
        dist_ab = np.linalg.norm(a - b)
        dist_ac = np.linalg.norm(a - c)
        dist_bc = np.linalg.norm(b - c)
        
        # Area = 0.5 * |(b-a) × (c-a)|
        grad_a = np.array([-(b[1] - c[1]), b[0] - c[0]]) * 0.5
        grad_b = np.array([-(c[1] - a[1]), c[0] - a[0]]) * 0.5
        grad_c = np.array([-(a[1] - b[1]), a[0] - b[0]]) * 0.5
        
        # Weight gradients by exponential decay based on distances
        # Scale adapts to current min area for appropriate weighting
        current_min_area = get_smallest_triangle_area(points)
        # Use dynamically tuned parameters
        scale = (gradient_base + gradient_factor * difficulty_score) * np.sqrt(max(1e-10, current_min_area))
        
        weight_a = np.exp(-(dist_ab + dist_ac) / scale)
        weight_b = np.exp(-(dist_ab + dist_bc) / scale)
        weight_c = np.exp(-(dist_ac + dist_bc) / scale)
        
        grad_a *= weight_a
        grad_b *= weight_b
        grad_c *= weight_c
        
        # Normalize gradients
        norm_a = np.linalg.norm(grad_a)
        norm_b = np.linalg.norm(grad_b)
        norm_c = np.linalg.norm(grad_c)
        
        if norm_a > 1e-10:
            grad_a = grad_a / norm_a
        if norm_b > 1e-10:
            grad_b = grad_b / norm_b
        if norm_c > 1e-10:
            grad_c = grad_c / norm_c

        return grad_a, grad_b, grad_c

    def run_annealing_chain(initial_points, params, difficulty_score, param_tuner):
        """Run a single annealing chain with specific parameters."""
        base_step = params['base_step']
        T0 = params['T0']
        T_decay_base = params['T_decay_base']
        step_decay_base = params['step_decay_base']
        min_ratio = params['min_ratio']
        
        best = initial_points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # Get dynamically tuned gradient parameters
        gradient_base, gradient_factor, sigmoid_base, sigmoid_factor = param_tuner.get_parameters(difficulty_score)
        
        # ADAPTIVE SEARCH BUDGET: Quadratic allocation based on problem difficulty
        initial_min_area = get_smallest_triangle_area(initial_points)
        n_rounds = int(200 + 350 * difficulty_score + 250 * difficulty_score ** 2)
        
        T_decay = T_decay_base
        step_decay = step_decay_base

        # Track improvement history for adaptive cooling
        improvement_history = []
        stagnation_counter = 0
        # ADAPTIVE STAGNATION THRESHOLD: Scales with difficulty_score
        stagnation_threshold = max(15, min(35, int(25 + 15 * difficulty_score)))
        
        # Track chain performance for dynamic resource allocation
        score_history = [best_score]
        
        for round_idx in range(n_rounds):
            # Adjust cooling rate based on recent progress
            if improvement_history and len(improvement_history) >= 10:
                recent_improvements = improvement_history[-10:]
                avg_improvement = np.mean(recent_improvements)
                # Scale stagnation threshold with problem difficulty
                adaptive_stagnation_threshold = 1e-6 * (0.0365 / max(initial_min_area, 1e-10))
                if avg_improvement < adaptive_stagnation_threshold:
                    T_decay = max(0.995, T_decay * 1.0015)
                    step_decay = min(0.9997, step_decay * 1.0003)
                    stagnation_counter += 1
                else:
                    T_decay = min(0.998, T_decay * 0.9995)
                    step_decay = max(0.996, step_decay * 0.9995)
                    stagnation_counter = max(0, stagnation_counter - 1)
            
            # PARTIAL RESET on stagnation instead of full reset
            if stagnation_counter > stagnation_threshold:
                # Partial reset preserves some search state
                T_decay = (T_decay + T_decay_base) / 2
                step_decay = (step_decay + step_decay_base) / 2
                stagnation_counter = 0
                improvement_history = []
                
                # Add small noise to current best solution
                current_step = base_step * (step_decay ** round_idx)
                # Adaptive noise scaling
                noise_std = 0.0015 * (1 + 2.5 * difficulty_score) * current_step
                for i in range(len(best)):
                    best[i] += np.random.normal(0, noise_std, size=2)
                    best[i] = barycentric_project(best[i])
                best_score = get_smallest_triangle_area(best)

            T = T0 * (T_decay ** round_idx)
            current_step = base_step * (step_decay ** round_idx)
            
            # Dynamically adjust min_ratio based on progress
            if stagnation_counter > stagnation_threshold // 2:
                adaptive_min_ratio = min(0.35, min_ratio * 1.15)
            else:
                adaptive_min_ratio = max(0.005, min_ratio * 0.85)

            # Get current min area for adaptive triangle selection
            current_min_area = get_smallest_triangle_area(best)
            triangle_indices = get_adaptive_triangle_indices(
                best, 
                current_min_area, 
                difficulty_score,
                improvement_history=improvement_history,
                k_max=5
            )
            
            # Select a random triangle from the relevant ones
            if triangle_indices:
                selected_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
            else:
                selected_triangle = (0, 1, 2)

            # Calculate dynamic gradient ratio using sigmoid progression
            progress = min(1.0, round_idx / n_rounds)
            # Use dynamically tuned parameters
            gradient_ratio = sigmoid_base / (sigmoid_base + np.exp(-sigmoid_factor * (progress - 0.5)))

            # Dynamic perturbation strategy based on progress
            if np.random.rand() < gradient_ratio:
                # Gradient-based perturbations (more targeted)
                grad_i, grad_j, grad_k = calculate_area_gradient(best, selected_triangle, gradient_base, gradient_factor)
                
                # 60% chance to perturb one point, 40% to perturb all three
                if np.random.rand() < 0.6:
                    idx = selected_triangle[np.random.randint(3)]
                    candidate = best.copy()
                    
                    if idx == selected_triangle[0]:
                        candidate[idx] += grad_i * current_step
                    elif idx == selected_triangle[1]:
                        candidate[idx] += grad_j * current_step
                    else:
                        candidate[idx] += grad_k * current_step
                    
                    # Project back if needed
                    candidate[idx] = barycentric_project(candidate[idx])
                else:
                    candidate = best.copy()
                    candidate[selected_triangle[0]] += grad_i * current_step
                    candidate[selected_triangle[1]] += grad_j * current_step
                    candidate[selected_triangle[2]] += grad_k * current_step
                    
                    # Project back if needed
                    for idx in selected_triangle:
                        candidate[idx] = barycentric_project(candidate[idx])
            else:
                # Isotropic perturbations (fallback)
                if np.random.rand() < 0.6:
                    idx = selected_triangle[np.random.randint(3)]
                    candidate = best.copy()
                    r = current_step * np.sqrt(np.random.rand())
                    theta = 2 * np.pi * np.random.rand()
                    perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                    candidate[idx] += perturbation
                    
                    # Project back if needed
                    candidate[idx] = barycentric_project(candidate[idx])
                else:
                    candidate = best.copy()
                    for idx in selected_triangle:
                        r = current_step * np.sqrt(np.random.rand())
                        theta = 2 * np.pi * np.random.rand()
                        perturbation = np.array([r * np.cos(theta), r * np.sin(theta)])
                        candidate[idx] += perturbation
                        
                        # Project back if needed
                        candidate[idx] = barycentric_project(candidate[idx])
            
            candidate_score = get_smallest_triangle_area(candidate)
            delta = candidate_score - best_score
            
            # Track improvements for adaptive cooling and parameter tuning
            if delta > 0:
                improvement_history.append(delta)
                # Record for parameter tuner
                param_tuner.record_improvement(
                    gradient_base, gradient_factor, 
                    sigmoid_base, sigmoid_factor,
                    delta
                )
                if len(improvement_history) > 50:
                    improvement_history.pop(0)

            # Acceptance criterion
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                best = candidate
                best_score = candidate_score

            # Record score for chain performance tracking
            if round_idx % 10 == 0:
                score_history.append(best_score)

            # GLOBAL RESTRUCTURING: Delaunay-based rearrangement with adaptive frequency
            # ADAPTIVE FREQUENCY: More frequent for harder problems
            adaptive_restructuring_interval = max(25, 45 - int(20 * difficulty_score))
            if round_idx > 0 and round_idx % adaptive_restructuring_interval == 0:
                try:
                    # Compute Delaunay triangulation
                    tri = Delaunay(best)
                    
                    # Find the triangle with largest area (largest empty space)
                    max_area = -1
                    max_idx = -1
                    for i, simplex in enumerate(tri.simplices):
                        a, b, c = best[simplex]
                        area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                        if area > max_area:
                            max_area = area
                            max_idx = i
                    
                    if max_idx != -1:
                        # Get the largest triangle
                        simplex = tri.simplices[max_idx]
                        a, b, c = best[simplex]
                        
                        # Calculate centroid of the largest triangle
                        centroid = (a + b + c) / 3
                        
                        # Find the point closest to the centroid (likely in a dense region)
                        distances = np.linalg.norm(best - centroid, axis=1)
                        farthest_idx = np.argmin(distances)
                        
                        # Move this point to the centroid
                        candidate = best.copy()
                        candidate[farthest_idx] = centroid
                        
                        # Project back if needed
                        candidate[farthest_idx] = barycentric_project(candidate[farthest_idx])
                        
                        # Evaluate the candidate
                        candidate_score = get_smallest_triangle_area(candidate)
                        
                        # Accept if it improves or with some probability
                        if candidate_score > best_score:
                            best = candidate
                            best_score = candidate_score
                except Exception as e:
                    # Handle specific triangulation errors
                    error_msg = str(e).lower()
                    
                    # Check for common Delaunay error indicators
                    if "qhull" in error_msg or "degenerate" in error_msg or "coplanar" in error_msg or "qh6" in error_msg:
                        # Randomly sample triangles instead of checking all combinations
                        n = len(best)
                        max_area = -1
                        max_triangle = None
                        
                        # Sample number adapts to difficulty
                        num_samples = max(30, int(50 * (1 + 0.5 * difficulty_score)))
                        
                        # Sample random triangles
                        for _ in range(num_samples):
                            i, j, k = np.random.choice(n, 3, replace=False)
                            a, b, c = best[i], best[j], best[k]
                            area = 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
                            if area > max_area:
                                max_area = area
                                max_triangle = (i, j, k)
                        
                        if max_triangle:
                            # Get the largest triangle
                            i, j, k = max_triangle
                            a, b, c = best[i], best[j], best[k]
                            
                            # Calculate centroid of the largest triangle
                            centroid = (a + b + c) / 3
                            
                            # Find the point closest to the centroid (likely in a dense region)
                            distances = np.linalg.norm(best - centroid, axis=1)
                            farthest_idx = np.argmin(distances)
                            
                            # Move this point to the centroid
                            candidate = best.copy()
                            candidate[farthest_idx] = centroid
                            
                            # Project back if needed
                            candidate[farthest_idx] = barycentric_project(candidate[farthest_idx])
                            
                            # Evaluate the candidate
                            candidate_score = get_smallest_triangle_area(candidate)
                            
                            # Accept if it improves
                            if candidate_score > best_score:
                                best = candidate
                                best_score = candidate_score
                    else:
                        # General fallback: random perturbation
                        candidate = best.copy()
                        idx = np.random.randint(len(best))
                        candidate[idx] += np.random.normal(0, 0.01, size=2)
                        candidate[idx] = barycentric_project(candidate[idx])
                        candidate_score = get_smallest_triangle_area(candidate)
                        if candidate_score > best_score:
                            best = candidate
                            best_score = candidate_score

        return best, best_score, score_history

    def improve(points: np.ndarray) -> np.ndarray:
        # Calculate composite difficulty score
        initial_min_area = get_smallest_triangle_area(points)
        difficulty_score = calculate_difficulty_score(points, initial_min_area)

        # Get initial chains based on difficulty
        chains = chain_manager.get_initial_chains(difficulty_score)
        
        # Run chains with dynamic resource allocation
        all_results = []
        
        # First pass: run each chain for minimal iterations to get initial performance
        for i, chain_params in enumerate(chains):
            # Run a short initial phase to evaluate chain potential
            result, score, score_history = run_annealing_chain(
                points.copy(),
                chain_params,
                difficulty_score,
                param_tuner
            )
            all_results.append((result, score, score_history, chain_params))
        
        # Evaluate and potentially adjust chains
        chains = chain_manager.evaluate_chains(chains, [score for _, score, _, _ in all_results], 50)
        
        # Second pass: run the refined set of chains
        final_results = []
        for i, chain_params in enumerate(chains):
            result, score, score_history = run_annealing_chain(
                points.copy(),
                chain_params,
                difficulty_score,
                param_tuner
            )
            final_results.append((result, score))
        
        # Select the best result
        best_result = max(final_results, key=lambda x: x[1])
        return best_result[0]

    return improve