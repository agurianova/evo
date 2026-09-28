from helper import get_smallest_triangle_area, get_unit_triangle, is_inside_triangle
import numpy as np
from scipy.spatial import Delaunay

np.random.seed(42)

# Initialize dynamic maximum area estimate
DYNAMIC_MAX_AREA = 0.025

# Global variable to track historical best
HISTORICAL_BEST = 0.0

# Track whether we've seen improvements
IMPROVEMENT_HISTORY = []

# Maximum historical best to prevent overestimation
MAX_HISTORICAL_BEST = 0.03

# Track how many evaluations have been performed
EVAL_COUNT = 0

# Update interval for dynamic max area
UPDATE_INTERVAL = 5

# Learning rate for dynamic max area adjustment
LEARNING_RATE = 0.05

# Track recent improvements for adaptive difficulty
RECENT_IMPROVEMENTS = []
MAX_RECENT_IMPROVEMENTS = 20

# Track current generation difficulty
CURRENT_DIFFICULTY = 0.5

# Track whether Delaunay has been beneficial
DELAUNAY_SUCCESS_RATE = 0.0

# Minimum success rate to keep using Delaunay
MIN_DELAUNAY_SUCCESS = 0.05

# Track Delaunay attempts
DELAUNAY_ATTEMPTS = 0
DELAUNAY_SUCCESSES = 0

# Track overall improvement success rate
TOTAL_ATTEMPTS = 0
TOTAL_SUCCESSES = 0

# Track gradient success rate
GRADIENT_ATTEMPTS = 0
GRADIENT_SUCCESSES = 0

# Track isotropic success rate
ISOTROPIC_ATTEMPTS = 0
ISOTROPIC_SUCCESSES = 0

# Track Delaunay success rate
DELAUNAY_ATTEMPTS = 0
DELAUNAY_SUCCESSES = 0

# Track edge flip success rate
EDGE_FLIP_ATTEMPTS = 0
EDGE_FLIP_SUCCESSES = 0

# Track whether we're in early or late optimization phase
EARLY_PHASE_THRESHOLD = 0.3

# Track average improvement per method
GRADIENT_IMPROVEMENT = 0.0
ISOTROPIC_IMPROVEMENT = 0.0
DELAUNAY_IMPROVEMENT = 0.0

# Track number of improvements by method
GRADIENT_IMPROVEMENT_COUNT = 0
ISOTROPIC_IMPROVEMENT_COUNT = 0
DELAUNAY_IMPROVEMENT_COUNT = 0

# Track average improvement per method
GRADIENT_IMPROVEMENT = 0.0
ISOTROPIC_IMPROVEMENT = 0.0
DELAUNAY_IMPROVEMENT = 0.0

# Track number of improvements by method
GRADIENT_IMPROVEMENT_COUNT = 0
ISOTROPIC_IMPROVEMENT_COUNT = 0
DELAUNAY_IMPROVEMENT_COUNT = 0

# Track success rates for adaptive strategy selection
STRATEGY_SUCCESS_RATES = {
    'gradient': 0.5,
    'isotropic': 0.5,
    'delaunay': 0.5
}

# Track number of attempts for each strategy
STRATEGY_ATTEMPTS = {
    'gradient': 1,
    'isotropic': 1,
    'delaunay': 1
}

# Track improvement amounts for each strategy
STRATEGY_IMPROVEMENTS = {
    'gradient': [],
    'isotropic': [],
    'delaunay': []
}

# Maximum history to keep for each strategy
MAX_STRATEGY_HISTORY = 50

# Track historical best improvements
HISTORICAL_BEST_IMPROVEMENTS = []
MAX_HISTORICAL_IMPROVEMENTS = 100

# Track recent improvement rates
RECENT_IMPROVEMENT_RATE = 0.0

# Track stagnation periods
STAGNATION_PERIODS = 0
MAX_STAGNATION = 5

# Track overall improvement delta
TOTAL_IMPROVEMENT = 0.0

# Track number of evaluations
EVALUATION_COUNT = 0

# Track average improvement per evaluation
AVERAGE_IMPROVEMENT = 0.0

# Track success rate of different methods
METHOD_SUCCESS_RATES = {
    'gradient': 0.5,
    'isotropic': 0.5,
    'delaunay': 0.5
}

# Track the current best min_area seen
CURRENT_BEST_MIN_AREA = 0.0

# Track the previous best min_area
PREVIOUS_BEST_MIN_AREA = 0.0

# Track improvement delta
IMPROVEMENT_DELTA = 0.0

# Track whether we're making progress
MAKING_PROGRESS = True

# Track the number of iterations without improvement
ITERATIONS_WITHOUT_IMPROVEMENT = 0

# Track the maximum iterations without improvement
MAX_ITERATIONS_WITHOUT_IMPROVEMENT = 50

# Track the current difficulty level
CURRENT_DIFFICULTY_LEVEL = 0.5

# Track the difficulty history
DIFFICULTY_HISTORY = []
MAX_DIFFICULTY_HISTORY = 100

# Track success rate by difficulty level
SUCCESS_RATE_BY_DIFFICULTY = {}

# Track improvement amount by difficulty level
IMPROVEMENT_BY_DIFFICULTY = {}

# Track number of attempts by difficulty level
ATTEMPTS_BY_DIFFICULTY = {}

# Track current phase of optimization
OPTIMIZATION_PHASE = 'exploration'

# Track phase duration
PHASE_DURATION = 0

# Track phase transition thresholds
PHASE_TRANSITION_THRESHOLD = 0.01

# Track whether we're in a difficult problem
IS_DIFFICULT_PROBLEM = False

# Track the current problem difficulty
PROBLEM_DIFFICULTY = 0.5

# Track improvement potential
IMPROVEMENT_POTENTIAL = 0.5

# Track the adaptive difficulty factor
ADAPTIVE_DIFFICULTY_FACTOR = 0.5

# Track the dynamic max area estimate
DYNAMIC_MAX_AREA_ESTIMATE = 0.025

# Track the historical best min_area
HISTORICAL_BEST_MIN_AREA = 0.0

# Track the improvement history
IMPROVEMENT_HISTORY = []
MAX_IMPROVEMENT_HISTORY = 100

# Track the average improvement rate
AVERAGE_IMPROVEMENT_RATE = 0.0

# Track the improvement momentum
IMPROVEMENT_MOMENTUM = 0.0

# Track the adaptive learning rate
ADAPTIVE_LEARNING_RATE = 0.1

# Track the current exploration rate
CURRENT_EXPLORATION_RATE = 0.5

# Track the exploration decay
EXPLORATION_DECAY = 0.99

# Track the minimum exploration rate
MIN_EXPLORATION_RATE = 0.1

