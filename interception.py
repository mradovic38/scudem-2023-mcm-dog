"""Interception planning.

Given the dog's position and the predicted ball path, decide which point on the
trajectory the dog should aim to intercept.
"""

import numpy as np

from constants import FPS, G, GOAL_Y
from physics import compute_ball_position_at_time, dog_distance, dog_time_for_distance


def _jump_time(target_y):
    """Time spent airborne to reach ``target_y`` above the rest head height."""
    jump_h = max(0, target_y - GOAL_Y)
    return np.sqrt(2 * jump_h / G) if jump_h > 0.01 else 0.0


def compute_interception(dog, dog_x, ball_t_vals, ball_x_vals, ball_y_vals,
                         t_flight, t_current, dt=1.0 / FPS):
    """Pick the best ball point for the dog to intercept.

    Preference order:
      1. A reachable point in front of the dog and above head height.
      2. The closest-to-reachable such point (smallest time deficit).
      3. A pure-running fallback (highest reachable ball point).

    Returns ``(target, target_time, is_preferred)``; ``target`` may be ``None``.
    """
    best_q2 = best_q2_t = None
    best_q2_timing_error = float("inf")

    best_q2_unreachable = best_q2_unreachable_t = None
    best_q2_unreachable_deficit = float("inf")

    best_fallback = best_fallback_t = None
    best_fallback_y = -1

    t_check = t_current
    while t_check <= t_flight:
        bx, by = compute_ball_position_at_time(t_check, ball_t_vals, ball_x_vals, ball_y_vals)
        by = max(by, 0)

        time_available = t_check - t_current
        dist = abs(dog_x - bx)
        dog_dist = dog_distance(time_available, dog.acceleration, dog.max_speed)

        if bx < dog_x and by > GOAL_Y:
            run_time = dog_time_for_distance(dist, dog.acceleration, dog.max_speed)
            total_dog_time = run_time + _jump_time(by)
            timing_error = abs(time_available - total_dog_time)

            if total_dog_time <= time_available:
                if timing_error < best_q2_timing_error:
                    best_q2 = (bx, by)
                    best_q2_t = t_check
                    best_q2_timing_error = timing_error
            else:
                deficit = total_dog_time - time_available
                if deficit < best_q2_unreachable_deficit:
                    best_q2_unreachable = (bx, by)
                    best_q2_unreachable_t = t_check
                    best_q2_unreachable_deficit = deficit
        elif dog_dist >= dist:
            if by > best_fallback_y:
                best_fallback = (bx, by)
                best_fallback_t = t_check
                best_fallback_y = by

        t_check += dt

    if best_q2 is not None:
        return best_q2, best_q2_t, True
    if best_q2_unreachable is not None:
        return best_q2_unreachable, best_q2_unreachable_t, True
    return best_fallback, best_fallback_t, False
