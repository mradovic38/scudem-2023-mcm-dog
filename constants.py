"""World & physics constants for the dog fetch simulation.

These describe the world and the throw, and are the same regardless of which
dog is fetching.
"""

# --- Physics ---
G = 9.81           # gravitational acceleration (m/s^2)
RHO = 1.225        # air density at sea level (kg/m^3)

# --- Throw ---
THROW_ERROR_RADIUS = 0.3       # meters, radius of the throw scatter zone
THROW_INIT_HEIGHT_MIN = 1.2    # meters
THROW_INIT_HEIGHT_MAX = 1.4    # meters
THROW_ANGLE_DEG_MIN = 20
THROW_ANGLE_DEG_MAX = 45

# --- Goal / dog rest position ---
GOAL_X_MIN = 1.2
GOAL_X_MAX = 1.8
GOAL_Y = 0.55      # meters, dog head height at rest

# --- Animation ---
FPS = 30
INTERVAL = 1000 / FPS  # milliseconds per frame
