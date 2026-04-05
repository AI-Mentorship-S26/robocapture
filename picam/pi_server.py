import asyncio
import websockets
import subprocess
import base64
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from image_preprocessing import ImagePreprocessingPipeline
from rl_models import run_random

PI_PORT = 8765
pipeline = ImagePreprocessingPipeline()
previous_image_path = None

async def handle_backend(websocket):
    global previous_image_path
    print("Backend connected!")
    async for message in websocket:
        print(f"Received: {message}")
        if message == "captureImage":
            # Step 1: Capture image
            capture_result = run_capture()

            if capture_result["type"] == "error":
                await websocket.send(json.dumps(capture_result))
                continue

            current_image_path = capture_result["image_path"]

            # Step 2: Run preprocessing pipeline
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

            # Step 3: Pass CNN embedding into RL model
            embedding = results['embedding']
            decision = run_random(embedding)
            print(f"RL decision: {decision}")

            if decision == 1:
                # Step 4: Send image to frontend
                with open(current_image_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                await websocket.send(json.dumps({
                    "type": "image",
                    "format": "image/jpeg",
                    "data": b64
                }))
            else:
                await websocket.send(json.dumps({
                    "type": "no_send",
                    "message": "RL model decided not to send image"
                }))

        elif message.startswith("reward") or message.startswith("punishment"):
            print(f"Received feedback: {message}")
            # TODO: pass into RL model update when ready


def run_capture():
    try:
        proc = subprocess.run(
            ["python3", "/home/mahd/Desktop/Robocapture/robocapture/picam/capture_once.py"],
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