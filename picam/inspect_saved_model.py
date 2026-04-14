from __future__ import annotations

import argparse
import pickle
from datetime import datetime
from pathlib import Path

import torch


DEFAULT_DIR = Path(__file__).resolve().parent / "saved_models"


def summarize_value(key: str, value, indent: str = "") -> None:
    if isinstance(value, torch.Tensor):
        flat = value.detach().float().reshape(-1)
        mean = flat.mean().item() if flat.numel() else 0.0
        std = flat.std(unbiased=False).item() if flat.numel() else 0.0
        print(
            f"{indent}{key}: tensor shape={tuple(value.shape)} "
            f"dtype={value.dtype} mean={mean:.6f} std={std:.6f}"
        )
        return

    if isinstance(value, dict):
        print(f"{indent}{key}: dict ({len(value)} keys)")
        for child_key, child_value in value.items():
            summarize_value(str(child_key), child_value, indent + "  ")
        return

    if isinstance(value, (list, tuple)):
        print(f"{indent}{key}: {type(value).__name__} (len={len(value)})")
        preview = list(value[:5])
        if preview:
            print(f"{indent}  preview: {preview}")
        return

    print(f"{indent}{key}: {value!r}")


def load_model(path: Path):
    if path.suffix == ".pt":
        return torch.load(path, map_location="cpu")
    if path.suffix in {".pkl", ".pickle"}:
        with path.open("rb") as handle:
            return pickle.load(handle)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def resolve_path(target: str) -> Path:
    candidate = Path(target)
    if candidate.exists():
        return candidate

    if not candidate.suffix:
        pt_candidate = DEFAULT_DIR / f"{candidate.name}.pt"
        if pt_candidate.exists():
            return pt_candidate

        pkl_candidate = DEFAULT_DIR / f"{candidate.name}.pkl"
        if pkl_candidate.exists():
            return pkl_candidate

    default_candidate = DEFAULT_DIR / candidate
    if default_candidate.exists():
        return default_candidate

    raise FileNotFoundError(f"Could not find saved model: {target}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a saved RoboCapture model file.")
    parser.add_argument(
        "target",
        nargs="?",
        default="reinforce",
        help="Model name or path. Examples: reinforce, reinforce.pt, /path/to/file.pt",
    )
    args = parser.parse_args()

    path = resolve_path(args.target)
    payload = load_model(path)

    stat = path.stat()
    print(f"Path: {path}")
    print(f"Size: {stat.st_size} bytes")
    print(f"Modified: {datetime.fromtimestamp(stat.st_mtime).isoformat(timespec='seconds')}")
    print(f"Type: {type(payload).__name__}")

    if isinstance(payload, dict):
        print("Contents:")
        for key, value in payload.items():
            summarize_value(key, value, indent="  ")
    else:
        summarize_value("payload", payload, indent="  ")


if __name__ == "__main__":
    main()