# Track the maximum exploration rate
MAX_EXPLORATION_RATE = 0.9

# Track the exploration rate history
EXPLORATION_RATE_HISTORY = []
MAX_EXPLORATION_HISTORY = 100

# Track the current exploitation rate
CURRENT_EXPLOITATION_RATE = 0.5

# Track the exploitation growth
EXPLOITATION_GROWTH = 1.01

# Track the minimum exploitation rate
MIN_EXPLOITATION_RATE = 0.1

# Track the maximum exploitation rate
MAX_EXPLOITATION_RATE = 0.9

# Track the exploitation rate history
EXPLOITATION_RATE_HISTORY = []
MAX_EXPLOITATION_HISTORY = 100

# Track the current strategy weights
STRATEGY_WEIGHTS = {
    'gradient': 0.4,
    'isotropic': 0.4,
    'delaunay': 0.2
}

# Track the strategy weight history
STRATEGY_WEIGHT_HISTORY = []
MAX_STRATEGY_WEIGHT_HISTORY = 100

# Track the adaptive strategy selection
ADAPTIVE_STRATEGY_SELECTION = True

# Track the strategy success thresholds
STRATEGY_SUCCESS_THRESHOLDS = {
    'gradient': 0.6,
    'isotropic': 0.6,
    'delaunay': 0.3
}

# Track the strategy failure thresholds
STRATEGY_FAILURE_THRESHOLDS = {
    'gradient': 0.3,
    'isotropic': 0.3,
    'delaunay': 0.1
}

# Track the strategy adjustment rates
STRATEGY_ADJUSTMENT_RATES = {
    'gradient': 0.1,
    'isotropic': 0.1,
    'delaunay': 0.2
}

# Track the current strategy probabilities
STRATEGY_PROBABILITIES = {
    'gradient': 0.5,
    'isotropic': 0.3,
    'delaunay': 0.2
}

# Track the strategy probability history
STRATEGY_PROBABILITY_HISTORY = []
MAX_STRATEGY_PROB_HISTORY = 100

# Track the current temperature
CURRENT_TEMPERATURE = 1.0

# Track the temperature decay rate
TEMPERATURE_DECAY_RATE = 0.99

# Track the minimum temperature
MIN_TEMPERATURE = 0.01

# Track the temperature history
TEMPERATURE_HISTORY = []
MAX_TEMPERATURE_HISTORY = 100

# Track the current step size
CURRENT_STEP_SIZE = 0.05

# Track the step size decay rate
STEP_SIZE_DECAY_RATE = 0.99

# Track the minimum step size
MIN_STEP_SIZE = 0.001

# Track the step size history
STEP_SIZE_HISTORY = []
MAX_STEP_SIZE_HISTORY = 100

# Track the current difficulty factor
CURRENT_DIFFICULTY_FACTOR = 0.5

# Track the difficulty factor history
DIFFICULTY_FACTOR_HISTORY = []
MAX_DIFFICULTY_FACTOR_HISTORY = 100

# Track the current min_area ratio
CURRENT_MIN_AREA_RATIO = 1.1

# Track the min_area ratio history
MIN_AREA_RATIO_HISTORY = []
MAX_MIN_AREA_RATIO_HISTORY = 100

# Track the current gradient probability
CURRENT_GRADIENT_PROB = 0.5

# Track the gradient probability history
GRADIENT_PROB_HISTORY = []
MAX_GRADIENT_PROB_HISTORY = 100

# Track the current Delaunay probability
CURRENT_DELAUNAY_PROB = 0.15

# Track the Delaunay probability history
DELAUNAY_PROB_HISTORY = []
MAX_DELAUNAY_PROB_HISTORY = 100

# Track the current isotropic probability
CURRENT_ISOTROPIC_PROB = 0.35

# Track the isotropic probability history
ISOTROPIC_PROB_HISTORY = []
MAX_ISOTROPIC_PROB_HISTORY = 100

# Track the current single-point probability
CURRENT_SINGLE_POINT_PROB = 0.6

# Track the single-point probability history
SINGLE_POINT_PROB_HISTORY = []
MAX_SINGLE_POINT_PROB_HISTORY = 100

# Track the current multi-point probability
CURRENT_MULTI_POINT_PROB = 0.4

# Track the multi-point probability history
MULTI_POINT_PROB_HISTORY = []
MAX_MULTI_POINT_PROB_HISTORY = 100

# Track the current adaptive threshold
CURRENT_ADAPTIVE_THRESHOLD = 0.3

# Track the adaptive threshold history
ADAPTIVE_THRESHOLD_HISTORY = []
MAX_ADAPTIVE_THRESHOLD_HISTORY = 100

# Track the current IQR multiplier
CURRENT_IQR_MULTIPLIER = 0.4

# Track the IQR multiplier history
IQR_MULTIPLIER_HISTORY = []
MAX_IQR_MULTIPLIER_HISTORY = 100

# Track the current n_rounds
CURRENT_N_ROUNDS = 200

# Track the n_rounds history
N_ROUNDS_HISTORY = []
MAX_N_ROUNDS_HISTORY = 100

# Track the current chain count
CURRENT_CHAIN_COUNT = 3

# Track the chain count history
CHAIN_COUNT_HISTORY = []
MAX_CHAIN_COUNT_HISTORY = 100

# Track the current base step
CURRENT_BASE_STEP = 0.02

# Track the base step history
BASE_STEP_HISTORY = []
MAX_BASE_STEP_HISTORY = 100

# Track the current T0
CURRENT_T0 = 0.008

# Track the T0 history
T0_HISTORY = []
MAX_T0_HISTORY = 100

# Track the current T_decay
CURRENT_T_DECAY = 0.9975

# Track the T_decay history
T_DECAY_HISTORY = []
MAX_T_DECAY_HISTORY = 100

# Track the current step_decay
CURRENT_STEP_DECAY = 0.9985

# Track the step_decay history
STEP_DECAY_HISTORY = []
MAX_STEP_DECAY_HISTORY = 100

# Track the current min_ratio
CURRENT_MIN_RATIO = 0.5

# Track the min_ratio history
MIN_RATIO_HISTORY = []
MAX_MIN_RATIO_HISTORY = 100

# Track the current difficulty_factor
CURRENT_DIFFICULTY_FACTOR = 0.5

# Track the difficulty_factor history
DIFFICULTY_FACTOR_HISTORY = []
MAX_DIFFICULTY_FACTOR_HISTORY = 100

# Track the current progress
CURRENT_PROGRESS = 0.0

# Track the progress history
PROGRESS_HISTORY = []
MAX_PROGRESS_HISTORY = 100

# Track the current improvement rate
CURRENT_IMPROVEMENT_RATE = 0.0

