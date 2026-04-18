import asyncio
import websockets
import subprocess
import base64
import json
import os
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))
from image_preprocessing import ImagePreprocessingPipeline
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
#for navigation
import threading
import robot_rl_nav

threading.Thread(target=robot_rl_nav.main, daemon=True).start()

PI_PORT = 8765
pipeline = ImagePreprocessingPipeline()
previous_image_path = None
current_model = "deep_contextual_bandit"  # default model

# Maps model name to its run and update functions
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
    global previous_image_path, current_model
    print("Backend connected!")
    async for message in websocket:
        print(f"Received: {message}")

        # Model switching
        if message.startswith("setModel:"):
            current_model = message.split(":")[1]
            robot_rl_nav.set_current_model(current_model)
            print(f"Switched to model: {current_model}")

        # Capture image
        elif message == "captureImage":
                # Check if robot is navigating
            if robot_rl_nav.is_navigating:
                await websocket.send(json.dumps({
                    "type": "no_send",
                    "message": "Robot is navigating — manual capture disabled"
                }))
                continue
            
            # Step 1: Generate image ID
            image_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

<<<<<<< Updated upstream
            # Step 2: Capture image
            capture_result = run_capture()
            if capture_result["type"] == "error":
                await websocket.send(json.dumps(capture_result))
