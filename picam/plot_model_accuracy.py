"""
Test all RL models against the labeled dataset and plot rolling accuracy.

For each image in labeled_dataset.csv:
  - Parse the 1287-float state vector
  - Run each RL model's inference  ->  0 (skip) or 1 (send)
  - Ground truth: reward=1, punishment=0
  - Correct prediction = model output matches ground truth
  - Plot rolling accuracy (window=20) per model in a subplot grid

Run from the robocapture root:
    .venv-1/Scripts/python picam/plot_model_accuracy.py
    .venv-1/Scripts/python picam/plot_model_accuracy.py --window 30
"""

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ── Path setup (rl_models.py uses relative imports from picam/) ───────────────
PICAM_DIR = Path(__file__).parent
sys.path.insert(0, str(PICAM_DIR))

# ── Constants ─────────────────────────────────────────────────────────────────
CSV_PATH = PICAM_DIR / "datasets" / "labeled_dataset.csv"
WINDOW   = 20

MODEL_ORDER = [
    "random",
    "contextual_bandit",
    "deep_contextual_bandit",
    "sarsa",
    "dqn",
    "reinforce",
    "ppo",
    "aac",
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
}

# ── Load CSV ──────────────────────────────────────────────────────────────────

def load_dataset(features_only: bool = False) -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, usecols=["image_id", "label", "state"],
                     dtype={"image_id": str, "label": str})
    df["gt"] = df["label"].map({"reward": 1, "punishment": 0})
    df = df.dropna(subset=["gt", "state"]).reset_index(drop=True)

    def parse_state(s: str) -> list:
        try:
            return json.loads(s)
        except Exception:
            return ast.literal_eval(s)

    df["state_vec"] = df["state"].apply(parse_state)

    if features_only:
        # Use only the 7 hand-crafted metrics — drops the 1280-dim embedding.
        # Smaller state space means models generalize across images instead of
        # treating every frame as a unique unseen state.
        df["state_vec"] = df["state_vec"].apply(lambda v: v[:7])
        print(f"[info] Features-only mode: state reduced 1287 -> 7 dims")

    print(f"[info] Loaded {len(df)} rows  (reward={df['gt'].sum():.0f}, "
          f"punishment={(df['gt']==0).sum():.0f})")
    return df

# ── Import RL model runners ───────────────────────────────────────────────────

def load_model_runners() -> tuple[dict, dict]:
    """
    Returns (run_fns, update_fns) dicts keyed by model name.
    tiny_sac excluded (stub, identical to random).
    """
    import rl_models as rm

    run_fns = {
        "random":                rm.run_random,
        "contextual_bandit":     rm.run_contextual_bandit,
        "deep_contextual_bandit":rm.run_deep_contextual_bandit,
        "sarsa":                 rm.run_sarsa,
        "dqn":                   rm.run_dqn,
        "reinforce":             rm.run_reinforce,
        "ppo":                   rm.run_ppo,
        "aac":                   rm.run_aac,
    }
    update_fns = {
        "random":                rm.update_random,
        "contextual_bandit":     rm.update_contextual_bandit,
        "deep_contextual_bandit":rm.update_deep_contextual_bandit,
        "sarsa":                 rm.update_sarsa,
        "dqn":                   rm.update_dqn,
        "reinforce":             rm.update_reinforce,
        "ppo":                   rm.update_ppo,
        "aac":                   rm.update_aac,
    }
    print(f"[info] Loaded {len(run_fns)} model runners.")
    return run_fns, update_fns

# ── Run inference (static) ────────────────────────────────────────────────────

def run_model_on_dataset(name: str, run_fn, df: pd.DataFrame) -> np.ndarray:
    """
    Static inference only — update_X never called.
    Returns bool array: correct[i] = model prediction matched ground truth.
    """
    correct = np.zeros(len(df), dtype=bool)
    for i, row in df.iterrows():
        try:
            pred = int(run_fn(row["image_id"], row["state_vec"]))
        except Exception as exc:
            print(f"  [warn] {name} failed on row {i}: {exc}")
            pred = 0
        correct[i] = pred == int(row["gt"])

    acc = correct.mean() * 100
    print(f"  {name:<26} overall accuracy: {acc:.1f}%")
    return correct

# ── Run online (prequential) evaluation ───────────────────────────────────────