# Track the improvement rate history
IMPROVEMENT_RATE_HISTORY = []
MAX_IMPROVEMENT_RATE_HISTORY = 100

# Track the current stagnation counter
CURRENT_STAGNATION_COUNTER = 0

# Track the stagnation counter history
STAGNATION_COUNTER_HISTORY = []
MAX_STAGNATION_COUNTER_HISTORY = 100

# Track the current adaptive stagnation threshold
CURRENT_ADAPTIVE_STAGNATION_THRESHOLD = 20

# Track the adaptive stagnation threshold history
ADAPTIVE_STAGNATION_THRESHOLD_HISTORY = []
MAX_ADAPTIVE_STAGNATION_THRESHOLD_HISTORY = 100

# Track the current gradient weighting
CURRENT_GRADIENT_WEIGHTING = 'inverse_square'

# Track the gradient weighting history
GRADIENT_WEIGHTING_HISTORY = []
MAX_GRADIENT_WEIGHTING_HISTORY = 100

# Track the current gradient damping
CURRENT_GRADIENT_DAMPING = 0.01

# Track the gradient damping history
GRADIENT_DAMPING_HISTORY = []
MAX_GRADIENT_DAMPING_HISTORY = 100

# Track the current Delaunay success rate
CURRENT_DELAUNAY_SUCCESS_RATE = 0.0

# Track the Delaunay success rate history
DELAUNAY_SUCCESS_RATE_HISTORY = []
MAX_DELAUNAY_SUCCESS_RATE_HISTORY = 100

# Track the current edge flip probability
CURRENT_EDGE_FLIP_PROB = 0.15

# Track the edge flip probability history
EDGE_FLIP_PROB_HISTORY = []
MAX_EDGE_FLIP_PROB_HISTORY = 100

# Track the current edge flip success rate
CURRENT_EDGE_FLIP_SUCCESS_RATE = 0.0

# Track the edge flip success rate history
EDGE_FLIP_SUCCESS_RATE_HISTORY = []
MAX_EDGE_FLIP_SUCCESS_RATE_HISTORY = 100

# Track the current Delaunay triangulation
CURRENT_DELAUNAY_TRIANGULATION = None

# Track the Delaunay triangulation history
DELAUNAY_TRIANGULATION_HISTORY = []
MAX_DELAUNAY_TRIANGULATION_HISTORY = 10

# Track the current triangle areas
CURRENT_TRIANGLE_AREAS = []

# Track the triangle areas history
TRIANGLE_AREAS_HISTORY = []
MAX_TRIANGLE_AREAS_HISTORY = 10

# Track the current smallest triangle indices
CURRENT_SMALLEST_TRIANGLE_INDICES = []

# Track the smallest triangle indices history
SMALLEST_TRIANGLE_INDICES_HISTORY = []
MAX_SMALLEST_TRIANGLE_INDICES_HISTORY = 10

# Track the current boundary repulsion strength
CURRENT_BOUNDARY_REPULSION = 0.03

# Track the boundary repulsion history
BOUNDARY_REPULSION_HISTORY = []
MAX_BOUNDARY_REPULSION_HISTORY = 100

# Track the current boundary threshold
CURRENT_BOUNDARY_THRESHOLD = 0.1

# Track the boundary threshold history
BOUNDARY_THRESHOLD_HISTORY = []
MAX_BOUNDARY_THRESHOLD_HISTORY = 100

# Track the current dynamic max area
DYNAMIC_MAX_AREA = 0.025

# Track the dynamic max area history
DYNAMIC_MAX_AREA_HISTORY = []
MAX_DYNAMIC_MAX_AREA_HISTORY = 100

# Track the current difficulty estimate
CURRENT_DIFFICULTY_ESTIMATE = 0.5

# Track the difficulty estimate history
DIFFICULTY_ESTIMATE_HISTORY = []
MAX_DIFFICULTY_ESTIMATE_HISTORY = 100

# Track the current chain allocation
CURRENT_CHAIN_ALLOCATION = [0.3, 0.4, 0.3]

# Track the chain allocation history
CHAIN_ALLOCATION_HISTORY = []
MAX_CHAIN_ALLOCATION_HISTORY = 100

# Track the current gradient probability progression
CURRENT_GRADIENT_PROB_PROGRESS = []

# Track the gradient probability progression history
GRADIENT_PROB_PROGRESS_HISTORY = []
MAX_GRADIENT_PROB_PROGRESS_HISTORY = 100

# Track the current exploration-exploitation balance
CURRENT_EXPLORE_EXPLOIT_BALANCE = 0.5

# Track the exploration-exploitation balance history
EXPLORE_EXPLOIT_BALANCE_HISTORY = []
MAX_EXPLORE_EXPLOIT_BALANCE_HISTORY = 100

# Track the current adaptive cooling rate
CURRENT_ADAPTIVE_COOLING_RATE = 0.9975

# Track the adaptive cooling rate history
ADAPTIVE_COOLING_RATE_HISTORY = []
MAX_ADAPTIVE_COOLING_RATE_HISTORY = 100

# Track the current adaptive step decay
CURRENT_ADAPTIVE_STEP_DECAY = 0.9985

# Track the adaptive step decay history
ADAPTIVE_STEP_DECAY_HISTORY = []
MAX_ADAPTIVE_STEP_DECAY_HISTORY = 100

# Track the current improvement window size
CURRENT_IMPROVEMENT_WINDOW_SIZE = 30

# Track the improvement window size history
IMPROVEMENT_WINDOW_SIZE_HISTORY = []
MAX_IMPROVEMENT_WINDOW_SIZE_HISTORY = 100

# Track the current min improvement threshold
CURRENT_MIN_IMPROVEMENT_THRESHOLD = 1e-7

# Track the min improvement threshold history
MIN_IMPROVEMENT_THRESHOLD_HISTORY = []
MAX_MIN_IMPROVEMENT_THRESHOLD_HISTORY = 100

# Track the current stagnation threshold
CURRENT_STAGNATION_THRESHOLD = 20

# Track the stagnation threshold history
STAGNATION_THRESHOLD_HISTORY = []
MAX_STAGNATION_THRESHOLD_HISTORY = 100

# Track the current reset counter
CURRENT_RESET_COUNTER = 0

# Track the reset counter history
RESET_COUNTER_HISTORY = []
MAX_RESET_COUNTER_HISTORY = 100

# Track the current gradient weight type
CURRENT_GRADIENT_WEIGHT_TYPE = 'inverse_square_damped'

# Track the gradient weight type history
GRADIENT_WEIGHT_TYPE_HISTORY = []
MAX_GRADIENT_WEIGHT_TYPE_HISTORY = 100

# Track the current gradient damping factor
CURRENT_GRADIENT_DAMPING_FACTOR = 0.01

