"""
Plot accuracy vs epoch count for each RL model.

Data collected from:  --online --shuffle --features-only  sweep over epochs 1, 3, 5, 10.
Checkpoints were cleared between each run to prevent leakage.

Run from the robocapture root:
    .venv-1/Scripts/python picam/plot_epoch_sweep.py
"""

import os
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ── Collected sweep data ──────────────────────────────────────────────────────

EPOCHS = [1, 3, 5, 10]

# Accuracy (0–100) for each model at each epoch count, in EPOCHS order
SWEEP = {
    "random":                [47.7, 49.0, 49.7, 50.3],
    "contextual_bandit":     [47.4, 45.2, 49.0, 51.9],
    "deep_contextual_bandit":[45.0, 42.8, 52.8, 63.2],
    "sarsa":                 [47.7, 48.3, 50.3,  7.4],   # crashed at 10 epochs
    "dqn":                   [53.7, 54.6, 51.0, 51.0],
    "reinforce":             [48.1, 48.1, 48.1, 48.1],   # flat — lr too slow / need more data
    "ppo":                   [47.7, 47.0, 47.9, 50.1],
    "aac":                   [48.1, 46.8, 48.1, 51.9],
}

MODEL_COLORS = {
    "random":                "#9e9e9e",
    "contextual_bandit":     "#42a5f5",
    "deep_contextual_bandit":"#1565c0",
    "sarsa":                 "#66bb6a",
    "dqn":                   "#f57c00",
    "reinforce":             "#ab47bc",
    "ppo":                   "#ec407a",
    "aac":                   "#26c6da",
}

# ── Plot ──────────────────────────────────────────────────────────────────────

def plot_epoch_sweep() -> None:
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.axhline(50, color="#bdbdbd", linestyle="--", linewidth=1.0,
               label="50 % (random baseline)", zorder=0)

    for name, accs in SWEEP.items():
        color = MODEL_COLORS.get(name, "#757575")
        ax.plot(EPOCHS, accs, marker="o", linewidth=2.0, markersize=6,
                color=color, label=name)
        # annotate final point
        ax.annotate(
            f"{accs[-1]:.1f}%",
            xy=(EPOCHS[-1], accs[-1]),
            xytext=(4, 0), textcoords="offset points",
            fontsize=7.5, color=color, va="center",
        )

    ax.set_title(
        "RL Model Accuracy vs Training Epochs\n"
        "(prequential · shuffled · 7-feature state · 551 images)",
        fontsize=13, fontweight="bold",
    )
    ax.set_xlabel("Training epochs (passes before final evaluation)")
    ax.set_ylabel("Final pass accuracy (%)")
    ax.set_xticks(EPOCHS)
    ax.set_ylim(0, 100)
    ax.legend(fontsize=9, loc="upper left", bbox_to_anchor=(0.01, 0.99))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    out = Path("epoch_sweep_accuracy.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"[info] Saved -> {out.resolve()}")
    try:
        os.startfile(out)
    except AttributeError:
        subprocess.run(["xdg-open", str(out)], check=False)


if __name__ == "__main__":
    plot_epoch_sweep()
