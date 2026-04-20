# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

RoboCapture is a Raspberry Pi robot that autonomously explores its environment. It rotates, captures images at multiple headings, scores each direction using contrastive MobileNetV2 embeddings, moves toward the most visually interesting direction, and streams images to a web dashboard in real time.

The repo has two independent halves:

- `picam/` — Python code that runs on the Raspberry Pi
- `frontend/` — Next.js dashboard that runs on any machine with Node.js

**`motors/` and `picam/` cannot run on Windows** — they depend on `pigpio`/`picamzero` which are Linux/Pi-only.

---

## Commands

### Frontend (Next.js)

```bash
cd frontend
npm run dev       # dev server at localhost:3000
npm run build     # production build
npm run lint      # ESLint
```

### Pi-side (run on the Raspberry Pi)

```bash
sudo pigpiod                          # must run first — starts pigpio daemon
python3 picam/pi_server.py            # start autonomous loop + WebSocket server on port 8765
python3 picam/capture_once.py         # test camera capture only
python3 motors/motors2.py             # test motor movement
python3 motors/encodersFull.py        # test encoder readings
python3 picam/inspect_saved_model.py  # inspect a saved RL checkpoint
```

---

## Architecture

### Pi Side (`picam/`)

**`pi_server.py`** is the entry point on the Pi. It runs two concurrent asyncio tasks:

1. **Autonomous loop** — the robot's main behavior: scan 4 headings → score by contrastive embedding distance → rotate to best direction → drive forward 5 seconds streaming movement images → repeat
2. **WebSocket server** (port 8765) — debug/manual interface accepting commands from the frontend:
   - `"captureImage"` → capture, preprocess, run RL model, send back base64 JPEG or `no_send`
   - `"setModel:NAME"` → switch active RL model
   - `"reward:IMAGE_ID"` / `"punishment:IMAGE_ID"` → update the active RL model

The autonomous loop pushes three message types to the connected frontend: `scan_image` (at each heading during the scan), `direction_chosen` (with heading and scores dict), and `move_image` (every second during forward drive).

**`capture_once.py`** is called as a subprocess by `pi_server.py`. It uses `picamzero` to save a JPEG to `picam/captures/` and prints the path to stdout.

**`image_preprocessing.py`** runs a 4-stage pipeline on each captured image:

1. Resize to 224×224
2. Change detection (pixel diff vs. previous frame)
3. Low-level quality filters (brightness, sharpness via Laplacian variance, edge count via Canny, FFT frequency)
4. MobileNetV2 embedding (1280 floats)

The output is a **1287-float state vector**: `[change_pct, brightness, saturation, sharpness, edge_count, mean_freq, embedding_magnitude, *embedding_1280]`

**`rl_models.py`** is a thin dispatch layer. Each model has two functions: `run_X(image_id, state) → int` and `update_X(image_id, reward)`. Adding a new model requires adding both functions here and registering them in `MODEL_MAP` in `pi_server.py`.

### Model Object Pattern (`picam/model_objects/`)

Every model follows the same interface — use `sarsa_object.py` as the canonical reference:

```python
class XObject:
    def __init__(self):
        self.history = {}           # {image_id: (state, action)} — async reward bookkeeping
        self.checkpoint_path = model_file("name", ".ext")
        self.load()

    def choose_action(self, state: list) -> int: ...   # epsilon-greedy or model inference
    def record(self, image_id, state, action): ...     # store before reward arrives
    def update(self, image_id, reward): ...            # called when reward arrives from frontend
    def save(self): ...
    def load(self): ...

x_object = XObject()  # singleton imported by rl_models.py
```

Rewards arrive asynchronously from the frontend after the image is displayed to the user. Because `next_state` is never available at reward time, all models treat transitions as **terminal** (no future reward component — equivalent to a 1-step Monte Carlo target).

**`persistence.py`** provides two save/load pairs:

- `save_pickle` / `load_pickle` — for tabular models (SARSA, contextual bandits)
- `save_torch` / `load_torch` — for neural models (DQN, PPO, REINFORCE, AAC)

All checkpoints go to `picam/saved_models/` (created automatically).

### Motors (`motors/`)

**`motor_controller.py`** is the importable module used by `pi_server.py`. It exports `set_motors`, `stop`, `shutdown`, and the constants `TURN_SPEED=150`, `TURN_DURATION_90=0.9`, `FORWARD_SPEED=200`.

`motors.py` and `motors2.py` are standalone test scripts with their own main loops — do not import them.

GPIO pin assignments (BCM numbering — do not reuse these):

- Motors: AIN1=6, AIN2=5, PWMA=12, BIN1=16, BIN2=26, PWMB=13, STBY=25
- Left encoder: A=17, B=27
- Right encoder: A=22, B=23
- Free pins available for new sensors: GPIO 4, 18, 24

`encodersFull.py` uses quadrature decoding (4× resolution lookup table). Prefer it over `encoders.py` which only reads rising edges.

All pigpio code requires `sudo pigpiod` running first. Each file creates its own `pi = pigpio.pi()` instance — this is safe since they all connect to the same daemon, but do not import multiple motor files simultaneously.

### Frontend (`frontend/`)

Next.js 16 app with TypeScript, Tailwind v4, Supabase auth.

Pages:

- `app/page.tsx` — landing page
- `app/login/page.tsx` / `app/signup/page.tsx` — auth
- `app/dashboard/page.tsx` — main UI: connects to Pi WebSocket, live image view, gallery, reward history, logs, RL model selector

The dashboard receives pushed images from the autonomous loop (`scan_image`, `move_image`, `direction_chosen`) and can also send debug commands (`captureImage`, `reward:`, `punishment:`).

---

## Key Design Constraints

- **Async reward timing**: The reward message arrives from the frontend long after `run_X` returns. The `history` dict bridges this gap — `record()` saves `(state, action)` keyed by `image_id`, and `update()` retrieves and deletes it.
- **1287-float state vector**: Fixed across all models. Any new model must accept exactly this input shape.
- **No next_state available**: All current models use terminal-transition approximations. Do not add next-state logic without restructuring the reward pipeline.
- **Direction scoring**: The autonomous loop uses contrastive embedding distance — `score[i] = L2(embedding[i], mean of other embeddings)`. Highest score = most visually unique direction. This is computed in `pi_server.py`, not inside any model object.
- **Rotation tracking**: After a 4-heading scan, the robot is at 270°. Turns to reach `best_idx * 90°`: `(best_idx + 1) % 4` right turns.
- **CPU-bound pipeline in async context**: `pipeline.process_image` runs MobileNetV2 inference and must be dispatched via `loop.run_in_executor` to avoid blocking the asyncio event loop.