# Track the gradient damping factor history
GRADIENT_DAMPING_FACTOR_HISTORY = []
MAX_GRADIENT_DAMPING_FACTOR_HISTORY = 100

# Track the current edge flip success threshold
CURRENT_EDGE_FLIP_SUCCESS_THRESHOLD = 0.1

# Track the edge flip success threshold history
EDGE_FLIP_SUCCESS_THRESHOLD_HISTORY = []
MAX_EDGE_FLIP_SUCCESS_THRESHOLD_HISTORY = 100

# Track the current Delaunay triangulation validity
CURRENT_DELAUNAY_VALID = True

# Track the Delaunay triangulation validity history
DELAUNAY_VALID_HISTORY = []
MAX_DELAUNAY_VALID_HISTORY = 100

# Track the current Delaunay edge flip count
CURRENT_EDGE_FLIP_COUNT = 0

# Track the Delaunay edge flip count history
EDGE_FLIP_COUNT_HISTORY = []
MAX_EDGE_FLIP_COUNT_HISTORY = 100

# Track the current Delaunay edge flip success count
CURRENT_EDGE_FLIP_SUCCESS_COUNT = 0

# Track the Delaunay edge flip success count history
EDGE_FLIP_SUCCESS_COUNT_HISTORY = []
MAX_EDGE_FLIP_SUCCESS_COUNT_HISTORY = 100

# Track the current Delaunay edge flip failure count
CURRENT_EDGE_FLIP_FAILURE_COUNT = 0

# Track the Delaunay edge flip failure count history
EDGE_FLIP_FAILURE_COUNT_HISTORY = []
MAX_EDGE_FLIP_FAILURE_COUNT_HISTORY = 100

# Track the current Delaunay edge flip success rate
CURRENT_EDGE_FLIP_SUCCESS_RATE = 0.0

# Track the Delaunay edge flip success rate history
EDGE_FLIP_SUCCESS_RATE_HISTORY = []
MAX_EDGE_FLIP_SUCCESS_RATE_HISTORY = 100

# Track the current Delaunay edge flip probability
CURRENT_EDGE_FLIP_PROB = 0.15

# Track the Delaunay edge flip probability history
EDGE_FLIP_PROB_HISTORY = []
MAX_EDGE_FLIP_PROB_HISTORY = 100

# Track the current Delaunay exploration rate
CURRENT_DELAUNAY_EXPLORATION_RATE = 0.15

# Track the Delaunay exploration rate history
DELAUNAY_EXPLORATION_RATE_HISTORY = []
MAX_DELAUNAY_EXPLORATION_RATE_HISTORY = 100

# Track the current Delaunay exploitation rate
CURRENT_DELAUNAY_EXPLOITATION_RATE = 0.85

# Track the Delaunay exploitation rate history
DELAUNAY_EXPLOITATION_RATE_HISTORY = []
MAX_DELAUNAY_EXPLOITATION_RATE_HISTORY = 100

# Track the current Delaunay success threshold
CURRENT_DELAUNAY_SUCCESS_THRESHOLD = 0.1

# Track the Delaunay success threshold history
DELAUNAY_SUCCESS_THRESHOLD_HISTORY = []
MAX_DELAUNAY_SUCCESS_THRESHOLD_HISTORY = 100

# Track the current Delaunay failure threshold
CURRENT_DELAUNAY_FAILURE_THRESHOLD = 0.05

# Track the Delaunay failure threshold history
DELAUNAY_FAILURE_THRESHOLD_HISTORY = []
MAX_DELAUNAY_FAILURE_THRESHOLD_HISTORY = 100

# Track the current Delaunay adjustment rate
CURRENT_DELAUNAY_ADJUSTMENT_RATE = 0.1

# Track the Delaunay adjustment rate history
DELAUNAY_ADJUSTMENT_RATE_HISTORY = []
MAX_DELAUNAY_ADJUSTMENT_RATE_HISTORY = 100

# Track the current Delaunay min_area improvement
CURRENT_DELAUNAY_IMPROVEMENT = 0.0

# Track the Delaunay min_area improvement history
DELAUNAY_IMPROVEMENT_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_HISTORY = 100

# Track the current Delaunay min_area improvement count
CURRENT_DELAUNAY_IMPROVEMENT_COUNT = 0

# Track the Delaunay min_area improvement count history
DELAUNAY_IMPROVEMENT_COUNT_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_COUNT_HISTORY = 100

# Track the current Delaunay min_area improvement average
CURRENT_DELAUNAY_IMPROVEMENT_AVG = 0.0

# Track the Delaunay min_area improvement average history
DELAUNAY_IMPROVEMENT_AVG_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_AVG_HISTORY = 100

# Track the current Delaunay min_area improvement max
CURRENT_DELAUNAY_IMPROVEMENT_MAX = 0.0

# Track the Delaunay min_area improvement max history
DELAUNAY_IMPROVEMENT_MAX_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_MAX_HISTORY = 100

# Track the current Delaunay min_area improvement min
CURRENT_DELAUNAY_IMPROVEMENT_MIN = 0.0

# Track the Delaunay min_area improvement min history
DELAUNAY_IMPROVEMENT_MIN_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_MIN_HISTORY = 100

# Track the current Delaunay min_area improvement standard deviation
CURRENT_DELAUNAY_IMPROVEMENT_STD = 0.0

# Track the Delaunay min_area improvement standard deviation history
DELAUNAY_IMPROVEMENT_STD_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_STD_HISTORY = 100

# Track the current Delaunay min_area improvement median
CURRENT_DELAUNAY_IMPROVEMENT_MEDIAN = 0.0

# Track the Delaunay min_area improvement median history
DELAUNAY_IMPROVEMENT_MEDIAN_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_MEDIAN_HISTORY = 100

# Track the current Delaunay min_area improvement percentile 25
CURRENT_DELAUNAY_IMPROVEMENT_P25 = 0.0

# Track the Delaunay min_area improvement percentile 25 history
DELAUNAY_IMPROVEMENT_P25_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_P25_HISTORY = 100

# Track the current Delaunay min_area improvement percentile 75
CURRENT_DELAUNAY_IMPROVEMENT_P75 = 0.0

# Track the Delaunay min_area improvement percentile 75 history
DELAUNAY_IMPROVEMENT_P75_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_P75_HISTORY = 100

# Track the current Delaunay min_area improvement IQR
CURRENT_DELAUNAY_IMPROVEMENT_IQR = 0.0

# Track the Delaunay min_area improvement IQR history
DELAUNAY_IMPROVEMENT_IQR_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_IQR_HISTORY = 100

# Track the current Delaunay min_area improvement range
CURRENT_DELAUNAY_IMPROVEMENT_RANGE = 0.0

