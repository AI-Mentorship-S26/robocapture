"""
Batch import phone/external images into labeled_dataset.csv.

Reads all images from a reward folder and a punishment folder, runs each
through the MobileNetV2 preprocessing pipeline, and appends 1287-float
state vectors to the dataset CSV — ready for model training.

Phone images are NOT rotated 180 degrees (that rotation is Pi-camera-specific).
EXIF orientation is respected, so portrait/landscape phone shots load correctly.
change_pct is fixed at 100.0 — imported images have no prior frame to diff against.

The label (reward / punishment) is detected automatically from the folder name —
the folder name just needs to contain the word "reward" or "punishment" anywhere.

Run from the robocapture root:
    .venv-1/Scripts/python picam/import_labeled_images.py rewards/ punishments/
    .venv-1/Scripts/python picam/import_labeled_images.py C:/photos/rewards C:/photos/punishments
    .venv-1/Scripts/python picam/import_labeled_images.py rewards/ punishments/ --dry-run

Supported formats: .jpg .jpeg .png .bmp .webp .tiff
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

PICAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PICAM_DIR))

from image_preprocessing import LowLevelImageFilter, SemanticFeatureExtractor

DEFAULT_DATASET = PICAM_DIR / "datasets" / "labeled_dataset.csv"
FIELDNAMES = [
    "image_id", "captured_at", "image_path", "label",
    "pipeline_would_send", "has_significant_change",
    "stage1_passes", "stage2_passes", "features", "state",
]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}
ANALYSIS_SIZE = (224, 224)


# ── Image loading ─────────────────────────────────────────────────────────────

def load_and_resize(image_path: Path) -> np.ndarray | None:
    """
    Load image via PIL (handles EXIF rotation from phone cameras),
    resize to 224x224, return as BGR numpy array for cv2 compatibility.
    Does NOT apply the Pi-camera 180-degree flip.
    """
    try:
        pil_img = Image.open(image_path)
        pil_img = ImageOps.exif_transpose(pil_img)   # fix phone portrait/landscape
        pil_img = pil_img.convert("RGB")
        pil_img = pil_img.resize(ANALYSIS_SIZE, Image.LANCZOS)
        img_rgb = np.array(pil_img)
        return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    except Exception as exc:
        print(f"  [skip] Load failed ({exc})")
        return None


# ── Dataset helpers ───────────────────────────────────────────────────────────

def load_existing_ids(dataset_path: Path) -> set[str]:
    if not dataset_path.exists():
        return set()
    with dataset_path.open(encoding="utf-8") as f:
        return {row["image_id"] for row in csv.DictReader(f)}


def ensure_dataset_file(dataset_path: Path) -> None:
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    if not dataset_path.exists():
        with dataset_path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()


def unique_image_id(stem: str, label: str, existing_ids: set[str]) -> str:
    base = f"import_{label[0]}_{stem}"
    if base not in existing_ids:
        return base
    for i in range(1, 10_000):
        candidate = f"{base}_{i}"
        if candidate not in existing_ids:
            return candidate
    raise RuntimeError(f"Could not generate a unique id for {stem!r}")


# ── Core processing ───────────────────────────────────────────────────────────

def process_image(
    image_path: Path,
    label: str,
    low_level: LowLevelImageFilter,
    semantic: SemanticFeatureExtractor,
    existing_ids: set[str],
) -> dict | None:
    resized = load_and_resize(image_path)
    if resized is None:
        return None

    stage1_passes, stage1_results = low_level.apply_filters(resized, verbose=False)
    stage2_passes, stage2_results = semantic.extract_features(resized, verbose=False)

    if not stage2_passes or "embedding" not in stage2_results:
        print(f"  [skip] Embedding failed: {image_path.name}")
        return None

    # change_pct fixed at 100.0 — imported images are treated as independent frames
    features = {
        "change_pct":          100.0,
        "brightness":          float(stage1_results["brightness"]),
        "saturation":          float(stage1_results["saturation"]),
        "sharpness":           float(stage1_results["sharpness"]),
        "edge_count":          float(stage1_results["edge_count"]),
        "mean_frequency":      float(stage1_results["mean_frequency"]),
        "embedding_magnitude": float(stage2_results["embedding_magnitude"]),
    }
    state = [
        features["change_pct"],
        features["brightness"],
        features["saturation"],
        features["sharpness"],
        features["edge_count"],
        features["mean_frequency"],
        features["embedding_magnitude"],
        *[float(v) for v in stage2_results["embedding"].tolist()],
    ]

    image_id = unique_image_id(image_path.stem, label, existing_ids)

    return {
        "image_id":               image_id,
        "captured_at":            datetime.now().isoformat(timespec="seconds"),
        "image_path":             str(image_path.resolve()),
        "label":                  label,
        "pipeline_would_send":    str(stage1_passes and stage2_passes).lower(),
        "has_significant_change": "true",
        "stage1_passes":          str(stage1_passes).lower(),
        "stage2_passes":          str(stage2_passes).lower(),
        "features":               json.dumps(features),
        "state":                  json.dumps(state),
    }


# ── Folder scanning ───────────────────────────────────────────────────────────

def collect_images(folder: Path) -> list[Path]:
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def detect_label(folder: Path) -> str:
    """Infer reward/punishment from the folder name (case-insensitive)."""
    name = folder.name.lower()
    if "reward" in name:
        return "reward"
    if "punishment" in name:
        return "punishment"
    print(f"[error] Cannot detect label from folder name '{folder.name}'.")
    print("        Folder name must contain 'reward' or 'punishment'.")
    sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Batch import labeled images into labeled_dataset.csv.\n"
            "Label is detected automatically from the folder name — "
            "the name must contain 'reward' or 'punishment'."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("folders", type=Path, nargs="+",
                        help="One or more image folders (name must contain 'reward' or 'punishment')")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET,
                        help="Output CSV (default: picam/datasets/labeled_dataset.csv)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be imported without writing anything")
    args = parser.parse_args()

    dataset_path = args.dataset.expanduser().resolve()

    # Resolve folders and detect labels from their names
    labeled_folders: list[tuple[str, Path, list[Path]]] = []
    for raw in args.folders:
        folder = raw.expanduser().resolve()
        if not folder.is_dir():
            print(f"[error] Folder not found: {folder}")
            sys.exit(1)
        label  = detect_label(folder)
        images = collect_images(folder)
        labeled_folders.append((label, folder, images))

    total = sum(len(imgs) for _, _, imgs in labeled_folders)

    for label, folder, images in labeled_folders:
        print(f"{label:<12} <- {folder}  ({len(images)} images)")
    print(f"Dataset:      {dataset_path}")
    print(f"Total:        {total} images")

    if total == 0:
        print("[warn] No images found — check folder paths and file extensions.")
        sys.exit(0)

    if args.dry_run:
        print("\n[dry-run] Nothing will be written.\n")
        for label, _, images in labeled_folders:
            for p in images:
                print(f"  {label:<12} {p.name}")
        return

    print("\nLoading MobileNetV2 (first run downloads ~14 MB weights)...")
    low_level = LowLevelImageFilter()
    semantic  = SemanticFeatureExtractor()
    print("Ready.\n")

    existing_ids = load_existing_ids(dataset_path)
    ensure_dataset_file(dataset_path)

    saved = skipped = 0

    with dataset_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

        for label, _, images in labeled_folders:
            print(f"--- {label.upper()} ({len(images)} images) ---")
            for i, img_path in enumerate(images, 1):
                print(f"  [{i:>3}/{len(images)}] {img_path.name:<40}", end=" ", flush=True)
                row = process_image(img_path, label, low_level, semantic, existing_ids)
                if row is None:
                    skipped += 1
                    continue
                writer.writerow(row)
                existing_ids.add(row["image_id"])
                saved += 1
                print(f"-> {row['image_id']}")
            print()

    print(f"Done.  Saved {saved} rows, skipped {skipped}.")
    print(f"Dataset: {dataset_path}  (total rows now: {len(existing_ids)})")
    print(
        f"\nRe-evaluate models:\n"
        f"  .venv-1/Scripts/python picam/plot_model_accuracy.py "
        f"--holdout --train-size 451 --epochs 20 --features-only"
    )


if __name__ == "__main__":
    main()
