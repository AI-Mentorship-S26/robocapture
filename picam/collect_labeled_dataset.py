import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from image_preprocessing import ImagePreprocessingPipeline


DEFAULT_DATASET = Path(__file__).resolve().parent / "datasets" / "labeled_dataset.csv"
FIELDNAMES = [
    "image_id",
    "captured_at",
    "image_path",
    "label",
    "pipeline_would_send",
    "has_significant_change",
    "stage1_passes",
    "stage2_passes",
    "features",
    "state",
]


def run_capture() -> Path:
    script_dir = Path(__file__).resolve().parent
    capture_script = script_dir / "capture_once.py"
    proc = subprocess.run(
        [sys.executable, str(capture_script)],
        capture_output=True,
        text=True,
        check=False,
    )
    image_path = proc.stdout.strip()

    if proc.returncode != 0 or not image_path:
        stderr = proc.stderr.strip() or "Capture failed."
        raise RuntimeError(stderr)

    resolved_path = Path(image_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"Capture script reported a missing file: {resolved_path}")

    return resolved_path


def prepare_previous_frame(pipeline: ImagePreprocessingPipeline, previous_image_path: Path | None):
    if previous_image_path is None:
        return None
    _, previous_resized_img = pipeline.capture_processor.prepare_images(str(previous_image_path))
    return previous_resized_img


def analyze_image(pipeline: ImagePreprocessingPipeline, image_path: Path, previous_image_path: Path | None, verbose: bool):
    _, resized_img = pipeline.capture_processor.prepare_images(str(image_path))
    previous_resized_img = prepare_previous_frame(pipeline, previous_image_path)

    has_change, change_pct = pipeline.change_detector.detect_change(
        resized_img,
        explicit_previous_frame=previous_resized_img,
    )
    stage1_passes, stage1_results = pipeline.low_level_filter.apply_filters(resized_img, verbose=verbose)
    stage2_passes, stage2_results = pipeline.semantic_extractor.extract_features(resized_img, verbose=verbose)

    if not stage2_passes or "embedding" not in stage2_results:
        raise RuntimeError("Could not extract an embedding for this image.")

    features = {
        "change_pct": float(change_pct),
        "brightness": float(stage1_results["brightness"]),
        "saturation": float(stage1_results["saturation"]),
        "sharpness": float(stage1_results["sharpness"]),
        "edge_count": float(stage1_results["edge_count"]),
        "mean_frequency": float(stage1_results["mean_frequency"]),
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
        *[float(value) for value in stage2_results["embedding"].tolist()],
    ]

    pipeline_would_send = bool(has_change and stage1_passes and stage2_passes)

    return {
        "pipeline_would_send": pipeline_would_send,
        "has_significant_change": bool(has_change),
        "stage1_passes": bool(stage1_passes),
        "stage2_passes": bool(stage2_passes),
        "features": features,
        "state": state,
    }


def ensure_dataset_file(dataset_path: Path) -> None:
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    if dataset_path.exists():
        return
    with dataset_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()


def prompt_for_label() -> str | None:
    while True:
        raw = input("Label this image: [r]eward, [p]unishment, [s]kip row, [q]uit: ").strip().lower()
        if raw in {"r", "reward"}:
            return "reward"
        if raw in {"p", "punishment"}:
            return "punishment"
        if raw in {"s", "skip"}:
            return None
        if raw in {"q", "quit"}:
            raise KeyboardInterrupt
        print("Please enter r, p, s, or q.")


def append_dataset_row(dataset_path: Path, row: dict) -> None:
    with dataset_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writerow(row)


def build_dataset_row(
    image_path: Path,
    label: str,
    analysis: dict,
    image_id: str | None = None,
    captured_at: str | None = None,
) -> dict:
    if image_id is None:
        image_id = image_path.stem
    if captured_at is None:
        captured_at = datetime.now().isoformat(timespec="seconds")
    return {
        "image_id": image_id,
        "captured_at": captured_at,
        "image_path": str(image_path),
        "label": label,
        "pipeline_would_send": str(analysis["pipeline_would_send"]).lower(),
        "has_significant_change": str(analysis["has_significant_change"]).lower(),
        "stage1_passes": str(analysis["stage1_passes"]).lower(),
        "stage2_passes": str(analysis["stage2_passes"]).lower(),
        "features": json.dumps(analysis["features"]),
        "state": json.dumps(analysis["state"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture and label Pi images into a local CSV dataset for offline RL training."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Maximum number of captures to collect before stopping.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="CSV path for the labeled dataset.",
    )
    parser.add_argument(
        "--quiet-preprocessing",
        action="store_true",
        help="Suppress detailed preprocessing logs during collection.",
    )
    args = parser.parse_args()

    dataset_path = args.dataset.expanduser().resolve()
    ensure_dataset_file(dataset_path)

    pipeline = ImagePreprocessingPipeline()
    previous_image_path = None
    saved_rows = 0

    print(f"Dataset file: {dataset_path}")
    print(f"Target captures: {args.count}")
    print("Press Enter before each capture. Use Ctrl+C or choose 'q' to stop.\n")

    try:
        for capture_index in range(args.count):
            input(f"[{capture_index + 1}/{args.count}] Press Enter to capture...")
            image_path = run_capture()
            print(f"Captured image: {image_path}")

            analysis = analyze_image(
                pipeline,
                image_path=image_path,
                previous_image_path=previous_image_path,
                verbose=not args.quiet_preprocessing,
            )
            previous_image_path = image_path

            print(
                "Pipeline summary: "
                f"would_send={analysis['pipeline_would_send']} | "
                f"change={analysis['features']['change_pct']:.2f}% | "
                f"brightness={analysis['features']['brightness']:.2f} | "
                f"sharpness={analysis['features']['sharpness']:.2f}"
            )

            label = prompt_for_label()
            if label is None:
                print("Skipped dataset row for this image.\n")
                continue

            row = build_dataset_row(image_path, label, analysis)
            append_dataset_row(dataset_path, row)
            saved_rows += 1
            print(f"Saved row {saved_rows} with label='{label}'.\n")

    except KeyboardInterrupt:
        print("\nStopping collection.")

    print(f"\nFinished. Saved {saved_rows} labeled rows to {dataset_path}")
    print(f"To train all models on the Pi, run:\npython3 picam/train_models_offline.py {dataset_path}")


if __name__ == "__main__":
    main()