def run_model_online(name: str, run_fn, update_fn, df: pd.DataFrame,
                     epochs: int = 1) -> np.ndarray:
    """
    Prequential (test-then-train) evaluation:
      1. Model predicts on image i  →  record correct/wrong
      2. Model is immediately updated with the true label
      3. Repeat for i+1

    This shows the learning curve — how accuracy improves as the model
    sees more labeled examples. Data must be in chronological order.
    """
    # Train-only passes first (epochs-1 times), then one final test-then-train pass
    for epoch in range(epochs - 1):
        for _, row in df.iterrows():
            img_id = f"{row['image_id']}_e{epoch}"   # unique id per epoch
            reward = 1 if int(row["gt"]) == 1 else -1
            try:
                run_fn(img_id, row["state_vec"])
                update_fn(img_id, reward)
            except Exception:
                pass

    # Final pass: test THEN train — this is what gets plotted
    correct = np.zeros(len(df), dtype=bool)
    for i, row in df.iterrows():
        state  = row["state_vec"]
        gt     = int(row["gt"])
        img_id = row["image_id"]
        reward = 1 if gt == 1 else -1

        try:
            pred = int(run_fn(img_id, state))
        except Exception as exc:
            print(f"  [warn] {name} predict failed row {i}: {exc}")
            pred = 0

        correct[i] = pred == gt

        try:
            update_fn(img_id, reward)
        except Exception as exc:
            print(f"  [warn] {name} update failed row {i}: {exc}")

    acc = correct.mean() * 100
    print(f"  {name:<26} final accuracy: {acc:.1f}%")
    return correct

# ── Run holdout (train/test split) evaluation ────────────────────────────────

def run_model_holdout(name: str, run_fn, update_fn,
                      train_df: pd.DataFrame, test_df: pd.DataFrame,
                      epochs: int = 1) -> np.ndarray:
    """
    Proper supervised holdout evaluation:
      1. Train on train_df for `epochs` full passes (update after every image)
      2. Evaluate on held-out test_df — no weight updates during testing

    This isolates train/test so epoch count comparisons are meaningful.
    Returns bool array over the test set.
    """
    for epoch in range(epochs):
        for _, row in train_df.iterrows():
            img_id = f"{row['image_id']}_e{epoch}"
            reward = 1 if int(row["gt"]) == 1 else -1
            try:
                run_fn(img_id, row["state_vec"])
                update_fn(img_id, reward)
            except Exception:
                pass

    correct = np.zeros(len(test_df), dtype=bool)
    for i, (_, row) in enumerate(test_df.iterrows()):
        try:
            pred = int(run_fn(row["image_id"], row["state_vec"]))
        except Exception as exc:
            print(f"  [warn] {name} predict failed row {i}: {exc}")
            pred = 0
        correct[i] = pred == int(row["gt"])

    acc = correct.mean() * 100
    print(f"  {name:<26} holdout test accuracy ({epochs} ep): {acc:.1f}%")
    return correct

# ── Rolling accuracy ──────────────────────────────────────────────────────────

def rolling_accuracy(correct: np.ndarray, window: int) -> np.ndarray:
    s = pd.Series(correct.astype(float))
    return s.rolling(window=window, min_periods=1).mean().values

# ── Plot ──────────────────────────────────────────────────────────────────────

