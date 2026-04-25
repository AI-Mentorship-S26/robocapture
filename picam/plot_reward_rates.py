"""
Rolling reward rate plot for all RL models.

Data source priority:
  1. Supabase image_vectors table (has rl_model column) → per-model subplots
  2. Local labeled_dataset.csv (no rl_model column) → single overall plot

Usage:
    python3 picam/plot_reward_rates.py
    python3 picam/plot_reward_rates.py --local   # force local CSV only
    python3 picam/plot_reward_rates.py --window 30
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _open(path: Path) -> None:
    """Open a file with the OS default viewer."""
    try:
        os.startfile(path)  # Windows
    except AttributeError:
        subprocess.run(["xdg-open", str(path)], check=False)

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — saves PNG without needing a display
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────

WINDOW = 20  # rolling window size (images)
LOCAL_CSV = Path(__file__).parent / "datasets" / "labeled_dataset.csv"
ENV_FILE = Path(__file__).parent.parent / ".env"

MODEL_ORDER = [
    "random",
    "contextual_bandit",
    "deep_contextual_bandit",
    "sarsa",
    "dqn",
    "reinforce",
    "ppo",
    "aac",
    "tiny_sac",
]

MODEL_COLORS = {
    "random":                "#9e9e9e",
    "contextual_bandit":     "#42a5f5",
    "deep_contextual_bandit":"#1565c0",
    "sarsa":                 "#66bb6a",
    "dqn":                   "#f57c00",
    "reinforce":             "#ab47bc",
    "ppo":                   "#ec407a",
    "aac":                   "#26c6da",
    "tiny_sac":              "#ef5350",
}

# ── Supabase fetch ────────────────────────────────────────────────────────────

def fetch_from_supabase() -> Optional[pd.DataFrame]:
    """
    Returns DataFrame with columns: image_id, label (1/-1), rl_model.
    Returns None if Supabase is unreachable or table is empty.
    """
    load_dotenv(ENV_FILE)
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("[warn] No Supabase credentials found in .env — using local CSV.")
        return None

    try:
        from supabase import create_client
    except ImportError:
        print("[warn] supabase-py not installed — using local CSV.")
        return None

    try:
        client = create_client(url, key)
        # Fetch all rows; select only the columns we need
        response = (
            client.table("image_vectors")
            .select("image_id, label, rl_model")
            .order("image_id", desc=False)
            .execute()
        )
        rows = response.data
        if not rows:
            print("[warn] image_vectors table is empty — using local CSV.")
            return None

        df = pd.DataFrame(rows)
        # label is stored as integer (+1 / -1) in Supabase
        df["label"] = pd.to_numeric(df["label"], errors="coerce")
        df = df.dropna(subset=["label", "rl_model"])
        print(f"[info] Loaded {len(df)} rows from Supabase across "
              f"{df['rl_model'].nunique()} model(s).")
        return df

    except Exception as exc:
        print(f"[warn] Supabase query failed ({exc}) — using local CSV.")
        return None

# ── Local CSV fetch ───────────────────────────────────────────────────────────

def fetch_from_csv() -> pd.DataFrame:
    """
    Returns DataFrame with columns: image_id, label (1/-1).
    label column in CSV is 'reward'/'punishment' string → converted to +1/-1.
    No rl_model column exists here.
    """
    if not LOCAL_CSV.exists():
        sys.exit(f"[error] {LOCAL_CSV} not found and Supabase unavailable.")

    df = pd.read_csv(
        LOCAL_CSV,
        usecols=["image_id", "label"],
        dtype={"image_id": str, "label": str},
    )
    df["label"] = df["label"].map({"reward": 1, "punishment": -1})
    df = df.dropna(subset=["label"])
    df = df.sort_values("image_id").reset_index(drop=True)
    print(f"[info] Loaded {len(df)} rows from local CSV (no model split available).")
    return df

# ── Rolling reward rate ───────────────────────────────────────────────────────

def rolling_reward_rate(labels: pd.Series, window: int) -> pd.Series:
    """
    Converts +1/-1 labels to binary (1=reward, 0=punishment),
    then computes a rolling mean → fraction of rewards in the last `window` images.
    min_periods=1 so the curve starts from image 0 instead of NaN.
    """
    binary = (labels == 1).astype(float)
    return binary.rolling(window=window, min_periods=1).mean()

# ── Plot: per-model subplots ──────────────────────────────────────────────────

def plot_per_model(df: pd.DataFrame, window: int) -> None:
    models_present = [m for m in MODEL_ORDER if m in df["rl_model"].values]
    # Any model not in MODEL_ORDER gets appended at the end
    extra = [m for m in df["rl_model"].unique() if m not in MODEL_ORDER]
    models_present += extra

    n = len(models_present)
    ncols = 2
    nrows = (n + 1) // ncols

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(14, 4 * nrows),
        constrained_layout=True,
    )
    fig.suptitle(
        f"Rolling Reward Rate per RL Model  (window = {window} images)",
        fontsize=15,
        fontweight="bold",
    )
    axes_flat = axes.flatten() if n > 1 else [axes]

    for ax, model in zip(axes_flat, models_present):
        sub = df[df["rl_model"] == model].reset_index(drop=True)
        rr = rolling_reward_rate(sub["label"], window)

        color = MODEL_COLORS.get(model, "#757575")
        ax.plot(rr.index, rr.values, color=color, linewidth=1.8, label=model)
        ax.axhline(0.5, color="#bdbdbd", linestyle="--", linewidth=0.9, label="50% baseline")

        # Shade above/below 50%
        ax.fill_between(rr.index, 0.5, rr.values,
                        where=(rr.values >= 0.5), alpha=0.15, color="green")
        ax.fill_between(rr.index, rr.values, 0.5,
                        where=(rr.values < 0.5),  alpha=0.15, color="red")

        n_reward = (sub["label"] == 1).sum()
        n_punish = (sub["label"] == -1).sum()
        final_rate = rr.iloc[-1] if len(rr) > 0 else 0.0

        ax.set_title(
            f"{model}  |  n={len(sub)}  (R={n_reward}, P={n_punish})  "
            f"final={final_rate:.1%}",
            fontsize=10,
        )
        ax.set_xlabel("Image index")
        ax.set_ylabel("Reward rate")
        ax.set_ylim(0, 1)
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    # Hide unused subplots
    for ax in axes_flat[len(models_present):]:
        ax.set_visible(False)

    out = Path("reward_rates_per_model.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"[info] Saved {out.resolve()}")
    _open(out)

# ── Plot: single overall (CSV fallback) ──────────────────────────────────────

def plot_overall(df: pd.DataFrame, window: int) -> None:
    rr = rolling_reward_rate(df["label"], window)
    n_reward = (df["label"] == 1).sum()
    n_punish = (df["label"] == -1).sum()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(rr.index, rr.values, color="#42a5f5", linewidth=1.8, label="reward rate")
    ax.axhline(0.5, color="#bdbdbd", linestyle="--", linewidth=0.9, label="50% baseline")
    ax.fill_between(rr.index, 0.5, rr.values,
                    where=(rr.values >= 0.5), alpha=0.15, color="green")
    ax.fill_between(rr.index, rr.values, 0.5,
                    where=(rr.values < 0.5),  alpha=0.15, color="red")

    ax.set_title(
        f"Overall Rolling Reward Rate  (window={window})  "
        f"n={len(df)}  R={n_reward}  P={n_punish}",
        fontsize=13,
    )
    ax.set_xlabel("Image index")
    ax.set_ylabel("Reward rate")
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    out = Path("reward_rates_overall.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"[info] Saved {out.resolve()}")
    _open(out)

# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Plot RL model reward rates.")
    parser.add_argument("--local",  action="store_true",
                        help="Force local CSV instead of Supabase")
    parser.add_argument("--window", type=int, default=WINDOW,
                        help=f"Rolling window size (default: {WINDOW})")
    args = parser.parse_args()

    df = None
    if not args.local:
        df = fetch_from_supabase()

    if df is None or "rl_model" not in df.columns:
        # CSV fallback — no model split
        df = fetch_from_csv()
        plot_overall(df, args.window)
    else:
        plot_per_model(df, args.window)


if __name__ == "__main__":
    main()
