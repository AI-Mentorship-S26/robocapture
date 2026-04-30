import asyncio
import websockets
import subprocess
import base64
import json
import os
import sys
import csv
import time
from pathlib import Path
from datetime import datetime

_t0 = time.time()
def _log(msg: str):
    print(f"[{time.time() - _t0:6.1f}s] {msg}", flush=True)

_log("Starting — loading dataset helpers...")
sys.path.insert(0, str(Path(__file__).parent))
from collect_labeled_dataset import (
    DEFAULT_DATASET,
    analyze_image,
    append_dataset_row,
    build_dataset_row,
    ensure_dataset_file,
)
_log("Dataset helpers loaded — loading RL models (may take 10-30s)...")
from rl_models import (
    run_random, update_random,
    run_deep_contextual_bandit, update_deep_contextual_bandit,
    run_contextual_bandit, update_contextual_bandit,
    run_sarsa, update_sarsa,
    run_dqn, update_dqn,
    run_ppo, update_ppo,
    run_reinforce, update_reinforce,
    run_aac, update_aac,
    run_tiny_sac, update_tiny_sac
)
_log("RL models loaded — loading robot_rl_nav + MobileNetV2 (may take 20-40s)...")

#for navigation
import threading
import robot_rl_nav

def nav_image_callback(image_id, b64):
    if nav_image_queue is not None:
        nav_image_queue.put_nowait((image_id, b64))

robot_rl_nav.set_send_callback(nav_image_callback)

_log("robot_rl_nav loaded — starting nav thread...")

def _run_nav():
    _log("Nav thread started — beginning navigation loop")
    try:
        robot_rl_nav.main()
    except Exception as e:
        print(f"\n[NAV THREAD CRASHED] {e}", flush=True)
        import traceback; traceback.print_exc()

PI_PORT = 8765
pipeline = robot_rl_nav.pipeline  # reuse already-loaded MobileNetV2 instance
nav_image_queue: asyncio.Queue = None  # initialised inside asyncio.run() to bind to the correct event loop
previous_image_path = None
current_model = "deep_contextual_bandit"
dataset_path = DEFAULT_DATASET.resolve()
ensure_dataset_file(dataset_path)
pending_dataset_samples = {}

def count_dataset_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))

dataset_saved_count = count_dataset_rows(dataset_path)

MODEL_MAP = {
    "random":   (run_random,    update_random),
    "deep_contextual_bandit": (run_deep_contextual_bandit, update_deep_contextual_bandit),
    "contextual_bandit": (run_contextual_bandit, update_contextual_bandit),
    "sarsa":    (run_sarsa,     update_sarsa),
    "dqn":      (run_dqn,       update_dqn),
    "ppo":      (run_ppo,       update_ppo),
    "reinforce":(run_reinforce, update_reinforce),
    "aac":      (run_aac,       update_aac),
    "tiny_sac": (run_tiny_sac,  update_tiny_sac),
}