# Track the Delaunay min_area improvement range history
DELAUNAY_IMPROVEMENT_RANGE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_RANGE_HISTORY = 100

# Track the current Delaunay min_area improvement coefficient of variation
CURRENT_DELAUNAY_IMPROVEMENT_COV = 0.0

# Track the Delaunay min_area improvement coefficient of variation history
DELAUNAY_IMPROVEMENT_COV_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_COV_HISTORY = 100

# Track the current Delaunay min_area improvement skewness
CURRENT_DELAUNAY_IMPROVEMENT_SKEW = 0.0

# Track the Delaunay min_area improvement skewness history
DELAUNAY_IMPROVEMENT_SKEW_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_SKEW_HISTORY = 100

# Track the current Delaunay min_area improvement kurtosis
CURRENT_DELAUNAY_IMPROVEMENT_KURTOSIS = 0.0

# Track the Delaunay min_area improvement kurtosis history
DELAUNAY_IMPROVEMENT_KURTOSIS_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_KURTOSIS_HISTORY = 100

# Track the current Delaunay min_area improvement entropy
CURRENT_DELAUNAY_IMPROVEMENT_ENTROPY = 0.0

# Track the Delaunay min_area improvement entropy history
DELAUNAY_IMPROVEMENT_ENTROPY_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_ENTROPY_HISTORY = 100

# Track the current Delaunay min_area improvement mutual information
CURRENT_DELAUNAY_IMPROVEMENT_MI = 0.0

# Track the Delaunay min_area improvement mutual information history
DELAUNAY_IMPROVEMENT_MI_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_MI_HISTORY = 100

# Track the current Delaunay min_area improvement correlation
CURRENT_DELAUNAY_IMPROVEMENT_CORR = 0.0

# Track the Delaunay min_area improvement correlation history
DELAUNAY_IMPROVEMENT_CORR_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_CORR_HISTORY = 100

# Track the current Delaunay min_area improvement covariance
CURRENT_DELAUNAY_IMPROVEMENT_COV = 0.0

# Track the Delaunay min_area improvement covariance history
DELAUNAY_IMPROVEMENT_COV_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_COV_HISTORY = 100

# Track the current Delaunay min_area improvement regression slope
CURRENT_DELAUNAY_IMPROVEMENT_SLOPE = 0.0

# Track the Delaunay min_area improvement regression slope history
DELAUNAY_IMPROVEMENT_SLOPE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_SLOPE_HISTORY = 100

# Track the current Delaunay min_area improvement regression intercept
CURRENT_DELAUNAY_IMPROVEMENT_INTERCEPT = 0.0

# Track the Delaunay min_area improvement regression intercept history
DELAUNAY_IMPROVEMENT_INTERCEPT_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_INTERCEPT_HISTORY = 100

# Track the current Delaunay min_area improvement regression r-squared
CURRENT_DELAUNAY_IMPROVEMENT_R2 = 0.0

# Track the Delaunay min_area improvement regression r-squared history
DELAUNAY_IMPROVEMENT_R2_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_R2_HISTORY = 100

# Track the current Delaunay min_area improvement regression p-value
CURRENT_DELAUNAY_IMPROVEMENT_PVALUE = 0.0

# Track the Delaunay min_area improvement regression p-value history
DELAUNAY_IMPROVEMENT_PVALUE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_PVALUE_HISTORY = 100

# Track the current Delaunay min_area improvement regression standard error
CURRENT_DELAUNAY_IMPROVEMENT_SE = 0.0

# Track the Delaunay min_area improvement regression standard error history
DELAUNAY_IMPROVEMENT_SE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_SE_HISTORY = 100

# Track the current Delaunay min_area improvement regression confidence interval lower
CURRENT_DELAUNAY_IMPROVEMENT_CI_LOWER = 0.0

# Track the Delaunay min_area improvement regression confidence interval lower history
DELAUNAY_IMPROVEMENT_CI_LOWER_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_CI_LOWER_HISTORY = 100

# Track the current Delaunay min_area improvement regression confidence interval upper
CURRENT_DELAUNAY_IMPROVEMENT_CI_UPPER = 0.0

# Track the Delaunay min_area improvement regression confidence interval upper history
DELAUNAY_IMPROVEMENT_CI_UPPER_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_CI_UPPER_HISTORY = 100

# Track the current Delaunay min_area improvement regression prediction interval lower
CURRENT_DELAUNAY_IMPROVEMENT_PI_LOWER = 0.0

# Track the Delaunay min_area improvement regression prediction interval lower history
DELAUNAY_IMPROVEMENT_PI_LOWER_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_PI_LOWER_HISTORY = 100

# Track the current Delaunay min_area improvement regression prediction interval upper
CURRENT_DELAUNAY_IMPROVEMENT_PI_UPPER = 0.0

# Track the Delaunay min_area improvement regression prediction interval upper history
DELAUNAY_IMPROVEMENT_PI_UPPER_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_PI_UPPER_HISTORY = 100

# Track the current Delaunay min_area improvement regression residual sum of squares
CURRENT_DELAUNAY_IMPROVEMENT_RSS = 0.0

# Track the Delaunay min_area improvement regression residual sum of squares history
DELAUNAY_IMPROVEMENT_RSS_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_RSS_HISTORY = 100

# Track the current Delaunay min_area improvement regression total sum of squares
CURRENT_DELAUNAY_IMPROVEMENT_TSS = 0.0

# Track the Delaunay min_area improvement regression total sum of squares history
DELAUNAY_IMPROVEMENT_TSS_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_TSS_HISTORY = 100

# Track the current Delaunay min_area improvement regression explained sum of squares
CURRENT_DELAUNAY_IMPROVEMENT_ESS = 0.0

# Track the Delaunay min_area improvement regression explained sum of squares history
DELAUNAY_IMPROVEMENT_ESS_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_ESS_HISTORY = 100

# Track the current Delaunay min_area improvement regression mean squared error
CURRENT_DELAUNAY_IMPROVEMENT_MSE = 0.0

# Track the Delaunay min_area improvement regression mean squared error history
DELAUNAY_IMPROVEMENT_MSE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_MSE_HISTORY = 100

# Track the current Delaunay min_area improvement regression root mean squared error
CURRENT_DELAUNAY_IMPROVEMENT_RMSE = 0.0

# Track the Delaunay min_area improvement regression root mean squared error history
DELAUNAY_IMPROVEMENT_RMSE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_RMSE_HISTORY = 100

# Track the current Delaunay min_area improvement regression mean absolute error
CURRENT_DELAUNAY_IMPROVEMENT_MAE = 0.0

