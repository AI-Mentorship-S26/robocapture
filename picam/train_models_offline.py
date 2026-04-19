import json
import logging
import argparse

import numpy as np
import pandas as pd

import rl_models


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_ORDER = [
    "random",
    "deep_contextual_bandit",
    "contextual_bandit",
    "sarsa",
    "dqn",
    "ppo",
    "reinforce",
    "aac",
    "tiny_sac",
]


def discover_models():
    run_models = {
        attr_name.removeprefix("run_")
        for attr_name in dir(rl_models)
        if attr_name.startswith("run_") and callable(getattr(rl_models, attr_name))
    }
    update_models = {
        attr_name.removeprefix("update_")
        for attr_name in dir(rl_models)
        if attr_name.startswith("update_") and callable(getattr(rl_models, attr_name))
    }
    discovered = run_models & update_models
    ordered = [model_name for model_name in MODEL_ORDER if model_name in discovered]
    unordered = sorted(discovered - set(ordered))
    return ordered + unordered


MODELS = discover_models()


def compute_alignment_reward(model_action, dataset_label):
    """Return +1 if model action matches label, else -1."""
    correct_action = 1 if dataset_label == "reward" else 0
    return 1.0 if model_action == correct_action else -1.0


def get_model_object(model_name):
    return getattr(rl_models, f"{model_name}_object", None)


def get_model_snapshot(model_name):
    model_object = get_model_object(model_name)
    if model_object is None:
        return {"model": model_name, "error": "model object not found"}

    snapshot = {
        "type": type(model_object).__name__,
        "update_count": getattr(model_object, "update_count", None),
        "last_reward": getattr(model_object, "last_reward", None),
        "history_size": len(getattr(model_object, "history", {})),
    }

    if hasattr(model_object, "epsilon"):
        snapshot["epsilon"] = round(float(model_object.epsilon), 6)

    if hasattr(model_object, "memory"):
        snapshot["memory_size"] = len(model_object.memory)

    if hasattr(model_object, "q_table"):
        snapshot["q_table_size"] = len(model_object.q_table)
        if model_object.q_table:
            first_key = next(iter(model_object.q_table))
            snapshot["q_probe"] = [round(float(x), 6) for x in model_object.q_table[first_key]]

    if hasattr(model_object, "weights"):
        weight_array = np.array(model_object.weights).reshape(-1)
        snapshot["weight_probe"] = [round(float(x), 6) for x in weight_array[:3]]

    network = None
    for attr_name in ("actor_model", "model", "network"):
        candidate = getattr(model_object, attr_name, None)
        if candidate is not None:
            network = candidate
            break

    if network is not None:
        first_param = next(network.parameters(), None)
        if first_param is not None:
            snapshot["param_probe"] = [
                round(float(x), 6)
                for x in first_param.detach().cpu().reshape(-1)[:3]
            ]

    checkpoint_path = getattr(model_object, "checkpoint_path", None)
    if checkpoint_path is not None:
        snapshot["checkpoint"] = checkpoint_path.name

    return snapshot


def format_snapshot(snapshot):
    ordered_keys = [
        "type",
        "update_count",
        "last_reward",
        "history_size",
        "epsilon",
        "memory_size",
        "q_table_size",
        "q_probe",
        "weight_probe",
        "param_probe",
        "checkpoint",
        "error",
    ]
    parts = []
    for key in ordered_keys:
        if key in snapshot and snapshot[key] is not None:
            parts.append(f"{key}={snapshot[key]}")
    return ", ".join(parts)


def train_all_models(csv_path, num_epochs=1, log_sample_updates=True):
    """Train all models on the dataset."""
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} samples\n")

    results = []

    for model_name in MODELS:
        logger.info(f"Training {model_name.upper()}...")
        logger.info(
            "  Model snapshot before training: %s",
            format_snapshot(get_model_snapshot(model_name)),
        )
        correct = 0
        total = len(df) * num_epochs

        try:
            for epoch in range(num_epochs):
                for idx, row in df.iterrows():
                    try:
                        state = np.array(json.loads(row["state"]), dtype=np.float32)
                        label = row["label"]

                        # Get the model's current action for this saved state.
                        image_id = f"{model_name}_epoch{epoch}_idx{idx}"
                        run_func = getattr(rl_models, f"run_{model_name}")
                        action = run_func(image_id, state.tolist())

                        # Turn label alignment into a reward signal.
                        reward = compute_alignment_reward(action, label)

                        # Update the model and show a compact before/after snapshot.
                        update_func = getattr(rl_models, f"update_{model_name}")
                        before_update = get_model_snapshot(model_name) if log_sample_updates else None
                        update_func(image_id, reward)
                        after_update = get_model_snapshot(model_name) if log_sample_updates else None

                        if log_sample_updates:
                            logger.info(
                                "  [%s sample %s] action=%s label=%s reward=%s",
                                model_name,
                                idx,
                                action,
                                label,
                                reward,
                            )
                            logger.info("    before update: %s", format_snapshot(before_update))
                            logger.info("    after update:  %s", format_snapshot(after_update))

                        if reward > 0:
                            correct += 1

                    except Exception as e:
                        logger.warning(f"  Sample {idx} failed: {e}")
                        continue

            accuracy = correct / total if total > 0 else 0
            logger.info(
                "  Model snapshot after training:  %s",
                format_snapshot(get_model_snapshot(model_name)),
            )
            logger.info(f"  OK {model_name}: {accuracy:.2%} accuracy ({correct}/{total})\n")
            results.append({"model": model_name, "accuracy": accuracy, "correct": correct, "total": total})

        except Exception as e:
            logger.error(f"  X {model_name} training failed: {e}\n")
            results.append({"model": model_name, "error": str(e)})

    logger.info("=" * 50)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 50)
    for result in results:
        if "error" in result:
            logger.info(f"{result['model']:15s} | ERROR: {result['error']}")
        else:
            logger.info(
                f"{result['model']:15s} | {result['accuracy']:.2%} ({result['correct']}/{result['total']})"
            )
    logger.info("=" * 50)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train RoboCapture RL models from a labeled offline dataset.")
    parser.add_argument(
        "csv_file",
        nargs="?",
        default="dataset.csv",
        help="Path to a CSV containing at least 'state' and 'label' columns.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=1,
        help="Number of passes over the dataset for each model.",
    )
    parser.add_argument(
        "--quiet-samples",
        action="store_true",
        help="Only print per-model snapshots and final summary, not every sample update.",
    )
    args = parser.parse_args()

    train_all_models(
        args.csv_file,
        num_epochs=args.epochs,
        log_sample_updates=not args.quiet_samples,
    )
