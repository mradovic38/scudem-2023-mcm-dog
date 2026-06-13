"""
Outputs are written to ``assets/figures/`` (or ``figures/`` if ``assets/``
does not exist), relative to the project root:

* ``drag_coeffs.pdf``    - bar chart of the effective drag term k per object.
* ``trajectories.pdf``   - ball trajectories with and without drag.
* ``dog_kinematics.pdf`` - speed and distance vs time for Optimal and Fitz.
* ``catch_rates.pdf``    - per-object Optimal vs Fitz catch-rate comparison.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from constants import G
from objects import DRAG_COEFFS
from physics import dog_distance, dog_velocity, generate_ball_trajectory

_ASSETS_DIR = os.path.join(ROOT, "assets", "figures")
OUT_DIR = _ASSETS_DIR if os.path.isdir(os.path.dirname(_ASSETS_DIR)) else os.path.join(ROOT, "figures")
os.makedirs(OUT_DIR, exist_ok=True)


def fig_drag_coeffs():
    names = list(DRAG_COEFFS.keys())
    values = [DRAG_COEFFS[n] for n in names]

    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    bars = ax.bar(
        [n.capitalize() for n in names], values,
        color=["#4C72B0", "#DD8452", "#55A467", "#C44E52", "#8172B2", "#937860"],
    )
    ax.set_ylabel(r"Drag term $k$ $(\mathrm{m}^{-1})$")
    ax.set_title(r"Effective per-object drag term $k = c_d \rho A / (2m)$")
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2, v + 0.004,
            f"{v:.3f}", ha="center", fontsize=9,
        )
    ax.set_ylim(0, max(values) * 1.15)
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "drag_coeffs.pdf"))
    fig.savefig(os.path.join(OUT_DIR, "drag_coeffs.png"), dpi=160)
    plt.close(fig)


def fig_catch_rates():
    # Both columns come from the same reproducible batch:
    #   run_batch(1000, dog=OPTIMAL, batch_seed=0)
    #   run_batch(1000, dog=FITZ,    batch_seed=0)
    # so the two dogs were evaluated on identical throws.
    optimal_rates = {
        "ball":    92.7,
        "sausage": 92.7,
        "pizza":   88.8,
        "taco":    93.2,
        "steak":   88.7,
        "fry":     95.4,
    }
    fitz_rates = {
        "ball":    25.1,
        "sausage": 21.2,
        "pizza":   18.8,
        "taco":    24.7,
        "steak":   19.5,
        "fry":     14.4,
    }
    labels = [n.capitalize() for n in fitz_rates]
    x = np.arange(len(labels))
    width = 0.38

    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    ax.bar(x - width / 2, [optimal_rates[n] for n in fitz_rates], width,
           label="Optimal", color="#55A467")
    ax.bar(x + width / 2, list(fitz_rates.values()), width,
           label="Fitz", color="#C44E52")
    ax.axhline(91.9, ls="--", color="#55A467", alpha=0.5, lw=1)
    ax.axhline(20.8, ls="--", color="#C44E52", alpha=0.5, lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel(r"Catch success rate (\%)")
    ax.set_ylim(0, 105)
    ax.set_title("Catch success rate per object (n = 1000 throws per dog)")
    ax.legend(loc="center right")
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "catch_rates.pdf"))
    fig.savefig(os.path.join(OUT_DIR, "catch_rates.png"), dpi=160)
    plt.close(fig)


def fig_trajectories():
    v0, alpha = 6.0, np.radians(35)
    vx0, vy0 = v0 * np.cos(alpha), v0 * np.sin(alpha)
    h0 = 1.3

    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    for obj, color, ls in [("ball", "#4C72B0", "-"),
                           ("fry",  "#C44E52", "-")]:
        t, x, y = generate_ball_trajectory(vx0, vy0, h0, G, DRAG_COEFFS[obj])
        ax.plot(x, y, color=color, lw=2, ls=ls,
                label=f"{obj.capitalize()} (k = {DRAG_COEFFS[obj]:.3f})")

    t, x, y = generate_ball_trajectory(vx0, vy0, h0, G, 0.0)
    ax.plot(x, y, color="black", lw=1.5, ls=":", label="No drag (reference)")

    ax.set_xlabel("Horizontal distance (m)")
    ax.set_ylabel("Height (m)")
    ax.set_title(
        f"Trajectories for a {v0} m/s launch at {np.degrees(alpha):.0f}°"
        f" from height {h0} m"
    )
    ax.legend()
    ax.grid(linestyle=":", alpha=0.6)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "trajectories.pdf"))
    fig.savefig(os.path.join(OUT_DIR, "trajectories.png"), dpi=160)
    plt.close(fig)


def fig_dog_kinematics():
    t = np.linspace(0, 1.5, 400)
    optimal = {"name": "Optimal", "a0": 15.0, "vmax": 12.0, "color": "#55A467"}
    fitz    = {"name": "Fitz",    "a0":  7.0, "vmax":  8.0, "color": "#C44E52"}

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2))
    for prof in (optimal, fitz):
        v = [dog_velocity(ti, prof["a0"], prof["vmax"]) for ti in t]
        d = [dog_distance(ti, prof["a0"], prof["vmax"]) for ti in t]
        axes[0].plot(t, v, color=prof["color"], lw=2, label=prof["name"])
        axes[1].plot(t, d, color=prof["color"], lw=2, label=prof["name"])

    axes[0].set_xlabel("Time (s)")
    axes[0].set_ylabel("Speed (m/s)")
    axes[0].set_title(r"$v(t) = v_{\max}\tanh(a_0 t / v_{\max})$")
    axes[0].legend()
    axes[0].grid(linestyle=":", alpha=0.6)

    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Distance (m)")
    axes[1].set_title(r"$d(t) = (v_{\max}^2/a_0)\ln\cosh(a_0 t / v_{\max})$")
    axes[1].legend()
    axes[1].grid(linestyle=":", alpha=0.6)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "dog_kinematics.pdf"))
    fig.savefig(os.path.join(OUT_DIR, "dog_kinematics.png"), dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    fig_drag_coeffs()
    fig_trajectories()
    fig_dog_kinematics()
    fig_catch_rates()
    print(f"Generated figures in {OUT_DIR}")
