import asyncio
import websockets
import subprocess
import base64
import json
import os

PI_PORT = 8765

async def handle_backend(websocket):
    print("Backend connected!")
    async for message in websocket:
        print(f"Received: {message}")
        if message == "captureImage":
            result = run_capture()
            await websocket.send(json.dumps(result))

def run_capture():
    try:
        proc = subprocess.run(
            ["python3", "/home/mahd/Desktop/Robocapture/robocapture/picam/capture_once.py"],
            capture_output=True, text=True
        )
        image_path = proc.stdout.strip()

        if proc.returncode == 0 and image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            return {"type": "image", "format": "image/jpeg", "data": b64}
        else:
            return {"type": "error", "message": proc.stderr or "Capture failed"}
    except Exception as e:
        return {"type": "error", "message": str(e)}

async def main():
    print(f"Pi WebSocket server starting on port {PI_PORT}...")
    async with websockets.serve(handle_backend, "0.0.0.0", PI_PORT):
        await asyncio.Future()  # run forever

asyncio.run(main())