def plot(results: dict, window: int, suffix: str = "") -> None:
    """
    results: {model_name: correct_bool_array}
    """
    models = [m for m in MODEL_ORDER if m in results]
    extra  = [m for m in results if m not in MODEL_ORDER]
    models += extra

    ncols = 2
    nrows = (len(models) + 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 4 * nrows),
                             constrained_layout=True)
    fig.suptitle(
        f"RL Model Accuracy on Labeled Dataset  (rolling window = {window} images)",
        fontsize=15, fontweight="bold",
    )
    axes_flat = axes.flatten() if len(models) > 1 else [axes]

    for ax, name in zip(axes_flat, models):
        correct = results[name]
        ra      = rolling_accuracy(correct, window)
        color   = MODEL_COLORS.get(name, "#757575")
        x       = np.arange(len(ra))

        ax.plot(x, ra, color=color, linewidth=1.8)
        ax.axhline(0.5, color="#bdbdbd", linestyle="--", linewidth=0.9,
                   label="50% (random baseline)")

        ax.fill_between(x, 0.5, ra, where=(ra >= 0.5),
                        alpha=0.15, color="green")
        ax.fill_between(x, ra, 0.5, where=(ra < 0.5),
                        alpha=0.15, color="red")

        overall = correct.mean()
        ax.set_title(
            f"{name}  |  overall acc = {overall:.1%}  "
            f"(correct={correct.sum()}/{len(correct)})",
            fontsize=10,
        )
        ax.set_xlabel("Image index")
        ax.set_ylabel("Rolling accuracy")
        ax.set_ylim(0, 1)
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    for ax in axes_flat[len(models):]:
        ax.set_visible(False)

    out = Path(f"model_accuracy_comparison{suffix}.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"\n[info] Saved -> {out.resolve()}")
    _open(out)

# ── Overlay plot (all models on one axes) ─────────────────────────────────────

def plot_overlay(results: dict, window: int, suffix: str = "") -> None:
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axhline(0.5, color="#bdbdbd", linestyle="--", linewidth=1.0,
               label="50% baseline", zorder=0)

    for name, correct in results.items():
        ra    = rolling_accuracy(correct, window)
        color = MODEL_COLORS.get(name, "#757575")
        acc   = correct.mean()
        ax.plot(np.arange(len(ra)), ra, color=color, linewidth=1.6,
                label=f"{name}  ({acc:.1%})")

    ax.set_title(
        f"All Models — Rolling Accuracy Overlay  (window={window})",
        fontsize=13, fontweight="bold",
    )
    ax.set_xlabel("Image index")
    ax.set_ylabel("Rolling accuracy")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    out = Path(f"model_accuracy_overlay{suffix}.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"[info] Saved -> {out.resolve()}")
    _open(out)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _open(path: Path) -> None:
    try:
        os.startfile(path)
    except AttributeError:
        subprocess.run(["xdg-open", str(path)], check=False)

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window",  type=int, default=WINDOW)
    parser.add_argument("--shuffle", action="store_true",
                        help="Shuffle rows to remove dataset order bias (static mode only)")
    parser.add_argument("--online",        action="store_true",
                        help="Prequential (test-then-train) evaluation")
    parser.add_argument("--features-only", action="store_true",
                        help="Use only 7 hand-crafted features instead of full 1287-dim state")
    parser.add_argument("--epochs",        type=int, default=1,
                        help="Training passes before the final evaluation pass (default: 1)")
    parser.add_argument("--holdout",       action="store_true",
                        help="Train on --train-size rows, test on the remaining held-out rows")
    parser.add_argument("--train-size",    type=int, default=500,
                        help="Number of rows used for training in holdout mode (default: 500)")
    args = parser.parse_args()

    df = load_dataset(features_only=args.features_only)

    # Always shuffle before a holdout split so the test set isn't all from one session
    if args.holdout or args.shuffle:
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)
        print("[info] Rows shuffled — distribution shift removed.")
    elif args.online:
        df = df.sort_values("image_id").reset_index(drop=True)
        print("[info] Online mode: chronological order.")

    run_fns, update_fns = load_model_runners()

    results = {}
    if args.holdout:
        n_train = min(args.train_size, len(df) - 1)
        train_df = df.iloc[:n_train].reset_index(drop=True)
        test_df  = df.iloc[n_train:].reset_index(drop=True)
        print(f"\n[info] Holdout split: {len(train_df)} train / {len(test_df)} test  "
              f"({args.epochs} epoch{'s' if args.epochs != 1 else ''})")
        for name in MODEL_ORDER:
            if name not in run_fns:
                continue
            results[name] = run_model_holdout(
                name, run_fns[name], update_fns[name],
                train_df, test_df, epochs=args.epochs,
            )
        suffix = f"_holdout_{args.epochs}ep"
        if args.features_only:  suffix += "_7feat"
    elif args.online:
        parts = []
        if args.shuffle:        parts.append("shuffled")
        if args.features_only:  parts.append("7-features")
        if args.epochs > 1:     parts.append(f"{args.epochs} epochs")
        mode = " + ".join(parts) if parts else "chronological"
        print(f"\n[info] Running prequential evaluation ({mode})...")
        for name in MODEL_ORDER:
            if name not in run_fns:
                continue
            results[name] = run_model_online(
                name, run_fns[name], update_fns[name], df, epochs=args.epochs
            )
        suffix = "_online"
        if args.shuffle:        suffix += "_shuffled"
        if args.features_only:  suffix += "_7feat"
        if args.epochs > 1:     suffix += f"_{args.epochs}ep"
    else:
        print("\n[info] Running static inference (no training)...")
        for name in MODEL_ORDER:
            if name not in run_fns:
                continue
            results[name] = run_model_on_dataset(name, run_fns[name], df)
        suffix = "_shuffled" if args.shuffle else ""

    print()
    plot(results, args.window, suffix)
    plot_overlay(results, args.window, suffix)


if __name__ == "__main__":
    main()