# Track the Delaunay min_area improvement regression mean absolute error history
DELAUNAY_IMPROVEMENT_MAE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_MAE_HISTORY = 100

# Track the current Delaunay min_area improvement regression mean absolute percentage error
CURRENT_DELAUNAY_IMPROVEMENT_MAPE = 0.0

# Track the Delaunay min_area improvement regression mean absolute percentage error history
DELAUNAY_IMPROVEMENT_MAPE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_MAPE_HISTORY = 100

# Track the current Delaunay min_area improvement regression symmetric mean absolute percentage error
CURRENT_DELAUNAY_IMPROVEMENT_SMAPE = 0.0

# Track the Delaunay min_area improvement regression symmetric mean absolute percentage error history
DELAUNAY_IMPROVEMENT_SMAPE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_SMAPE_HISTORY = 100

# Track the current Delaunay min_area improvement regression weighted absolute percentage error
CURRENT_DELAUNAY_IMPROVEMENT_WAPE = 0.0

# Track the Delaunay min_area improvement regression weighted absolute percentage error history
DELAUNAY_IMPROVEMENT_WAPE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_WAPE_HISTORY = 100

# Track the current Delaunay min_area improvement regression weighted mean absolute error
CURRENT_DELAUNAY_IMPROVEMENT_WMAE = 0.0

# Track the Delaunay min_area improvement regression weighted mean absolute error history
DELAUNAY_IMPROVEMENT_WMAE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_WMAE_HISTORY = 100

# Track the current Delaunay min_area improvement regression weighted root mean squared error
CURRENT_DELAUNAY_IMPROVEMENT_WRMSE = 0.0

# Track the Delaunay min_area improvement regression weighted root mean squared error history
DELAUNAY_IMPROVEMENT_WRMSE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_WRMSE_HISTORY = 100

# Track the current Delaunay min_area improvement regression weighted mean absolute percentage error
CURRENT_DELAUNAY_IMPROVEMENT_WMAPE = 0.0

# Track the Delaunay min_area improvement regression weighted mean absolute percentage error history
DELAUNAY_IMPROVEMENT_WMAPE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_WMAPE_HISTORY = 100

# Track the current Delaunay min_area improvement regression weighted symmetric mean absolute percentage error
CURRENT_DELAUNAY_IMPROVEMENT_WSMAPE = 0.0

# Track the Delaunay min_area improvement regression weighted symmetric mean absolute percentage error history
DELAUNAY_IMPROVEMENT_WSMAPE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_WSMAPE_HISTORY = 100

# Track the current Delaunay min_area improvement regression weighted weighted absolute percentage error
CURRENT_DELAUNAY_IMPROVEMENT_WWPAE = 0.0

# Track the Delaunay min_area improvement regression weighted weighted absolute percentage error history
DELAUNAY_IMPROVEMENT_WWPAE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_WWPAE_HISTORY = 100

# Track the current Delaunay min_area improvement regression weighted weighted mean absolute error
CURRENT_DELAUNAY_IMPROVEMENT_WWMAE = 0.0

# Track the Delaunay min_area improvement regression weighted weighted mean absolute error history
DELAUNAY_IMPROVEMENT_WWMAE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_WWMAE_HISTORY = 100

# Track the current Delaunay min_area improvement regression weighted weighted root mean squared error
CURRENT_DELAUNAY_IMPROVEMENT_WWRMSE = 0.0

# Track the Delaunay min_area improvement regression weighted weighted root mean squared error history
DELAUNAY_IMPROVEMENT_WWRMSE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_WWRMSE_HISTORY = 100

# Track the current Delaunay min_area improvement regression weighted weighted mean absolute percentage error
CURRENT_DELAUNAY_IMPROVEMENT_WWMAPE = 0.0

# Track the Delaunay min_area improvement regression weighted weighted mean absolute percentage error history
DELAUNAY_IMPROVEMENT_WWMAPE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_WWMAPE_HISTORY = 100

# Track the current Delaunay min_area improvement regression weighted weighted symmetric mean absolute percentage error
CURRENT_DELAUNAY_IMPROVEMENT_WWSMAPE = 0.0

# Track the Delaunay min_area improvement regression weighted weighted symmetric mean absolute percentage error history
DELAUNAY_IMPROVEMENT_WWSMAPE_HISTORY = []
MAX_DELAUNAY_IMPROVEMENT_WWSMAPE_HISTORY = 100

