"""Visualization.

Animate a single fetch attempt: the thrown object, the dog's delayed perception
of it, and the dog running / jumping / snapping its jaw.

``plot`` takes ``rotated_jaw_angle`` as an argument so this module stays
independent of the catch-detection code that defines it.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from IPython.display import HTML, display

from constants import GOAL_Y, INTERVAL


def _jaw_open_amount(dog, t_now, time_since_seen, reaction_delay_s, intercept_t, jaw_close_mistime):
    trigger_time = intercept_t + 0.02 + jaw_close_mistime
    if t_now < trigger_time:
        total_intercept_time = intercept_t - reaction_delay_s
        progress = min(1.0, max(0.0, time_since_seen / max(total_intercept_time, 0.01)))
        return dog.jaw_open_angle * progress
    if t_now < trigger_time + dog.jaw_close_duration:
        close_progress = (t_now - trigger_time) / dog.jaw_close_duration
        return dog.jaw_open_angle * (1.0 - close_progress)
    return 0.0


def _setup_axes(throw_range, throw_angle_deg, error_radius, v0,
                reaction_delay_s, thrown_object, goal_x, dog):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)
    ax.set_aspect("equal")
    ax.set_xlabel("Horizontal Distance (m)")
    ax.set_ylabel("Height (m)")
    ax.set_title(
        f"Dog Fetch Simulation \u2013 {dog.name} ({thrown_object.upper()}) "
        f"(\u00b1{error_radius * 100:.0f}cm throw error)\n"
        f"Range={throw_range:.2f}m | Reaction Delay={reaction_delay_s * 1000:.0f}ms\n"
        f"Speed={v0:.2f}m/s | Angle={throw_angle_deg:.1f}\u00b0"
    )
    ax.grid(True)
    target_zone = plt.Circle((goal_x, GOAL_Y), error_radius, color="green",
                             fill=False, linestyle="--", alpha=0.5)
    ax.add_patch(target_zone)
    return fig, ax


def _update_arrow(dog_arrow, i, t, reaction_delay_s, head_x, head_y, intercept_target):
    if i > 0 and t[i] >= reaction_delay_s and intercept_target is not None:
        dx = intercept_target[0] - head_x
        dy = intercept_target[1] - head_y
        dist = np.sqrt(dx**2 + dy**2)
        if dist > 0.02:
            scale = min(dist, 0.3)
            dog_arrow.xy = (head_x + dx / dist * scale, head_y + dy / dist * scale)
            dog_arrow.set_position((head_x, head_y))
            dog_arrow.set_visible(True)
            return
    dog_arrow.set_visible(False)


def _update_jaw(dog, rotated_jaw_angle, jaw_upper, jaw_lower, t_now, reaction_delay_s,
                head_x, head_y, intercept_target, intercept_t,
                jaw_target, jaw_close_mistime):
    if t_now < reaction_delay_s or intercept_target is None:
        jaw_upper.set_data([head_x, head_x - dog.arrow_length], [head_y, head_y])
        jaw_lower.set_data([], [])
        return

    time_since_seen = t_now - reaction_delay_s
    current_angle = rotated_jaw_angle(dog, jaw_target, time_since_seen)
    jaw_open = _jaw_open_amount(dog, t_now, time_since_seen, reaction_delay_s,
                               intercept_t, jaw_close_mistime)

    upper_angle = current_angle + jaw_open
    jaw_upper.set_data(
        [head_x, head_x + np.cos(upper_angle) * dog.arrow_length],
        [head_y, head_y + np.sin(upper_angle) * dog.arrow_length],
    )
    lower_angle = current_angle - jaw_open
    jaw_lower.set_data(
        [head_x, head_x + np.cos(lower_angle) * dog.arrow_length],
        [head_y, head_y + np.sin(lower_angle) * dog.arrow_length],
    )


def plot(dog, rotated_jaw_angle, throw_range, throw_angle_deg, goal_x, error_radius, v0,
         x1, y1, x2, y2, t, reaction_delay_s, num_frames,
         dog_positions, intercept_target, intercept_is_q2, intercept_t,
         jaw_target, thrown_object, jaw_close_mistime):
    """Render and display an animation of a single fetch attempt."""
    fig, ax = _setup_axes(throw_range, throw_angle_deg, error_radius, v0,
                          reaction_delay_s, thrown_object, goal_x, dog)

    line, = ax.plot([], [], lw=2, color="gray", alpha=0.5)
    ball1, = ax.plot([], [], "ro", markersize=8, label="Thrown Ball")
    ball2, = ax.plot([], [], "bo", markersize=8, label="Dog's Perception")
    dog_marker, = ax.plot([], [], "gs", markersize=12, label=f"Dog ({dog.name})")
    dog_arrow = ax.annotate("", xy=(0, 0), xytext=(0, 0),
                            arrowprops=dict(arrowstyle="->", color="green", lw=2))
    dog_arrow.set_visible(False)
    jaw_upper, = ax.plot([], [], color="red", linestyle="--", lw=1.5)
    jaw_lower, = ax.plot([], [], color="red", linestyle="--", lw=1.5)

    if intercept_target is not None:
        ix_color = "g" if intercept_is_q2 else "r"
        ax.plot([intercept_target[0]], [intercept_target[1]], marker="x",
                color=ix_color, markersize=10, markeredgewidth=2,
                label="Intercept Point", alpha=0.6)

    ax.legend(loc="upper right")

    def init():
        line.set_data([], [])
        ball1.set_data([], [])
        ball2.set_data([], [])
        dog_marker.set_data([], [])
        dog_arrow.set_visible(False)
        jaw_upper.set_data([], [])
        jaw_lower.set_data([], [])
        return line, ball1, ball2, dog_marker

    def animate(i):
        line.set_data(x1[:i], y1[:i])
        ball1.set_data([x1[i]], [y1[i]])

        if t[i] >= reaction_delay_s:
            ball2.set_data([x2[i]], [y2[i]])
        else:
            ball2.set_data([], [])

        dog_x, dog_y = dog_positions[i]
        head_x = dog_x
        head_y = dog_y + GOAL_Y
        dog_marker.set_data([dog_x], [head_y])

        _update_arrow(dog_arrow, i, t, reaction_delay_s, head_x, head_y, intercept_target)
        _update_jaw(dog, rotated_jaw_angle, jaw_upper, jaw_lower, t[i], reaction_delay_s,
                    head_x, head_y, intercept_target, intercept_t,
                    jaw_target, jaw_close_mistime)
        return line, ball1, ball2, dog_marker

    ani = FuncAnimation(fig, animate, frames=num_frames, init_func=init,
                        interval=INTERVAL, blit=True)
    display(HTML(ani.to_jshtml()))
    plt.close(fig)