=======
            elif message == "captureImage":
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
                    if not results["stage_0_5"]["has_significant_change"]:
                        reason = "Image too similar to previous frame"
                    elif not results["stage_1"]["passes"]:
                        reason = "Image quality too low (too dark or blurry)"
                    else:
                        reason = "Image rejected by preprocessing pipeline"
                    await websocket.send(json.dumps({"type": "no_send", "message": reason}))
                    continue

                state = [
                    results["stage_0_5"]["change_percentage"],
                    results["stage_1"]["brightness"],
                    results["stage_1"]["saturation"],
                    results["stage_1"]["sharpness"],
                    results["stage_1"]["edge_count"],
                    results["stage_1"]["mean_frequency"],
                    results["stage_2"]["embedding_magnitude"],
                    *results["embedding"],
                ]

                run_fn, _ = MODEL_MAP[current_model]
                decision = run_fn(image_id, state)
                logger.info("Model: %s | Decision: %d", current_model, decision)

                if decision == 1:
                    with open(current_image_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    await websocket.send(json.dumps({
                        "type": "image",
                        "format": "image/jpeg",
                        "data": b64,
                        "image_id": image_id,
                        "features": {
                            "change_pct":         results["stage_0_5"]["change_percentage"],
                            "brightness":         results["stage_1"]["brightness"],
                            "saturation":         results["stage_1"]["saturation"],
                            "sharpness":          results["stage_1"]["sharpness"],
                            "edge_count":         results["stage_1"]["edge_count"],
                            "mean_frequency":     results["stage_1"]["mean_frequency"],
                            "embedding_magnitude":results["stage_2"]["embedding_magnitude"],
                        },
                    }))
                else:
                    await websocket.send(json.dumps({
                        "type": "no_send",
                        "message": "RL model decided not to send image",
                    }))

            elif message.startswith("reward:") or message.startswith("punishment:"):
                parts = message.split(":")
                feedback_type = parts[0]
                image_id = parts[1]
                reward = 1 if feedback_type == "reward" else -1
                _, update_fn = MODEL_MAP[current_model]
                update_fn(image_id, reward)
                logger.info("Updated %s with reward %d for image %s", current_model, reward, image_id)

    finally:
        if active_websocket is websocket:
            active_websocket = None
        logger.info("Frontend disconnected.")


# ── Autonomous exploration loop ───────────────────────────────────────────────

async def autonomous_loop() -> None:
    """
    Main autonomous exploration loop. Runs as a background asyncio task.

    Each cycle:
      1. SCAN   — rotate 90° × 3 (visiting 4 headings), capture + preprocess at each
      2. SCORE  — rank directions by contrastive embedding distance:
                  score[i] = L2(embedding[i], mean of the other embeddings)
                  Highest score = most visually unique direction
      3. ROTATE — face the best direction (minimal right turns from current heading)
      4. MOVE   — drive forward FORWARD_DURATION seconds, streaming movement images

    Rotation tracking:
      After the scan the robot is at heading 270° (3 right turns from start).
      Turns to reach best_idx * 90°: (best_idx + 1) % 4 right turns.
    """
    if not MOTORS_AVAILABLE:
        logger.warning("Autonomous loop: motors unavailable — not starting.")
        return

    logger.info("Autonomous loop started.")
    scan_previous_path = None   # previous image path for change detection within a scan

    while True:
        ws = active_websocket   # snapshot — safe if client reconnects mid-cycle
        if ws is None:
            await asyncio.sleep(1.0)
            continue

        try:
            loop = asyncio.get_running_loop()

            # ── SCAN PHASE ────────────────────────────────────────────────────
            # Visit 4 headings (0°, 90°, 180°, 270°) by turning right before each.
            scan_embeddings: list[tuple[int, list | None]] = []

            for i in range(4):
                if i > 0:
                    set_motors(TURN_SPEED, -TURN_SPEED)
                    await asyncio.sleep(TURN_DURATION_90)
                    stop_motors()
                    await asyncio.sleep(0.2)   # settle before capture

                capture_result = await loop.run_in_executor(None, run_capture)
                if capture_result["type"] != "success":
                    scan_embeddings.append((i, None))
                    continue

                image_path = capture_result["image_path"]

                # Pipeline is CPU-bound (MobileNetV2) — run in thread pool
                should_send, results = await loop.run_in_executor(
                    None,
                    functools.partial(
                        pipeline.process_image, image_path, scan_previous_path, verbose=False
                    ),
                )
                scan_previous_path = image_path

                # Push scan image to frontend (non-fatal if client dropped)
                try:
                    with open(image_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    await ws.send(json.dumps({
                        "type": "scan_image",
                        "heading": i * 90,
                        "passes_filter": should_send,
                        "format": "image/jpeg",
                        "data": b64,
                    }))
                except Exception:
                    pass

                embedding = results.get("embedding") if should_send else None
                scan_embeddings.append((i, embedding))

            # ── SCORE PHASE ───────────────────────────────────────────────────
            # Robot is now at heading 270° (3 right turns completed).
            valid = [(i, emb) for i, emb in scan_embeddings if emb is not None]

            if len(valid) < 2:
                logger.warning("Fewer than 2 valid scan directions — retrying after pause.")
                stop_motors()
                await asyncio.sleep(2.0)
>>>>>>> Stashed changes
                continue

            current_image_path = capture_result["image_path"]

<<<<<<< Updated upstream
            # Step 3: Run preprocessing pipeline
            should_send, results = pipeline.process_image(
                current_image_path,
                previous_image_path,
                verbose=True
            )
            previous_image_path = current_image_path
=======
            score_values = list(scores.values())
            score_range = max(score_values) - min(score_values)
            max_score = max(score_values)
            all_similar = max_score == 0 or score_range < SIMILARITY_THRESHOLD * max_score
>>>>>>> Stashed changes

            if not should_send:
                if not results['stage_0_5']['has_significant_change']:
                    reason = "Image too similar to previous frame"
                elif not results['stage_1']['passes']:
                    reason = "Image quality too low (too dark or blurry)"
                else:
                    reason = "Image rejected by preprocessing pipeline"

                await websocket.send(json.dumps({
                    "type": "no_send",
                    "message": reason
                }))
                continue

            # Step 4: Build state
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

            # Step 5: Run RL model
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
                    "image_id": image_id
                }))
            else:
                await websocket.send(json.dumps({
                    "type": "no_send",
                    "message": "RL model decided not to send image"
                }))

        # Reward/punishment from backend
        elif message.startswith("reward:") or message.startswith("punishment:"):
            parts = message.split(":")
            feedback_type = parts[0]   # "reward" or "punishment"
            image_id = parts[1]        # the image ID

            reward = 1 if feedback_type == "reward" else -1

            _, update_fn = MODEL_MAP[current_model]
            update_fn(image_id, reward)
            print(f"Updated {current_model} with reward {reward} for image {image_id}")


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
<<<<<<< Updated upstream
    print(f"Pi WebSocket server starting on port {PI_PORT}...")
    async with websockets.serve(handle_backend, "0.0.0.0", PI_PORT):
        await asyncio.Future()
=======
    loop_task = asyncio.create_task(autonomous_loop())
    logger.info("Pi WebSocket server starting on port %d...", PI_PORT)
    try:
        async with websockets.serve(handle_backend, "0.0.0.0", PI_PORT):
            await asyncio.Future()
    finally:
        loop_task.cancel()
        try:
            await loop_task
        except asyncio.CancelledError:
            pass
        if MOTORS_AVAILABLE:
            motor_shutdown()

>>>>>>> Stashed changes

asyncio.run(main())
