import os
import pickle
from pathlib import Path

import torch


MODEL_STORE_DIR = Path(__file__).resolve().parent.parent / "saved_models"


def model_file(stem: str, suffix: str) -> Path:
    MODEL_STORE_DIR.mkdir(parents=True, exist_ok=True)
    return MODEL_STORE_DIR / f"{stem}{suffix}"


def save_pickle(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with temp_path.open("wb") as handle:
        pickle.dump(payload, handle)
    os.replace(temp_path, path)


def load_pickle(path: Path):
    if not path.exists():
        return None
    with path.open("rb") as handle:
        return pickle.load(handle)


def save_torch(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    torch.save(payload, temp_path)
    os.replace(temp_path, path)


def load_torch(path: Path):
    if not path.exists():
        return None
    return torch.load(path, map_location="cpu")