async def handle_backend(websocket):
    global previous_image_path, current_model, dataset_saved_count
    print("Backend connected!")

    async def forward_nav_images():
        while True:
            image_id, b64 = await nav_image_queue.get()
            await websocket.send(json.dumps({
                "type": "image",
                "format": "image/jpeg",
                "data": b64,
                "image_id": image_id
            }))

    nav_task = asyncio.create_task(forward_nav_images())

    try:
        async for message in websocket:
            print(f"Received: {message}")

            if message.startswith("setModel:"):
                current_model = message.split(":")[1]
                robot_rl_nav.set_current_model(current_model)
                print(f"Switched to model: {current_model}")

            elif message == "startNavigation":
                if not robot_rl_nav.is_navigating:
                    threading.Thread(target=robot_rl_nav.main, daemon=True).start()
                    print("Navigation started!")
            elif message == "stopNavigation":
                robot_rl_nav.stop_navigation()
                print("Navigation stopped!")
            elif message == "captureImage":
                if robot_rl_nav.is_navigating:
                    await websocket.send(json.dumps({
                        "type": "no_send",
                        "message": "Robot is navigating — manual capture disabled"
                    }))
                    continue

                image_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                capture_result = run_capture()
                if capture_result["type"] == "error":
                    await websocket.send(json.dumps(capture_result))
                    continue

                current_image_path = capture_result["image_path"]
                should_send, results = pipeline.process_image(
                    current_image_path, previous_image_path, verbose=True
                )
                previous_image_path = current_image_path

                if not should_send:
                    if not results['stage_0_5']['has_significant_change']:
                        reason = "Image too similar to previous frame"
                    elif not results['stage_1']['passes']:
                        reason = "Image quality too low (too dark or blurry)"
                    else:
                        reason = "Image rejected by preprocessing pipeline"
                    await websocket.send(json.dumps({"type": "no_send", "message": reason}))
                    continue

                state = [
                    results['stage_0_5']['change_percentage'],
                    results['stage_1']['brightness'],
                    results['stage_1']['saturation'],
                    results['stage_1']['sharpness'],
                    results['stage_1']['edge_count'],
                    results['stage_1']['mean_frequency'],
                    results['stage_2']['embedding_magnitude'],
                    *results['embedding']
                ]
                state = [float(x) for x in state]

                run_fn, _ = MODEL_MAP[current_model]
                decision = run_fn(image_id, state)
                print(f"Model: {current_model} | Decision: {decision}")

                if decision == 1:
                    with open(current_image_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    await websocket.send(json.dumps({
                        "type": "image",
                        "format": "image/jpeg",
                        "data": b64,
                        "image_id": image_id,
                        "features": {
                            "change_pct":          float(results['stage_0_5']['change_percentage']),
                            "brightness":          float(results['stage_1']['brightness']),
                            "saturation":          float(results['stage_1']['saturation']),
                            "sharpness":           float(results['stage_1']['sharpness']),
                            "edge_count":          float(results['stage_1']['edge_count']),
                            "mean_frequency":      float(results['stage_1']['mean_frequency']),
                            "embedding_magnitude": float(results['stage_2']['embedding_magnitude']),
                        },
                        "state": state,
                    }))
                else:
                    await websocket.send(json.dumps({
                        "type": "no_send",
                        "message": "RL model decided not to send image"
                    }))

            elif message == "captureDatasetImage":
                image_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                captured_at = datetime.now().isoformat(timespec="seconds")
                capture_result = run_capture()
                if capture_result["type"] == "error":
                    await websocket.send(json.dumps(capture_result))
                    continue

                current_image_path = capture_result["image_path"]
                try:
                    analysis = analyze_image(
                        pipeline,
                        image_path=Path(current_image_path),
                        previous_image_path=Path(previous_image_path) if previous_image_path else None,
                        verbose=True,
                    )
                except Exception as e:
                    await websocket.send(json.dumps({"type": "error", "message": f"Dataset capture preprocessing failed: {e}"}))
                    continue

                previous_image_path = current_image_path
                pending_dataset_samples[image_id] = {
                    "image_path": current_image_path,
                    "captured_at": captured_at,
                    "analysis": analysis,
                }

                with open(current_image_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")

                await websocket.send(json.dumps({
                    "type": "image",
                    "format": "image/jpeg",
                    "data": b64,
                    "image_id": image_id,
                    "features": analysis["features"],
                    "state": analysis["state"],
                    "capture_mode": "dataset",
                    "pipeline_would_send": analysis["pipeline_would_send"],
                    "has_significant_change": analysis["has_significant_change"],
                    "stage1_passes": analysis["stage1_passes"],
                    "stage2_passes": analysis["stage2_passes"],
                }))

            elif message.startswith("reward:") or message.startswith("punishment:"):
                parts = message.split(":")
                feedback_type = parts[0]
                image_id = parts[1]
                reward = 1 if feedback_type == "reward" else -1
                _, update_fn = MODEL_MAP[current_model]
                update_fn(image_id, reward)
                print(f"Updated {current_model} with reward {reward} for image {image_id}")

            elif message.startswith("datasetLabel:"):
                parts = message.split(":", 2)
                if len(parts) != 3:
                    await websocket.send(json.dumps({"type": "error", "message": "Invalid datasetLabel message format"}))
                    continue
                _, image_id, label = parts
                if label not in {"reward", "punishment"}:
                    await websocket.send(json.dumps({"type": "error", "message": f"Invalid dataset label: {label}"}))
                    continue
                sample = pending_dataset_samples.pop(image_id, None)
                if sample is None:
                    await websocket.send(json.dumps({"type": "error", "message": f"No pending dataset sample found for image_id {image_id}"}))
                    continue
                row = build_dataset_row(
                    image_path=Path(sample["image_path"]),
                    label=label,
                    analysis=sample["analysis"],
                    image_id=image_id,
                    captured_at=sample["captured_at"],
                )
                append_dataset_row(dataset_path, row)
                dataset_saved_count += 1
                await websocket.send(json.dumps({
                    "type": "dataset_saved",
                    "image_id": image_id,
                    "label": label,
                    "saved_count": dataset_saved_count,
                    "dataset_path": str(dataset_path),
                }))

            elif message.startswith("datasetSkip:"):
                parts = message.split(":", 1)
                if len(parts) != 2:
                    await websocket.send(json.dumps({"type": "error", "message": "Invalid datasetSkip message format"}))
                    continue
                _, image_id = parts
                pending_dataset_samples.pop(image_id, None)
                await websocket.send(json.dumps({
                    "type": "dataset_skipped",
                    "image_id": image_id,
                    "saved_count": dataset_saved_count,
                }))

    finally:
        nav_task.cancel()


def run_capture():
    try:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        CAPTURE_SCRIPT = os.path.join(SCRIPT_DIR, "capture_once.py")
        proc = subprocess.run(
            ["python3", CAPTURE_SCRIPT],
            capture_output=True, text=True
        )
        image_path = proc.stdout.strip()

        if proc.returncode == 0 and image_path and os.path.exists(image_path):
            return {"type": "success", "image_path": image_path}
        else:
            return {"type": "error", "message": proc.stderr or "Capture failed"}
    except Exception as e:
        return {"type": "error", "message": str(e)}


async def main():
    global nav_image_queue
    nav_image_queue = asyncio.Queue()  # created inside the running event loop
    _log(f"WebSocket server ready on port {PI_PORT} — waiting for frontend connection...")
    async with websockets.serve(handle_backend, "0.0.0.0", PI_PORT):
        await asyncio.Future()

asyncio.run(main())