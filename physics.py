import numpy as np


def generate_ball_trajectory(vx0, vy0, h0, g, drag, dt=0.01):
    """Integrate the ball trajectory until it hits the ground."""
    t_vals = [0.0]
    x_vals = [0.0]
    y_vals = [h0]
    vx, vy = vx0, vy0
    x, y = 0.0, h0
    while y >= 0:
        v = np.sqrt(vx**2 + vy**2)
        ax = -drag * vx * v
        ay = -g - drag * vy * v
        vx += ax * dt
        vy += ay * dt
        x += vx * dt
        y += vy * dt
        t_vals.append(t_vals[-1] + dt)
        x_vals.append(x)
        y_vals.append(y)
    return np.array(t_vals), np.array(x_vals), np.array(y_vals)


def compute_ball_position_at_time(t_val, t_vals, x_vals, y_vals):
    """Interpolate the ball position at an arbitrary time."""
    x = np.interp(t_val, t_vals, x_vals)
    y = np.interp(t_val, t_vals, y_vals)
    return float(x), float(y)


def dog_distance(dt, a0, vmax):
    """Distance covered by an accelerating dog after ``dt`` seconds."""
    if dt <= 0:
        return 0.0
    return (vmax**2 / a0) * np.log(np.cosh(a0 * dt / vmax))


def dog_velocity(dt, a0, vmax):
    """Speed of an accelerating dog after ``dt`` seconds."""
    if dt <= 0:
        return 0.0
    return vmax * np.tanh(a0 * dt / vmax)


def dog_time_for_distance(dist, a0, vmax):
    """Time required for an accelerating dog to cover ``dist`` (bisection)."""
    if dist <= 0:
        return 0.0
    t_hi = dist / vmax + vmax / a0
    t_lo = 0.0
    for _ in range(50):
        t_mid = (t_lo + t_hi) / 2
        if dog_distance(t_mid, a0, vmax) < dist:
            t_lo = t_mid
        else:
            t_hi = t_mid
    return (t_lo + t_hi) / 2