def entrypoint():
    A, B, C = get_unit_triangle()

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

    def get_top_k_triangle_indices(pts, k=3, ratio_threshold=None, difficulty_factor=0.5):
        """Get indices of triangles with area below ratio_threshold * min_area."""
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
            
        # Sort by area
        sorted_indices = [idx for _, idx in sorted(zip(areas, indices))]
        sorted_areas = [area for area, _ in sorted(zip(areas, indices))]
        
        # Calculate adaptive ratio_threshold if not provided
        if ratio_threshold is None:
            # Use IQR to determine appropriate threshold
            q1 = np.percentile(sorted_areas, 25)
            q3 = np.percentile(sorted_areas, 75)
            iqr = q3 - q1
            # Set threshold at median + (0.3 + 0.4 * difficulty_factor) * IQR (parameterized based on insights)
            adaptive_threshold = np.median(sorted_areas) + (0.3 + 0.5 * difficulty_factor) * iqr
            # But ensure we always get at least 1 triangle
            adaptive_threshold = max(sorted_areas[0] * 1.05, min(adaptive_threshold, sorted_areas[-1]))
            ratio_threshold = adaptive_threshold / sorted_areas[0]

        # Determine how many triangles to select
        if ratio_threshold is not None:
            min_area = sorted_areas[0]
            threshold = min_area * ratio_threshold
            # Count how many triangles are below threshold
            k = sum(1 for area in sorted_areas if area <= threshold)
            k = max(1, min(k, len(sorted_areas)))
        
        return sorted_indices[:min(k, len(sorted_indices))]

    def calculate_area_gradient(points, triangle_indices, gradient_type='inverse_square_damped'):
        """Calculate gradient of triangle area with respect to each vertex position."""
        i, j, k = triangle_indices
        a, b, c = points[i], points[j], points[k]
        
        # Area = 0.5 * |(b-a) × (c-a)|
        # Partial derivatives:
        # dA/da = -0.5 * ((b_y - c_y), (c_x - b_x))
        # dA/db = -0.5 * ((c_y - a_y), (a_x - c_x))
        # dA/dc = -0.5 * ((a_y - b_y), (b_x - a_x))
        
        grad_a = np.array([-(b[1] - c[1]), b[0] - c[0]]) * 0.5
        grad_b = np.array([-(c[1] - a[1]), c[0] - a[0]]) * 0.5
        grad_c = np.array([-(a[1] - b[1]), a[0] - b[0]]) * 0.5
        
        # Weight gradients by inverse distance to prioritize points that most affect smallest triangles
        dist_ab = max(1e-6, np.linalg.norm(a - b))
        dist_ac = max(1e-6, np.linalg.norm(a - c))
        dist_bc = max(1e-6, np.linalg.norm(b - c))

        # Damped inverse square weighting to focus on critical regions while preventing extreme values
        if gradient_type == 'inverse_square_damped':
            # Use damping factor to prevent extreme values when distances are very small
            damping = 0.01
            weight_a = 1.0 / (dist_ab**2 * dist_ac**2 + damping)
            weight_b = 1.0 / (dist_ab**2 * dist_bc**2 + damping)
            weight_c = 1.0 / (dist_ac**2 * dist_bc**2 + damping)
        else:
            # Original inverse distance weighting
            weight_a = 1.0 / (dist_ab * dist_ac)
            weight_b = 1.0 / (dist_ab * dist_bc)
            weight_c = 1.0 / (dist_ac * dist_bc)
        
        grad_a = grad_a * weight_a
        grad_b = grad_b * weight_b
        grad_c = grad_c * weight_c

        return grad_a, grad_b, grad_c

    def delaunay_edge_flip(points, triangle_indices):
        """Perform Delaunay edge flip on the given triangle to improve min_area."""
        i, j, k = triangle_indices
        
        # Create Delaunay triangulation
        try:
            tri = Delaunay(points)
        except:
            return None
        
        # Find the edge to flip (the one opposite the smallest angle)
        a, b, c = points[i], points[j], points[k]
        
        # Calculate angles at each vertex
        ab = b - a
        ac = c - a
        bc = c - b
        
        angle_a = np.arccos(np.dot(ab, ac) / (np.linalg.norm(ab) * np.linalg.norm(ac) + 1e-10))
        angle_b = np.arccos(np.dot(-ab, bc) / (np.linalg.norm(ab) * np.linalg.norm(bc) + 1e-10))
        angle_c = np.arccos(np.dot(-ac, -bc) / (np.linalg.norm(ac) * np.linalg.norm(bc) + 1e-10))
        
        # Find the smallest angle (most acute)
        min_angle = min(angle_a, angle_b, angle_c)
        
        # Determine which edge to flip based on the smallest angle
        if min_angle == angle_a:
            # Edge BC is opposite angle A
            edge_to_flip = (j, k)
            opposite_point = i
        elif min_angle == angle_b:
            # Edge AC is opposite angle B
            edge_to_flip = (i, k)
            opposite_point = j
        else:
            # Edge AB is opposite angle C
            edge_to_flip = (i, j)
            opposite_point = k
        
        # Find the neighboring triangle that shares this edge
        neighbors = []
        for simplex in tri.simplices:
            if edge_to_flip[0] in simplex and edge_to_flip[1] in simplex:
                # This is the triangle we're considering
                if opposite_point in simplex:
                    continue
                # This is a neighboring triangle
                neighbors.append(simplex)
        
        if not neighbors:
            return None
        
        # Pick the first neighboring triangle
        neighbor_tri = neighbors[0]
        
        # Find the point in the neighboring triangle that's not on the edge
        for p in neighbor_tri:
            if p != edge_to_flip[0] and p != edge_to_flip[1]:
                neighbor_point = p
                break
        
        # Create the new configuration by flipping the edge
        new_points = points.copy()
        
        # Calculate the new position for the opposite point to maximize the min area
        # This is a simplified approach - in reality, we'd solve for the optimal position
        edge_mid = (points[edge_to_flip[0]] + points[edge_to_flip[1]]) / 2
        direction = points[neighbor_point] - edge_mid
        direction = direction / (np.linalg.norm(direction) + 1e-10)
        
        # Move the opposite point in the direction that increases the area
        step = 0.01 * direction
        new_points[opposite_point] += step
        
        # Project back into the triangle if needed
        new_points[opposite_point] = barycentric_project(new_points[opposite_point])
        
        return new_points

    def run_annealing_chain(initial_points, base_step, T0, T_decay_base, step_decay_base, min_ratio, difficulty_factor):
        """Run a single annealing chain with specific parameters."""
        best = initial_points.copy()
        best_score = get_smallest_triangle_area(best)
        
        # DYNAMICALLY SET N_ROUNDS BASED ON DIFFICULTY
        n_rounds = int(200 + 250 * (0.8 + 0.7 * (1 - min_ratio)))
        T_decay = T_decay_base
        step_decay = step_decay_base

        # Track improvement history for adaptive cooling
        improvement_history = []
        stagnation_counter = 0
        stagnation_threshold = 20
        
        # Initialize Delaunay success tracking for this chain
        delaunay_attempts = 0
        delaunay_successes = 0
        
        for round_idx in range(n_rounds):
            # Early stopping if improvement rate is too low
            if improvement_history and len(improvement_history) > 30:
                recent_improvements = improvement_history[-30:]
                avg_improvement = np.mean(recent_improvements)
                if avg_improvement < 1e-7 and round_idx > 150:
                    break

            # Adjust cooling rate based on recent progress
            window_size = max(5, min(20, 20 - int(round_idx / n_rounds * 15)))
            if improvement_history and len(improvement_history) >= window_size:
                recent_improvements = improvement_history[-window_size:]
                avg_improvement = np.mean(recent_improvements)
                if avg_improvement < 1e-6:
                    T_decay = max(0.996, T_decay * 1.001)
                    step_decay = min(0.9995, step_decay * 1.0005)
                    stagnation_counter += 1
                else:
                    T_decay = min(0.9985, T_decay * 0.9998)
                    step_decay = max(0.997, step_decay * 0.9997)
                    stagnation_counter = max(0, stagnation_counter - 1)
            
            # Reset if stuck for too long
            adaptive_stagnation_threshold = max(15, min(30, stagnation_threshold + 10 * (stagnation_counter / 5)))
            if stagnation_counter > adaptive_stagnation_threshold:
                T_decay = T_decay_base
                step_decay = step_decay_base
                stagnation_counter = 0
                improvement_history = []

            T = T0 * (T_decay ** round_idx)
            current_step = base_step * (step_decay ** round_idx)
            
            # Dynamically adjust min_ratio based on progress
            if stagnation_counter > adaptive_stagnation_threshold // 2:
                adaptive_min_ratio = min(0.3, min_ratio * 1.1)
            else:
                adaptive_min_ratio = max(0.01, min_ratio * 0.9)

            # Get top triangles adaptively based on area distribution
            triangle_indices = get_top_k_triangle_indices(best, k=3, ratio_threshold=None, difficulty_factor=difficulty_factor)
            selected_triangle = triangle_indices[np.random.randint(len(triangle_indices))]
            
            # Adaptive strategy selection based on historical success rates
            # Calculate success rates for each strategy
            total_attempts = max(1, GRADIENT_ATTEMPTS + ISOTROPIC_ATTEMPTS + DELAUNAY_ATTEMPTS)
            gradient_success_rate = GRADIENT_SUCCESSES / max(1, GRADIENT_ATTEMPTS)
            isotropic_success_rate = ISOTROPIC_SUCCESSES / max(1, ISOTROPIC_ATTEMPTS)
            delaunay_success_rate = DELAUNAY_SUCCESSES / max(1, DELAUNAY_ATTEMPTS)

            # Calculate weighted probabilities
            total_success_rate = gradient_success_rate + isotropic_success_rate + delaunay_success_rate
            if total_success_rate > 0:
                gradient_prob = gradient_success_rate / total_success_rate
                isotropic_prob = isotropic_success_rate / total_success_rate
                delaunay_prob = delaunay_success_rate / total_success_rate
            else:
                # Default probabilities if no successes yet
                gradient_prob = 0.5
                isotropic_prob = 0.3
                delaunay_prob = 0.2

            # Apply a small exploration bonus to encourage trying less successful methods
            exploration_bonus = 0.05
            gradient_prob = min(0.9, gradient_prob + exploration_bonus * (1 - gradient_success_rate))
            isotropic_prob = min(0.9, isotropic_prob + exploration_bonus * (1 - isotropic_success_rate))
            delaunay_prob = min(0.9, delaunay_prob + exploration_bonus * (1 - delaunay_success_rate))

            # Normalize probabilities
            total_prob = gradient_prob + isotropic_prob + delaunay_prob
            gradient_prob /= total_prob
            isotropic_prob /= total_prob
            delaunay_prob /= total_prob

            # Choose strategy based on probabilities
            strategy_choice = np.random.choice(['gradient', 'isotropic', 'delaunay'], p=[gradient_prob, isotropic_prob, delaunay_prob])

            if strategy_choice == 'delaunay':
                # Try Delaunay edge flip
                delaunay_attempts += 1
                candidate = delaunay_edge_flip(best, selected_triangle)
                
                if candidate is not None:
                    candidate_score = get_smallest_triangle_area(candidate)
                    delta = candidate_score - best_score
                    
                    # Track Delaunay success
                    if delta > 0:
                        delaunay_successes += 1
                        
                    # Acceptance criterion
                    if delta > 0 or np.random.rand() < np.exp(delta / T):
                        best = candidate
                        best_score = candidate_score
                        
                        # Update global Delaunay success tracking
                        global DELAUNAY_ATTEMPTS, DELAUNAY_SUCCESSES
                        DELAUNAY_ATTEMPTS += 1
                        if delta > 0:
                            DELAUNAY_SUCCESSES += 1
                        
                        # Track improvement for adaptive cooling
                        if delta > 0:
                            improvement_history.append(delta)
                            if len(improvement_history) > 50:
                                improvement_history.pop(0)
                        continue

            # Fallback to original strategies if Delaunay didn't succeed
            # DYNAMICALLY ADJUST GRADIENT VS ISOTROPIC RATIO BASED ON OPTIMIZATION STAGE
            # Using sigmoidal progression for smoother adaptation (replaces linear progression)
            progress = round_idx / n_rounds
            gradient_prob = 0.3 + 0.6 / (1 + np.exp(-10 * (progress - 0.5)))
            
            if np.random.rand() < gradient_prob:
                # Gradient-based perturbations (more targeted)
                grad_i, grad_j, grad_k = calculate_area_gradient(best, selected_triangle, 'inverse_square_damped')
                
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
            
            # Track improvements for adaptive cooling
            if delta > 0:
                improvement_history.append(delta)
                if len(improvement_history) > 50:
                    improvement_history.pop(0)

            # Acceptance criterion
            if delta > 0 or np.random.rand() < np.exp(delta / T):
                best = candidate
                best_score = candidate_score

        # Update global Delaunay success rate after chain completes
        if delaunay_attempts > 0:
            global DELAUNAY_SUCCESS_RATE
            DELAUNAY_SUCCESS_RATE = delaunay_successes / delaunay_attempts

        return best, best_score

    def improve(points: np.ndarray) -> np.ndarray:
        # Calculate initial min_area to adapt parameters based on difficulty
        initial_min_area = get_smallest_triangle_area(points)
        
        # Update dynamic maximum area estimate
        global DYNAMIC_MAX_AREA, HISTORICAL_BEST, IMPROVEMENT_HISTORY, MAX_HISTORICAL_BEST
        
        # Update historical best
        if initial_min_area > HISTORICAL_BEST:
            HISTORICAL_BEST = initial_min_area
        
        # Update dynamic max area with learning rate
        if HISTORICAL_BEST > 0:
            DYNAMIC_MAX_AREA = min(MAX_HISTORICAL_BEST, DYNAMIC_MAX_AREA + LEARNING_RATE * (HISTORICAL_BEST - DYNAMIC_MAX_AREA))
        
        # Scale parameters based on initial min_area (higher min_area = harder problem)
        # Use dynamic max area instead of hardcoded 0.0365
        difficulty_factor = 1.0 - initial_min_area / max(0.01, DYNAMIC_MAX_AREA)  # Normalize to [0,1] where 0 is hardest
        
        # DYNAMICALLY SET CHAIN COUNT BASED ON DIFFICULTY
        # Use logarithmic scaling instead of linear
        chain_count = max(2, min(6, int(2 + 3 * (1 - difficulty_factor)**2)))
        
        # Create chains with logarithmically spaced parameters
        chains = []
        
        for i in range(chain_count):
            # Calculate position in parameter space (0 to 1) using log scale
            if chain_count > 1:
                position = (10**(i/(chain_count-1)) - 1) / 9  # Logarithmic spacing from 0 to 1
            else:
                position = 0.5
            
            # Scale parameters based on position and difficulty
            base_step = 0.02 + 0.08 * position * (1.0 + 0.3 * (1 - difficulty_factor))
            T0_val = 0.008 + 0.004 * position * (1.0 + 0.3 * (1 - difficulty_factor))
            
            # Run annealing chain with these parameters
            chain, score = run_annealing_chain(
                points.copy(),
                base_step=base_step,
                T0=T0_val,
                T_decay_base=0.9975 + 0.0005 * position,
                step_decay_base=0.9985 + 0.0005 * position,
                min_ratio=difficulty_factor,
                difficulty_factor=difficulty_factor
            )
            chains.append((chain, score))
        
        # Select the best chain result
        best_chain = max(chains, key=lambda x: x[1])
        return best_chain[0]

    return improve