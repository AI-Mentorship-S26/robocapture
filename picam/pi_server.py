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
            # Step 1: Generate image ID
            image_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

            # Step 2: Capture image
            capture_result = run_capture()
            if capture_result["type"] == "error":
                await websocket.send(json.dumps(capture_result))
                continue

            current_image_path = capture_result["image_path"]

            # Step 3: Run preprocessing pipeline
            should_send, results = pipeline.process_image(
                current_image_path,
                previous_image_path,
                verbose=True
            )
            previous_image_path = current_image_path

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
                    "image_id": image_id,
                    "features": {
                        "change_pct":          results['stage_0_5']['change_percentage'],
                        "brightness":          results['stage_1']['brightness'],
                        "saturation":          results['stage_1']['saturation'],
                        "sharpness":           results['stage_1']['sharpness'],
                        "edge_count":          results['stage_1']['edge_count'],
                        "mean_frequency":      results['stage_1']['mean_frequency'],
                        "embedding_magnitude": results['stage_2']['embedding_magnitude'],
                    },
                    "state": state,
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
    print(f"Pi WebSocket server starting on port {PI_PORT}...")
    async with websockets.serve(handle_backend, "0.0.0.0", PI_PORT):
        await asyncio.Future()

asyncio.run(main())
